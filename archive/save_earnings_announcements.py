import requests
import pandas as pd
import os
import json

from config.config import (
    JQUANTS_EMAIL, JQUANTS_PASSWORD, JQ_BASE_URL, ANNOUNCEMENT_CALENDAR_ENDPOINT, UNIVERSE_CSV,
)

# NEED TO FIX THIS MODULE, ESPECIALLY THE API CALLS

JQUANTS_API_URL = "https://api.jquants.com/v1/fins/announcement"
ID_TOKEN = os.getenv("JQUANTS_ID_TOKEN")

def get_id_token():
    data = {"mailaddress": JQUANTS_EMAIL, "password": JQUANTS_PASSWORD}
    r = requests.post(f"{JQ_BASE_URL}/token/auth_user", data=json.dumps(data), headers={"Content-Type": "application/json"})
    r.raise_for_status()
    refresh_token = r.json()["refreshToken"]
    r = requests.post(f"{JQ_BASE_URL}/token/auth_refresh?refreshtoken={refresh_token}")
    r.raise_for_status()
    return r.json()["idToken"]

def fetch_earnings_announcements():
    token = get_id_token()
    url = ANNOUNCEMENT_CALENDAR_ENDPOINT
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    data = resp.json()
    records = data.get("announcements", [])
    df = pd.DataFrame(records)
    print(df.head(3))  # Debug: show first rows, check columns
    # Defensive check for empty result
    if df.empty:
        print("[WARN] No announcements returned from J-Quants API.")
        return pd.DataFrame(columns=["code", "date", "CompanyName"])
    # Rename and keep only necessary columns
    for required_col in ["Date", "Code"]:
        if required_col not in df.columns:
            raise RuntimeError(f"Missing required column {required_col} in J-Quants data. Got columns: {df.columns}")
    df = df.rename(columns={"Code": "code", "Date": "date"})
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["code", "date"])
    # Only keep useful columns
    cols = ["code", "date"]
    if "CompanyName" in df.columns:
        cols.append("CompanyName")
    df = df[cols]
    return df

def save_to_csv(path="earnings_announcements.csv"):
    df = fetch_earnings_announcements()
    df.to_csv(path, index=False)
    print(f"[EARNINGS] Saved {len(df)} records to {path}")

if __name__ == "__main__":
    save_to_csv()
