"""
PJ Fire — Signal Ranker (Config-Driven, Clean, PATCHED)
Scores and ranks candidate stocks after all filtering, using only config-driven parameters.
Ensures candidates are never mutated in a way that breaks later logic.
Outputs all fields needed for logging, trading, and analysis.
"""

from typing import List, Dict, Any
from config.config import (
    WEIGHTS,                 # dict, e.g. {"price_drop_pct": 3.0, ...}
    SCORE_CUTOFF,            # minimum total score for candidate inclusion
    TOP_N_RANK,              # candidates forwarded to signal stage
    MAX_SIGNAL_PER_DAY,      # (optional) user-facing upper bound
)

def score_candidate(candidate: Dict[str, Any]) -> Dict[str, Any]:
    """
    Scores a single candidate based on config-driven weights + scoring modifiers.
    Returns a new dict with score and normalized_score fields added.
    Never mutates the original input dict.
    """
    # Defensive copy
    c = candidate.copy()
    # Required features: must default to 0 if missing
    price_drop = abs(c.get("price_drop_pct", 0))
    gpt_reason_score = c.get("gpt_reason_score", 0.0)
    fundamental_strength = c.get("fundamental_strength", 0.0)
    volume_spike = c.get("volume_spike", 0.0)

    # Use config weights (no hardcoding)
    score = (
        WEIGHTS.get("price_drop_pct", 0.0) * price_drop +
        WEIGHTS.get("gpt_reason_score", 0.0) * gpt_reason_score +
        WEIGHTS.get("fundamental_strength", 0.0) * fundamental_strength +
        WEIGHTS.get("volume_spike", 0.0) * volume_spike
    )

    # --- Candlestick pattern scoring (v1 logic, simple additive) ---
    bullish_patterns = ["is_hammer", "is_bullish_engulfing", "is_morning_star"]
    bearish_patterns = ["is_shooting_star", "is_bearish_engulfing", "is_evening_star"]

    pattern_score = 0
    for p in bullish_patterns:
        if c.get(p, False):
            pattern_score += 1
    for p in bearish_patterns:
        if c.get(p, False):
            pattern_score -= 1
    c["candlestick_score"] = pattern_score  # log for reference
    score += pattern_score  # incorporate into final score

    # === Score Modifiers: MA(5) Distance, Pre-trend, Volume Anomaly ===

    modifiers = {}

    # 1. MA(5) distance (%)
    ma5 = c.get("ma5")
    close = c.get("price")
    ma5_distance_pct = None
    if ma5 is not None and close:
        ma5_distance_pct = (ma5 - close) / close * 100
        c["ma5_distance_pct"] = ma5_distance_pct
        if 2.0 <= ma5_distance_pct <= 8.0:
            score += 7
            modifiers["ma5_distance"] = 7
        elif ma5_distance_pct < 1.0:
            modifiers["ma5_distance"] = 0
        elif ma5_distance_pct > 10.0:
            score -= 2
            modifiers["ma5_distance"] = -2

    # 2. Pre-drop 5-day trend (%)
    pre_trend_pct = c.get("pre_trend_pct")  # Should be computed in screening
    if pre_trend_pct is not None:
        if pre_trend_pct > 1.0:
            score += 4
            modifiers["pre_trend"] = 4
        else:
            modifiers["pre_trend"] = 0
    c["pre_trend_pct"] = pre_trend_pct

    # 3. Volume anomaly (spike ratio)
    volume_spike_ratio = c.get("volume_spike_ratio")  # Should be computed in screening
    if volume_spike_ratio is not None:
        if volume_spike_ratio > 2.0:
            score += 3
            modifiers["volume_anomaly"] = 3
        else:
            modifiers["volume_anomaly"] = 0
    c["volume_spike_ratio"] = volume_spike_ratio

    c["score_modifiers"] = modifiers

    c["score"] = score
    c["normalized_score"] = round(min(score * 20, 100), 1)  # Example: rescale, cap at 100

    return c

def rank_candidates(candidates: List[Dict[str, Any]], top_n: int = None) -> List[Dict[str, Any]]:
    """
    Scores and ranks the candidate stocks.
    Returns the top N ranked stocks as a list of dicts, sorted by descending score.
    Outputs all required fields for downstream modules.
    """
    scored = [score_candidate(c) for c in candidates]
    filtered = [c for c in scored if c['score'] >= SCORE_CUTOFF]
    top_n = top_n or TOP_N_RANK
    ranked = sorted(filtered, key=lambda x: x['score'], reverse=True)[:top_n]
    return ranked

def get_top_signals_for_day(
    candidates: List[Dict[str, Any]], 
    strategy: str = None,
    regime: str = None
) -> List[Dict[str, Any]]:
    """
    Returns the top signals to execute for the day, after all scoring/ranking.
    If both TOP_N_RANK and MAX_SIGNAL_PER_DAY are set, the smaller value is enforced.
    Propagates strategy/regime to output for downstream modules.
    """
    limit = min(TOP_N_RANK, MAX_SIGNAL_PER_DAY)
    ranked = rank_candidates(candidates, top_n=limit)
    for c in ranked:
        if strategy:
            c["strategy"] = strategy
        if regime:
            c["regime"] = regime
    return ranked
