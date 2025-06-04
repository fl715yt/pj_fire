# tools/migrate_schema.py
import sqlite3
from config.config import SIM_DB_FILE, BT_DB_FILE

def add_signal_score_column(db_file):
    conn = sqlite3.connect(db_file)
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(portfolio)")
    cols = [row[1] for row in cur.fetchall()]
    if "signal_score" not in cols:
        cur.execute("ALTER TABLE portfolio ADD COLUMN signal_score REAL")
        print(f"Added signal_score to {db_file}/portfolio.")
    else:
        print(f"signal_score already exists in {db_file}/portfolio.")
    conn.commit()
    conn.close()

def migrate_fundamentals_schema(db_file):
    conn = sqlite3.connect(db_file)
    cur = conn.cursor()
    # Check if period_type and period_end columns exist
    cur.execute("PRAGMA table_info(fundamentals)")
    cols = [row[1] for row in cur.fetchall()]
    needs_period_type = "period_type" not in cols
    needs_period_end = "period_end" not in cols
    if needs_period_type or needs_period_end:
        # You would need to dump old data, drop table, create new, and reinsert
        print(f"[WARN] Fundamentals table in {db_file} needs manual migration.")
    else:
        print(f"Fundamentals table OK in {db_file}.")
    conn.close()

if __name__ == "__main__":
    for db in [SIM_DB_FILE, BT_DB_FILE]:
        add_signal_score_column(db)
        migrate_fundamentals_schema(db)
