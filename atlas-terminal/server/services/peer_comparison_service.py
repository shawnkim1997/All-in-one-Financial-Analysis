"""Peer valuation multiples for overview (yfinance, no LLM)."""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

import yfinance as yf

from server.core.data_gateway import DataGateway, Fundamentals
from server.core.providers.base import DataUnavailable
from server.utils.peer_universe import peer_symbols_for_profile
from server.utils.safe_float import _safe_float


def _peer_symbols(ticker: str, sector: str, industry: str) -> List[str]:
    return peer_symbols_for_profile(ticker, sector, industry, cap=8)


def _peer_row(sym: str) -> Dict[str, Any]:
    info = (yf.Ticker(sym).info) or {}
    return {
        "ticker": sym,
        "name": str(info.get("shortName") or info.get("longName") or sym)[:80],
        "market_cap": _safe_float(info.get("marketCap")),
        "pe": _safe_float(info.get("trailingPE")) or _safe_float(info.get("forwardPE")),
        "pb": _safe_float(info.get("priceToBook")),
        "ps": _safe_float(info.get("priceToSalesTrailing12Months")),
        "ev_ebitda": _safe_float(info.get("enterpriseToEbitda")),
        "roic": _safe_float(info.get("returnOnInvestedCapital") or info.get("returnOnCapital")),
        "gross_margin": _safe_float(info.get("grossMargins")),
        "rev_growth": _safe_float(info.get("revenueGrowth")),
    }


def _avg(vals: List[Optional[float]]) -> Optional[float]:
    nums = [v for v in vals if v is not None]
    if not nums:
        return None
    return round(sum(nums) / len(nums), 2)


def build_peer_comparison(ticker: str) -> Dict[str, Any]:
    """Return payload matching PeerComparisonData on the frontend."""
    t = ticker.upper().strip()
    try:
        info = (yf.Ticker(t).info) or {}
    except Exception:
        info = {}
    sector = str(info.get("sector") or "")
    industry = str(info.get("industry") or "")
    syms = _peer_symbols(t, sector, industry)
    peers = [_peer_row(s) for s in syms]
    pes = [p["pe"] for p in peers]
    pbs = [p["pb"] for p in peers]
    pss = [p["ps"] for p in peers]
    evs = [p["ev_ebitda"] for p in peers]
    roics = [p["roic"] for p in peers]
    gross_margins = [p["gross_margin"] for p in peers]
    rev_growths = [p["rev_growth"] for p in peers]
    return {
        "ticker": t,
        "primary": t,
        "sector": sector or "—",
        "industry": industry or "—",
        "metrics": ["pe", "pb", "ps", "ev_ebitda", "roic", "gross_margin", "rev_growth"],
        "averages": {
            "pe": _avg(pes),
            "pb": _avg(pbs),
            "ps": _avg(pss),
            "ev_ebitda": _avg(evs),
            "roic": _avg(roics),
            "gross_margin": _avg(gross_margins),
            "rev_growth": _avg(rev_growths),
        },
        "peer_symbols": syms[1:],
        "matrix": peers,
        "peers": peers,
    }


def _metric_from_fundamentals(fundamentals: Fundamentals, metric: str) -> Optional[float]:
    raw = fundamentals.raw or {}
    if metric == "pe":
        return _safe_float(fundamentals.pe or raw.get("trailingPE") or raw.get("forwardPE"))
    if metric == "pb":
        return _safe_float(fundamentals.pb or raw.get("priceToBook"))
    if metric == "ps":
        return _safe_float(fundamentals.ps or raw.get("priceToSalesTrailing12Months"))
    if metric == "ev_ebitda":
        return _safe_float(fundamentals.ev_ebitda or raw.get("enterpriseToEbitda"))
    if metric == "roic":
        return _safe_float(fundamentals.roic or raw.get("returnOnInvestedCapital") or raw.get("returnOnCapital"))
    if metric == "gross_margin":
        return _safe_float(fundamentals.gross_margin or raw.get("grossMargins"))
    if metric in {"rev_growth", "revenue_growth"}:
        return _safe_float(fundamentals.revenue_growth or raw.get("revenueGrowth"))
    return None


def _matrix_row(symbol: str, fundamentals: Fundamentals, metrics: list[str]) -> Dict[str, Any]:
    raw = fundamentals.raw or {}
    row: Dict[str, Any] = {
        "ticker": symbol.upper(),
        "name": str(fundamentals.name or raw.get("shortName") or raw.get("longName") or symbol.upper())[:80],
        "market_cap": _safe_float(fundamentals.market_cap or raw.get("marketCap")),
        "source": fundamentals.source,
    }
    for metric in metrics:
        row[metric] = _metric_from_fundamentals(fundamentals, metric)
    # Keep report/overview legacy fields available even when callers request a
    # smaller metric set.
    for metric in ["pe", "pb", "ps", "ev_ebitda", "roic", "gross_margin", "rev_growth"]:
        row.setdefault(metric, _metric_from_fundamentals(fundamentals, metric))
    return row


async def build_peer_comparison_matrix(
    ticker: str,
    metrics: list[str],
    gateway: DataGateway,
    max_peers: int = 5,
) -> Dict[str, Any]:
    """Build a gateway-backed peer matrix with bounded parallel fundamentals fetches."""

    primary = ticker.upper().strip()
    requested_metrics = [m.strip().lower() for m in metrics if m.strip()]
    if not requested_metrics:
        requested_metrics = ["pe", "ev_ebitda", "roic", "gross_margin"]

    try:
        profile, peer_symbols = await asyncio.gather(
            gateway.profile(primary),
            gateway.peers(primary),
        )
    except DataUnavailable:
        legacy = await asyncio.to_thread(build_peer_comparison, primary)
        legacy["metrics"] = requested_metrics
        return legacy

    targets = [primary] + [symbol.upper() for symbol in peer_symbols if symbol.upper() != primary][:max_peers]
    semaphore = asyncio.Semaphore(5)

    async def fetch_one(symbol: str) -> Fundamentals | Exception:
        async with semaphore:
            try:
                return await gateway.fundamentals(symbol, period="ttm")
            except Exception as exc:
                return exc

    results = await asyncio.gather(*(fetch_one(symbol) for symbol in targets))
    matrix: list[Dict[str, Any]] = []
    for symbol, result in zip(targets, results):
        if isinstance(result, Fundamentals):
            matrix.append(_matrix_row(symbol, result, requested_metrics))

    if not matrix:
        legacy = await asyncio.to_thread(build_peer_comparison, primary)
        legacy["metrics"] = requested_metrics
        return legacy

    averages = {
        metric: _avg([_safe_float(row.get(metric)) for row in matrix])
        for metric in ["pe", "pb", "ps", "ev_ebitda", "roic", "gross_margin", "rev_growth"]
    }
    return {
        "ticker": primary,
        "primary": primary,
        "sector": profile.sector or "—",
        "industry": profile.industry or "—",
        "metrics": requested_metrics,
        "peer_symbols": targets[1:],
        "averages": averages,
        "matrix": matrix,
        "peers": matrix,
    }
