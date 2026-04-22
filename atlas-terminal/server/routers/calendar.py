"""Institutional calendar router -- economic events and earnings dates."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from fastapi import APIRouter, Query

router = APIRouter()


def _event_date(row: dict[str, Any]) -> str:
    raw = row.get("date") or row.get("publishedDate") or row.get("epsDate") or row.get("time")
    value = str(raw or "")[:10]
    return value if value else "unknown"


def _group_by_date(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        key = _event_date(row)
        grouped.setdefault(key, []).append(row)
    return dict(sorted(grouped.items()))


@router.get("/economic", summary="Economic calendar grouped by date")
async def economic_calendar(days_ahead: int = Query(7, ge=1, le=60)) -> dict[str, Any]:
    from server.services.fmp_client import fetch_economic_calendar, fmp_is_configured

    start = date.today()
    end = start + timedelta(days=days_ahead)
    if not fmp_is_configured():
        return {
            "available": False,
            "message": "Set FMP_API_KEY for the economic calendar.",
            "from": start.isoformat(),
            "to": end.isoformat(),
            "grouped": {},
        }

    rows = await fetch_economic_calendar(start.isoformat(), end.isoformat()) or []
    return {
        "available": True,
        "from": start.isoformat(),
        "to": end.isoformat(),
        "grouped": _group_by_date(rows),
    }


@router.get("/earnings", summary="Earnings calendar grouped by date")
async def earnings_calendar(
    days_ahead: int = Query(14, ge=1, le=90),
    watchlist_only: bool = False,
) -> dict[str, Any]:
    from server.services.fmp_client import fetch_earning_calendar, fmp_is_configured

    start = date.today()
    end = start + timedelta(days=days_ahead)
    if not fmp_is_configured():
        return {
            "available": False,
            "message": "Set FMP_API_KEY for the earnings calendar.",
            "from": start.isoformat(),
            "to": end.isoformat(),
            "watchlist_only": watchlist_only,
            "grouped": {},
        }

    rows = await fetch_earning_calendar(start.isoformat(), end.isoformat()) or []
    if watchlist_only:
        # Local-first project: watchlist is currently browser-side.  Keep the
        # flag in the contract and let the frontend highlight its local list.
        rows = list(rows)

    return {
        "available": True,
        "from": start.isoformat(),
        "to": end.isoformat(),
        "watchlist_only": watchlist_only,
        "grouped": _group_by_date(rows),
    }
