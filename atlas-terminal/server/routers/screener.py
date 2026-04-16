"""Screener and backtesting router."""

from __future__ import annotations

import logging
from fastapi import APIRouter

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/search")
async def search_stocks(filters: dict):
    """Run stock screener with simple filters."""
    try:
        from server.services.screener import run_screener

        return await run_screener(filters)
    except Exception as e:
        logger.exception("screener endpoint failed")
        return {"error": str(e), "data": []}


@router.post("/backtest")
async def backtest(body: dict):
    """Run strategy backtest for one ticker."""
    try:
        from server.services.backtester import run_backtest

        return await run_backtest(
            ticker=body.get("ticker", ""),
            strategy=body.get("strategy", "buy_and_hold"),
            start_date=body.get("start_date", "2024-01-01"),
            end_date=body.get("end_date", "2026-01-01"),
            initial_capital=float(body.get("initial_capital", 10000.0)),
            benchmark_ticker=str(body.get("benchmark_ticker") or "SPY"),
            rebalance_months=body.get("rebalance_months"),
        )
    except Exception as e:
        logger.exception("screener endpoint failed")
        return {"error": str(e)}


@router.post("/portfolio-backtest")
async def portfolio_backtest(body: dict):
    """Run multi-asset portfolio backtest with rebalancing."""
    try:
        from server.services.backtester import run_portfolio_backtest

        tickers = body.get("tickers", [])
        weights = body.get("weights", [])
        if not tickers:
            return {"error": "At least one ticker is required"}
        if not weights:
            weights = [1.0 / len(tickers)] * len(tickers)

        return await run_portfolio_backtest(
            tickers=tickers,
            weights=[float(w) for w in weights],
            start_date=body.get("start_date", "2021-01-01"),
            end_date=body.get("end_date", "2026-01-01"),
            rebalance_months=int(body.get("rebalance_months", 3)),
            benchmark_ticker=str(body.get("benchmark_ticker") or "SPY"),
        )
    except Exception as e:
        logger.exception("screener endpoint failed")
        return {"error": str(e)}
