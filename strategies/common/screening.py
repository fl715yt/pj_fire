"""
PJ Fire — Screening Logic (Regime-Aware, ML-Ready)
- Adds regime features (market & sector) to every candidate.
- Gating: skips mean reversion in 'bear' or 'volatile' market.
- Logs summary stats for technical filter fails (counts + sample tickers).
- Logs all higher-level (reasoning) exclusions individually.
"""

import os
import pandas as pd
from strategies.common.technical import add_indicators
from simulation.db_utils import get_prices, get_fundamentals, get_quarterly_fundamentals
from strategies.common.fundamental_features import extract_fy_features, extract_ttm_features, is_broken_fundamental
from simulation.logger import log_info
from simulation.regime import calc_market_regime, calc_sector_regime  # <--- new

from config.config import (
    UNIVERSE_CSV,
    MIN_VOLUME,
    DROP_PCT_THRESHOLD,
    RSI_THRESHOLD,
    USE_FUNDAMENTAL_FILTER,
    MARKET_ETF,
    SECTOR_ETF_MAP
)

TECH_FILTERS = [
    "empty_data", "missing_date", "no_row_after_indicators", "low_volume", "no_prev_day", "prev_close_zero",
    "fails_technical", "regime_blocked"
]

def load_universe():
    df = pd.read_csv(UNIVERSE_CSV, dtype=str)
    sector_col = "sector17" if "sector17" in df.columns else ("sector" if "sector" in df.columns else None)
    if sector_col is None:
        raise ValueError("Ticker universe CSV must have 'sector17' or 'sector' column.")
    df = df.set_index("ticker")
    return df, sector_col

def screen_stocks(
    conn, date,
    drop_pct_threshold=DROP_PCT_THRESHOLD,
    rsi_threshold=RSI_THRESHOLD,
    min_volume=MIN_VOLUME,
    strategy="mean_reversion",
    regime=None  # ignore input; will set per candidate
):
    """
    Returns list of candidate dicts for the given date (with sector17/sector and regime attached).
    Regime is computed per-candidate and also attached as 'market_regime', 'sector_regime'.
    Gating: mean reversion is skipped in bear/volatile regime.
    """
    universe, sector_col = load_universe()
    candidates = []
    fail_counts = {f: [] for f in TECH_FILTERS}

    # --- Preload market ETF data for regime detection
    market_df = get_prices(conn, "{}0".format(MARKET_ETF))
    # print("MARKET_ETF QUERY:", "{}0".format(MARKET_ETF))
    # print("market_df shape:", market_df.shape)
    # print("market_df dates min/max:", market_df['date'].min(), market_df['date'].max())
    # print("date being checked:", date)
    # print("All available dates (head):", market_df['date'].tolist()[:10])
    # print("All available dates (tail):", market_df['date'].tolist()[-10:])
    if market_df.empty or date not in market_df["date"].values:
        raise RuntimeError(f"Market ETF data missing for {date}")
    market_regime = calc_market_regime(market_df[market_df["date"] <= date].tail(22))  # Use last 20-22 days

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
                continue

        # --- Sector regime detection (ETF or peer mean) ---
        sector_regime = None
        if sector_val in SECTOR_ETF_MAP:
            sector_etf = SECTOR_ETF_MAP[sector_val]
            sector_df = get_prices(conn, sector_etf)
            if not sector_df.empty and date in sector_df["date"].values:
                sector_regime = calc_sector_regime(sector_df[sector_df["date"] <= date].tail(22))
            else:
                sector_regime = "stable"
        else:
            # fallback: stable (or you can code sector mean logic)
            sector_regime = "stable"

        # --- Regime gating: skip mean reversion in bear or volatile
        if strategy == "mean_reversion" and market_regime in ("bear", "volatile"):
            fail_counts["regime_blocked"].append(ticker)
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
            "strategy": strategy,
            "market_regime": market_regime,
            "sector_regime": sector_regime,
            "regime": market_regime,  # for downstream pipeline logic; change to combined if desired
            "raw_regime_features": {  # for ML use
                "market_mean_return": float(market_df["close"].pct_change(20).iloc[-1]),
                "market_volatility": float(market_df["close"].pct_change().rolling(20).std().iloc[-1]),
                "sector": sector_val,
                "sector_mean_return": float(sector_df["close"].pct_change(20).iloc[-1]) if 'sector_df' in locals() and not sector_df.empty else 0.0,
                "sector_volatility": float(sector_df["close"].pct_change().rolling(20).std().iloc[-1]) if 'sector_df' in locals() and not sector_df.empty else 0.0,
            }
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
    msg_lines.append(f"  Passed all technicals+regime: {n_pass}")
    log_info(" | ".join(msg_lines))

    return candidates

if __name__ == "__main__":
    import sqlite3
    conn = sqlite3.connect("backtest/backtest_bt.db")
    candidates = screen_stocks(conn, "2024-03-15")
    print(pd.DataFrame(candidates).head())
