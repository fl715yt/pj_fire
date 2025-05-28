import os
import requests
import pandas as pd
import re
import json
from dotenv import load_dotenv

load_dotenv()

JQUANTS_EMAIL = os.getenv("JQUANTS_EMAIL")
JQUANTS_PASSWORD = os.getenv("JQUANTS_PASSWORD")
API_BASE = "https://api.jquants.com"

def halfwidth_to_fullwidth(s):
    return ''.join(chr(ord(c) + 0xFEE0) if c.isdigit() else c for c in str(s))

# def strip_kabushiki(name):
#     return re.sub(r'^株式会社|株式会社$', '', name)

def get_id_token():
    try:
        data = {"mailaddress": JQUANTS_EMAIL, "password": JQUANTS_PASSWORD}
        auth_url = f"{API_BASE}/v1/token/auth_user"
        r = requests.post(auth_url, data=json.dumps(data), headers={"Content-Type": "application/json"})
        r.raise_for_status()
        refresh_token = r.json()["refreshToken"]

        # J-Quants expects the refresh token as a GET param, not JSON
        refresh_url = f"{API_BASE}/v1/token/auth_refresh?refreshtoken={refresh_token}"
        r = requests.post(refresh_url)
        r.raise_for_status()
        return r.json()["idToken"]
    except Exception as e:
        raise RuntimeError(f"[ERROR] get_id_token: {e}")

def fetch_topix_list(id_token):
    url = f"{API_BASE}/v1/listed/info"
    headers = {"Authorization": f"Bearer {id_token}"}
    resp = requests.get(url, headers=headers)
    if not resp.ok:
        raise RuntimeError("Failed to fetch J-Quants listed info: " + resp.text)
    data = resp.json()["info"]
    topix_rows = []
    for entry in data:
        scale = entry.get("ScaleCategory", "")
        if "TOPIX" not in scale:
            continue
        ticker = entry["Code"]
        ticker_fw = halfwidth_to_fullwidth(ticker)
        name = entry["CompanyName"]
        # name_stripped = strip_kabushiki(name)
        topix_rows.append({
            "ticker": ticker,
            "ticker_fullwidth": ticker_fw,
            "company_name": name,
            # "company_name_stripped": name_stripped,
        })
    return pd.DataFrame(topix_rows)

if __name__ == "__main__":
    print("Logging in to J-Quants...")
    id_token = get_id_token()
    print("Fetching TOPIX stock list...")
    df = fetch_topix_list(id_token)
    df.to_csv("pjfire_topix_company_patterns.csv", index=False, encoding="utf-8-sig")
    print(df.head(10))
    print(f"Total TOPIX stocks: {len(df)}")
