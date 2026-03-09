import sqlite3

conn = sqlite3.connect("pii_sentinel.db")
cursor = conn.cursor()

count = cursor.execute("SELECT COUNT(*) FROM scan_results").fetchone()[0]
print("scan_results row count:", count)

rows = cursor.execute("SELECT * FROM scan_results LIMIT 5").fetchall()
print("sample rows:", rows)

conn.close()