import sqlite3
from datetime import datetime
from screening.fetcher import fetch_stock_data_yf, fetch_market_index_from_yf
import yfinance as yf

DB_FILE = "db/pj_fire.db"

def save_snapshots():
    today = datetime.now().strftime("%Y-%m-%d")

    # Step 1: Get all tickers from stock_metadata
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT ticker FROM stock_metadata")
    tickers = [row[0] for row in cur.fetchall()]
    conn.close()

    # Step 2: Fetch stock data
    stock_data = fetch_stock_data_yf(tickers)

    # Step 3: Save to stock_snapshots
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    inserted = 0
    for ticker, data in stock_data.items():
        cur.execute("""
            INSERT OR REPLACE INTO stock_snapshots (date, ticker, close_price, volume)
            VALUES (?, ?, ?, ?)
        """, (today, ticker, data["price"], data["volume"]))
        inserted += 1
    conn.commit()
    print(f"✅ Saved {inserted} stock snapshots for {today}")

    # Step 4: Fetch ETF prices for market index calculation
    etf_data = yf.download(["1306.T", "1321.T"], period="2d", interval="1d", group_by="ticker")
    index_changes = fetch_market_index_from_yf(etf_data)

    for index_name, pct in index_changes.items():
        cur.execute("""
            INSERT OR REPLACE INTO market_snapshots (date, index_name, percent_change)
            VALUES (?, ?, ?)
        """, (today, index_name, pct))
    conn.commit()
    conn.close()

    print(f"✅ Saved market index snapshot: {index_changes}")

if __name__ == "__main__":
    save_snapshots()
