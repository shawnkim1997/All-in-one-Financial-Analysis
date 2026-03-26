"""FMP-backed valuation ratios and key metrics (optional API key)."""

from typing import Any, Dict

from fastapi import APIRouter, Query

from server.services import fmp_client

router = APIRouter()


@router.get(
    "/key-metrics/{ticker}",
    summary="Historical key metrics (FMP or Yahoo fallback)",
)
async def get_key_metrics(
    ticker: str,
    period: str = Query("annual", description="annual or quarter"),
    limit: int = Query(10, ge=1, le=40),
) -> Dict[str, Any]:
    """Return FMP key-metrics time series when ``FMP_API_KEY`` is set; else Yahoo snapshot."""
    sym = ticker.strip().upper()
    rows = await fmp_client.fetch_key_metrics(sym, period=period, limit=limit)
    if rows:
        return {"ticker": sym, "source": "fmp", "period": period, "data": rows}
    fb = await fmp_client.fallback_valuation_snapshot(sym)
    return {"ticker": sym, "source": "fallback", "period": period, "data": [], "snapshot": fb}


@router.get(
    "/ratios/{ticker}",
    summary="Historical financial ratios (FMP or Yahoo fallback)",
)
async def get_ratios(
    ticker: str,
    period: str = Query("annual", description="annual or quarter"),
    limit: int = Query(10, ge=1, le=40),
) -> Dict[str, Any]:
    """Return FMP ratios time series when key is set; else Yahoo snapshot."""
    sym = ticker.strip().upper()
    rows = await fmp_client.fetch_ratios(sym, period=period, limit=limit)
    if rows:
        return {"ticker": sym, "source": "fmp", "period": period, "data": rows}
    fb = await fmp_client.fallback_valuation_snapshot(sym)
    return {"ticker": sym, "source": "fallback", "period": period, "data": [], "snapshot": fb}
