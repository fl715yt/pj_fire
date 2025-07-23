"""
PJ Fire — Strategy Module Interface Contract

Each strategy's `generate_signals()` must:
    - Accept (conn, date, regime_override=None, model=None)
    - Return a list of signal dicts, each with (at minimum):
        - 'ticker'
        - 'date'
        - 'strategy'
        - 'score' and/or 'ml_score_norm'
        - any other fields required by the execution and logging pipeline

All screening, filtering, ML, and (if needed) reasoning logic must be *inside* the strategy.
No cross-strategy imports or dependencies allowed.
"""


from strategies.common.screening import screen_stocks
from strategies.common.ml_scoring import score_candidates_with_ml, get_model_path
from strategies.common.ranker import get_top_signals_for_day
from strategies.mean_reversion.reasoning import attach_reason_to_candidates
from simulation.regime import is_regime_blocked

from config.config import (
    DROP_PCT_THRESHOLD,
    RSI_THRESHOLD,
    MIN_VOLUME,
    SCORE_FILTER_THRESHOLD,
    ENABLE_SCORE_FILTER,
)

import joblib

# Allowed reason categories for mean reversion
ALLOWED_REASON_CATEGORIES = {"no_news", "misinterpreted_news"}

def generate_mean_reversion_signals(conn, date, regime_override=None, model=None):
    """
    Runs mean reversion screening, GPT reasoning, ML scoring, and ranking for the given date.
    Returns ranked candidate signals ready for execution.
    """
    # 1. Screening step — already does regime-aware regime field computation
    candidates = screen_stocks(
        conn,
        date,
        drop_pct_threshold=DROP_PCT_THRESHOLD,
        rsi_threshold=RSI_THRESHOLD,
        min_volume=MIN_VOLUME,
        strategy="mean_reversion"
    )
    if not candidates:
        print(f"[MeanReversion] No candidates after screening on {date}.")
        return []

    # 2. Regime-aware gating (global for strategy)
    market_regime = candidates[0]["market_regime"] if candidates else "unknown"
    if is_regime_blocked("mean_reversion", market_regime):
        print(f"[MeanReversion] Blocking signals due to regime={market_regime}.")
        return []

    # 3. Attach GPT reasoning (now local function, no date param)
    candidates = attach_reason_to_candidates(conn, candidates)
    if not candidates:
        print(f"[MeanReversion] No candidates after GPT reasoning on {date}.")
        return []

    # 4. Filter by allowed reason categories
    candidates = [
        c for c in candidates
        if c.get("reason_category") in ALLOWED_REASON_CATEGORIES
    ]
    if not candidates:
        print(f"[MeanReversion] No candidates after reason_category filter on {date}.")
        return []

    # 5. ML scoring — always load the model for this strategy unless passed explicitly
    if model is None:
        model = joblib.load(get_model_path("mean_reversion"))
    candidates = score_candidates_with_ml(candidates, model=model)

    # 6. Score-based gating
    if ENABLE_SCORE_FILTER:
        candidates = [
            c for c in candidates
            if c.get("ml_score_norm", 0) >= SCORE_FILTER_THRESHOLD
        ]
        if not candidates:
            print(f"[MeanReversion] No candidates passed ML score filter on {date}.")
            return []

    # 7. Final ranking
    ranked_signals = get_top_signals_for_day(
        candidates,
        strategy="mean_reversion",
        regime=regime_override or candidates[0]["regime"]
    )
    print(f"[MeanReversion] Final ranked signals on {date}: {len(ranked_signals)} candidates.")

    return ranked_signals

if __name__ == "__main__":
    import sqlite3
    conn = sqlite3.connect("backtest/backtest_bt.db")
    signals = generate_mean_reversion_signals(conn, "2024-03-15")
    for s in signals:
        print(s)
