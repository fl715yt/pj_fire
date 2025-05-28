import sqlite3
import shutil

SOURCE_DB = "db/pj_fire.db"
DEST_DB = "backtest/backtest.db"
SOURCE_TABLE = "stock_fundamentals"
DEST_TABLE = "bt_fundamentals"

def copy_table():
    # Connect to both databases
    src_conn = sqlite3.connect(SOURCE_DB)
    dest_conn = sqlite3.connect(DEST_DB)
    src_cursor = src_conn.cursor()
    dest_cursor = dest_conn.cursor()

    # Drop the destination table if it exists
    dest_cursor.execute(f"DROP TABLE IF EXISTS {DEST_TABLE}")

    # Get table schema from source
    src_cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{SOURCE_TABLE}'")
    create_stmt = src_cursor.fetchone()
    if not create_stmt:
        raise Exception(f"Source table '{SOURCE_TABLE}' not found.")
    
    # Modify table name in schema and create it in destination
    dest_cursor.execute(create_stmt[0].replace(SOURCE_TABLE, DEST_TABLE))

    # Copy data
    src_cursor.execute(f"SELECT * FROM {SOURCE_TABLE}")
    rows = src_cursor.fetchall()

    # Get column placeholders
    col_count = len(src_cursor.description)
    placeholders = ", ".join(["?"] * col_count)

    dest_cursor.executemany(
        f"INSERT INTO {DEST_TABLE} VALUES ({placeholders})", rows
    )

    # Commit and close
    dest_conn.commit()
    src_conn.close()
    dest_conn.close()

    print(f"✅ Table '{SOURCE_TABLE}' copied to '{DEST_TABLE}' in {DEST_DB}")

if __name__ == "__main__":
    copy_table()
