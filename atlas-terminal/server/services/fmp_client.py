"""Financial Modeling Prep (FMP) API client with TTL cache and Yahoo fallbacks.

Requires ``FMP_API_KEY`` in the environment for FMP calls.  When absent or on
failure, :func:`fallback_valuation_snapshot` fills a minimal snapshot from
yfinance / yahooquery (see ``claude.md`` §2.3).
"""

from __future__ import annotations

import hashlib
import json
import os
from typing import Any, Dict, List, Optional

import httpx

from server.db.cache import cache_manager
from server.utils.safe_float import _safe_float

_FMP_BASE_V3 = "https://financialmodelingprep.com/api/v3"
_FMP_BASE_V4 = "https://financialmodelingprep.com/api/v4"
_DEFAULT_LIMIT = 10
_CACHE_MEM = 300
_CACHE_DB = 3600


def _fmp_api_key() -> Optional[str]:
    key = (os.getenv("FMP_API_KEY") or "").strip()
    return key or None


def fmp_is_configured() -> bool:
    """True when ``FMP_API_KEY`` is set (used by routers)."""
    return _fmp_api_key() is not None


def _cache_key(prefix: str, *parts: str) -> str:
    h = hashlib.sha256("|".join(parts).encode()).hexdigest()[:16]
    return f"fmp:{prefix}:{h}"


async def _fmp_get_json(path: str, params: Dict[str, Any]) -> Optional[Any]:
    """GET JSON from FMP with memory+SQLite cache."""
    api_key = _fmp_api_key()
    if not api_key:
        return None
    q = dict(params)
    q["apikey"] = api_key
    cache_key = _cache_key(path, json.dumps(q, sort_keys=True))
    cached = await cache_manager.get(cache_key)
    if cached is not None:
        return cached

    url = f"{_FMP_BASE_V3}{path}"

    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            r = await client.get(url, params=q)
            if r.status_code != 200:
                return None
            data = r.json()
    except (httpx.HTTPError, json.JSONDecodeError, ValueError):
        return None

    await cache_manager.set(cache_key, data, memory_ttl=_CACHE_MEM, db_ttl=_CACHE_DB)
    return data


async def _fmp_get_v4(path: str, params: Dict[str, Any]) -> Optional[Any]:
    key = _fmp_api_key()
    if not key:
        return None
    q = dict(params)
    q["apikey"] = key
    cache_key = _cache_key("v4" + path, json.dumps(q, sort_keys=True))
    cached = await cache_manager.get(cache_key)
    if cached is not None:
        return cached
    url = f"{_FMP_BASE_V4}{path}"
    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            r = await client.get(url, params=q)
            if r.status_code != 200:
                return None
            data = r.json()
    except (httpx.HTTPError, json.JSONDecodeError, ValueError):
        return None

    await cache_manager.set(cache_key, data, memory_ttl=_CACHE_MEM, db_ttl=_CACHE_DB)
    return data


async def fetch_key_metrics(
    ticker: str,
    period: str = "annual",
    limit: int = _DEFAULT_LIMIT,
) -> Optional[List[Dict[str, Any]]]:
    """FMP key-metrics time series (PE, PB, FCF yield, etc.)."""
    t = ticker.strip().upper()
    if not t:
        return None
    data = await _fmp_get_json(
        f"/key-metrics/{t}",
        {"period": period, "limit": limit},
    )
    if isinstance(data, list):
        return data
    return None


async def fetch_ratios(
    ticker: str,
    period: str = "annual",
    limit: int = _DEFAULT_LIMIT,
) -> Optional[List[Dict[str, Any]]]:
    """FMP financial ratios time series."""
    t = ticker.strip().upper()
    if not t:
        return None
    data = await _fmp_get_json(
        f"/ratios/{t}",
        {"period": period, "limit": limit},
    )
    if isinstance(data, list):
        return data
    return None


async def fetch_economic_calendar(
    date_from: str,
    date_to: str,
) -> Optional[List[Dict[str, Any]]]:
    """FMP economic calendar between two ISO dates (requires API key)."""
    data = await _fmp_get_json(
        "/economic_calendar",
        {"from": date_from, "to": date_to},
    )
    if isinstance(data, list):
        return data
    return None


async def fetch_earning_calendar(
    date_from: str,
    date_to: str,
) -> Optional[List[Dict[str, Any]]]:
    """FMP earnings calendar between two ISO dates (requires API key)."""
    data = await _fmp_get_json(
        "/earning_calendar",
        {"from": date_from, "to": date_to},
    )
    if isinstance(data, list):
        return data
    return None


async def fetch_earning_call_transcript(
    ticker: str,
    year: int,
    quarter: int,
) -> Optional[List[Dict[str, Any]]]:
    """FMP earning call transcript (one quarter)."""
    t = ticker.strip().upper()
    if not t or year < 1990 or quarter not in (1, 2, 3, 4):
        return None
    data = await _fmp_get_v4(
        "/earning_call_transcript",
        {"symbol": t, "year": year, "quarter": quarter},
    )
    if isinstance(data, list):
        return data
    return None


def _yf_info_snapshot(ticker: str) -> Dict[str, Any]:
    """Best-effort valuation fields from yfinance ``info``."""
    try:
        import yfinance as yf  # noqa: WPS433

        info = yf.Ticker(ticker.upper()).info or {}
    except Exception:
        return {}
    return {
        "source": "yfinance",
        "peRatio": _safe_float(info.get("trailingPE")),
        "pegRatio": _safe_float(info.get("pegRatio")),
        "priceToBookRatio": _safe_float(info.get("priceToBook")),
        "enterpriseValueOverEBITDA": _safe_float(info.get("enterpriseToEbitda")),
        "dividendYield": _safe_float(info.get("dividendYield")),
        "marketCap": _safe_float(info.get("marketCap")),
    }


def _yq_snapshot(ticker: str) -> Dict[str, Any]:
    """Best-effort fields from yahooquery ``summary_detail``."""
    try:
        from yahooquery import Ticker as YQTicker  # noqa: WPS433

        yq = YQTicker(ticker.upper())
        d = yq.summary_detail
        if not isinstance(d, dict):
            return {}
        row = d.get(ticker.upper()) or next(iter(d.values()), None)
        if not isinstance(row, dict):
            return {}
    except Exception:
        return {}
    return {
        "source": "yahooquery",
        "peRatio": _safe_float(row.get("trailingPE") or row.get("forwardPE")),
        "pegRatio": _safe_float(row.get("pegRatio")),
        "priceToBookRatio": _safe_float(row.get("priceToBook")),
        "enterpriseValueOverEBITDA": _safe_float(
            row.get("enterpriseToRevenue")
        ),  # YQ naming differs; best effort
        "dividendYield": _safe_float(row.get("dividendYield")),
        "marketCap": _safe_float(row.get("marketCap")),
    }


async def fallback_valuation_snapshot(ticker: str) -> Dict[str, Any]:
    """When FMP is unavailable: merge yfinance and yahooquery snapshots."""
    import asyncio

    t = ticker.strip().upper()
    if not t:
        return {"ticker": "", "source": "none", "data": {}}

    yf_part, yq_part = await asyncio.gather(
        asyncio.to_thread(_yf_info_snapshot, t),
        asyncio.to_thread(_yq_snapshot, t),
    )
    merged: Dict[str, Any] = {"ticker": t, "source": "fallback", "yfinance": yf_part, "yahooquery": yq_part}
    return merged
