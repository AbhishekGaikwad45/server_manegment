import pg8000
import os
from dotenv import load_dotenv

load_dotenv('.env.local')

DB_HOST     = os.environ.get('DB_HOST',     'localhost')
DB_PORT     = int(os.environ.get('DB_PORT', '5432'))
DB_NAME     = os.environ.get('DB_NAME',     'server_monitor')
DB_USER     = os.environ.get('DB_USER',     'postgres')
DB_PASSWORD = os.environ.get('DB_PASSWORD', 'root')

def get_db():
    conn = pg8000.connect(
        host=DB_HOST, port=DB_PORT,
        database=DB_NAME, user=DB_USER, password=DB_PASSWORD
    )
    conn.autocommit = True
    return conn

def _fetchall(c):
    cols = [d[0] for d in c.description]
    return [dict(zip(cols, row)) for row in c.fetchall()]

def _fetchone(c):
    cols = [d[0] for d in c.description]
    row  = c.fetchone()
    return dict(zip(cols, row)) if row else None

def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS servers (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            ip TEXT NOT NULL,
            port INTEGER DEFAULT 22,
            parent_id INTEGER REFERENCES servers(id) ON DELETE SET NULL,
            ssh_user TEXT,
            ssh_password TEXT,
            restart_command TEXT DEFAULT 'sudo systemctl restart nginx',
            status TEXT DEFAULT 'unknown',
            ping_ms INTEGER,
            last_checked TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS alerts (
            id SERIAL PRIMARY KEY,
            server_id INTEGER REFERENCES servers(id) ON DELETE CASCADE,
            message TEXT NOT NULL,
            severity TEXT DEFAULT 'critical',
            acknowledged INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS ping_history (
            id SERIAL PRIMARY KEY,
            server_id INTEGER REFERENCES servers(id) ON DELETE CASCADE,
            status TEXT,
            ping_ms INTEGER,
            checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    from werkzeug.security import generate_password_hash
    try:
        c.execute("INSERT INTO users (username, password) VALUES (%s, %s)",
                  ('admin', generate_password_hash('admin123')))
    except Exception:
        pass

    c.close()
    conn.close()

# ── Server CRUD ──────────────────────────────────────────────
def get_all_servers():
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        SELECT s.*, p.name as parent_name
        FROM servers s
        LEFT JOIN servers p ON s.parent_id = p.id
        ORDER BY s.parent_id NULLS FIRST, s.name
    ''')
    result = _fetchall(c)
    c.close(); conn.close()
    return result

def get_server(server_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM servers WHERE id=%s', (server_id,))
    result = _fetchone(c)
    c.close(); conn.close()
    return result

def add_server(name, ip, port, parent_id, ssh_user, ssh_password, restart_command):
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        INSERT INTO servers (name, ip, port, parent_id, ssh_user, ssh_password, restart_command)
        VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id
    ''', (name, ip, int(port or 22), parent_id or None,
          ssh_user, ssh_password, restart_command))
    sid = c.fetchone()[0]
    c.close(); conn.close()
    return sid

def delete_server(server_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('DELETE FROM servers WHERE id=%s', (server_id,))
    c.close(); conn.close()

def update_server_status(server_id, status, ping_ms):
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        UPDATE servers SET status=%s, ping_ms=%s, last_checked=CURRENT_TIMESTAMP
        WHERE id=%s
    ''', (status, ping_ms, server_id))
    c.execute('''
        INSERT INTO ping_history (server_id, status, ping_ms)
        VALUES (%s,%s,%s)
    ''', (server_id, status, ping_ms))
    c.close(); conn.close()

# ── Alerts ───────────────────────────────────────────────────
def add_alert(server_id, message, severity='critical'):
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        INSERT INTO alerts (server_id, message, severity)
        VALUES (%s,%s,%s)
    ''', (server_id, message, severity))
    c.close(); conn.close()

def get_active_alerts():
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        SELECT a.*, s.name as server_name, s.ip
        FROM alerts a JOIN servers s ON a.server_id=s.id
        WHERE a.acknowledged=0
        ORDER BY a.created_at DESC
    ''')
    result = _fetchall(c)
    c.close(); conn.close()
    return result

def acknowledge_alert(alert_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('UPDATE alerts SET acknowledged=1 WHERE id=%s', (alert_id,))
    c.close(); conn.close()

def get_ping_history(server_id, limit=50):
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        SELECT * FROM ping_history WHERE server_id=%s
        ORDER BY checked_at DESC LIMIT %s
    ''', (server_id, limit))
    result = _fetchall(c)
    c.close(); conn.close()
    return result

def get_stats():
    conn = get_db()
    c = conn.cursor()
    def count(q):
        c.execute(q); return c.fetchone()[0]
    result = {
        'total':  count('SELECT COUNT(*) FROM servers'),
        'up':     count("SELECT COUNT(*) FROM servers WHERE status='up'"),
        'down':   count("SELECT COUNT(*) FROM servers WHERE status='down'"),
        'warning':count("SELECT COUNT(*) FROM servers WHERE status='warning'"),
        'alerts': count("SELECT COUNT(*) FROM alerts WHERE acknowledged=0"),
    }
    c.close(); conn.close()
    return result