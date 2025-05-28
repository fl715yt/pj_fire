"""
PJ Fire — Unified Reasoning Module
Classifies/categorizes reason for stock price drops, using:
- GPT-based news analysis (primary if available)
- Fundamentals (FY and TTM/quarterly)
- Event-driven checks (earnings, macro, etc.)
Usable in both simulation and backtest.
"""

import os
import pandas as pd
import time
from dotenv import load_dotenv
from simulation.db_utils import get_fundamentals, get_quarterly_fundamentals
from simulation.fundamental_features import extract_fy_features, extract_ttm_features, is_broken_fundamental
from simulation.fetch_news import fetch_news_for_ticker
from simulation.news_reason_gpt import categorize_reason_with_gpt, CATEGORY_SCORING

# --- CONFIG ---
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GPT_MODEL = os.getenv("PJ_FIRE_GPT_MODEL", "gpt-4o")
GPT_DELAY_SEC = 1.2

REASONING_CATEGORY_LABELS = [
    "misinterpreted_news",
    "slightly_bad_news",
    "very_bad_news",
    "no_news",
    "macro_or_sector_drop"
]

def categorize_drop_reason(conn, ticker, drop_date, price_drop_pct, use_gpt=True):
    """
    Returns:
      reason_category: e.g. "misinterpreted_news", "very_bad_news", etc.
      explanation: str (for logs/display)
      fy_features: dict
      ttm_features: dict
      headlines: str
    """
    # --- 1. Fetch news headlines ---
    headlines = fetch_news_for_ticker(ticker, drop_date)
    gpt_category = None

    # --- 2. Try GPT-based news categorization ---
    if use_gpt:
        gpt_category = categorize_reason_with_gpt(ticker, drop_date, price_drop_pct, headlines)
        score = CATEGORY_SCORING.get(gpt_category, 0.0)
        if score == 0.0:
            explanation = f"[EXCLUDED] {ticker} {drop_date} due to GPT category: {gpt_category}"
            return gpt_category, explanation, {}, {}, headlines
        # If the GPT category is "misinterpreted_news" or "slightly_bad_news" or "no_news", continue to fundamental checks below.
        # If it's "very_bad_news" or "macro_or_sector_drop", treat as excluded and return here.

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
            last_fy_disclose = pd.to_datetime(df_fy.iloc[0]["CurrentPeriodEndDate"])
            if abs((pd.to_datetime(drop_date) - last_fy_disclose).days) <= 2:
                event_driven = True
                event_detail = f"Drop within 2 days of annual earnings ({last_fy_disclose.date()})"
        except Exception: pass
    if not df_q.empty:
        try:
            last_q_disclose = pd.to_datetime(df_q.iloc[0]["CurrentPeriodEndDate"])
            if abs((pd.to_datetime(drop_date) - last_q_disclose).days) <= 2:
                event_driven = True
                event_detail = f"Drop within 2 days of quarterly earnings ({last_q_disclose.date()})"
        except Exception: pass

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

    return reason, explanation, fy_feat, ttm_feat, headlines

# For backtest, just do:
# from simulation.reasoning import categorize_drop_reason

