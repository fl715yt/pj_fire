"""
PJ Fire — Unified Reasoning Module (Macro/Sector Hybrid, GPT, Fundamentals)
Classifies/categorizes reason for stock price drops, using:
- Macro/sector drop logic (ETF or sector mean, from config)
- GPT-based news analysis (category labels, model, and scoring from config)
- Fundamentals (FY, TTM/quarterly)
- Event-driven checks (earnings, macro, etc.)
Usable in both simulation and backtest.
"""

import os
import pandas as pd
import time
from config.config import (
    REASONING_CATEGORY_LABELS,
    SECTOR_ETF_MAP,
    CATEGORY_SCORING,
    UNIVERSE_CSV,
    GPT_DELAY_SEC,
    OPENAI_API_KEY,
    GPT_MODEL,
)
from simulation.db_utils import get_fundamentals, get_quarterly_fundamentals, get_prices
from simulation.fundamental_features import extract_fy_features, extract_ttm_features, is_broken_fundamental
from simulation.fetch_news import fetch_news_for_ticker
from simulation.news_reason_gpt import categorize_reason_with_gpt

def is_macro_or_sector_drop(
    conn, ticker, drop_date, price_drop_pct, sector_code=None,
    market_ticker="1306", sector_etf_map=SECTOR_ETF_MAP
):
    """
    Returns True if the drop is likely macro/sector-driven (ETF or sector mean).
    Tries sector ETF first; else falls back to sector mean.
    """
    # --- 1. Market ETF (TOPIX: 1306) ---
    try:
        market_df = get_prices(conn, market_ticker)
        m_row = market_df[market_df["date"] == drop_date]
        if not m_row.empty:
            market_idx = market_df.index[market_df["date"] == drop_date][0]
            if market_idx > 0:
                prev_market_close = market_df.iloc[market_idx-1]["close"]
                market_return = (m_row.iloc[0]["close"] - prev_market_close) / prev_market_close
            else:
                market_return = 0
        else:
            market_return = 0
    except Exception:
        market_return = 0

    # --- 2. Sector ETF (if mapping provided and ETF exists for sector) ---
    sector_etf_return = None
    if sector_etf_map and sector_code and sector_code in sector_etf_map:
        sector_etf = sector_etf_map[sector_code]
        try:
            etf_df = get_prices(conn, sector_etf)
            etf_row = etf_df[etf_df["date"] == drop_date]
            if not etf_row.empty:
                etf_idx = etf_df.index[etf_df["date"] == drop_date][0]
                if etf_idx > 0:
                    prev_etf_close = etf_df.iloc[etf_idx-1]["close"]
                    if prev_etf_close != 0:
                        sector_etf_return = (etf_row.iloc[0]["close"] - prev_etf_close) / prev_etf_close
        except Exception:
            sector_etf_return = None

    # --- 3. Sector mean fallback ---
    sector_mean_return = None
    if (sector_etf_return is None) and sector_code:
        try:
            universe = pd.read_csv(UNIVERSE_CSV, dtype=str)
            sector_tickers = universe[universe["sector17"] == sector_code]["ticker"].tolist()
            returns = []
            for s in sector_tickers:
                df = get_prices(conn, s)
                s_row = df[df["date"] == drop_date]
                if not s_row.empty:
                    s_idx = df.index[df["date"] == drop_date][0]
                    if s_idx > 0:
                        prev_close = df.iloc[s_idx-1]["close"]
                        if prev_close != 0:
                            returns.append((s_row.iloc[0]["close"] - prev_close) / prev_close)
            if returns:
                sector_mean_return = sum(returns) / len(returns)
        except Exception:
            sector_mean_return = None

    # --- 4. Decision logic: macro or sector-driven? ---
    for ref_return in [market_return, sector_etf_return, sector_mean_return]:
        if ref_return is not None:
            if abs(price_drop_pct - ref_return) < 0.015:
                return True
            if price_drop_pct < 0 and abs(price_drop_pct) < abs(ref_return) * 1.5:
                return True
    return False

def categorize_drop_reason(conn, ticker, drop_date, price_drop_pct, sector_code=None, use_gpt=True):
    """
    Returns:
      reason_category: e.g. "misinterpreted_news", "very_bad_news", etc.
      explanation: str (for logs/display)
      fy_features: dict
      ttm_features: dict
      headlines: str
      event_driven: bool
    """
    # --- Macro/Sector check (before anything else!) ---
    if is_macro_or_sector_drop(conn, ticker, drop_date, price_drop_pct, sector_code=sector_code):
        return "macro_or_sector_drop", "Drop matches market/sector move.", {}, {}, "", False

    # --- 1. Fetch news headlines ---
    headlines = fetch_news_for_ticker(ticker, drop_date)
    gpt_category = None

    # --- 2. Try GPT-based news categorization ---
    if use_gpt:
        gpt_category = categorize_reason_with_gpt(ticker, drop_date, price_drop_pct, headlines)
        score = CATEGORY_SCORING.get(gpt_category, 0.0)
        if score == 0.0:
            explanation = f"[EXCLUDED] {ticker} {drop_date} due to GPT category: {gpt_category}"
            return gpt_category, explanation, {}, {}, headlines, False  # << add 'False'

    # --- 3. Fundamentals: FY + Quarterly/TTM ---
    df_fy = get_fundamentals(conn, ticker, period_type="FY", n=5)
    df_q = get_quarterly_fundamentals(conn, ticker, n=4)
    fy_feat = extract_fy_features(df_fy) if not df_fy.empty else {}
    ttm_feat = extract_ttm_features(df_q) if not df_q.empty else {}

    # --- 4. Event-driven? (drop coincides with new FY/quarter disclosure) ---
    event_driven = False
    event_detail = ""
    if not df_fy.empty:
        try:
            last_fy_disclose = pd.to_datetime(df_fy.iloc[0].get("period_end"))
            if abs((pd.to_datetime(drop_date) - last_fy_disclose).days) <= 2:
                event_driven = True
                event_detail = f"Drop within 2 days of annual earnings ({last_fy_disclose.date()})"
        except Exception:
            pass
    if not df_q.empty:
        try:
            last_q_disclose = pd.to_datetime(df_q.iloc[0].get("period_end"))
            if abs((pd.to_datetime(drop_date) - last_q_disclose).days) <= 2:
                event_driven = True
                event_detail = f"Drop within 2 days of quarterly earnings ({last_q_disclose.date()})"
        except Exception:
            pass

    # --- 5. Broken fundamental? ---
    broken = is_broken_fundamental(fy_feat, ttm_feat)

    # --- 6. Compose reason/explanation ---
    explanation = ""
    if gpt_category:
        explanation = f"GPT reason: {gpt_category}. "
    if event_driven and broken:
        reason = "fundamental-driven"
        explanation += (f"{event_detail}. EPS: {fy_feat.get('eps','?')}, EPS YoY: {fy_feat.get('eps_yoy','?'):.1%}, "
                        f"Profit TTM: {ttm_feat.get('profit_ttm','?')}. Broken multi-year trend detected.")
    elif broken:
        reason = "broken"
        explanation += "Stock failed fundamental health checks (negative EPS, profit downtrend, or negative TTM profit)."
    elif gpt_category:
        reason = gpt_category
    else:
        reason = "technical/unknown"
        explanation += "No clear fundamental or news reason for this drop."

    return reason, explanation, fy_feat, ttm_feat, headlines, event_driven  # << always 6

def attach_reason_to_candidates(conn, candidates, use_gpt=True, verbose=False):
    """
    For a list of candidate dicts, attaches:
      - reason_category
      - reason_explanation
      - fy_features
      - ttm_features
      - headlines
    Drops candidates with excluded GPT categories (very_bad_news, macro_or_sector_drop, fundamental-driven, broken).
    Returns filtered & enriched list.
    """
    enriched = []
    for c in candidates:
        ticker = c["ticker"]
        date = c["date"]
        price_drop_pct = c.get("price_drop_pct", 0)
        sector_code = c.get("sector17", None)
        # Run the canonical drop reason classifier
        reason, explanation, fy_feat, ttm_feat, headlines, event_driven = categorize_drop_reason(
            conn, ticker, date, price_drop_pct, sector_code=sector_code, use_gpt=use_gpt
        )
        # Exclude if reason is a filter-out category
        if reason in ["very_bad_news", "macro_or_sector_drop", "fundamental-driven", "broken"]:
            if verbose:
                print(f"[SKIP] {ticker} {date}: {reason} ({explanation})")
            continue
        c["reason_category"] = reason
        c["reason_explanation"] = explanation
        c["fy_features"] = fy_feat
        c["ttm_features"] = ttm_feat
        c["headlines"] = headlines
        c["gpt_reason_score"] = CATEGORY_SCORING.get(reason, 0.0)
        c["fundamental_strength"] = fy_feat.get("eps_yoy", 0) if fy_feat else 0
        c["recent_earnings_release"] = event_driven
        enriched.append(c)

        if verbose:
            print(f"[PASS] {ticker} {date}: {reason} ({explanation})")
        # Optional: avoid hitting API rate limits
        if use_gpt:
            time.sleep(GPT_DELAY_SEC)
    return enriched
