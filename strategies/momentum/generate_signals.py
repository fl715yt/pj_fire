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
from strategies.common.ml_scoring import score_candidates_with_ml
from strategies.common.ranker import get_top_signals_for_day
from simulation.regime import is_regime_blocked

from config.config import (
    MIN_VOLUME,
    SCORE_FILTER_THRESHOLD,
    ENABLE_SCORE_FILTER
)

# Momentum strategy hyperparameters — tune later
MOMENTUM_LOOKBACK_DAYS = 5
MOMENTUM_MIN_RETURN = 0.03  # +3% over last 5 days
VOLUME_SPIKE_THRESHOLD = 1.5  # 1.5x avg volume

def generate_signals(conn, date, regime_override=None, model=None):
    """
    Runs momentum screening, ML scoring, and ranking for the given date.
    Returns ranked candidate signals ready for execution.
    """
    # 1. Screening step — base screening with no RSI / price_drop filters
    candidates = screen_stocks(
        conn,
        date,
        drop_pct_threshold=-1.0,  # disable price drop filter for momentum
        rsi_threshold=999,        # disable RSI filter
        min_volume=MIN_VOLUME,
        strategy="momentum"
    )
    if not candidates:
        print(f"[Momentum] No candidates after base screening on {date}.")
        return []

    # 2. Regime-aware gating (global for strategy)
    market_regime = candidates[0]["market_regime"] if candidates else "unknown"
    if is_regime_blocked("momentum", market_regime):
        print(f"[Momentum] Blocking signals due to regime={market_regime}.")
        return []

    # 3. Apply simple momentum logic — filter on recent price momentum and volume spike
    filtered_candidates = []
    for c in candidates:
        ma5 = c.get("ma5", 0)
        ma25 = c.get("ma25", 0)
        momentum_signal = (ma5 > ma25)
        volume_ok = c.get("volume_spike", 0) >= VOLUME_SPIKE_THRESHOLD
        price_ok = c.get("price_drop_pct", 0) >= MOMENTUM_MIN_RETURN  # positive return

        if momentum_signal and volume_ok and price_ok:
            filtered_candidates.append(c)

    if not filtered_candidates:
        print(f"[Momentum] No candidates passed momentum filters on {date}.")
        return []

    # 4. ML scoring
    filtered_candidates = score_candidates_with_ml(filtered_candidates, model=model)

    # 5. Score-based gating
    if ENABLE_SCORE_FILTER:
        filtered_candidates = [
            c for c in filtered_candidates
            if c.get("ml_score_norm", 0) >= SCORE_FILTER_THRESHOLD
        ]
        if not filtered_candidates:
            print(f"[Momentum] No candidates passed ML score filter on {date}.")
            return []

    # 6. Final ranking
    ranked_signals = get_top_signals_for_day(
        filtered_candidates,
        strategy="momentum",
        regime=regime_override or filtered_candidates[0]["regime"]
    )
    print(f"[Momentum] Final ranked signals on {date}: {len(ranked_signals)} candidates.")

    return ranked_signals

if __name__ == "__main__":
    import sqlite3
    conn = sqlite3.connect("backtest/backtest_bt.db")
    signals = generate_signals(conn, "2024-03-15")
    for s in signals:
        print(s)
