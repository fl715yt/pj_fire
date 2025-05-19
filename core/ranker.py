"""
PJ Fire — Stock Ranking Module

Ranks screened stock candidates using weighted criteria.
All weights and ranking logic are imported from config or hard-coded here (as approved).
Returns a sorted list of dicts with rank/score.
"""

from config.config import FORCED_EXIT_THRESHOLD
from utils.logger import log_info

# Example weights (set/adjust as needed)
WEIGHTS = {
    "price_drop": 0.5,    # Strong mean reversion signal
    "eps": 0.2,           # Profitability/strength
    "profit": 0.2,        # Ditto
    "gpt_score": 0.1,     # Optional sentiment overlay
    # Add other weights as you confirm them
}

def rank_stocks(candidates):
    """
    Scores and ranks candidate stocks.
    :param candidates: List of dicts, output of screen_stocks()
    :return: Ranked list of dicts (highest score first)
    """
    ranked = []
    for c in candidates:
        # Example scoring logic
        score = 0
        # 1. Price drop: bigger drop = higher score (inverted sign since price_drop_pct is negative)
        score += WEIGHTS["price_drop"] * abs(c["price_drop_pct"])
        # 2. EPS (normalized)
        if c.get("eps"):
            score += WEIGHTS["eps"] * float(c["eps"]) / 100  # Adjust divisor as appropriate
        # 3. Profit (normalized)
        if c.get("profit"):
            score += WEIGHTS["profit"] * float(c["profit"]) / 1e9  # Adjust divisor as appropriate
        # 4. GPT sentiment/qualitative overlay (optional, e.g., 0-1 score)
        if "gpt_score" in c:
            score += WEIGHTS["gpt_score"] * c["gpt_score"]
        # Extend with more signals as needed

        c["score"] = score
        ranked.append(c)

    ranked_sorted = sorted(ranked, key=lambda x: x["score"], reverse=True)
    log_info(f"Ranked {len(ranked_sorted)} stock candidates.")
    return ranked_sorted

# Example usage:
# ranked = rank_stocks(candidates)

