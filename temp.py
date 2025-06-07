import sqlite3
conn = sqlite3.connect("backtest/backtest_bt.db")
conn.execute("DELETE FROM cash")
conn.commit()


from simulation.simulation_engine import init_simulation_db
init_simulation_db("backtest/backtest_bt.db", 1_000_000)