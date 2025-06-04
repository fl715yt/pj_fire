"""
PJ Fire — Screening Logic (Backtest & Simulation, Macro/Sector-Aware)
Loads universe from CSV (with sector17), prices from DB, computes technicals, and runs all filters.
Outputs candidates with sector17 for use in macro/sector reasoning and scoring.
"""

import os
import pandas as pd
from simulation.technical import add_indicators
from simulation.db_utils import get_prices, get_fundamentals, get_quarterly_fundamentals
from simulation.fundamental_features import extract_fy_features, extract_ttm_features, is_broken_fundamental

from config.config import (
    UNIVERSE_CSV,
    MIN_VOLUME,
    DROP_PCT_THRESHOLD,
    RSI_THRESHOLD,
    USE_FUNDAMENTAL_FILTER
)

def load_universe():
    df = pd.read_csv(UNIVERSE_CSV, dtype=str)
    # Try sector17; fallback to sector or error
    sector_col = "sector17" if "sector17" in df.columns else ("sector" if "sector" in df.columns else None)
    if sector_col is None:
        raise ValueError("Ticker universe CSV must have 'sector17' or 'sector' column.")
    df = df.set_index("ticker")
    return df, sector_col

def screen_stocks(conn, date, drop_pct_threshold=DROP_PCT_THRESHOLD, rsi_threshold=RSI_THRESHOLD, min_volume=MIN_VOLUME):
    """
    Returns list of candidate dicts for the given date (with sector17/sector attached).
    Each dict has: ticker, date, price, price_drop_pct, rsi_14, ma5, ma25, sector17, volume, etc.
    """
    universe, sector_col = load_universe()
    candidates = []
    for ticker, meta in universe.iterrows():
        sector_val = meta[sector_col]
        df = get_prices(conn, ticker)
        # Defensive: Ensure 'date' column exists and is not empty
        if df.empty or "date" not in df.columns or date not in df["date"].values:
            if df.empty:
                print(f"[WARN] Ticker {ticker}: price data is empty.")
            elif "date" not in df.columns:
                print(f"[WARN] Ticker {ticker}: no 'date' column in price data.")
            else:
                print(f"[WARN] Ticker {ticker}: {date} not found in price data.")
            continue
        df = add_indicators(df)
        row = df[df["date"] == date]
        if row.empty:
            continue
        row = row.iloc[0]
        # --- Volume filter ---
        try:
            vol = float(row["volume"])
        except Exception:
            vol = 0
        if vol < min_volume:
            continue
        # Compute price drop % vs prev close
        idxs = df.index[df["date"] == date]
        if len(idxs) == 0:
            continue
        idx = idxs[0]
        if idx == 0:
            continue  # no prev day
        prev_close = df.iloc[idx-1]["close"]
        if prev_close == 0:
            continue
        price_drop_pct = (row["close"] - prev_close) / prev_close

        # Compute volume spike vs 20-day average
        start_idx = max(idx - 20, 0)
        avg_volume = df.iloc[start_idx:idx]["volume"].mean() if idx > 0 else 0
        volume_spike = (vol / avg_volume) if avg_volume > 0 else 0

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
                sector_col: sector_val,
                "date": date,
                "price": row["close"],
                "price_drop_pct": price_drop_pct,
                "rsi_14": row["rsi_14"],
                "ma5": row["ma5"],
                "ma25": row["ma25"],
                "volume": vol,
                "volume_spike": volume_spike,
                # Add more fields as needed for scoring/GPT
            })
    return candidates

if __name__ == "__main__":
    import sqlite3
    conn = sqlite3.connect("backtest/backtest_bt.db")
    candidates = screen_stocks(conn, "2024-03-15")
    print(pd.DataFrame(candidates).head())
