# test_simulation.py

from simulation.simulation_engine import run_simulation

# Dummy test data — should reflect structure from ranker.py
ranked_stocks = [
    {
        "ticker": "7203.T",  # Toyota
        "price": 2225.0,
        "score": 0.87
    },
    {
        "ticker": "6758.T",  # Sony
        "price": 13980.0,
        "score": 0.84
    },
    {
        "ticker": "9432.T",  # NTT
        "price": 170.0,
        "score": 0.78
    },
]

# Run the test
run_simulation(ranked_stocks, strategy_name="mean_reversion")
