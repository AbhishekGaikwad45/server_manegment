import pg8000
import os
from dotenv import load_dotenv

load_dotenv('.env.local')

DB_HOST     = os.environ.get('DB_HOST', 'localhost')
DB_PORT     = int(os.environ.get('DB_PORT', '5432'))
DB_NAME     = os.environ.get('DB_NAME', 'server_monitor')
DB_USER     = os.environ.get('DB_USER', 'postgres')
DB_PASSWORD = os.environ.get('DB_PASSWORD', 'root')

conn = pg8000.connect(
    host=DB_HOST,
    port=DB_PORT,
    database=DB_NAME,
    user=DB_USER,
    password=DB_PASSWORD
)

conn.autocommit = True
c = conn.cursor()

print("\n🚀 Creating Custom Tree Topology...\n")

# ----------------------------------------------------
# HELPER
# ----------------------------------------------------
def add_server(
    name,
    ip,
    parent_id=None,
    port=22
):

    c.execute(
        """
        INSERT INTO servers
        (name, ip, port, parent_id, ssh_user, restart_command)
        VALUES (%s,%s,%s,%s,%s,%s)
        RETURNING id
        """,
        (
            name,
            ip,
            port,
            parent_id,
            'root',
            'sudo reboot'
        )
    )

    sid = c.fetchone()[0]

    typ = "🌐 LIVE" if not ip.startswith("192.168") else "🏠 OFFLINE"

    print(f"✅ {typ} : {name}")

    return sid


# ====================================================
# ROOT
# ====================================================

root = add_server(
    "Main-Core",
    "8.8.8.8"
)


# ====================================================
# LEFT BRANCH
# ====================================================

left_1 = add_server(
    "Left-Gateway",
    "192.168.1.1",
    root
)

left_2 = add_server(
    "Left-Node",
    "192.168.1.2",
    left_1
)

left_down_1 = add_server(
    "Left-Child-01",
    "192.168.1.10",
    left_1
)

left_down_2 = add_server(
    "Left-Child-02",
    "192.168.1.11",
    left_1
)


# ====================================================
# RIGHT BRANCH
# ====================================================

right_1 = add_server(
    "Right-Core",
    "1.1.1.1",
    root
)

right_2 = add_server(
    "Right-Hub",
    "192.168.2.1",
    right_1
)

right_3 = add_server(
    "Right-Edge",
    "192.168.2.2",
    right_2
)


# ====================================================
# RIGHT SIDE CHILDREN
# ====================================================

right_child_1 = add_server(
    "Right-Web",
    "142.250.195.46",
    right_2
)

right_child_2 = add_server(
    "Right-API",
    "192.168.2.20",
    right_2
)

right_child_3 = add_server(
    "Right-DB",
    "192.168.2.21",
    right_2
)

right_child_4 = add_server(
    "Right-Cache",
    "192.168.2.22",
    right_2
)


# ====================================================
# DEEP CHILDREN
# ====================================================

deep_1 = add_server(
    "Deep-Service-01",
    "192.168.3.1",
    right_child_2
)

deep_2 = add_server(
    "Deep-Service-02",
    "192.168.3.2",
    right_child_2
)

deep_3 = add_server(
    "Deep-Service-03",
    "9.9.9.9",
    right_child_2
)

deep_4 = add_server(
    "Deep-Service-04",
    "192.168.3.4",
    right_child_2
)


# ====================================================
# FINAL LEAF
# ====================================================

add_server(
    "Final-Leaf",
    "192.168.5.1",
    right_3
)

c.close()
conn.close()

print("\n🎉 DONE!")
print("🌐 LIVE servers = ONLINE")
print("🏠 192.168.x.x = OFFLINE")
print("\nDashboard:")
print("http://localhost:5000")