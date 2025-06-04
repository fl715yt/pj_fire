"""
PJ Fire — Fundamentals Saver (FY + Quarterly, Config-Driven)
Fetches full-year and quarterly fundamentals from J-Quants and stores to unified DB.
All paths and thresholds from config.
"""

import os
import json
import sqlite3
import requests
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
import argparse
from config.config import (
    SIM_DB_FILE,
    BT_DB_FILE,
    JQUANTS_EMAIL,
    JQUANTS_PASSWORD,
    UNIVERSE_CSV,
    ENABLE_QUARTERLY_IMPORT,
)
from simulation.db_utils import init_pjfire_tables, insert_fundamentals

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
    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()
    return r.json().get("statements", [])

def store_fundamentals(df):
    conn = sqlite3.connect(SIM_DB_FILE)
    init_pjfire_tables(conn)
    print(f"Will insert {len(df)} rows into {SIM_DB_FILE}")
    print(df.head())
    insert_fundamentals(conn, df)
    print(f"✅ Saved fundamentals for {df['ticker'].nunique()} tickers.")
    conn.close()

def fetch_and_save_fundamentals():
    token = get_id_token()
    if not token:
        print("[ERROR] No token, aborting.")
        return

    if os.path.exists(UNIVERSE_CSV):
        tickers_df = pd.read_csv(UNIVERSE_CSV, dtype=str)
        # Use "ticker" as both ticker and stock_code for J-Quants API
        if "ticker" not in tickers_df.columns:
            raise ValueError(f"{UNIVERSE_CSV} missing 'ticker' column.")
        tickers_df["stock_code"] = tickers_df["ticker"]
    else:
        raise FileNotFoundError(f"{UNIVERSE_CSV} not found.")

    all_records = []
    N = len(tickers_df)
    for idx, row in tickers_df.iterrows():
        ticker = row["ticker"]
        code = row["stock_code"]
        try:
            records = fetch_fundamentals_by_code(token, code)
            df = pd.DataFrame(records)
            if df.empty:
                print(f"[{idx+1}/{N}] {ticker}: No data")
                continue
            # --- Only use supported period types and map "1Q累計" etc. ---
            df["TypeOfCurrentPeriod"] = df["TypeOfCurrentPeriod"].replace({
                "1Q累計": "1Q", "2Q累計": "2Q", "3Q累計": "3Q", "4Q累計": "4Q"
            })
            allowed_types = ["FY", "1Q", "2Q", "3Q", "4Q"]
            df = df[df["TypeOfCurrentPeriod"].isin(allowed_types)]
            for col in ["NetSales", "Profit", "EarningsPerShare"]:
                df[col] = pd.to_numeric(df[col], errors="coerce")
            df["ticker"] = ticker
            df["period_type"] = df["TypeOfCurrentPeriod"]
            df["period_end"] = pd.to_datetime(df["CurrentPeriodEndDate"]).dt.strftime("%Y-%m-%d")
            df = df[["ticker", "period_type", "period_end", "NetSales", "EarningsPerShare", "Profit"]]
            df.rename(columns={
                "NetSales": "revenue",
                "EarningsPerShare": "eps",
                "Profit": "profit"
            }, inplace=True)
            # --- Make sure period_end is string for SQLite ---
            df["period_end"] = df["period_end"].astype(str)
            all_records.append(df)
            print(f"[{idx+1}/{N}] {ticker}: OK ({len(df)} rows)")
        except Exception as e:
            print(f"[{idx+1}/{N}] [WARN] {ticker}: {e}")
        if (idx+1) % 25 == 0 or idx+1 == N:
            print(f"[PROGRESS] Processed {idx+1} of {N} tickers...")

    if all_records:
        combined = pd.concat(all_records, ignore_index=True)
        store_fundamentals(combined)
    else:
        print("⚠️ No fundamentals data collected.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Save J-Quants fundamentals to PJ Fire DB.")
    parser.add_argument('--db', choices=['sim', 'bt'], default='sim', help="Target database: sim (default) or bt")
    args = parser.parse_args()

    if args.db == 'sim':
        db_file = SIM_DB_FILE
    else:
        db_file = BT_DB_FILE

    # Patch: set the DB path for store_fundamentals
    def store_fundamentals(df):
        conn = sqlite3.connect(db_file)
        init_pjfire_tables(conn)
        print(f"Will insert {len(df)} rows into {db_file}")
        print(df.head())
        insert_fundamentals(conn, df)
        print(f"✅ Saved fundamentals for {df['ticker'].nunique()} tickers.")
        conn.close()

    fetch_and_save_fundamentals()
