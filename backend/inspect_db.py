import sqlite3

conn = sqlite3.connect('test_v03.db')
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = [row[0] for row in cursor.fetchall()]

print("✓ Database tables created:")
for table in tables:
    print(f"  - {table}")
    cursor.execute(f"PRAGMA table_info({table})")
    columns = cursor.fetchall()
    for col in columns:
        print(f"      {col[1]}: {col[2]}")

conn.close()
