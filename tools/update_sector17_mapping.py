# tools/update_sector17_mapping.py

import os
import pandas as pd
import requests
import json
from dotenv import load_dotenv

load_dotenv()

JQUANTS_EMAIL = os.getenv("JQUANTS_EMAIL")
JQUANTS_PASSWORD = os.getenv("JQUANTS_PASSWORD")
API_BASE = "https://api.jquants.com"
ROOT_CSV = "pjfire_topix_company_patterns_filtered.csv"
OUT_CSV = "pjfire_topix_company_patterns_filtered_with_sector17.csv"

def get_id_token():
    data = {"mailaddress": JQUANTS_EMAIL, "password": JQUANTS_PASSWORD}
    r = requests.post(f"{API_BASE}/v1/token/auth_user", data=json.dumps(data), headers={"Content-Type": "application/json"})
    r.raise_for_status()
    refresh_token = r.json()["refreshToken"]
    r = requests.post(f"{API_BASE}/v1/token/auth_refresh?refreshtoken={refresh_token}")
    r.raise_for_status()
    return r.json()["idToken"]

def fetch_topix17_metadata():
    id_token = get_id_token()
    url = f"{API_BASE}/v1/listed/info"
    headers = {"Authorization": f"Bearer {id_token}"}
    r = requests.get(url, headers=headers)
    r.raise_for_status()
    info = r.json().get("info", [])
    # Official TOPIX-17 sector columns: "Sector17Code" and "Sector17CodeName"
    df = pd.DataFrame(info)
    df = df[df["ScaleCategory"].str.contains("TOPIX", na=False)]
    sector_df = df[["Code", "Sector17Code", "Sector17CodeName"]].copy()
    sector_df.rename(columns={
        "Code": "ticker",
        "Sector17Code": "sector17_code",
        "Sector17CodeName": "sector17"
    }, inplace=True)
    sector_df["ticker"] = sector_df["ticker"].astype(str)
    return sector_df

def update_company_patterns_with_sector():
    # 1. Fetch official sector mapping from J-Quants
    sector_map = fetch_topix17_metadata()

    # 2. Read your current expanded CSV (root folder)
    patterns = pd.read_csv(ROOT_CSV, dtype=str)
    patterns["ticker"] = patterns["ticker"].astype(str)

    # 3. Merge by ticker (left join: keep all tickers in your patterns)
    updated = patterns.merge(sector_map, how="left", on="ticker")

    # 4. Show warning if any sector17 is missing
    missing = updated[updated["sector17"].isnull()]
    if not missing.empty:
        print(f"Warning: {len(missing)} tickers have no sector17 assigned. (Check for ticker code mismatches.)")
        print(missing[["ticker", "company_name"]].head())

    # 5. Save new CSV with sector17 mapping
    updated.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")
    print(f"✅ Updated CSV saved: {OUT_CSV}")
    print(updated.head())

if __name__ == "__main__":
    update_company_patterns_with_sector()
