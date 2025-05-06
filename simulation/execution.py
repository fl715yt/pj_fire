from simulation.portfolio import get_cash, update_cash, get_open_positions
from simulation.logger import log_simulated_trade, log_forced_exit
from datetime import datetime

FORCED_EXIT_THRESHOLD = 0.05  # 5% higher score
LOT_SIZE = 100


def calculate_position_size(price: float, cash_available: float):
    max_affordable = int(cash_available // price)
    return max_affordable if max_affordable > 0 else 0


def evaluate_forced_exit(new_stock, held_stocks):
    for held in held_stocks:
        if (
            new_stock['score'] >= held['score'] * (1 + FORCED_EXIT_THRESHOLD)
            and new_stock['score'] > 0
        ):
            return held['ticker']
    return None


def decide_entry_and_exit(ranked_stocks: list, today: str):
    """
    Input: ranked_stocks - list of dicts with keys like ticker, price, score
           today - YYYY-MM-DD string
    """
    sim_cash = get_simulation_cash()
    held_stocks = get_held_stocks()
    executed_trades = []

    for stock in ranked_stocks:
        price = stock['price']
        ticker = stock['ticker']

        # Skip if already held
        if ticker in [h['ticker'] for h in held_stocks]:
            continue

        # Check if we need to force-exit a lower-scoring stock
        to_exit = evaluate_forced_exit(stock, held_stocks)
        if to_exit:
            log_forced_exit(to_exit, today)
            held_stocks = [h for h in held_stocks if h['ticker'] != to_exit]

        # Re-check cash after any exits
        sim_cash = get_simulation_cash()
        qty = calculate_position_size(price, sim_cash)
        if qty == 0:
            continue

        # Simulate buy
        cost = qty * price
        update_simulation_cash(-cost)
        log_simulated_trade(ticker, today, price, qty)

        executed_trades.append({
            'ticker': ticker,
            'buy_price': price,
            'qty': qty,
            'score': stock['score']
        })

    return executed_trades
