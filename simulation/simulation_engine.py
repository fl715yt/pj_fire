# simulation_engine.py

from datetime import datetime
from simulation.portfolio import (
    get_cash,
    update_cash,
    get_open_positions,
    log_sim_trade
)
from simulation.logger import log_info, log_warning
from utils.config import FORCED_EXIT_THRESHOLD, DEFAULT_LOT_SIZE


def evaluate_forced_exit(new_stock, held_stocks):
    """
    If any held stock has a lower score by > threshold, return its ticker for forced exit.
    """
    for held in held_stocks:
        if (
            new_stock["score"] >= held["score"] * (1 + FORCED_EXIT_THRESHOLD)
            and new_stock["score"] > 0
        ):
            return held["ticker"]
    return None


def simulate_trades(ranked_stocks, strategy_name="mean_reversion"):
    """
    Main simulation logic. Executes 1 trade per day based on ranking and available cash.
    """
    today = datetime.now().strftime("%Y-%m-%d")
    cash = get_cash()
    held_tickers = set(get_open_positions())
    executed = False

    for stock in ranked_stocks:
        ticker = stock["ticker"]
        price = stock["price"]
        score = stock["score"]

        if ticker in held_tickers:
            continue

        # Forced exit logic (1-for-1 swap)
        to_exit = evaluate_forced_exit(stock, ranked_stocks)
        if to_exit:
            log_info(f"♻️ Forced exit triggered: {to_exit} → {ticker}")
            # Remove the exited stock
            held_tickers.remove(to_exit)

        # Position sizing
        max_affordable = int(cash // price)
        shares = min(DEFAULT_LOT_SIZE, max_affordable)

        if shares < 1:
            log_warning(f"❌ Skipping {ticker}: Not enough cash.")
            continue

        cost = shares * price
        update_cash(cash - cost)
        log_sim_trade(ticker, strategy_name, price, shares, today)

        log_info(f"✅ Simulated BUY: {ticker} x{shares} @ ¥{price:.2f}")
        executed = True
        break  # One trade per day

    if not executed:
        log_info("📭 No trades executed today.")
