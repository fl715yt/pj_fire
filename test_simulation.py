# test_simulation.py
import pandas as pd
from simulation_engine import simulate_trades

# Dummy test data
test_df = pd.DataFrame({
    "ticker": ["9101.T", "6758.T"],
    "close_price": [3000.0, 15000.0],
    "score": [0.92, 0.85],
})

def test_simulate():
    print("Running simulation test...")
    simulate_trades(test_df)

if __name__ == "__main__":
    test_simulate()