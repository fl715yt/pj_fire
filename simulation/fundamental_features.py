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
    # Latest and previous year
    latest = df.iloc[0]
    prev = df.iloc[1]
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
    return False
