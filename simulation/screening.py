"""
PJ Fire — Screening Logic (Optimized Logging)
Logs only summary stats for technical filter fails (counts + a few sample tickers).
Logs all higher-level (reasoning) exclusions individually.
"""

import os
import pandas as pd
from simulation.technical import add_indicators
from simulation.db_utils import get_prices, get_fundamentals, get_quarterly_fundamentals
from simulation.fundamental_features import extract_fy_features, extract_ttm_features, is_broken_fundamental
from simulation.logger import log_info

from config.config import (
    UNIVERSE_CSV,
    MIN_VOLUME,
    DROP_PCT_THRESHOLD,
    RSI_THRESHOLD,
    USE_FUNDAMENTAL_FILTER
)

TECH_FILTERS = [
    "empty_data", "missing_date", "no_row_after_indicators", "low_volume", "no_prev_day", "prev_close_zero",
    "fails_technical"
]

def load_universe():
    df = pd.read_csv(UNIVERSE_CSV, dtype=str)
    sector_col = "sector17" if "sector17" in df.columns else ("sector" if "sector" in df.columns else None)
    if sector_col is None:
        raise ValueError("Ticker universe CSV must have 'sector17' or 'sector' column.")
    df = df.set_index("ticker")
    return df, sector_col

def screen_stocks(conn, date, drop_pct_threshold=DROP_PCT_THRESHOLD, rsi_threshold=RSI_THRESHOLD, min_volume=MIN_VOLUME):
    """
    Returns list of candidate dicts for the given date (with sector17/sector attached).
    Logs summary stats for all technical filter fails.
    Logs all higher-level exclusions individually elsewhere.
    """
    universe, sector_col = load_universe()
    candidates = []

    # Track fails for summary stats (reason -> [tickers])
    fail_counts = {f: [] for f in TECH_FILTERS}

    for ticker, meta in universe.iterrows():
        sector_val = meta[sector_col]
        df = get_prices(conn, ticker)
        # --- Data present? ---
        if df.empty:
            fail_counts["empty_data"].append(ticker)
            continue
        if "date" not in df.columns or date not in df["date"].values:
            fail_counts["missing_date"].append(ticker)
            continue
        df = add_indicators(df)
        row = df[df["date"] == date]
        if row.empty:
            fail_counts["no_row_after_indicators"].append(ticker)
            continue
        row = row.iloc[0]
        # --- Volume filter ---
        try:
            vol = float(row["volume"])
        except Exception:
            vol = 0
        if vol < min_volume:
            fail_counts["low_volume"].append(ticker)
            continue
        # --- Price drop filter ---
        idxs = df.index[df["date"] == date]
        if len(idxs) == 0:
            fail_counts["no_row_after_indicators"].append(ticker)
            continue
        idx = idxs[0]
        if idx == 0:
            fail_counts["no_prev_day"].append(ticker)
            continue
        prev_close = df.iloc[idx-1]["close"]
        if prev_close == 0:
            fail_counts["prev_close_zero"].append(ticker)
            continue
        price_drop_pct = (row["close"] - prev_close) / prev_close

        # --- Volume spike ---
        start_idx = max(idx - 20, 0)
        avg_volume = df.iloc[start_idx:idx]["volume"].mean() if idx > 0 else 0
        volume_spike = (vol / avg_volume) if avg_volume > 0 else 0

        # --- Technical filter ---
        if price_drop_pct >= drop_pct_threshold or row["rsi_14"] >= rsi_threshold:
            fail_counts["fails_technical"].append(ticker)
            continue

        # --- Fundamental filter (if enabled) ---
        if USE_FUNDAMENTAL_FILTER:
            df_fy = get_fundamentals(conn, ticker, period_type="FY", n=5)
            df_q = get_quarterly_fundamentals(conn, ticker, n=4)
            fy_feat = extract_fy_features(df_fy) if not df_fy.empty else {}
            ttm_feat = extract_ttm_features(df_q) if not df_q.empty else {}
            if is_broken_fundamental(fy_feat, ttm_feat):
                # This will be logged individually by higher-level logic (not here).
                continue

        candidate = {
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
        }
        candidates.append(candidate)

    # ---- LOG SUMMARY STATS (after loop) ----
    total = len(universe)
    msg_lines = [f"Screened {total} stocks on {date}:"]
    for key in TECH_FILTERS:
        count = len(fail_counts[key])
        if count > 0:
            # Show up to 3 sample tickers for each fail reason
            samples = ", ".join(fail_counts[key][:3]) + ("..." if count > 3 else "")
            msg_lines.append(f"  {key}: {count} ({samples})")
    n_pass = len(candidates)
    msg_lines.append(f"  Passed all technicals: {n_pass}")
    log_info(" | ".join(msg_lines))

    return candidates

if __name__ == "__main__":
    import sqlite3
    conn = sqlite3.connect("backtest/backtest_bt.db")
    candidates = screen_stocks(conn, "2024-03-15")
    print(pd.DataFrame(candidates).head())
