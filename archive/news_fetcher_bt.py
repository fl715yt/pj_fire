# backtest/news_fetcher_bt_cse.py

import os
import sqlite3
from datetime import datetime, timedelta
from dotenv import load_dotenv
from googleapiclient.discovery import build

load_dotenv()

DB_FILE = "backtest/backtest.db"
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID")
MAX_RESULTS = 10  # Pull more initially, filter later

# Trusted sources for prioritization
TRUSTED_DOMAINS = ["kabutan", "fisco", "quick", "nikkei", "bloomberg", "reuters"]

# Terms that boost score
SIGNAL_KEYWORDS = ["決算", "下方修正", "減益", "買収", "粉飾", "監査", "訴訟", "不正", "警告", "中止", "急落"]

# Junk patterns that should be excluded
JUNK_KEYWORDS = ["ADRランキング", "出来高ランキング", "PTS", "注目銘柄", "ランキング", "個別銘柄", "売買代金", "上昇銘柄"]

def get_company_name_ja(ticker):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT company_name_ja FROM stock_metadata WHERE ticker = ?", (ticker,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

def is_junk(text):
    return any(bad in text for bad in JUNK_KEYWORDS)

def score_headline(text, url, company_name, ticker):
    score = 0
    if any(term in text for term in SIGNAL_KEYWORDS):
        score += 2
    if any(domain in url for domain in TRUSTED_DOMAINS):
        score += 2
    if company_name in text or ticker in text:
        score += 1
    return score

def fetch_news_for_ticker(ticker, signal_date):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bt_news_cache (
            ticker TEXT,
            signal_date TEXT,
            headlines TEXT,
            PRIMARY KEY (ticker, signal_date)
        )
    """)

    cursor.execute("""
        SELECT headlines FROM bt_news_cache
        WHERE ticker = ? AND signal_date = ?
    """, (ticker, signal_date))
    row = cursor.fetchone()
    if row:
        return row[0]

    company_name = get_company_name_ja(ticker) or ticker
    query = f"{company_name} 株式"

    service = build("customsearch", "v1", developerKey=GOOGLE_API_KEY)
    try:
        result = service.cse().list(
            q=query,
            cx=GOOGLE_CSE_ID,
            lr="lang_ja",
            num=MAX_RESULTS,
            sort="date",
            dateRestrict="d3"
        ).execute()
    except Exception as e:
        print(f"\u26a0\ufe0f Google CSE failed for {ticker} on {signal_date}: {e}")
        return "\u274c No headlines due to Google API error."

    items = result.get("items", [])
    if not items:
        headlines = "\u274c No relevant headlines found."
    else:
        cleaned = []
        for item in items:
            title = item.get("title", "")
            link = item.get("link", "")
            if is_junk(title):
                continue
            s = score_headline(title, link, company_name, ticker)
            cleaned.append((s, f"- {title} ({link})"))

        cleaned.sort(reverse=True)
        top_n = [line for _, line in cleaned[:3]]
        headlines = "\n".join(top_n) if top_n else "\u274c No high-quality headlines found."

    cursor.execute("""
        INSERT OR REPLACE INTO bt_news_cache (ticker, signal_date, headlines)
        VALUES (?, ?, ?)
    """, (ticker, signal_date, headlines))
    conn.commit()
    conn.close()

    return headlines

# Test
if __name__ == "__main__":
    print(fetch_news_for_ticker("9984", "2025-04-05"))
    print(fetch_news_for_ticker("7203", "2025-02-14"))
    print(fetch_news_for_ticker("6758", "2025-03-18"))
    print(fetch_news_for_ticker("9432", "2025-01-23"))
    print(fetch_news_for_ticker("8058", "2025-03-25"))
