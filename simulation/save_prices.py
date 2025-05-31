"""
PJ Fire — Price Data Loader (Config-Driven)
Fetches daily price data from J-Quants API, stores into the unified DB.
Supports both daily and bulk (backfill) modes.
"""

import os
import requests
import pandas as pd
import sqlite3
import json
from datetime import datetime, timedelta
import argparse
from dotenv import load_dotenv

from config.config import (
    SIM_DB_FILE,    # simulation/pjfire.db by default
    BT_DB_FILE,     # backtest/backtest_bt.db by default
)
from simulation.db_utils import init_pjfire_tables, insert_prices

load_dotenv()

JQUANTS_EMAIL = os.getenv("JQUANTS_EMAIL")
JQUANTS_PASSWORD = os.getenv("JQUANTS_PASSWORD")
API_BASE = "https://api.jquants.com"

# Use the authoritative universe CSV from config or fallback
TICKER_CSV = os.getenv("PJ_FIRE_UNIVERSE_CSV", "pjfire_topix_company_patterns_expanded.csv")

def get_id_token():
    data = {"mailaddress": JQUANTS_EMAIL, "password": JQUANTS_PASSWORD}
    r = requests.post(f"{API_BASE}/v1/token/auth_user", data=json.dumps(data), headers={"Content-Type": "application/json"})
    r.raise_for_status()
    refresh_token = r.json()["refreshToken"]
    r = requests.post(f"{API_BASE}/v1/token/auth_refresh?refreshtoken={refresh_token}")
    r.raise_for_status()
    return r.json()["idToken"]

def load_topix_tickers(patterns_csv=TICKER_CSV):
    df = pd.read_csv(patterns_csv, dtype=str)
    return df["ticker"].astype(str).tolist()

def fetch_and_save_prices(start_date, end_date, tickers, db_path=SIM_DB_FILE):
    id_token = get_id_token()
    headers = {"Authorization": f"Bearer {id_token}"}
    all_records = []
    N = len(tickers)
    print(f"[START] Fetching prices for {N} tickers ({start_date} to {end_date})")
    for idx, code in enumerate(tickers, 1):
        url = f"{API_BASE}/v1/prices/daily_quotes?code={code}&from={start_date}&to={end_date}"
        try:
            resp = requests.get(url, headers=headers, timeout=30)
            if not resp.ok:
                print(f"[{idx}/{N}] [WARN] Failed for {code}: {resp.text}")
                continue
            rows = resp.json().get("daily_quotes", [])
            for r in rows:
                all_records.append({
                    "date": r["Date"],
                    "ticker": r["Code"],
                    "open": r["Open"],
                    "high": r["High"],
                    "low": r["Low"],
                    "close": r["Close"],
                    "volume": r["Volume"],
                })
            print(f"[{idx}/{N}] {code}: {len(rows)} rows")
        except Exception as e:
            print(f"[{idx}/{N}] [ERROR] {code}: {e}")
        if idx % 50 == 0 or idx == N:
            print(f"[PROGRESS] Processed {idx} of {N} tickers...")

    if all_records:
        conn = sqlite3.connect(db_path)
        init_pjfire_tables(conn)
        df = pd.DataFrame(all_records)
        insert_prices(conn, df)
        print(f"[COMPLETE] Saved {len(df)} price records to {db_path}")
        conn.close()
    else:
        print("[COMPLETE] No records to save.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Save daily or bulk price data for PJ Fire.")
    parser.add_argument("--start_date", type=str, default=None, help="YYYY-MM-DD for start of date range (defaults to today)")
    parser.add_argument("--end_date", type=str, default=None, help="YYYY-MM-DD for end of date range (defaults to today)")
    parser.add_argument("--bulk", action="store_true", help="If set, loads for the last 3 months by default")
    parser.add_argument("--db", type=str, choices=["sim", "bt"], default="sim", help="Target DB: sim (default) or bt (backtest)")
    args = parser.parse_args()

    tickers = load_topix_tickers()
    today = datetime.now().date()
    if args.bulk:
        start_date = (today - timedelta(days=90)).strftime("%Y-%m-%d")
        end_date = today.strftime("%Y-%m-%d")
    else:
        start_date = args.start_date or today.strftime("%Y-%m-%d")
        end_date = args.end_date or today.strftime("%Y-%m-%d")

    # Choose DB file
    db_path = SIM_DB_FILE if args.db == "sim" else BT_DB_FILE

    print(f"[INFO] Loading prices from {start_date} to {end_date} for {len(tickers)} tickers")
    fetch_and_save_prices(start_date, end_date, tickers, db_path=db_path)
    print("[FINISHED]")
