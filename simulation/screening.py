"""
PJ Fire — Screening Logic (Backtest & Simulation, Macro/Sector-Aware)
Loads universe from CSV (with sector17), prices from DB, computes technicals, and runs all filters.
Outputs candidates with sector17 for use in macro/sector reasoning and scoring.
"""

import os
import pandas as pd
from simulation.technical import add_indicators
from simulation.db_utils import get_conn, get_prices, get_fundamentals, get_quarterly_fundamentals
from simulation.fundamental_features import extract_fy_features, extract_ttm_features, is_broken_fundamental

# Set CSV path and DB connection
UNIVERSE_CSV = os.getenv("PJ_FIRE_UNIVERSE_CSV", "pjfire_topix_company_patterns_expanded.csv")
MIN_VOLUME = 10000           # Volume threshold (change as needed)
DROP_PCT_THRESHOLD = -0.04   # -4% price drop or more
RSI_THRESHOLD = 30           # RSI under 30 for signal
USE_FUNDAMENTAL_FILTER = True

def load_universe():
    df = pd.read_csv(UNIVERSE_CSV, dtype=str)
    if "sector17" not in df.columns:
        raise ValueError("pjfire_topix_company_patterns_expanded.csv must have 'sector17' column")
    df = df.set_index("ticker")
    return df

def screen_stocks(conn, date, drop_pct_threshold=DROP_PCT_THRESHOLD, rsi_threshold=RSI_THRESHOLD, min_volume=MIN_VOLUME):
    """
    Returns list of candidate dicts for the given date (with sector17 attached).
    Each dict has: ticker, date, price, price_drop_pct, rsi_14, ma5, ma25, sector17, volume, etc.
    """
    universe = load_universe()
    candidates = []
    for ticker, meta in universe.iterrows():
        sector17 = meta["sector17"]
        df = get_prices(conn, ticker)
        if df.empty or date not in df["date"].values:
            continue
        df = add_indicators(df)
        row = df[df["date"] == date]
        if row.empty:
            continue
        row = row.iloc[0]
        # --- Volume filter ---
        if "volume" not in row or pd.isna(row["volume"]) or float(row["volume"]) < min_volume:
            continue
        # Compute price drop % vs prev close
        idx = df.index[df["date"] == date][0]
        if idx == 0:
            continue  # no prev day
        prev_close = df.iloc[idx-1]["close"]
        if prev_close == 0:
            continue
        price_drop_pct = (row["close"] - prev_close) / prev_close
        # --- Technical filters ---
        if price_drop_pct < drop_pct_threshold and row["rsi_14"] < rsi_threshold:
            # --- Fundamental filter (optional, can be toggled off for testing) ---
            if USE_FUNDAMENTAL_FILTER:
                df_fy = get_fundamentals(conn, ticker, period_type="FY", n=5)
                df_q = get_quarterly_fundamentals(conn, ticker, n=4)
                fy_feat = extract_fy_features(df_fy) if not df_fy.empty else {}
                ttm_feat = extract_ttm_features(df_q) if not df_q.empty else {}
                if is_broken_fundamental(fy_feat, ttm_feat):
                    continue
            candidates.append({
                "ticker": ticker,
                "sector17": sector17,
                "date": date,
                "price": row["close"],
                "price_drop_pct": price_drop_pct,
                "rsi_14": row["rsi_14"],
                "ma5": row["ma5"],
                "ma25": row["ma25"],
                "volume": row["volume"],
                # Add more fields as needed
            })
    return candidates

if __name__ == "__main__":
    # Example usage/test
    import sqlite3
    conn = sqlite3.connect("backtest/backtest_bt.db")
    candidates = screen_stocks(conn, "2024-03-15")
    print(pd.DataFrame(candidates).head())
