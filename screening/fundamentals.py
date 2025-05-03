import os
import requests
import json
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

JQUANTS_EMAIL = os.getenv("JQUANTS_EMAIL")
JQUANTS_PASSWORD = os.getenv("JQUANTS_PASSWORD")

def get_id_token():
    try:
        data = {"mailaddress": JQUANTS_EMAIL, "password": JQUANTS_PASSWORD}
        auth_url = "https://api.jquants.com/v1/token/auth_user"
        r = requests.post(auth_url, data=json.dumps(data), headers={"Content-Type": "application/json"})
        r.raise_for_status()
        refresh_token = r.json()["refreshToken"]

        # Refresh token to get ID token
        refresh_url = f"https://api.jquants.com/v1/token/auth_refresh?refreshtoken={refresh_token}"
        r = requests.post(refresh_url)
        r.raise_for_status()
        return r.json()["idToken"]
    except Exception as e:
        print(f"[ERROR] get_id_token: {e}")
        return None

def fetch_fundamentals_from_jquants():
    """
    Fetches fundamental financial data from /fins/statements endpoint.
    Filters for latest full-year reports only.
    Returns: list of dicts with revenue, profit, EPS, etc.
    """
    try:
        id_token = get_id_token()
        if not id_token:
            raise Exception("Missing ID token")

        url = "https://api.jquants.com/v1/fins/statements"
        headers = {'Authorization': f'Bearer {id_token}'}
        r = requests.get(url, headers=headers)
        r.raise_for_status()

        raw_data = r.json().get("statements", [])
        df = pd.DataFrame(raw_data)

        # Filter to latest fiscal year reports only (TypeOfCurrentPeriod == 'FY')
        df = df[df["TypeOfCurrentPeriod"] == "FY"]

        results = []
        for _, row in df.iterrows():
            try:
                ticker = row["LocalCode"] + ".T"
                fiscal_year = int(row["CurrentPeriodEndDate"][:4])
                revenue = int(row["NetSales"]) if row["NetSales"] else 0
                op_profit = int(row["OperatingProfit"]) if row["OperatingProfit"] else 0
                net_profit = int(row["Profit"]) if row["Profit"] else 0
                eps = float(row["EarningsPerShare"]) if row["EarningsPerShare"] else 0.0
                dividend = float(row["ForecastDividendPerShareAnnual"]) if row["ForecastDividendPerShareAnnual"] else 0.0

                results.append({
                    "ticker": ticker,
                    "fiscal_year": fiscal_year,
                    "revenue": revenue,
                    "operating_profit": op_profit,
                    "profit": net_profit,
                    "eps": eps,
                    "dividend": dividend
                })
            except Exception as row_error:
                continue  # skip malformed rows

        print(f"✅ Parsed {len(results)} fundamental records.")
        return results

    except Exception as e:
        print(f"[ERROR] fetch_fundamentals_from_jquants: {e}")
        return []
