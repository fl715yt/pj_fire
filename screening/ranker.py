import pandas as pd

# Scoring weights for mean reversion strategy
MEAN_REVERSION_WEIGHTS = {
    "price_drop_pct": 0.35,
    "rsi": 0.20,
    "revenue_growth": 0.15,
    "net_income_positive": 0.10,
    "equity_ratio_check": 0.10,
    "tdnet_risk": 0.00,  # Filter — not a score
    "reason_category": 0.10,
}

def normalize_series(series):
    return (series - series.min()) / (series.max() - series.min() + 1e-9)

def score_mean_reversion(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # ─── Step 1: TDnet Filter ─────────────────────
    df["tdnet_risk"] = df["tdnet_risk"].fillna(0)
    df["score"] = 0
    df.loc[df["tdnet_risk"] == 1, "score"] = 0
    df = df[df["tdnet_risk"] == 0]

    if df.empty:
        return df

    # ─── Step 2: Score Components ─────────────────

    # Price drop: higher is better (normalize)
    df["score_price_drop"] = normalize_series(df["price_drop_pct"]) * MEAN_REVERSION_WEIGHTS["price_drop_pct"]

    # RSI: lower is better → inverted + normalized
    df["score_rsi"] = (1 - normalize_series(df["rsi"])) * MEAN_REVERSION_WEIGHTS["rsi"]

    # Revenue Growth: keep as-is if ≥ 0, else 0
    df["revenue_growth"] = df["revenue_growth"].fillna(-1)
    df["score_revenue"] = df["revenue_growth"].apply(lambda x: x if x >= 0 else 0) * MEAN_REVERSION_WEIGHTS["revenue_growth"]

    # Net Income Positive: 1 if positive, 0 if not
    df["score_net_income"] = df["net_income"].apply(lambda x: 1 if x > 0 else 0) * MEAN_REVERSION_WEIGHTS["net_income_positive"]

    # Equity Ratio > 33% or Debt/Equity < 2.0
    df["score_equity"] = df.apply(
        lambda row: MEAN_REVERSION_WEIGHTS["equity_ratio_check"] if (row["equity_ratio"] and row["equity_ratio"] > 33) else 0,
        axis=1
    )

    # Reason Score Mapping
    REASON_SCORES = {
        "misinterpreted_news": 1.0,
        "slightly_bad_news": 0.5,
        "unknown_or_no_news": 0.8,
        "very_bad_news": 0.0,
        "macro_or_sector": 0.0,
    }
    df["score_reason"] = df["reason_category"].map(REASON_SCORES).fillna(0) * MEAN_REVERSION_WEIGHTS["reason_category"]

    # ─── Step 3: Combine ─────────────────────────
    df["score"] = (
        df["score_price_drop"] +
        df["score_rsi"] +
        df["score_revenue"] +
        df["score_net_income"] +
        df["score_equity"] +
        df["score_reason"]
    )

    # ─── Step 4: Final Sort ───────────────────────
    df = df.sort_values(by="score", ascending=False).reset_index(drop=True)
    return df
