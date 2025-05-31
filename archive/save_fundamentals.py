"""
PJ Fire — Universal Fundamentals Saver

Fetches all available (FY + quarterly) fundamentals via J-Quants, stores to unified fundamentals table.
"""

import os
import json
import sqlite3
import requests
import pandas as pd
from dotenv import load_dotenv
from config.config import SIM_DB_FILE, BT_DB_FILE, JQUANTS_EMAIL, JQUANTS_PASSWORD

load_dotenv()

def get_id_token():
    auth_url = "https://api.jquants.com/v1/token/auth_user"
    refresh_url = "https://api.jquants.com/v1/token/auth_refresh"
    try:
        data = {"mailaddress": JQUANTS_EMAIL, "password": JQUANTS_PASSWORD}
        r = requests.post(auth_url, data=json.dumps(data), headers={"Content-Type": "application/json"})
        r.raise_for_status()
        refresh_token = r.json()["refreshToken"]
        r = requests.post(f"{refresh_url}?refreshtoken={refresh_token}")
        r.raise_for_status()
        return r.json()["idToken"]
    except Exception as e:
        print(f"[ERROR] Token retrieval failed: {e}")
        return None

def fetch_fundamentals_by_code(token, code):
    url = f"https://api.jquants.com/v1/fins/statements?code={code}"
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get(url, headers=headers)
    r.raise_for_status()
    return r.json().get("statements", [])

def store_fundamentals(df, db_file):
    conn = sqlite3.connect(db_file)
    from simulation.db_utils import insert_fundamentals, init_pjfire_tables
    init_pjfire_tables(conn)
    insert_fundamentals(conn, df)
    print(f"✅ Saved fundamentals for {df['ticker'].nunique()} tickers to {db_file}.")
    conn.close()

def fetch_and_save_fundamentals(db_file, ticker_list):
    token = get_id_token()
    if not token:
        print("[ERROR] No token, aborting.")
        return

    all_records = []
    for i, ticker in enumerate(ticker_list):
        print(f"[{i+1}/{len(ticker_list)}] Fetching for {ticker}...")
        try:
            records = fetch_fundamentals_by_code(token, ticker)
            for row in records:
                # Accept all period types (FY, 1Q, etc.)
                period_type = row.get("TypeOfCurrentPeriod")
                period_end = row.get("CurrentPeriodEndDate")
                if not (period_type and period_end):
                    continue
                all_records.append({
                    "ticker": ticker,
                    "period_type": period_type,
                    "period_end": period_end,
                    "revenue": pd.to_numeric(row.get("NetSales"), errors="coerce"),
                    "eps": pd.to_numeric(row.get("EarningsPerShare"), errors="coerce"),
                    "profit": pd.to_numeric(row.get("Profit"), errors="coerce"),
                })
        except Exception as e:
            print(f"[WARN] Failed for {ticker}: {e}")
    if all_records:
        df = pd.DataFrame(all_records)
        store_fundamentals(df, db_file)
    else:
        print("⚠️ No fundamentals data collected.")

if __name__ == "__main__":
    # Load ticker list from universe CSV
    UNIVERSE_CSV = os.getenv("PJ_FIRE_UNIVERSE_CSV", "pjfire_topix_company_patterns_expanded.csv")
    df_univ = pd.read_csv(UNIVERSE_CSV, dtype=str)
    tickers = df_univ["ticker"].astype(str).tolist()
    # Use SIM_DB_FILE or BT_DB_FILE as needed
    fetch_and_save_fundamentals(SIM_DB_FILE, tickers)
