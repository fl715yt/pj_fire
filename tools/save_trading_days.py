import os
import requests
import pandas as pd
from dotenv import load_dotenv
from config.config import TRADING_CALENDAR_ENDPOINT, TRADING_CALENDAR_CSV

def fetch_and_save_trading_days_jquants(id_token, from_date="20000101", to_date="20301231"):
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

if __name__ == "__main__":
    load_dotenv()
    # Use your pipeline's environment variable, e.g. JQUANTS_ID_TOKEN or OPENAI_API_KEY if re-used
    id_token = os.environ.get("JQUANTS_ID_TOKEN") or os.environ.get("JQUANTS_API_TOKEN")
    if not id_token:
        raise EnvironmentError("JQUANTS_ID_TOKEN not found in environment!")
    fetch_and_save_trading_days_jquants(id_token)
