import sqlite3
from datetime import datetime

DB_FILE = "db/pj_fire.db"

def simulate_trade_entries(ranked_stocks, max_positions=5):
    """
    Simulates virtual BUY entries for top N ranked stocks if not already held.
    """
    today = datetime.now().strftime("%Y-%m-%d")
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    # --- Step 1: Check current open positions
    cur.execute("SELECT ticker FROM sim_trades WHERE status = 'OPEN'")
    held = {row[0] for row in cur.fetchall()}

    buys_made = 0

    for stock in ranked_stocks:
        if buys_made >= max_positions:
            break
        if stock["ticker"] in held:
            continue

        cur.execute("""
            INSERT INTO sim_trades (
                date, ticker, action, price, size, reason_category,
                reason_score, ranking_score, status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            today,
            stock["ticker"],
            "BUY",
            stock["price_drop_pct"],  # for now use this field as a placeholder; update later with actual price
            100,  # placeholder size
            stock["reason_category"],
            stock["reason_score"],
            stock["ranking_score"],
            "OPEN"
        ))

        buys_made += 1

    conn.commit()
    conn.close()
    print(f"✅ Simulated {buys_made} BUY entries.")
