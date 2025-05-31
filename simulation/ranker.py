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

def score_candidate(candidate: Dict[str, Any]) -> float:
    """
    Compute composite score for a candidate stock.
    Any missing field is treated as zero.
    """
    score = 0.0
    for k, w in WEIGHTS.items():
        v = candidate.get(k, 0) or 0
        score += w * v
    return round(score, 3)

def rank_candidates(candidates: List[Dict[str, Any]], top_n: int = None) -> List[Dict[str, Any]]:
    """
    Scores and ranks the candidate stocks.
    Returns the top N ranked stocks as a list of dicts, sorted by descending score.
    """
    for c in candidates:
        c['score'] = score_candidate(c)
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
