"""
PJ Fire — Screening Logic (Backtest & Simulation)
Loads universe from CSV, prices from DB, computes technicals and runs all filters.
"""

import os
import pandas as pd
from simulation.technical import add_indicators
from simulation.db_utils import get_conn, get_prices, get_fundamentals, get_quarterly_fundamentals
from simulation.fundamental_features import extract_fy_features, extract_ttm_features, is_broken_fundamental

# Set CSV path and DB connection
UNIVERSE_CSV = os.getenv("PJ_FIRE_UNIVERSE_CSV", "pjfire_topix_company_patterns_expanded.csv")

def load_ticker_universe():
    df = pd.read_csv(UNIVERSE_CSV, dtype=str)
    return df["ticker"].astype(str).tolist()

def screen_stocks(conn, date, drop_pct_threshold=-0.04, rsi_threshold=30, min_volume=100000):
    """
    Returns list of candidate dicts:
    [{
        'ticker': ...,
        'date': ...,
        'price': ...,
        'price_drop_pct': ...,
        'rsi_14': ...,
        'ma5': ...,
        'ma25': ...,
        ...
    }]
    """
    tickers = load_ticker_universe()
    candidates = []
    for ticker in tickers:
        df = get_prices(conn, ticker)
        if df.empty or date not in df["date"].values:
            continue
        df = add_indicators(df)
        row = df[df["date"] == date]
        if row.empty:
            continue
        row = row.iloc[0]
        # --- Volume filter ---
        if "volume" not in row or pd.isna(row["volume"]) or row["volume"] < min_volume:
            continue
        # Compute price drop % vs prev close
        idx = df.index[df["date"] == date][0]
        if idx == 0:
            continue  # no prev day
        prev_close = df.iloc[idx-1]["close"]
        if prev_close == 0:
            continue
        price_drop_pct = (row["close"] - prev_close) / prev_close
        # --- Technical & fundamental filters ---
        if price_drop_pct < drop_pct_threshold and row["rsi_14"] < rsi_threshold:
            # Fundamental health
            df_fy = get_fundamentals(conn, ticker, period_type="FY", n=5)
            df_q = get_quarterly_fundamentals(conn, ticker, n=4)
            fy_feat = extract_fy_features(df_fy) if not df_fy.empty else {}
            ttm_feat = extract_ttm_features(df_q) if not df_q.empty else {}
            if is_broken_fundamental(fy_feat, ttm_feat):
                continue
            candidates.append({
                "ticker": ticker,
                "date": date,
                "price": row["close"],
                "price_drop_pct": price_drop_pct,
                "rsi_14": row["rsi_14"],
                "ma5": row["ma5"],
                "ma25": row["ma25"],
                # Add more as needed...
            })
    return candidates
