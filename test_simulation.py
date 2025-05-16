import sqlite3

conn = sqlite3.connect("backtest/backtest.db")
cursor = conn.cursor()

cursor.executemany("""
    DELETE FROM bt_news_cache WHERE ticker = ? AND signal_date = ?
""", [
    ("7203", "2025-02-14"),
    ("6758", "2025-03-18"),
    ("9432", "2025-01-23"),
    ("8058", "2025-03-25"),
    ("9984", "2025-04-05"),
])

conn.commit()
conn.close()

print("✅ Cleared bt_news_cache for 2025 test signals.")
