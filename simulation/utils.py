import os
import json
import requests
import pandas as pd
import bisect
from dotenv import load_dotenv
from config.config import (
    TRADING_CALENDAR_ENDPOINT,
    TRADING_CALENDAR_CSV,
    JQUANTS_EMAIL,
    JQUANTS_PASSWORD,
    JQ_BASE_URL,
    VARIANT_CSV
)

load_dotenv()  # Ensure env vars loaded

def get_id_token():
    """
    Retrieves J-Quants idToken using email and password from env/config.
    """
    data = {"mailaddress": JQUANTS_EMAIL, "password": JQUANTS_PASSWORD}
    r = requests.post(f"{JQ_BASE_URL}/token/auth_user", data=json.dumps(data), headers={"Content-Type": "application/json"})
    r.raise_for_status()
    refresh_token = r.json()["refreshToken"]
    r = requests.post(f"{JQ_BASE_URL}/token/auth_refresh?refreshtoken={refresh_token}")
    r.raise_for_status()
    return r.json()["idToken"]

def fetch_and_save_trading_days_jquants(id_token, from_date="20230101", to_date="20301231"):
    """
    Fetches trading calendar from J-Quants API and saves all営業日 to a CSV.
    Only rows with HolidayDivision == "1" or "2" are considered trading days.
    """
    url = f"{TRADING_CALENDAR_ENDPOINT}?from={from_date}&to={to_date}"
    headers = {'Authorization': f'Bearer {id_token}'}
    response = requests.get(url, headers=headers)
    response.raise_for_status()

    calendar = response.json().get("trading_calendar", [])
    if not calendar:
        raise ValueError("No trading_calendar data returned from J-Quants.")

    df = pd.DataFrame(calendar)
    # Only営業日 (1: normal, 2: half-day, treat both as trading days)
    df = df[df["HolidayDivision"].isin(["1", "2"])]
    df = df[["Date", "HolidayDivision"]].sort_values("Date")
    df.to_csv(TRADING_CALENDAR_CSV, index=False)
    print(f"Saved {len(df)} trading days to {TRADING_CALENDAR_CSV}")

def load_trading_days(trading_days_csv=TRADING_CALENDAR_CSV):
    """
    Loads trading days from CSV.
    Returns a sorted list of trading day strings (YYYY-MM-DD).
    """
    df = pd.read_csv(trading_days_csv, dtype=str)
    valid_days = df[df["HolidayDivision"].isin(["1", "2"])]["Date"].tolist()
    valid_days.sort()
    return valid_days

def get_next_trading_day(current_date, trading_days, offset=1):
    """
    Returns the trading day string (YYYY-MM-DD) offset days after current_date.
    trading_days: sorted list of trading days.
    """
    idx = bisect.bisect_right(trading_days, current_date)
    next_idx = idx + offset - 1
    if 0 <= next_idx < len(trading_days):
        return trading_days[next_idx]
    else:
        return None

def get_ticker_to_variants():
    variant_df = pd.read_csv(VARIANT_CSV, dtype=str)
    variant_df["ticker"] = variant_df["ticker"].apply(lambda code: code[:-1] if len(code) == 5 and code.endswith("0") else code)
    return {
        row["ticker"]: [v.strip() for v in str(row["variants"]).split(" / ") if v.strip() and not v.strip().isdigit()]
        for _, row in variant_df.iterrows()
    }

if __name__ == "__main__":
    id_token = get_id_token()
    fetch_and_save_trading_days_jquants(id_token)
    # Example: To use loaded days elsewhere
    # trading_days = load_trading_days()
    # print(trading_days[:5])  # print first 5 for sanity check

