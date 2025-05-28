import sqlite3

DB_FILE = "db/pj_fire.db"

def reset_all_tables():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    # List of all known tables
    tables = [
        "stock_metadata",
        "stock_snapshots",
        "market_snapshots",
        "sim_trades",
        "stock_fundamentals"
    ]

    for table in tables:
        cur.execute(f"DROP TABLE IF EXISTS {table};")
        print(f"🗑️ Dropped: {table}")

    conn.commit()
    conn.close()
    print("✅ All tables dropped. You can now rerun schema_migration.py to recreate.")

if __name__ == "__main__":
    reset_all_tables()
