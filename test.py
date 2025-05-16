import sqlite3

# Connect to your backtest DB
conn = sqlite3.connect("backtest/backtest.db")
cursor = conn.cursor()

# 1. Delete all existing rows (safe reset)
cursor.execute("DELETE FROM bt_signals")

# 2. Insert new test signals (2025, one for each category)
new_rows = [
    ("7203", "2025-02-14", 4.1),  # Slightly bad news
    ("6758", "2025-03-18", 6.2),  # Very bad news
    ("9432", "2025-01-23", 3.9),  # Unknown / no news
    ("8058", "2025-03-25", 5.0),  # Macro/sector-wide
    ("9984", "2025-04-05", 5.7),  # Misinterpreted news
]

cursor.executemany("""
INSERT INTO bt_signals (ticker, signal_date, price_drop_pct, drop_reason)
VALUES (?, ?, ?, NULL)
""", new_rows)

conn.commit()
conn.close()

print("✅ Reset complete. Only 2025 test cases are in bt_signals.")
