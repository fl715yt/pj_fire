"""
PJ Fire — ML Scoring Integration Module (XGBoost Version)
- Supports model load, inference, and scoring for any candidate list.
- Can be used in both backtest and simulation/production.
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Any

import xgboost as xgb
import joblib
import os

ML_MODEL_PATH = "model/pjfire_ml_model_xgb.pkl"  # Change as needed

# ---- FEATURE LIST: update to match your feature engineering ----
MODEL_FEATURES = [
    # Core technicals
    "price_drop_pct",
    "rsi_14",
    "ma5", "ma25",
    "volume_spike",
    # Regime features
    "market_mean_return",
    "market_volatility",
    "sector_mean_return",
    "sector_volatility",
    # Candlestick, zscore, atr, etc.
    "zscore_20",
    "atr_14",
    "volatility5",
    "candlestick_reversal",
    # Fundamentals (optional, if present)
    "eps", "eps_yoy", "profit", "profit_yoy", "revenue", "revenue_yoy",
    "piotroski_f_score",
    # Add more as needed
]

def extract_features(candidate: Dict[str, Any]) -> np.ndarray:
    """
    Extract feature vector from candidate dict for ML model.
    """
    feats = []
    regime = candidate.get("raw_regime_features", {})
    for key in MODEL_FEATURES:
        if key in candidate:
            feats.append(candidate[key])
        elif key in regime:
            feats.append(regime[key])
        else:
            feats.append(0.0)
    return np.array(feats, dtype=float)

def score_candidates_with_ml(candidates: List[Dict[str, Any]], model=None):
    """
    For each candidate, produce ML score (probability) and normalized score.
    Attaches to each dict: .ml_score, .ml_score_norm (0-100).
    """
    if model is None:
        if os.path.exists(ML_MODEL_PATH):
            model = joblib.load(ML_MODEL_PATH)
        else:
            # Fallback: use random model if no real model found (REMOVE FOR PRODUCTION)
            print("[WARN] No ML model found; using random scoring.")
            for c in candidates:
                c["ml_score"] = np.random.rand()
                c["ml_score_norm"] = int(100 * c["ml_score"])
            return candidates

    X = np.array([extract_features(c) for c in candidates])
    # XGBoost always supports predict_proba
    probs = model.predict_proba(X)[:, 1]
    max_prob, min_prob = np.max(probs), np.min(probs)
    norm_scores = 100 * (probs - min_prob) / (max_prob - min_prob + 1e-8) if max_prob > min_prob else 100 * probs

    for i, c in enumerate(candidates):
        c["ml_score"] = float(probs[i])
        c["ml_score_norm"] = int(norm_scores[i])
    return candidates

def train_dummy_model():
    """
    Trains and saves a dummy XGBoost classifier for testing.
    This is for pipeline integration ONLY. Replace with your real data pipeline.
    """
    X = np.random.randn(100, len(MODEL_FEATURES))
    y = (np.random.rand(100) > 0.5).astype(int)
    model = xgb.XGBClassifier(use_label_encoder=False, eval_metric="logloss")
    model.fit(X, y)
    joblib.dump(model, ML_MODEL_PATH)
    print(f"Dummy XGBoost model trained and saved to {ML_MODEL_PATH}")
    return model

if __name__ == "__main__":
    # Train a dummy model if you just want to test end-to-end pipeline
    train_dummy_model()
    dummy_candidates = [{
        "price_drop_pct": -0.04, "rsi_14": 25, "ma5": 1000, "ma25": 1100,
        "volume_spike": 2.0, "zscore_20": -1.2, "atr_14": 50, "volatility5": 0.03,
        "candlestick_reversal": 1,
        "raw_regime_features": {
            "market_mean_return": 0.01, "market_volatility": 0.02,
            "sector_mean_return": 0.00, "sector_volatility": 0.025
        },
        "eps": 100, "eps_yoy": 0.15, "profit": 200, "profit_yoy": 0.12,
        "revenue": 5000, "revenue_yoy": 0.10,
        "piotroski_f_score": 2
    } for _ in range(5)]
    model = joblib.load(ML_MODEL_PATH)
    scored = score_candidates_with_ml(dummy_candidates, model=model)
    print(scored)
