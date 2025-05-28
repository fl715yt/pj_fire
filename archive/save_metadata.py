# save_metadata.py

import os
import json
import sqlite3
import requests
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

DB_FILE = "backtest/backtest.db"  # Or backtest.db if you're populating both
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

def fetch_metadata(token):
    url = "https://api.jquants.com/v1/listed/info"
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get(url, headers=headers)
    r.raise_for_status()
    return r.json()["info"]

def store_metadata(records):
    df = pd.DataFrame(records)
    df = df.rename(columns={
        "Code": "ticker",
        "CompanyName": "company_name_ja",
        "CompanyNameEnglish": "company_name_en",
        "Sector17CodeName": "sector_name_17",
        "Sector33CodeName": "sector_name_33",
        "MarketCodeName": "market_name"
    })

    df = df[[
        "ticker", "company_name_ja", "company_name_en", 
        "sector_name_17", "sector_name_33", "market_name"
    ]]

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS stock_metadata (
            ticker TEXT PRIMARY KEY,
            company_name_ja TEXT,
            company_name_en TEXT,
            sector_name_17 TEXT,
            sector_name_33 TEXT,
            market_name TEXT
        )
    """)

    for _, row in df.iterrows():
        cur.execute("""
            INSERT OR REPLACE INTO stock_metadata (
                ticker, company_name_ja, company_name_en,
                sector_name_17, sector_name_33, market_name
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, tuple(row))

    conn.commit()
    conn.close()
    print(f"✅ Saved metadata for {len(df)} companies.")

def main():
    token = get_id_token()
    if not token:
        return

    records = fetch_metadata(token)
    store_metadata(records)

if __name__ == "__main__":
    main()
