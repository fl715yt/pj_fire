# backtest/news_fetcher_bt.py

import os
import sqlite3
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()
DB_FILE = "backtest/backtest.db"
API_KEY = os.getenv("GNEWS_API_KEY")

def fetch_news_for_ticker(ticker, signal_date):
    """
    Fetches real Japanese news headlines from GNews API for a given ticker and date.
    Results are cached in SQLite for reuse.
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Create cache table if needed
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bt_news_cache (
            ticker TEXT,
            signal_date TEXT,
            headlines TEXT,
            PRIMARY KEY (ticker, signal_date)
        )
    """)

    # Check cache
    cursor.execute("""
        SELECT headlines FROM bt_news_cache
        WHERE ticker = ? AND signal_date = ?
    """, (ticker, signal_date))
    row = cursor.fetchone()
    if row:
        return row[0]

    # Prepare query
    from_date = datetime.strptime(signal_date, "%Y-%m-%d")
    to_date = from_date + timedelta(days=1)
    query = f"{ticker} 株"

    url = (
        f"https://gnews.io/api/v4/search"
        f"?q={query}"
        f"&lang=ja"
        f"&from={from_date.date()}"
        f"&to={to_date.date()}"
        f"&token={API_KEY}"
        f"&max=10"
    )

    # Request
    response = requests.get(url)
    if response.status_code != 200:
        print(f"⚠️ GNews API failed for {ticker} on {signal_date}: {response.text}")
        return ""

    data = response.json()
    articles = data.get("articles", [])

    if not articles:
        result = "No news headlines found."
    else:
        result = "\n".join(f"- {a['title']}" for a in articles)

    # Cache
    cursor.execute("""
        INSERT OR REPLACE INTO bt_news_cache (ticker, signal_date, headlines)
        VALUES (?, ?, ?)
    """, (ticker, signal_date, result))
    conn.commit()
    conn.close()

    return result

# Test
if __name__ == "__main__":
    sample = fetch_news_for_ticker("7203", "2023-02-15")
    print(sample)
