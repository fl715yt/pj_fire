# 📁 Folder: simulation/

import sqlite3
from datetime import datetime

DB_FILE = "db/pj_fire.db"


def execute_trade(ticker, quantity, price, trade_type, strategy, reason):
    """
    Executes a trade and logs it into sim_trades table.
    """
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Insert trade into log
    cur.execute("""
        INSERT INTO sim_trades (
            datetime, ticker, quantity, price, trade_type, strategy, reason
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (now, ticker, quantity, price, trade_type, strategy, reason))

    # Update portfolio
    if trade_type == "buy":
        cur.execute("""
            INSERT INTO portfolio (ticker, quantity, avg_price)
            VALUES (?, ?, ?)
            ON CONFLICT(ticker) DO UPDATE SET
                quantity = quantity + excluded.quantity,
                avg_price = (
                    (portfolio.quantity * portfolio.avg_price + excluded.quantity * excluded.avg_price)
                    / (portfolio.quantity + excluded.quantity)
                )
        """, (ticker, quantity, price))

        cur.execute("""
            UPDATE sim_cash
            SET balance = balance - ?
        """, (quantity * price,))

    elif trade_type == "sell":
        cur.execute("""
            UPDATE portfolio
            SET quantity = quantity - ?
            WHERE ticker = ?
        """, (quantity, ticker))

        cur.execute("""
            DELETE FROM portfolio
            WHERE ticker = ? AND quantity <= 0
        """, (ticker,))

        cur.execute("""
            UPDATE sim_cash
            SET balance = balance + ?
        """, (quantity * price,))

    conn.commit()
    conn.close()


if __name__ == "__main__":
    # 🔧 Example manual test run
    execute_trade(
        ticker="7203.T",
        quantity=100,
        price=2000,
        trade_type="buy",
        strategy="mean_reversion",
        reason="Oversold with good fundamentals"
    )
