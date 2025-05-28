import requests
import json
import pandas as pd
import sqlite3
import os
from dotenv import load_dotenv

# Load J-Quants credentials
load_dotenv()
JQUANTS_EMAIL = os.getenv("JQUANTS_EMAIL")
JQUANTS_PASSWORD = os.getenv("JQUANTS_PASSWORD")

DB_FILE = "db/pj_fire.db"

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
        print(f"[ERROR] get_id_token: {e}")
        return None

def fetch_topix_metadata():
    token = get_id_token()
    if not token:
        return pd.DataFrame()

    url = "https://api.jquants.com/v1/listed/info"
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get(url, headers=headers)
    r.raise_for_status()

    info = r.json().get("info", [])
    df = pd.DataFrame(info)

    df = df[
        (df["MarketCodeName"] == "プライム") &
        (df["ScaleCategory"].str.contains("TOPIX", na=False))
    ][["Code", "CompanyName", "Sector17CodeName"]].copy()

    df["ticker"] = df["Code"].astype(str).str[:-1] + ".T"
    df.rename(columns={
        "Code": "stock_code",
        "CompanyName": "stock_name",
        "Sector17CodeName": "sector"
    }, inplace=True)

    return df[["ticker", "stock_code", "stock_name", "sector"]]

def store_metadata(df):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    for _, row in df.iterrows():
        cur.execute("""
            INSERT OR REPLACE INTO stock_metadata (ticker, stock_code, stock_name, sector)
            VALUES (?, ?, ?, ?)
        """, (row["ticker"], row["stock_code"], row["stock_name"], row["sector"]))

    conn.commit()
    conn.close()
    print(f"✅ Stored {len(df)} TOPIX stock records into stock_metadata")

if __name__ == "__main__":
    df = fetch_topix_metadata()
    if not df.empty:
        store_metadata(df)
    else:
        print("⚠️ No TOPIX data fetched.")
