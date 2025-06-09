"""
PJ Fire — IR Bank Bulk News Scraper (2-Year Window, Config-Driven)
Downloads all IR headlines for all tickers in your universe and stores them in irbank_news table,
but only for headlines within [START_DATE, END_DATE] from config.py.
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import sqlite3
import os
import sys

# ===== CONFIG IMPORT =====
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from config.config import (
    UNIVERSE_CSV,
    BT_DB_FILE,
    START_DATE,
    END_DATE,
)

TABLE_NAME = "irbank_news"
SLEEP_SEC = 2  # Be polite to IR Bank

def load_tickers(csv_path=UNIVERSE_CSV):
    df = pd.read_csv(csv_path, dtype=str)
    tickers = [t[:-1] for t in df["ticker"].astype(str)]
    return tickers

def create_table_if_needed(conn):
    cur = conn.cursor()
    cur.execute(f"""
    CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
        ticker TEXT,
        date TEXT,
        headline TEXT,
        url TEXT,
        PRIMARY KEY (ticker, date, headline)
    )
    """)
    conn.commit()

def insert_irbank_news(conn, rows):
    cur = conn.cursor()
    cur.executemany(
        f"INSERT OR REPLACE INTO {TABLE_NAME} (ticker, date, headline, url) VALUES (?, ?, ?, ?)", rows
    )
    conn.commit()

def parse_rows_from_soup(soup):
    rows = []
    dl = soup.find("dl", class_="sdl")
    if not dl:
        return rows
    dt_tags = dl.find_all("dt")
    dd_tags = dl.find_all("dd")
    if len(dt_tags) != len(dd_tags):
        # Mismatched pairs (shouldn't happen)
        min_len = min(len(dt_tags), len(dd_tags))
        dt_tags = dt_tags[:min_len]
        dd_tags = dd_tags[:min_len]
    for dt, dd in zip(dt_tags, dd_tags):
        date_text = dt.text.strip().replace("/", "-")
        a_tag = dd.find("a")
        if not a_tag:
            continue
        headline = a_tag.text.strip()
        url = a_tag["href"] if "href" in a_tag.attrs else ""
        rows.append((date_text, headline, url))
    return rows

def fetch_all_news_for_ticker(ticker, start_date, end_date, max_pages=100):
    results = []
    seen_pairs = set()
    base_url = f"https://irbank.net/{ticker}/ir"
    dt_start = pd.to_datetime(start_date)
    dt_end = pd.to_datetime(end_date)
    for page in range(1, max_pages+1):
        url = f"{base_url}?page={page}" if page > 1 else base_url
        print(f"  Fetching {ticker} page {page} ...", end="")
        r = requests.get(url, timeout=15)
        if not r.ok:
            print("Failed.")
            break
        soup = BeautifulSoup(r.text, "html.parser")
        page_rows = parse_rows_from_soup(soup)
        if not page_rows:
            print("Done (no more rows).")
            break
        # Only keep rows within date window
        filtered_rows = []
        num_new = 0
        reached_too_old = False
        for d, h, u in page_rows:
            try:
                dt = pd.to_datetime(d)
            except Exception:
                continue
            pair = (d, h)
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)
            if dt_start <= dt <= dt_end:
                filtered_rows.append((d, h, u))
                num_new += 1
            if dt < dt_start:
                reached_too_old = True  # Everything past this will also be too old
        print(f" {num_new} new rows in range.")
        if num_new == 0:
            print(" (all rows already seen, breaking loop for this ticker).")
            break
        results.extend(filtered_rows)
        if reached_too_old:
            print(" (headlines older than start_date found, stopping this ticker).")
            break
        time.sleep(SLEEP_SEC)
    return results


def main():
    db_abspath = os.path.abspath(BT_DB_FILE)
    if not os.path.exists(db_abspath):
        open(db_abspath, "w").close()
    conn = sqlite3.connect(db_abspath)
    create_table_if_needed(conn)
    tickers = load_tickers()
    print(f"\n[INFO] Scraping {len(tickers)} tickers from {START_DATE} to {END_DATE}...\n")
    for i, ticker in enumerate(tickers):
        print(f"\n[{i+1}/{len(tickers)}] Scraping {ticker}")
        all_news = fetch_all_news_for_ticker(ticker, START_DATE, END_DATE)
        if all_news:
            rows = [(ticker, date, headline, url) for date, headline, url in all_news]
            insert_irbank_news(conn, rows)
            print(f"  Saved {len(rows)} headlines.")
        else:
            print("  No news found.")
        time.sleep(SLEEP_SEC)
    conn.close()
    print("\n✅ Done. All IR Bank news saved to", db_abspath)

if __name__ == "__main__":
    main()
