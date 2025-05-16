# backtest/reset_drop_reason.py

import sqlite3

DB_FILE = "backtest/backtest.db"

conn = sqlite3.connect(DB_FILE)
cursor = conn.cursor()

cursor.execute("UPDATE bt_signals SET drop_reason = NULL")
conn.commit()
conn.close()

print("✅ All drop_reason values have been reset.")
