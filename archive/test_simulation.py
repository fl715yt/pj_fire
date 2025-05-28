# simulation/test_simulation.py
"""
Basic test runner for simulation engine, portfolio, and logger.
Use this to verify logic after refactors.
"""

from simulation.simulation_engine import run_simulation_for_day
from datetime import datetime, timedelta

def run_tests():
    print("[TEST] Starting simulation tests...")

    today = datetime.now()
    for days_ago in range(3, 0, -1):
        date = (today - timedelta(days=days_ago)).strftime("%Y-%m-%d")
        print(f"\n[TEST] Running for {date} ...")
        run_simulation_for_day(date)

    print("[TEST] All simulation engine runs complete.")

if __name__ == "__main__":
    run_tests()
