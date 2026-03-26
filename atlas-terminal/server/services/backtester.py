"""Backtesting service for simple strategies.

Uses **adjusted** close prices (``auto_adjust=True``) so splits/dividends do not
distort returns.  Survivorship bias is **not** removed — the ticker must exist
today; historical universes require a separate constituent database.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional


def _months_between(a: Any, b: Any) -> int:
    return (b.year - a.year) * 12 + (b.month - a.month)


def _run_backtest_impl(
    ticker: str,
    strategy: str,
    start_date: str,
    end_date: str,
    initial_capital: float = 10000.0,
    benchmark_ticker: str = "SPY",
    rebalance_months: Optional[int] = None,
) -> Dict[str, Any]:
    import yfinance as yf
    import ta

    sym = ticker.upper()
    bm_sym = (benchmark_ticker or "SPY").upper()

    df = yf.Ticker(sym).history(
        start=start_date,
        end=end_date,
        auto_adjust=True,
    )
    if df is None or df.empty:
        return {"error": "No price data"}

    price = df["Close"]

    if strategy == "sma_crossover":
        df = df.copy()
        df["sma50"] = ta.trend.sma_indicator(price, 50)
        df["sma200"] = ta.trend.sma_indicator(price, 200)
        df["signal"] = (df["sma50"] > df["sma200"]).astype(int)
    elif strategy == "rsi_oversold":
        df = df.copy()
        df["rsi"] = ta.momentum.rsi(price, 14)
        df["signal"] = 0
        df.loc[df["rsi"] < 30, "signal"] = 1
        df.loc[df["rsi"] > 70, "signal"] = 0
    else:
        df = df.copy()
        df["signal"] = 1

    if rebalance_months is not None and int(rebalance_months) >= 1:
        months = int(rebalance_months)
        raw = df["signal"].astype(float)
        last_rebal = None
        hold = 0.0
        carried: list[float] = []
        for dt in df.index:
            if last_rebal is None or _months_between(last_rebal, dt) >= months:
                last_rebal = dt
                hold = float(raw.loc[dt])
            carried.append(hold)
        df["signal"] = carried

    bm_hist = yf.Ticker(bm_sym).history(
        start=start_date,
        end=end_date,
        auto_adjust=True,
    )
    if bm_hist is None or bm_hist.empty:
        return {"error": f"No benchmark data for {bm_sym}"}

    common = df.index.intersection(bm_hist.index)
    if len(common) < 5:
        return {"error": "Insufficient overlap between asset and benchmark history"}

    df = df.loc[common]
    price = df["Close"]
    bm_close = bm_hist.loc[common, "Close"]

    df["returns"] = price.pct_change().fillna(0)
    bm_returns = bm_close.pct_change().fillna(0)

    df["strategy_returns"] = (df["returns"] * df["signal"].shift(1)).fillna(0)
    cumulative = (1 + df["strategy_returns"]).cumprod()
    benchmark = (1 + bm_returns).cumprod()

    return {
        "ticker": sym,
        "benchmark_ticker": bm_sym,
        "total_return_pct": round((float(cumulative.iloc[-1]) - 1) * 100, 2),
        "benchmark_return_pct": round((float(benchmark.iloc[-1]) - 1) * 100, 2),
        "alpha": round((float(cumulative.iloc[-1]) - float(benchmark.iloc[-1])) * 100, 2),
        "max_drawdown_pct": round(float(((cumulative / cumulative.cummax()) - 1).min()) * 100, 2),
        "sharpe_ratio": round(
            float(df["strategy_returns"].mean() / (df["strategy_returns"].std() + 1e-10) * (252**0.5)),
            2,
        ),
        "equity_curve": [float(x) for x in cumulative.tolist()],
        "benchmark_curve": [float(x) for x in benchmark.tolist()],
        "dates": df.index.strftime("%Y-%m-%d").tolist(),
        "initial_capital": initial_capital,
        "rebalance_months": rebalance_months,
    }


async def run_backtest(
    ticker: str,
    strategy: str,
    start_date: str,
    end_date: str,
    initial_capital: float = 10000.0,
    benchmark_ticker: str = "SPY",
    rebalance_months: Optional[int] = None,
) -> dict:
    """Run a basic backtest for selected strategy vs. a benchmark index."""
    return await asyncio.to_thread(
        _run_backtest_impl,
        ticker,
        strategy,
        start_date,
        end_date,
        initial_capital,
        benchmark_ticker,
        rebalance_months,
    )
