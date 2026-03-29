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


def _run_portfolio_backtest_impl(
    tickers: list[str],
    weights: list[float],
    start_date: str,
    end_date: str,
    rebalance_months: int = 3,
    benchmark_ticker: str = "SPY",
) -> Dict[str, Any]:
    """Multi-asset portfolio backtest with periodic rebalancing."""
    import numpy as np
    import pandas as pd
    import yfinance as yf

    if len(tickers) != len(weights) or not tickers:
        return {"error": "Tickers and weights must be non-empty and same length"}

    # Normalize weights
    total_w = sum(weights)
    if total_w <= 0:
        return {"error": "Weights must sum to a positive number"}
    norm_weights = [w / total_w for w in weights]

    # Fetch price data
    price_frames = {}
    for t in tickers:
        hist = yf.Ticker(t.upper()).history(start=start_date, end=end_date, auto_adjust=True)
        if hist is not None and not hist.empty and "Close" in hist:
            price_frames[t.upper()] = hist["Close"]
    if not price_frames:
        return {"error": "No price data for any ticker"}

    prices = pd.DataFrame(price_frames).dropna()
    if len(prices) < 5:
        return {"error": "Insufficient overlapping price data"}

    # Benchmark
    bm_sym = (benchmark_ticker or "SPY").upper()
    bm_hist = yf.Ticker(bm_sym).history(start=start_date, end=end_date, auto_adjust=True)
    if bm_hist is None or bm_hist.empty:
        return {"error": f"No benchmark data for {bm_sym}"}

    common = prices.index.intersection(bm_hist.index)
    if len(common) < 5:
        return {"error": "Insufficient overlap with benchmark"}
    prices = prices.loc[common]
    bm_close = bm_hist.loc[common, "Close"]

    returns = prices.pct_change().fillna(0)
    bm_returns = bm_close.pct_change().fillna(0)

    # Map tickers to weights (use only tickers that have data)
    avail_tickers = list(prices.columns)
    ticker_weight = {}
    for t, w in zip(tickers, norm_weights):
        tu = t.upper()
        if tu in avail_tickers:
            ticker_weight[tu] = w
    # Re-normalize
    tw_sum = sum(ticker_weight.values())
    if tw_sum <= 0:
        return {"error": "No valid tickers with data"}
    for k in ticker_weight:
        ticker_weight[k] /= tw_sum

    # Rebalancing: compute portfolio returns
    current_weights = {t: ticker_weight[t] for t in ticker_weight}
    portfolio_returns = []
    last_rebal = None

    for i, dt in enumerate(prices.index):
        if i == 0:
            portfolio_returns.append(0.0)
            last_rebal = dt
            continue

        # Daily portfolio return = sum of weight * return
        daily_ret = sum(current_weights.get(t, 0) * returns.loc[dt, t] for t in avail_tickers if t in current_weights)
        portfolio_returns.append(daily_ret)

        # Drift weights
        for t in current_weights:
            current_weights[t] *= (1 + returns.loc[dt, t])
        w_sum = sum(current_weights.values())
        if w_sum > 0:
            for t in current_weights:
                current_weights[t] /= w_sum

        # Rebalance check
        if last_rebal is not None and _months_between(last_rebal, dt) >= rebalance_months:
            current_weights = {t: ticker_weight[t] for t in ticker_weight}
            last_rebal = dt

    port_ret = pd.Series(portfolio_returns, index=prices.index)
    cumulative = (1 + port_ret).cumprod()
    benchmark_cum = (1 + bm_returns).cumprod()

    # Metrics
    total_ret = round((float(cumulative.iloc[-1]) - 1) * 100, 2)
    bm_ret = round((float(benchmark_cum.iloc[-1]) - 1) * 100, 2)
    mdd = round(float(((cumulative / cumulative.cummax()) - 1).min()) * 100, 2)
    sharpe = round(float(port_ret.mean() / (port_ret.std() + 1e-10) * (252**0.5)), 2)

    # Sortino
    downside = port_ret[port_ret < 0]
    sortino = round(float(port_ret.mean() / (downside.std() + 1e-10) * (252**0.5)), 2) if len(downside) > 0 else 0.0

    # Contribution per ticker
    contributions = {}
    for t in ticker_weight:
        t_ret = returns[t]
        contrib = float((t_ret * ticker_weight[t]).sum()) * 100
        contributions[t] = round(contrib, 2)

    return {
        "tickers": list(ticker_weight.keys()),
        "weights": {t: round(w, 4) for t, w in ticker_weight.items()},
        "benchmark_ticker": bm_sym,
        "total_return_pct": total_ret,
        "benchmark_return_pct": bm_ret,
        "alpha": round(total_ret - bm_ret, 2),
        "max_drawdown_pct": mdd,
        "sharpe_ratio": sharpe,
        "sortino_ratio": sortino,
        "rebalance_months": rebalance_months,
        "contributions": contributions,
        "equity_curve": [round(float(x), 4) for x in cumulative.tolist()],
        "benchmark_curve": [round(float(x), 4) for x in benchmark_cum.tolist()],
        "dates": prices.index.strftime("%Y-%m-%d").tolist(),
    }


async def run_portfolio_backtest(
    tickers: list[str],
    weights: list[float],
    start_date: str,
    end_date: str,
    rebalance_months: int = 3,
    benchmark_ticker: str = "SPY",
) -> dict:
    """Run a multi-asset portfolio backtest with periodic rebalancing."""
    return await asyncio.to_thread(
        _run_portfolio_backtest_impl,
        tickers,
        weights,
        start_date,
        end_date,
        rebalance_months,
        benchmark_ticker,
    )


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
