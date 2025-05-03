import sqlite3

DB_PATH = "db/pj_fire.db"

def get_connection():
    return sqlite3.connect(DB_PATH)

def execute_query(query, params=None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(query, params or [])
    conn.commit()
    conn.close()

def fetch_all(query, params=None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(query, params or [])
    results = cursor.fetchall()
    conn.close()
    return results
