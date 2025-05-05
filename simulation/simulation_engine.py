# simulation_engine.py
from datetime import datetime
from portfolio import get_cash, update_cash, get_open_positions, log_sim_trade

DEFAULT_LOT_SIZE = 100


def simulate_trades(ranked_df, strategy_name="mean_reversion"):
    today = datetime.now().strftime("%Y-%m-%d")
    available_cash = get_cash()
    open_positions = set(get_open_positions())

    for _, row in ranked_df.iterrows():
        ticker = row["ticker"]
        price = row["close_price"]

        if ticker in open_positions:
            continue

        trade_amount = price * DEFAULT_LOT_SIZE
        if trade_amount > available_cash:
            affordable_shares = int(available_cash // price)
            if affordable_shares < 1:
                continue
            shares = affordable_shares
        else:
            shares = DEFAULT_LOT_SIZE

        log_sim_trade(ticker, strategy_name, price, shares, today)
        update_cash(available_cash - (price * shares))
        print(f"[SIM] Bought {shares} shares of {ticker} @ {price:.2f} ({strategy_name})")
        break  # Buy only 1 per day for now