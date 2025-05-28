# backtest/bt_save_fundamentals.py

import os
import json
import sqlite3
import requests
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

DB_FILE = "db/pj_fire.db"  # adjust if needed
JQUANTS_EMAIL = os.getenv("JQUANTS_EMAIL")
JQUANTS_PASSWORD = os.getenv("JQUANTS_PASSWORD")

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

def store_fundamentals(df):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS stock_fundamentals (
            ticker TEXT,
            fiscal_year TEXT,
            revenue REAL,
            net_income REAL,
            equity_ratio REAL,
            equity REAL,
            operating_profit REAL,
            eps REAL,
            dividend REAL,
            company_name_ja TEXT,
            PRIMARY KEY (ticker, fiscal_year)
        )
    """)

    for _, row in df.iterrows():
        cur.execute("""
            INSERT OR REPLACE INTO stock_fundamentals
            (ticker, fiscal_year, revenue, net_income, equity_ratio, equity,
             operating_profit, eps, dividend, company_name_ja)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            row["ticker"],
            row["fiscal_year"],
            row["revenue"],
            row["net_income"],
            row["equity_ratio"],
            row["equity"],
            row["operating_profit"],
            row["eps"],
            row["dividend"],
            row["company_name_ja"]
        ))

    conn.commit()
    conn.close()
    print(f"✅ Saved fundamentals for {df['ticker'].nunique()} tickers.")

def fetch_all_fundamentals():
    token = get_id_token()
    if not token:
        return

    conn = sqlite3.connect(DB_FILE)
    tickers_df = pd.read_sql("SELECT ticker, stock_code FROM stock_metadata", conn)
    conn.close()

    all_records = []

    for _, row in tickers_df.iterrows():
        ticker = row["ticker"]
        code = row["stock_code"]
        try:
            records = fetch_fundamentals_by_code(token, code)
            df = pd.DataFrame(records)
            if df.empty:
                continue

            df = df[
                (df["TypeOfCurrentPeriod"] == "FY") & 
                (df["TypeOfDocument"].str.contains("FY", na=False))
            ]
            if df.empty:
                continue

            for col in [
                "NetSales", "Profit", "EquityToAssetRatio", "Equity",
                "OperatingProfit", "EarningsPerShare", "ResultDividendPerShareAnnual"
            ]:
                df[col] = pd.to_numeric(df[col], errors="coerce")

            df["ticker"] = ticker
            df["fiscal_year"] = pd.to_datetime(df["CurrentPeriodEndDate"]).dt.year.astype(str)
            df["company_name_ja"] = df["CompanyNameJa"]

            df = df[[  # include company name here
                "ticker", "fiscal_year", "NetSales", "Profit", "EquityToAssetRatio",
                "Equity", "OperatingProfit", "EarningsPerShare", "ResultDividendPerShareAnnual",
                "company_name_ja"
            ]]
            df.rename(columns={
                "NetSales": "revenue",
                "Profit": "net_income",
                "EquityToAssetRatio": "equity_ratio",
                "Equity": "equity",
                "OperatingProfit": "operating_profit",
                "EarningsPerShare": "eps",
                "ResultDividendPerShareAnnual": "dividend"
            }, inplace=True)

            df.sort_values("fiscal_year", ascending=False, inplace=True)
            df = df.head(2)

            all_records.append(df)

        except Exception as e:
            print(f"[WARN] Failed to fetch fundamentals for {ticker} ({code}): {e}")

    if all_records:
        combined = pd.concat(all_records, ignore_index=True)
        store_fundamentals(combined)
    else:
        print("⚠️ No fundamentals data collected.")

if __name__ == "__main__":
    fetch_all_fundamentals()
