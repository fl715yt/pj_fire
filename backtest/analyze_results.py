import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

def analyze_backtest(equity_curve: pd.Series, trades: pd.DataFrame, benchmark_curve: pd.Series = None):
    returns = equity_curve.pct_change().dropna()
    total_return = (equity_curve.iloc[-1] / equity_curve.iloc[0]) - 1
    years = (equity_curve.index[-1] - equity_curve.index[0]).days / 365
    cagr = (equity_curve.iloc[-1] / equity_curve.iloc[0])**(1/years) - 1 if years > 0 else np.nan

    running_max = equity_curve.cummax()
    dd = (equity_curve / running_max) - 1
    max_drawdown = dd.min()

    sharpe = returns.mean() / returns.std() * np.sqrt(252) if returns.std() > 0 else np.nan
    downside = returns[returns < 0]
    sortino = returns.mean() / downside.std() * np.sqrt(252) if not downside.empty and downside.std() > 0 else np.nan
    calmar = cagr / abs(max_drawdown) if max_drawdown != 0 else np.nan
    annual_vol = returns.std() * np.sqrt(252) if returns.std() > 0 else np.nan

    win_rate = (trades['pl'] > 0).mean() if not trades.empty else 0
    profit_factor = (trades.loc[trades['pl'] > 0, 'pl'].sum() / abs(trades.loc[trades['pl'] < 0, 'pl'].sum())) if not trades[trades['pl'] < 0].empty else np.nan
    avg_gain = trades.loc[trades['pl'] > 0, 'pl'].mean() if not trades[trades['pl'] > 0].empty else np.nan
    avg_loss = trades.loc[trades['pl'] < 0, 'pl'].mean() if not trades[trades['pl'] < 0].empty else np.nan
    trade_count = len(trades)
    if 'exit_date' in trades.columns and 'entry_date' in trades.columns:
        avg_hold = (pd.to_datetime(trades['exit_date']) - pd.to_datetime(trades['entry_date'])).dt.days.mean()
    else:
        avg_hold = np.nan

    monthly_returns = equity_curve.resample('M').last().pct_change().dropna()
    best_month = monthly_returns.max() if not monthly_returns.empty else np.nan
    worst_month = monthly_returns.min() if not monthly_returns.empty else np.nan
    best_trade = trades['pl'].max() if not trades.empty else np.nan
    worst_trade = trades['pl'].min() if not trades.empty else np.nan

    highs = equity_curve.cummax()
    under_water = equity_curve < highs
    stagnation_lengths = (under_water != under_water.shift()).cumsum()[under_water]
    longest_stagnation = stagnation_lengths.value_counts().max() if not stagnation_lengths.empty else 0

    if benchmark_curve is not None:
        bench_total_return = (benchmark_curve.iloc[-1] / benchmark_curve.iloc[0]) - 1
        bench_years = (benchmark_curve.index[-1] - benchmark_curve.index[0]).days / 365
        bench_cagr = (benchmark_curve.iloc[-1] / benchmark_curve.iloc[0])**(1/bench_years) - 1 if bench_years > 0 else np.nan
        alpha = cagr - bench_cagr
        beta = np.cov(returns, benchmark_curve.pct_change().dropna().reindex(returns.index).fillna(0))[0,1] / np.var(benchmark_curve.pct_change().dropna()) if np.var(benchmark_curve.pct_change().dropna()) > 0 else np.nan
    else:
        bench_total_return = bench_cagr = alpha = beta = np.nan

    summary = pd.DataFrame({
        'Metric': [
            'CAGR', 'Total Return', 'Max Drawdown', 'Sharpe Ratio', 'Sortino Ratio', 'Calmar Ratio',
            'Win Rate', 'Profit Factor', 'Avg Gain', 'Avg Loss', 'Trade Count', 'Avg Hold (days)',
            'Annualized Volatility', 'Best Month', 'Worst Month', 'Best Trade', 'Worst Trade',
            'Benchmark Return', 'Alpha', 'Beta', 'Longest Stagnation (days)'
        ],
        'Value': [
            f"{cagr*100:.2f}%", f"{total_return*100:.2f}%", f"{max_drawdown*100:.2f}%",
            f"{sharpe:.2f}", f"{sortino:.2f}", f"{calmar:.2f}",
            f"{win_rate*100:.2f}%", f"{profit_factor:.2f}",
            f"{avg_gain:.2f}", f"{avg_loss:.2f}", trade_count, f"{avg_hold:.2f}",
            f"{annual_vol*100:.2f}%", f"{best_month*100:.2f}%", f"{worst_month*100:.2f}%",
            f"{best_trade:.2f}", f"{worst_trade:.2f}",
            f"{bench_total_return*100:.2f}%", f"{alpha*100:.2f}%", f"{beta:.2f}", longest_stagnation
        ]
    })

    print("\n===== PJ Fire Backtest Performance Summary =====\n")
    print(summary.to_string(index=False))

    # --- CHARTS ---
    plt.figure()
    plt.plot(equity_curve, label='Strategy')
    if benchmark_curve is not None:
        plt.plot(benchmark_curve, label='Benchmark')
    plt.title('Equity Curve')
    plt.legend()
    plt.show()

    plt.figure()
    plt.plot(dd, label='Drawdown')
    plt.title('Drawdown Curve')
    plt.legend()
    plt.show()

    plt.figure()
    monthly_returns.plot(kind='bar')
    plt.title('Monthly Returns')
    plt.show()

    plt.figure()
    trades['pl'].hist(bins=30)
    plt.title('Trade PnL Distribution')
    plt.show()

    # --- EXPORTS ---
    summary.to_csv('backtest_summary.csv', index=False)
    trades.to_csv('backtest_trades.csv', index=False)

    # --- SUMMARY PARAGRAPH ---
    summary_text = (
        f"PJ Fire Backtest Results: The strategy produced a CAGR of {cagr*100:.2f}% with a max drawdown of {max_drawdown*100:.2f}%. "
        f"Sharpe ratio is {sharpe:.2f} and win rate is {win_rate*100:.2f}%. Profit factor is {profit_factor:.2f}. "
        f"Best month was {best_month*100:.2f}%, worst month was {worst_month*100:.2f}%. "
        f"Over {trade_count} trades, the average holding period was {avg_hold:.2f} days. "
        f"Compared to benchmark return of {bench_total_return*100:.2f}%, alpha was {alpha*100:.2f}% and beta {beta:.2f}. "
        f"Longest equity stagnation was {longest_stagnation} days. "
        f"Overall, these results are "
        f"{'acceptable' if cagr>0.07 and max_drawdown<0.20 and sharpe>1.0 else 'not acceptable'} based on professional standards."
    )
    print("\n===== Auto-Generated Analyst Summary =====\n")
    print(summary_text)
    return summary, summary_text

if __name__ == "__main__":
    # Adjust these paths as needed:
    equity_path = "backtest/outputs/equity_curve.csv"
    trades_path = "backtest/outputs/trades.csv"
    if not os.path.exists(equity_path) or not os.path.exists(trades_path):
        print(f"Missing equity curve or trades CSV in backtest/outputs/")
        exit(1)
    equity = pd.read_csv(equity_path, parse_dates=["date"], index_col="date")["equity"]
    trades = pd.read_csv(trades_path)
    analyze_backtest(equity, trades)
