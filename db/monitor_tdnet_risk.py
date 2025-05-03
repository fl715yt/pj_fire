import os
import re
import sqlite3
import feedparser
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

DB_FILE = "db/pj_fire.db"
TDNET_RSS_URL = "https://www.release.tdnet.info/rss/tdnetall.xml"

RED_FLAG_KEYWORDS = [
    "赤字転落",
    "民事再生",
    "上場廃止",
    "上場廃止猶予",
    "特設注意",
    "債務超過",
    "継続企業の前提"
]

def create_tdnet_log_table():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tdnet_logs (
            pub_date TEXT PRIMARY KEY,
            title TEXT,
            processed_at TEXT
        )
    """)
    conn.commit()
    conn.close()

def already_processed(pub_date):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM tdnet_logs WHERE pub_date = ?", (pub_date,))
    result = cur.fetchone()
    conn.close()
    return result is not None

def log_disclosure(pub_date, title):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
        INSERT OR IGNORE INTO tdnet_logs (pub_date, title, processed_at)
        VALUES (?, ?, ?)
    """, (pub_date, title, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def ensure_tdnet_column():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    try:
        cur.execute("ALTER TABLE stock_fundamentals ADD COLUMN tdnet_risk BOOLEAN DEFAULT 0")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # Already exists
    conn.close()

def set_tdnet_risk(ticker):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("UPDATE stock_fundamentals SET tdnet_risk = 1 WHERE ticker = ?", (ticker,))
    conn.commit()
    conn.close()

def extract_stock_code(description):
    match = re.search(r"【(\d{4,5})】", description)
    if match:
        return match.group(1) + ".T"
    return None

def clean_expired_flags():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    cur.execute("SELECT DISTINCT ticker FROM stock_fundamentals WHERE tdnet_risk = 1")
    tickers = [row[0] for row in cur.fetchall()]

    for ticker in tickers:
        stock_code = ticker.replace(".T", "")
        cur.execute("""
            SELECT MAX(processed_at)
            FROM tdnet_logs
            WHERE title LIKE ?
        """, (f"%{stock_code}%",))
        result = cur.fetchone()[0]
        if not result:
            continue

        last_seen = datetime.fromisoformat(result)
        if (datetime.now() - last_seen).days > 45:
            cur.execute("UPDATE stock_fundamentals SET tdnet_risk = 0 WHERE ticker = ?", (ticker,))
            print(f"✅ Expired TDnet Risk Unflagged: {ticker}")

    conn.commit()
    conn.close()

def monitor_tdnet():
    print(f"[INFO] Fetching TDnet feed...")
    feed = feedparser.parse(TDNET_RSS_URL)
    create_tdnet_log_table()
    ensure_tdnet_column()

    for entry in feed.entries:
        pub_date = entry.get("published", "")
        title = entry.get("title", "")
        description = entry.get("description", "")

        if already_processed(pub_date):
            continue

        for keyword in RED_FLAG_KEYWORDS:
            if keyword in title:
                ticker = extract_stock_code(description)
                if ticker:
                    set_tdnet_risk(ticker)
                    print(f"⚠️ TDnet Red Flag: {ticker} - {keyword} in \"{title}\"")
                else:
                    print(f"⚠️ TDnet Red Flag (no ticker found): {title}")
                break

        log_disclosure(pub_date, title)

    clean_expired_flags()

if __name__ == "__main__":
    monitor_tdnet()
