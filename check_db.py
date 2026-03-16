import sqlite3

conn = sqlite3.connect('studybuddy.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print("\n=== USERS ===")
cursor.execute('SELECT * FROM users')
for row in cursor.fetchall():
    print(dict(row))
    print("\n")

print("\n=== RESOURCES ===")
cursor.execute('SELECT * FROM resources')
for row in cursor.fetchall():
    print(dict(row))

conn.close()