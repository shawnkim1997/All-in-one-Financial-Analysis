"""Backtesting service for simple strategies."""

from __future__ import annotations


async def run_backtest(
    ticker: str,
    strategy: str,
    start_date: str,
    end_date: str,
    initial_capital: float = 10000.0,
) -> dict:
    """Run a basic backtest for selected strategy."""
    import yfinance as yf
    import ta

    df = yf.Ticker(ticker.upper()).history(start=start_date, end=end_date)
    if df is None or df.empty:
        return {"error": "No price data"}

    if strategy == "sma_crossover":
        df["sma50"] = ta.trend.sma_indicator(df["Close"], 50)
        df["sma200"] = ta.trend.sma_indicator(df["Close"], 200)
        df["signal"] = (df["sma50"] > df["sma200"]).astype(int)
    elif strategy == "rsi_oversold":
        df["rsi"] = ta.momentum.rsi(df["Close"], 14)
        df["signal"] = 0
        df.loc[df["rsi"] < 30, "signal"] = 1
        df.loc[df["rsi"] > 70, "signal"] = 0
    else:
        df["signal"] = 1

    df["returns"] = df["Close"].pct_change().fillna(0)
    df["strategy_returns"] = (df["returns"] * df["signal"].shift(1)).fillna(0)
    cumulative = (1 + df["strategy_returns"]).cumprod()
    benchmark = (1 + df["returns"]).cumprod()

    return {
        "total_return_pct": round((float(cumulative.iloc[-1]) - 1) * 100, 2),
        "benchmark_return_pct": round((float(benchmark.iloc[-1]) - 1) * 100, 2),
        "alpha": round((float(cumulative.iloc[-1]) - float(benchmark.iloc[-1])) * 100, 2),
        "max_drawdown_pct": round(float(((cumulative / cumulative.cummax()) - 1).min()) * 100, 2),
        "sharpe_ratio": round(float(df["strategy_returns"].mean() / (df["strategy_returns"].std() + 1e-10) * (252 ** 0.5)), 2),
        "equity_curve": [float(x) for x in cumulative.tolist()],
        "benchmark_curve": [float(x) for x in benchmark.tolist()],
        "dates": df.index.strftime("%Y-%m-%d").tolist(),
    }
