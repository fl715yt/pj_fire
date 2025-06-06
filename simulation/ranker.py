"""
PJ Fire — Signal Ranker (Config-Driven, Robust)
Scores and ranks candidate stocks after full filtering.
- All scoring parameters, cutoffs, and ranking counts are imported from config.
- Explicitly handles missing features for stable ranking.
"""

from typing import List, Dict, Any
from config.config import (
    WEIGHTS,                 # dict, e.g. {"price_drop_pct": 3.0, ...}
    SCORE_CUTOFF,            # minimum total score for candidate inclusion
    TOP_N_RANK,              # candidates forwarded to signal stage
    MAX_SIGNAL_PER_DAY,      # (optional) user-facing upper bound
)

SCORING_WEIGHTS = {
    "price_drop": 1.0,
    "rsi": 0.7,
    "ma5_dist": 1.0,
    "volume_spike": 0.5,
    "gpt_category": 0.6,
}

MAX_SCORE = (
    SCORING_WEIGHTS["price_drop"] * 0.07 +          # capped at 7%
    SCORING_WEIGHTS["rsi"] * 0.714 +                # (70-20)/70
    SCORING_WEIGHTS["ma5_dist"] * 0.05 +            # capped at 5%
    SCORING_WEIGHTS["volume_spike"] * 3.0 +         # capped at 3x
    SCORING_WEIGHTS["gpt_category"] * 1.0           # max boost
)  # = 2.72 if default

def score_candidate(candidate):
    # Cap each feature
    price_drop = min(abs(candidate.get("price_drop_pct", 0)), 0.07)
    rsi = max(min(candidate.get("rsi_14", 70), 80), 20)
    rsi_component = (70 - rsi) / 70
    ma5_dist = min(
        (candidate.get("ma5", 0) - candidate.get("price", 0)) / candidate.get("ma5", 1) if candidate.get("ma5") else 0, 
        0.05)
    volume_spike = min(candidate.get("volume_spike", 0), 3.0)
    gpt_category_boost = candidate.get("gpt_category_boost", 0)

    # Raw score
    raw_score = (
        SCORING_WEIGHTS["price_drop"] * price_drop +
        SCORING_WEIGHTS["rsi"] * rsi_component +
        SCORING_WEIGHTS["ma5_dist"] * ma5_dist +
        SCORING_WEIGHTS["volume_spike"] * volume_spike +
        SCORING_WEIGHTS["gpt_category"] * gpt_category_boost
    )
    normalized_score = (raw_score / MAX_SCORE) * 100

    candidate["score"] = raw_score
    candidate["normalized_score"] = round(normalized_score, 1)  # e.g., 72.4 out of 100

    return candidate

def rank_candidates(candidates: List[Dict[str, Any]], top_n: int = None) -> List[Dict[str, Any]]:
    """
    Scores and ranks the candidate stocks.
    Returns the top N ranked stocks as a list of dicts, sorted by descending score.
    """
    for i, c in enumerate(candidates):
        candidates[i] = score_candidate(c)
    filtered = [c for c in candidates if c['score'] >= SCORE_CUTOFF]
    top_n = top_n or TOP_N_RANK
    ranked = sorted(filtered, key=lambda x: x['score'], reverse=True)[:top_n]
    return ranked

def get_top_signals_for_day(candidates: List[Dict[str, Any]], strategy: str = 'mean_reversion') -> List[Dict[str, Any]]:
    """
    Returns the top signals to execute for the day, after all scoring/ranking.
    If both TOP_N_RANK and MAX_SIGNAL_PER_DAY are set, the smaller value is enforced.
    """
    limit = min(TOP_N_RANK, MAX_SIGNAL_PER_DAY)
    return rank_candidates(candidates, top_n=limit)

# --- Demo/Test Block ---
if __name__ == "__main__":
    test_candidates = [
        {'ticker': '7203', 'price_drop_pct': -0.07, 'gpt_reason_score': 1, 'fundamental_strength': 0.8, 'volume_spike': 1},
        {'ticker': '9984', 'price_drop_pct': -0.15, 'gpt_reason_score': 2, 'fundamental_strength': 0.9, 'volume_spike': 0},
        {'ticker': '8058', 'price_drop_pct': -0.03, 'gpt_reason_score': 0.5, 'fundamental_strength': 0.5, 'volume_spike': 1},
    ]
    results = get_top_signals_for_day(test_candidates)
    for r in results:
        print(r)
