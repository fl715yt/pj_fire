"""
PJ Fire — Data Fetcher Module

Centralized functions to fetch prices, fundamentals, and news
from external APIs (J-Quants, others). No direct DB writes here.
"""

import os
import requests
from config.config import (
    JQUANTS_DAILY_QUOTES, 
    JQUANTS_STATEMENTS, 
    JQUANTS_LISTED_INFO,
    JQUANTS_EMAIL,
    JQUANTS_PASSWORD
)
from utils.logger import log_info, log_warning, log_error

def fetch_jquants_token():
    """
    Authenticate with J-Quants and return the token.
    """
    url = "https://api.jquants.com/v1/token/auth_user"
    payload = {
        "mailaddress": JQUANTS_EMAIL,
        "password": JQUANTS_PASSWORD
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        token = response.json().get("token")
        if not token:
            log_error("Failed to obtain J-Quants token.")
            return None
        return token
    except Exception as e:
        log_error(f"J-Quants token fetch failed: {e}")
        return None

def fetch_daily_quotes(token, date):
    """
    Fetch daily quotes for all stocks for the given date.
    """
    headers = {"Authorization": f"Bearer {token}"}
    params = {"date": date}
    try:
        response = requests.get(JQUANTS_DAILY_QUOTES, headers=headers, params=params)
        response.raise_for_status()
        return response.json().get("daily_quotes", [])
    except Exception as e:
        log_error(f"Failed to fetch daily quotes for {date}: {e}")
        return []

def fetch_fundamentals(token, ticker=None):
    """
    Fetch full-year fundamentals for all or a specific ticker.
    """
    headers = {"Authorization": f"Bearer {token}"}
    params = {}
    if ticker:
        params["code"] = ticker
    try:
        response = requests.get(JQUANTS_STATEMENTS, headers=headers, params=params)
        response.raise_for_status()
        return response.json().get("statements", [])
    except Exception as e:
        log_error(f"Failed to fetch fundamentals: {e}")
        return []

def fetch_company_info(token):
    """
    Fetch ticker-to-company name mapping (required for displaying names).
    """
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.get(JQUANTS_LISTED_INFO, headers=headers)
        response.raise_for_status()
        return response.json().get("info", [])
    except Exception as e:
        log_error(f"Failed to fetch listed company info: {e}")
        return []

def fetch_news_for_ticker(ticker):
    """
    Placeholder for custom news retrieval function (TDNet, RSS, or vendor).
    To be implemented based on your preferred source.
    """
    # Implement logic as needed (requests, BeautifulSoup, etc.)
    log_warning(f"fetch_news_for_ticker not yet implemented for {ticker}.")
    return []

# Example usage:
# token = fetch_jquants_token()
# daily_quotes = fetch_daily_quotes(token, "2024-05-17")
# fundamentals = fetch_fundamentals(token)
# company_info = fetch_company_info(token)