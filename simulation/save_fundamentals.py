import os
import json
import sqlite3
import requests
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
from simulation.db_utils import init_pjfire_tables, insert_fundamentals

load_dotenv()

DB_FILE = os.getenv("PJ_FIRE_DB", "simulation/pjfire.db")
JQUANTS_EMAIL = os.getenv("JQUANTS_EMAIL")
JQUANTS_PASSWORD = os.getenv("JQUANTS_PASSWORD")

# === CONFIG ===
TICKER_CSV = "pjfire_topix_company_patterns_filtered.csv"   # Use latest TOPIX ticker/metadata CSV

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
    conn = sqlite3.connect(DB_FILE)
    init_pjfire_tables(conn)
    insert_fundamentals(conn, df)
    print(f"✅ Saved fundamentals for {df['ticker'].nunique()} tickers.")
    conn.close()

def fetch_and_save_fundamentals():
    token = get_id_token()
    if not token:
        print("[ERROR] No token, aborting.")
        return

    if os.path.exists(TICKER_CSV):
        tickers_df = pd.read_csv(TICKER_CSV, dtype=str)
        # Use "ticker" as both ticker and stock_code for J-Quants API
        if "ticker" not in tickers_df.columns:
            raise ValueError(f"{TICKER_CSV} missing 'ticker' column.")
        tickers_df["stock_code"] = tickers_df["ticker"]
    else:
        raise FileNotFoundError(f"{TICKER_CSV} not found.")

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
            df = df[df["TypeOfCurrentPeriod"] == "FY"]  # Only FY (annual) data
            for col in ["NetSales", "Profit", "EarningsPerShare"]:
                df[col] = pd.to_numeric(df[col], errors="coerce")
            df["ticker"] = ticker
            df["fiscal_year"] = pd.to_datetime(df["CurrentPeriodEndDate"]).dt.year.astype(str)
            df = df[["ticker", "fiscal_year", "NetSales", "EarningsPerShare", "Profit"]]
            df.rename(columns={
                "NetSales": "revenue",
                "EarningsPerShare": "eps",
                "Profit": "profit"
            }, inplace=True)
            df.sort_values("fiscal_year", ascending=False, inplace=True)
            df = df.head(5)  # Change this if you want more/less years
            all_records.append(df)
            print(f"[{idx+1}/{N}] {ticker}: OK ({len(df)} years)")
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
    fetch_and_save_fundamentals()
