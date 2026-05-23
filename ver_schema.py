import sqlite3

DB_PATH = "./db/biblioteca.sqlite"

def obter_schema(cursor) -> str:
    cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND sql IS NOT NULL;")
    return "\n\n".join(row[0] for row in cursor.fetchall())

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

try:
    schema = obter_schema(cursor)
    print(schema)
finally:
    conn.close()