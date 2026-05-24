from flask import Flask, render_template, request, redirect, url_for, jsonify, session, flash
from werkzeug.security import check_password_hash, generate_password_hash
from apscheduler.schedulers.background import BackgroundScheduler
from functools import wraps
from dotenv import load_dotenv
import models
import monitor
import os

load_dotenv('.env.local')

app = Flask(__name__)
app.secret_key = 'serverwatch-secret-key-change-in-production'

models.init_db()

scheduler = BackgroundScheduler()
scheduler.add_job(monitor.check_all_servers, 'interval', seconds=30, id='ping_all')
scheduler.start()

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        # pg8000 ला cursor लागतो — conn.execute नाही
        conn = models.get_db()
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE username=%s', (username,))
        cols = [d[0] for d in c.description]
        row  = c.fetchone()
        c.close()
        conn.close()
        user = dict(zip(cols, row)) if row else None
        if user and check_password_hash(user['password'], password):
            session['user'] = username
            return redirect(url_for('dashboard'))
        flash('Invalid username or password')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def dashboard():
    servers = models.get_all_servers()
    alerts  = models.get_active_alerts()
    stats   = models.get_stats()
    parents = [s for s in servers if s['parent_id'] is None]
    return render_template('dashboard.html',
                           servers=servers,
                           alerts=alerts,
                           stats=stats,
                           parents=parents)

@app.route('/api/status')
@login_required
def api_status():
    return jsonify({
        'servers': models.get_all_servers(),
        'alerts':  models.get_active_alerts(),
        'stats':   models.get_stats()
    })

@app.route('/servers/add', methods=['GET', 'POST'])
@login_required
def add_server():
    parents = [s for s in models.get_all_servers() if s['parent_id'] is None]
    if request.method == 'POST':
        models.add_server(
            name            = request.form['name'],
            ip              = request.form['ip'],
            port            = request.form.get('port', 22),
            parent_id       = request.form.get('parent_id') or None,
            ssh_user        = request.form.get('ssh_user', ''),
            ssh_password    = request.form.get('ssh_password', ''),
            restart_command = request.form.get('restart_command', 'sudo systemctl restart nginx')
        )
        flash('Server added successfully!')
        return redirect(url_for('dashboard'))
    return render_template('add_server.html', parents=parents)

@app.route('/servers/delete/<int:server_id>', methods=['POST'])
@login_required
def delete_server(server_id):
    models.delete_server(server_id)
    flash('Server deleted.')
    return redirect(url_for('dashboard'))

@app.route('/api/ping/<int:server_id>', methods=['POST'])
@login_required
def ping_server(server_id):
    srv = models.get_server(server_id)
    if not srv:
        return jsonify({'error': 'Server not found'}), 404
    status, ping_ms = monitor.ssh_ping(srv)
    return jsonify({'status': status, 'ping_ms': ping_ms, 'server': srv['name']})

@app.route('/api/restart/<int:server_id>', methods=['POST'])
@login_required
def restart_server(server_id):
    srv = models.get_server(server_id)
    if not srv:
        return jsonify({'error': 'Server not found'}), 404
    success, message = monitor.ssh_restart(srv)
    return jsonify({'success': success, 'message': message})

@app.route('/api/alerts/ack/<int:alert_id>', methods=['POST'])
@login_required
def ack_alert(alert_id):
    models.acknowledge_alert(alert_id)
    return jsonify({'ok': True})

@app.route('/api/history/<int:server_id>')
@login_required
def server_history(server_id):
    history = models.get_ping_history(server_id, limit=60)
    return jsonify(history)



@app.route('/api/delete-server/<int:sid>', methods=['POST'])
@login_required
def delete_server_api(sid):

    conn = models.get_db()

    c = conn.cursor()

    c.execute(
        "DELETE FROM servers WHERE id=%s",
        (sid,)
    )

    conn.commit()

    c.close()
    conn.close()

    return jsonify({
        "success": True,
        "message": "Server deleted successfully"
    })
    
    

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

