import socket
import time
import threading
import subprocess
import platform
from datetime import datetime

try:
    import paramiko
    PARAMIKO_OK = True
except ImportError:
    PARAMIKO_OK = False

from models import (get_all_servers, update_server_status,
                    add_alert, get_db)

# Track previous status to fire alerts only on change
_prev_status = {}
_lock = threading.Lock()


def ping_host(ip, timeout=2):

    try:

        is_windows = (
            platform.system().lower() == 'windows'
        )

        if is_windows:

            cmd = [
                'ping',
                '-n',
                '1',
                '-w',
                str(timeout * 1000),
                ip
            ]

        else:

            cmd = [
                'ping',
                '-c',
                '1',
                '-W',
                str(timeout),
                ip
            ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout + 2
        )

        output = result.stdout.lower()

        success = (
            result.returncode == 0
            or 'ttl=' in output
        )

        if not success:
            return 'down', None

        ping_ms = None

        # WINDOWS
        if 'time=' in output:

            try:

                if 'ms' in output:

                    part = output.split('time=')[1]

                    value = part.split('ms')[0]

                    value = value.replace('<', '').strip()

                    ping_ms = int(float(value))

            except:
                ping_ms = 1

        # LINUX
        elif 'time<' in output:

            ping_ms = 1

        if ping_ms is None:
            ping_ms = 0

        status = (
            'warning'
            if ping_ms > 200
            else 'up'
        )

        return status, ping_ms

    except Exception as e:

        print("PING ERROR:", e)

        return 'down', None

def tcp_check(ip, port=22, timeout=3):
    """Fallback TCP check when ICMP ping is blocked."""
    try:
        start = time.time()
        s = socket.create_connection((ip, port), timeout=timeout)
        ms = int((time.time() - start) * 1000)
        s.close()
        status = 'warning' if ms > 200 else 'up'
        return status, ms
    except Exception:
        return 'down', None


def check_server(server):
    """Ping a single server and update DB. Fire alert if status changed."""
    sid  = server['id']
    ip   = server['ip']
    port = server.get('port') or 22
    name = server['name']

    status, ping_ms = ping_host(ip)

    if status == 'down':
        status, ping_ms = tcp_check(ip, port)

    print(
        f"[CHECK] {name} | {ip} | {status} | {ping_ms}"
    )

    update_server_status(
        sid,
        status,
        ping_ms
    )

    with _lock:
        prev = _prev_status.get(sid)
        if prev != status:
            _prev_status[sid] = status
            if status == 'down' and prev is not None:
                add_alert(sid, f'{name} ({ip}) is DOWN', 'critical')
            elif status == 'warning' and prev == 'up':
                add_alert(sid, f'{name} ({ip}) high latency ({ping_ms}ms)', 'warning')
            elif status == 'up' and prev == 'down':
                add_alert(sid, f'{name} ({ip}) is back ONLINE', 'info')

    return status, ping_ms


def check_all_servers():
    """Called by scheduler every 30 seconds."""
    servers = get_all_servers()
    threads = []
    for srv in servers:
        t = threading.Thread(target=check_server, args=(srv,), daemon=True)
        threads.append(t)
        t.start()
    for t in threads:
        t.join(timeout=10)


# ── SSH Actions ──────────────────────────────────────────────
def ssh_ping(server):
    """Manual ping — returns (status, ping_ms)."""
    return check_server(server)


def ssh_restart(server):
    """SSH into server and run restart command. Returns (success, message)."""
    if not PARAMIKO_OK:
        return False, 'paramiko not installed. Run: pip install paramiko'

    ip       = server['ip']
    port     = server.get('port') or 22
    user     = server.get('ssh_user') or 'root'
    password = server.get('ssh_password') or ''
    command  = server.get('restart_command') or 'sudo systemctl restart nginx'

    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(ip, port=int(port), username=user,
                       password=password, timeout=10)
        stdin, stdout, stderr = client.exec_command(command, timeout=30)
        out = stdout.read().decode('utf-8', errors='replace').strip()
        err = stderr.read().decode('utf-8', errors='replace').strip()
        client.close()
        if err and 'warning' not in err.lower():
            return False, f'Error: {err}'
        return True, f'Restart command sent. Output: {out or "OK"}'
    except paramiko.AuthenticationException:
        return False, 'SSH authentication failed. Check username/password.'
    except Exception as e:
        return False, f'SSH error: {str(e)}'
