import pandas as pd

# Scoring weights for mean reversion strategy
MEAN_REVERSION_WEIGHTS = {
    "price_drop_pct": 0.35,
    "rsi": 0.20,
    "revenue_growth": 0.15,
    "net_income_positive": 0.10,
    "equity_ratio_check": 0.10,
    "tdnet_risk": 0.00,  # Used as a filter, not scoring
    "reason_category": 0.10,
}

# Reason category to score mapping
REASON_SCORES = {
    "misinterpreted_news": 1.0,
    "slightly_bad_news": 0.5,
    "unknown_or_no_news": 0.8,
    "very_bad_news": 0.0,
    "macro_or_sector": 0.0,
}

def normalize_series(series):
    return (series - series.min()) / (series.max() - series.min() + 1e-9)

def passes_equity_check(row):
    eq = row.get("equity_ratio")
    de = row.get("debt_to_equity_ratio")
    if eq is not None and eq > 33:
        return True
    if de is not None and de < 2.0:
        return True
    return False

def score_mean_reversion(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df["tdnet_risk"] = df["tdnet_risk"].fillna(0)
    df["net_income"] = df["net_income"].fillna(0)
    df["equity_ratio"] = df["equity_ratio"].fillna(0)
    df["debt_to_equity_ratio"] = df["debt_to_equity_ratio"].fillna(None)
    df["revenue_growth"] = df["revenue_growth"].fillna(-1)
    df["rsi"] = df["rsi"].fillna(50)
    df["price_drop_pct"] = df["price_drop_pct"].fillna(0)
    df["reason_category"] = df["reason_category"].fillna("unknown_or_no_news")

    df = df[df["tdnet_risk"] == 0]
    if df.empty:
        return df

    df["score_price_drop"] = normalize_series(df["price_drop_pct"]) * MEAN_REVERSION_WEIGHTS["price_drop_pct"]
    df["score_rsi"] = (1 - normalize_series(df["rsi"])) * MEAN_REVERSION_WEIGHTS["rsi"]
    df["score_revenue"] = df["revenue_growth"].apply(lambda x: x if x >= 0 else 0) * MEAN_REVERSION_WEIGHTS["revenue_growth"]
    df["score_net_income"] = df["net_income"].apply(lambda x: 1 if x > 0 else 0) * MEAN_REVERSION_WEIGHTS["net_income_positive"]
    df["score_equity"] = df.apply(lambda row: MEAN_REVERSION_WEIGHTS["equity_ratio_check"] if passes_equity_check(row) else 0, axis=1)
    df["score_reason"] = df["reason_category"].map(REASON_SCORES).fillna(0) * MEAN_REVERSION_WEIGHTS["reason_category"]

    df["score"] = (
        df["score_price_drop"] +
        df["score_rsi"] +
        df["score_revenue"] +
        df["score_net_income"] +
        df["score_equity"] +
        df["score_reason"]
    )

    return df.sort_values(by="score", ascending=False).reset_index(drop=True)
