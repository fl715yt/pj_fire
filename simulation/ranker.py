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
    Scores a single candidate based on config-driven weights.
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

    # Optional: add more features as needed

    c["score"] = score
    # Simple normalization: scale out of 100 (max possible, or leave as-is if no upper bound)
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

def get_top_signals_for_day(candidates: List[Dict[str, Any]], strategy: str = 'mean_reversion') -> List[Dict[str, Any]]:
    """
    Returns the top signals to execute for the day, after all scoring/ranking.
    If both TOP_N_RANK and MAX_SIGNAL_PER_DAY are set, the smaller value is enforced.
    """
    limit = min(TOP_N_RANK, MAX_SIGNAL_PER_DAY)
    ranked = rank_candidates(candidates, top_n=limit)
    # Add strategy field for downstream tracking/logging
    for c in ranked:
        c["strategy"] = strategy
    return ranked

# No demo/test block, no unused scoring weights, no magic numbers.
