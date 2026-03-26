"""Macro data: FRED, OECD (best effort), ECOS, economic calendar (FMP)."""

import asyncio
import os
from typing import Any, Dict, Optional

from fastapi import APIRouter, Query

from server.services import fmp_client
from server.services import macro_fetcher
from server.services.global_macro_quadrant import get_global_macro_quadrant
from server.services.smart_money_service import get_smart_money_snapshot
from server.services.yield_fx_service import get_yield_fx_pair

router = APIRouter()


@router.get("/quadrant", summary="Global growth vs inflation quadrant (Z-scores)")
async def macro_quadrant() -> Dict[str, Any]:
    try:
        return await asyncio.to_thread(get_global_macro_quadrant)
    except Exception as exc:
        return {"updated_at": None, "points": [], "error": str(exc)}


@router.get("/yield-fx", summary="US10Y spread vs FX (usdjpy|eurusd|usdkrw)")
async def macro_yield_fx(
    pair: str = Query("usdjpy", description="usdjpy, eurusd, or usdkrw"),
) -> Dict[str, Any]:
    try:
        return await asyncio.to_thread(get_yield_fx_pair, pair)
    except Exception as exc:
        return {
            "pair": pair,
            "updated_at": None,
            "series": [],
            "error": str(exc),
        }


@router.get("/smart-money", summary="Copper/Gold + RORO composite")
async def macro_smart_money() -> Dict[str, Any]:
    try:
        return await asyncio.to_thread(get_smart_money_snapshot)
    except Exception as exc:
        return {
            "updated_at": None,
            "roro_z": None,
            "roro_label": None,
            "copper_gold": [],
            "components": {},
            "error": str(exc),
        }


@router.get("/fred/{series_id}", summary="FRED time series (public CSV)")
async def macro_fred(
    series_id: str,
    start: Optional[str] = Query(None, description="YYYY-MM-DD"),
    end: Optional[str] = Query(None, description="YYYY-MM-DD"),
) -> Dict[str, Any]:
    rows = await asyncio.to_thread(
        macro_fetcher.fetch_fred_series,
        series_id,
        start,
        end,
    )
    return {"series": series_id.strip().upper(), "count": len(rows), "data": rows}


@router.get("/oecd/mei", summary="OECD MEI (best effort)")
async def macro_oecd_mei() -> Dict[str, Any]:
    rows = await asyncio.to_thread(macro_fetcher.fetch_oecd_mei)
    return {"count": len(rows), "data": rows}


@router.get("/oecd/cli", summary="OECD CLI snapshot (DBnomics)")
async def macro_oecd_cli() -> Dict[str, Any]:
    from server.services.oecd_cycle import get_oecd_cli_snapshot

    try:
        return await asyncio.to_thread(get_oecd_cli_snapshot)
    except Exception as exc:
        return {"updated_at": None, "countries": [], "error": str(exc)}


@router.get("/snapshot", summary="Macro cycle heatmap, countries, asset valuation")
async def macro_snapshot() -> Dict[str, Any]:
    from server.services.macro_cycle import get_macro_cycle_snapshot

    try:
        return await asyncio.to_thread(get_macro_cycle_snapshot)
    except Exception as exc:
        return {
            "updated_at": None,
            "cycle_score": 0.0,
            "regime": "Unknown",
            "cycle_heatmap": [],
            "country_heatmap": [],
            "asset_valuation": [],
            "error": str(exc),
        }


@router.get("/korea", summary="Korea indicators (ECOS or yfinance fallback)")
async def macro_korea(
    api_key: Optional[str] = Query(None, description="ECOS API key (optional)"),
) -> Dict[str, Any]:
    from server.services.ecos_fetcher import get_korea_snapshot

    key = (api_key or os.getenv("ECOS_API_KEY") or "").strip() or None
    return await asyncio.to_thread(get_korea_snapshot, key)


@router.get("/economic-calendar", summary="Economic calendar (scraped; no API key)")
async def macro_economic_calendar(
    days: int = Query(7, ge=1, le=30),
) -> Dict[str, Any]:
    from server.services.economic_calendar import get_economic_calendar

    try:
        return await asyncio.to_thread(get_economic_calendar, days)
    except Exception as exc:
        return {"events": [], "next_high_impact": None, "total": 0, "error": str(exc)}


@router.get("/ecos", summary="Korea Bank ECOS (requires ECOS_API_KEY)")
async def macro_ecos(
    stat_code: str = Query(..., description="ECOS 통계표 코드"),
    cycle: str = Query("M", description="D/W/M/Q/S/Y"),
    start_ym: str = Query("201501"),
    end_ym: Optional[str] = Query(None),
) -> Dict[str, Any]:
    rows = await asyncio.to_thread(
        macro_fetcher.fetch_ecos_series,
        stat_code,
        cycle,
        start_ym,
        end_ym,
    )
    return {"stat_code": stat_code, "count": len(rows), "data": rows}


@router.get("/calendar", summary="Economic calendar (FMP when key set)")
async def macro_calendar(
    date_from: str = Query(..., description="YYYY-MM-DD"),
    date_to: str = Query(..., description="YYYY-MM-DD"),
) -> Dict[str, Any]:
    if not fmp_client.fmp_is_configured():
        return {
            "source": "none",
            "data": [],
            "message": "Set FMP_API_KEY for economic_calendar, or use FRED directly.",
        }
    rows = await fmp_client.fetch_economic_calendar(date_from, date_to)
    if rows:
        return {"source": "fmp", "count": len(rows), "data": rows}
    return {"source": "fmp", "data": [], "message": "No rows (range or API limit)."}
