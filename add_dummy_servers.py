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

print("\n🚀 Creating LIVE Server Topology...\n")


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

    print(f"✅ 🌐 LIVE : {name} ({ip})")

    return sid


# ====================================================
# ROOT
# ====================================================

root = add_server(
    "Google-DNS",
    "8.8.8.8"
)


# ====================================================
# CLOUD BRANCH
# ====================================================

cloud_1 = add_server(
    "Cloudflare-DNS",
    "1.1.1.1",
    root
)

cloud_2 = add_server(
    "Quad9-DNS",
    "9.9.9.9",
    cloud_1
)

cloud_3 = add_server(
    "OpenDNS",
    "208.67.222.222",
    cloud_1
)


# ====================================================
# GOOGLE SERVICES
# ====================================================

google_1 = add_server(
    "Google-Web",
    "142.250.195.46",
    root
)

google_2 = add_server(
    "YouTube",
    "142.250.183.206",
    google_1
)

google_3 = add_server(
    "Gmail",
    "64.233.177.17",
    google_1
)


# ====================================================
# AMAZON AWS
# ====================================================

aws_1 = add_server(
    "AWS-Server-01",
    "52.95.110.1",
    root
)

aws_2 = add_server(
    "AWS-Server-02",
    "54.239.28.85",
    aws_1
)

aws_3 = add_server(
    "AWS-Server-03",
    "3.33.165.172",
    aws_1
)


# ====================================================
# MICROSOFT / AZURE
# ====================================================

azure_1 = add_server(
    "Azure-Gateway",
    "20.112.52.29",
    root
)

azure_2 = add_server(
    "Microsoft",
    "40.76.4.15",
    azure_1
)

azure_3 = add_server(
    "Bing",
    "204.79.197.200",
    azure_1
)


# ====================================================
# FINAL LEAF
# ====================================================

add_server(
    "Final-Live-Node",
    "151.101.1.69",
    azure_3
)

c.close()
conn.close()

print("\n🎉 DONE!")
print("🌐 ALL servers are LIVE")
print("\nDashboard:")
print("http://localhost:6000")