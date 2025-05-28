"""
ranker.py
PJ Fire — Final Refactored Version

Responsible for scoring, ranking, and ordering candidate stocks after filtering
for mean reversion, trend, or other strategies.
- Imports scoring rules and signal logic
- Outputs top N tickers, scores, and reasons for downstream modules
- All scoring and ranking rules are parameterized
"""

import pandas as pd
from typing import List, Dict, Any

# --- Scoring Weights and Criteria (Move to config.py if needed) ---
WEIGHTS = {
    'price_drop_pct': 3.0,
    'gpt_reason_score': 2.0,
    'fundamental_strength': 1.5,
    'volume_spike': 1.0,
    # Add others as needed
}

SCORE_CUTOFF = 0.0  # Minimum score to be considered
TOP_N = 10           # Number of tickers to return


def score_candidate(c: Dict[str, Any]) -> float:
    """
    Compute composite score for a candidate stock.
    - c: Dict containing keys such as price_drop_pct, gpt_reason_score, fundamental_strength, etc.
    """
    score = 0.0
    for k, w in WEIGHTS.items():
        v = c.get(k, 0)
        score += w * v
    return round(score, 3)


def rank_candidates(candidates: List[Dict[str, Any]], top_n=TOP_N) -> List[Dict[str, Any]]:
    """
    Scores and ranks the candidate stocks.
    Returns the top N ranked stocks as a list of dicts, sorted by descending score.
    """
    for c in candidates:
        c['score'] = score_candidate(c)
    # Optional: filter out below-cutoff
    filtered = [c for c in candidates if c['score'] >= SCORE_CUTOFF]
    # Sort and return top N
    ranked = sorted(filtered, key=lambda x: x['score'], reverse=True)[:top_n]
    return ranked


def get_top_signals_for_day(candidates: List[Dict[str, Any]], strategy: str = 'mean_reversion') -> List[Dict[str, Any]]:
    """
    Main entry point: given a list of dicts (candidates with features),
    returns the top signals to execute for the day.
    Optionally filters by strategy if needed.
    """
    # Example: for now, just call rank_candidates
    # In future, strategy-specific filtering/scoring goes here
    return rank_candidates(candidates, top_n=TOP_N)


if __name__ == "__main__":
    # Simple test/demo
    test_candidates = [
        {'ticker': '7203', 'price_drop_pct': -0.07, 'gpt_reason_score': 1, 'fundamental_strength': 0.8, 'volume_spike': 1},
        {'ticker': '9984', 'price_drop_pct': -0.15, 'gpt_reason_score': 2, 'fundamental_strength': 0.9, 'volume_spike': 0},
        {'ticker': '8058', 'price_drop_pct': -0.03, 'gpt_reason_score': 0.5, 'fundamental_strength': 0.5, 'volume_spike': 1},
    ]
    results = get_top_signals_for_day(test_candidates)
    for r in results:
        print(r)
