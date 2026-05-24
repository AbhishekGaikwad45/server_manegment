# ServerWatch — Server Monitor Dashboard

Python Flask dashboard for monitoring 30+ servers.

## Features
- **Real-time monitoring** — All servers pinged every 30 seconds
- **Topology Graph** — Visual graph showing server parent/child relationships
- **Auto Alerts** — Immediate alarm on dashboard when server goes down
- **Ping** — Manual ping functionality
- **SSH Restart** — Restart servers via SSH
- **History** — Ping history for each server
- **Search** — Search by server name or IP
- **Login** — Secure sign in

## Setup

### 1. Install Python (3.8+)

### 2. Install dependencies
```bash
cd server_monitor
pip install -r requirements.txt
```

### 3. Run the app
```bash
python app.py
```

### 4. Open in browser
```
http://localhost:5000
```

### 5. Login
- Username: `admin`
- Password: `admin123`

---

## Adding Servers

Click "Add Server" button on dashboard:
- **Server Name** — e.g. DB-Server-01
- **IP Address** — Server IP
- **SSH Port** — Default 22
- **Parent Server** — Select parent from dropdown (if it's a child)
- **SSH Username/Password** — For restart (optional)
- **Restart Command** — e.g. `sudo systemctl restart nginx`

---

## Color Codes

| Color | Meaning |
|-------|---------|
| 🟢 Green | Server Online (UP) |
| 🔴 Red | Server DOWN |
| 🟡 Yellow | Warning (High Latency > 200ms) |
| ⚫ Gray | Unknown / Not yet checked |

In topology graph, **red dashed line** means one of the servers in that link is down.

---

## File Structure

```
server_monitor/
├── app.py              ← Flask routes
├── models.py           ← Database (PostgreSQL)
├── monitor.py          ← Background ping + SSH restart
├── requirements.txt
├── .env.local          ← Database credentials
├── templates/
│   ├── login.html
│   ├── dashboard.html
│   └── add_server.html
└── static/
    ├── css/style.css
    └── js/
        ├── dashboard.js    ← Ping, restart, alerts, auto-refresh
        └── topology.js     ← Interactive topology graph
```

---

## For Production

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

Don't forget to change `app.secret_key` (in `app.py`).
