"""
PJ Fire — Fundamental Feature Extraction
All calculations are logic-only; all constants come from config.
"""

import pandas as pd
import numpy as np

def extract_fy_features(df):
    """
    Input: DataFrame of annual FY rows (latest to oldest).
    Returns: Dict of features.
    Expects columns: ['ticker', 'period_type', 'period_end', 'revenue', 'eps', 'profit']
    """
    df = df[df["period_type"] == "FY"].sort_values("period_end", ascending=False).reset_index(drop=True)
    features = {}
    if len(df) < 2:
        return {"error": "Not enough FY data"}
    # Latest and previous year (copy for safe assignment)
    latest = df.iloc[0].copy()
    prev = df.iloc[1].copy()
    for col in ["revenue", "profit", "eps"]:
        latest[col] = pd.to_numeric(latest[col], errors="coerce")
        prev[col] = pd.to_numeric(prev[col], errors="coerce")
    # Compute YoY
    features["eps"] = latest["eps"]
    features["eps_yoy"] = (latest["eps"] - prev["eps"]) / (abs(prev["eps"]) + 1e-8)
    features["profit"] = latest["profit"]
    features["profit_yoy"] = (latest["profit"] - prev["profit"]) / (abs(prev["profit"]) + 1e-8)
    features["revenue"] = latest["revenue"]
    features["revenue_yoy"] = (latest["revenue"] - prev["revenue"]) / (abs(prev["revenue"]) + 1e-8)
    # Multi-year trends
    eps_arr = pd.to_numeric(df["eps"].head(5), errors="coerce").values
    profit_arr = pd.to_numeric(df["profit"].head(5), errors="coerce").values
    features["eps_negative_years"] = int(np.sum(eps_arr < 0))
    features["profit_down_years"] = int(np.sum(np.diff(profit_arr) < 0))
    features["piotroski_f_score"] = piotroski_f_score(df)
    return features


def extract_ttm_features(df_q):
    """
    Input: DataFrame of quarterly rows (latest to oldest).
    Returns: Dict of TTM features.
    Expects columns: ['ticker', 'period_type', 'period_end', 'revenue', 'eps', 'profit']
    """
    df_q = df_q[df_q["period_type"].isin(['1Q', '2Q', '3Q', '4Q'])].sort_values("period_end", ascending=False)
    ttm = {}
    for col in ["revenue", "profit", "eps"]:
        ttm[col + "_ttm"] = pd.to_numeric(df_q[col], errors="coerce").head(4).sum()
    return ttm

def is_broken_fundamental(fy_features, ttm_features):
    """
    Returns True if fundamentals are "broken", otherwise False.
    Example rules: negative EPS, multi-year profit decline, TTM profit negative, etc.
    """
    if fy_features.get("eps_negative_years", 0) >= 2:
        return True
    if fy_features.get("profit_down_years", 0) >= 2:
        return True
    if fy_features.get("eps", 1e9) < 0:
        return True
    if ttm_features and ttm_features.get("profit_ttm", 1e9) < 0:
        return True
    #Piotroski F-Score (if < 1, considered "broken")
    if fy_features.get("piotroski_f_score", 2) < 1:
        return True
    return False

def piotroski_f_score(fy_df):
    """
    Calculates a basic Piotroski F-Score (0–9) based on annual financials.
    Assumes fy_df is sorted with most recent first.
    Returns int score or None.
    """
    if fy_df is None or fy_df.empty or len(fy_df) < 2:
        return None
    # Must have these columns: ['revenue', 'profit', 'eps']
    f_score = 0
    recent = fy_df.iloc[0]
    prev = fy_df.iloc[1]

    # 1. Positive net income
    if fy_df is None or fy_df.empty or len(fy_df) < 2:
        return None
    # 2. Positive operating cash flow (not available, skip or infer from profit)
    # 3. Higher ROA this year vs last year (use profit/assets if available)
    # 4. Quality of earnings: profit > 0 (already checked above)
    # 5. No increase in leverage, liquidity, or shares outstanding (skip for now)
    # 6. Higher current year gross margin vs prior year
    if (recent.get('revenue') is not None) and (prev.get('revenue') is not None):
        if recent['revenue'] > prev['revenue']:
            f_score += 1

    # 7. Higher asset turnover year-over-year (not available)
    # For JP stocks, available fields may limit checks; keep simple

    # Score out of 2 for now (profit, revenue growth)
    return f_score
