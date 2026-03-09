import os
import sqlite3

db_path = os.getenv("SQLITE_DB_PATH", "./pii_sentinel.db")
print("DB:", db_path)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Show tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
tables = cursor.fetchall()

print("\nTables and Columns:\n")

for t in tables:
    table_name = t[0]
    print(f"Table: {table_name}")

    cursor.execute(f"PRAGMA table_info({table_name});")
    columns = cursor.fetchall()

    for column in columns:
        column_name = column[1]
        column_type = column[2]
        print(f"   - {column_name} ({column_type})")
    print()

# Show users separately
rows = cursor.execute("SELECT id, email FROM users LIMIT 10").fetchall()
print("Users:")
print(rows)

conn.close()