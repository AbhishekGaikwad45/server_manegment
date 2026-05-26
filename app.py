from flask import Flask, render_template, request, redirect, url_for, jsonify, session, flash
from werkzeug.security import check_password_hash, generate_password_hash
from apscheduler.schedulers.background import BackgroundScheduler
from functools import wraps
from dotenv import load_dotenv
import models
import monitor
import os
import pandas as pd
from datetime import datetime, timedelta
from models import get_all_servers, add_server
from io import BytesIO
from flask import send_file


load_dotenv('.env.local')

app = Flask(__name__)
app.secret_key = os.environ.get(
    'SECRET_KEY',
    'dev-secret'
)
models.init_db()
print("RUNNING THIS FILE")
print(__file__)
scheduler = BackgroundScheduler()
scheduler.add_job(monitor.check_all_servers, 'interval', seconds=30, id='ping_all')
if not scheduler.running:
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
def add_server_route():

    if request.method == 'POST':

        add_server(
            request.form['name'],
            request.form['ip'],
            request.form.get('port') or 22,
            request.form.get('parent_id') or None,
            request.form.get('ssh_user'),
            request.form.get('ssh_password'),
            request.form.get('restart_command')
        )

        return redirect('/')

    parents = models.get_all_servers()

    return render_template(
        'add_server.html',
        parents=parents
    )
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

    models.update_server_status(
        server_id,
        status,
        ping_ms
    )

    return jsonify({
        'status': status,
        'ping_ms': ping_ms,
        'server': srv['name']
    })

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
    
@app.route('/servers/edit/<int:server_id>', methods=['GET', 'POST'])
@login_required
def edit_server(server_id):

    server = models.get_server(server_id)

    if not server:
        flash('Server not found')
        return redirect(url_for('dashboard'))

    parents = [
        s for s in models.get_all_servers()
        if s['id'] != server_id
    ]

    if request.method == 'POST':

        conn = models.get_db()
        c = conn.cursor()

        c.execute("""
            UPDATE servers
            SET
                name=%s,
                ip=%s,
                port=%s,
                parent_id=%s,
                ssh_user=%s,
                ssh_password=%s,
                restart_command=%s
            WHERE id=%s
        """, (
            request.form['name'],
            request.form['ip'],
            request.form.get('port', 22),
            request.form.get('parent_id') or None,
            request.form.get('ssh_user', ''),
            request.form.get('ssh_password', ''),
            request.form.get(
                'restart_command',
                'sudo systemctl restart nginx'
            ),
            server_id
        ))

        conn.commit()

        c.close()
        conn.close()

        flash('Server updated successfully')

        return redirect(url_for('dashboard'))

    return render_template(
        'edit_server.html',
        server=server,
        parents=parents
    )  
    
@app.route('/reports')
@login_required
def reports_page():

    return render_template(
        'reports.html'
    )
    
@app.route('/api/report-preview')
@login_required
def report_preview():

    from_date = datetime.strptime(
        request.args.get('from'),
        '%Y-%m-%dT%H:%M'
    )

    to_date = datetime.strptime(
        request.args.get('to'),
        '%Y-%m-%dT%H:%M'
    )
    to_date = to_date + timedelta(minutes=1)
    conn = models.get_db()

    c = conn.cursor()

    c.execute("""

        SELECT
            s.name,
            s.ip,
            s.status,
            s.ping_ms,
            s.last_checked,
            p.name AS parent_name

        FROM servers s

        LEFT JOIN servers p
            ON s.parent_id = p.id

        WHERE s.last_checked
        BETWEEN %s AND %s

        ORDER BY s.last_checked DESC

    """, (from_date, to_date))

    cols = [d[0] for d in c.description]

    rows = c.fetchall()

    c.close()

    conn.close()

    data = []

    for row in rows:

        r = dict(zip(cols, row))

        data.append({

            'name':
                r['name'],

            'ip':
                r['ip'],

            'status':
                (
                    'Online'
                    if r['status'] == 'up'
                    else 'Offline'
                    if r['status'] == 'down'
                    else 'Warning'
                    if r['status'] == 'warning'
                    else 'Unknown'
                ),

            'ping_ms':
                r['ping_ms'],

            'parent_name':
                r['parent_name'] or '-',

            'last_checked':
                r['last_checked'].strftime(
                    '%d-%m-%Y %H:%M'
                )
                if r['last_checked']
                else '-'
        })

    return jsonify(data)

@app.route('/export/report')
@login_required
def export_report():

    from_date = datetime.strptime(
        request.args.get('from'),
        '%Y-%m-%dT%H:%M'
    )

    to_date = datetime.strptime(
        request.args.get('to'),
        '%Y-%m-%dT%H:%M'
    )

    to_date = to_date + timedelta(minutes=1)

    conn = models.get_db()

    c = conn.cursor()

    c.execute("""

        SELECT
            s.name,
            s.ip,
            s.status,
            s.ping_ms,
            s.last_checked,
            p.name AS parent_name

        FROM servers s

        LEFT JOIN servers p
            ON s.parent_id = p.id

        WHERE s.last_checked
        BETWEEN %s AND %s

        ORDER BY s.last_checked DESC

    """, (from_date, to_date))

    cols = [d[0] for d in c.description]

    rows = c.fetchall()

    c.close()

    conn.close()

    data = []

    for row in rows:

        r = dict(zip(cols, row))

        data.append({

            'Server Name':
                r['name'],

            'IP Address':
                r['ip'],

            'Status':
                (
                    'Online'
                    if r['status'] == 'up'
                    else 'Offline'
                    if r['status'] == 'down'
                    else 'Warning'
                    if r['status'] == 'warning'
                    else 'Unknown'
                ),

            'Ping (ms)':
                r['ping_ms'],

            'Parent Server':
                r['parent_name'] or '-',

            'Last Checked':
                r['last_checked'].strftime(
                    '%d-%m-%Y %H:%M'
                )
                if r['last_checked']
                else '-'
        })
        print(data)

    df = pd.DataFrame(data)

    output = BytesIO()

    with pd.ExcelWriter(
        output,
        engine='openpyxl'
    ) as writer:

        df.to_excel(
            writer,
            index=False,
            sheet_name='Server Report'
        )

    output.seek(0)

    return send_file(

        output,

        as_attachment=True,

        download_name='server_report.xlsx',

        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )        

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)

