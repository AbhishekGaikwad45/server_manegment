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

print("\nDeleting all servers...\n")

# Child tables first
c.execute("DELETE FROM alerts")
print("✓ alerts deleted")

c.execute("DELETE FROM ping_history")
print("✓ ping_history deleted")

# Main table
c.execute("DELETE FROM servers")
print("✓ servers deleted")

# Reset auto increment id
c.execute("ALTER SEQUENCE servers_id_seq RESTART WITH 1")
print("✓ server id reset")

c.close()
conn.close()

print("\nDone! All servers removed.\n")