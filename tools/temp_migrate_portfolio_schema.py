import sqlite3
from config.config import SIM_DB_FILE, BT_DB_FILE

def add_signal_score_column(db_file):
    conn = sqlite3.connect(db_file)
    cur = conn.cursor()
    # Check if 'signal_score' already exists
    cur.execute("PRAGMA table_info(portfolio);")
    columns = [row[1] for row in cur.fetchall()]
    if "signal_score" not in columns:
        cur.execute("ALTER TABLE portfolio ADD COLUMN signal_score REAL;")
        print(f"✅ Added 'signal_score' column to {db_file}/portfolio.")
        conn.commit()
    else:
        print(f"Column already exists in {db_file}/portfolio (skip).")
    conn.close()

if __name__ == "__main__":
    add_signal_score_column(SIM_DB_FILE)
    add_signal_score_column(BT_DB_FILE)
