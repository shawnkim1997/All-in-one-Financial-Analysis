"""Peer valuation multiples for overview (yfinance, no LLM)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import yfinance as yf

from server.utils.ticker_utils import SECTORS
from server.utils.safe_float import _safe_float

# Extra keyword → bucket name (must match keys in SECTORS)
_BUCKET_KEYWORDS: List[Tuple[str, List[str]]] = [
    ("Semiconductors & Hardware", ["semiconductor", "semiconductors", "semi ", "hardware"]),
    ("Software & Cloud", ["software", "cloud", "saas", "internet content"]),
    ("Consumer Retail", ["retail", "consumer", "restaurant", "specialty retail"]),
    ("Financial Services", ["financial", "bank", "insurance", "capital market"]),
    ("Healthcare", ["health", "drug", "biotech", "medical"]),
]


def _match_bucket(sector: str, industry: str) -> Optional[str]:
    text = f"{sector} {industry}".lower()
    for bucket, kws in _BUCKET_KEYWORDS:
        if any(kw in text for kw in kws):
            return bucket
    for bucket_name in SECTORS:
        parts = bucket_name.lower().replace("&", " ").split()
        if any(p in text for p in parts if len(p) > 3):
            return bucket_name
    return None


def _fallback_large_caps(sector: str) -> List[str]:
    s = (sector or "").lower()
    if "technology" in s or "tech" in s:
        return ["MSFT", "AAPL", "GOOGL", "META", "NVDA"]
    if "financial" in s or "financials" in s:
        return ["JPM", "BAC", "GS", "MS", "V"]
    if "health" in s:
        return ["UNH", "JNJ", "LLY", "ABBV", "MRK"]
    if "consumer" in s:
        return ["AMZN", "WMT", "HD", "MCD", "SBUX"]
    return ["MSFT", "AAPL", "GOOGL", "AMZN", "JPM"]


def _peer_symbols(ticker: str, sector: str, industry: str) -> List[str]:
    t = ticker.upper().strip()
    bucket = _match_bucket(sector, industry)
    if bucket and bucket in SECTORS:
        syms = list(SECTORS[bucket])
    else:
        syms = _fallback_large_caps(sector)
    if t not in syms:
        syms = [t] + [x for x in syms if x != t]
    # unique preserve order, cap 8
    seen: set[str] = set()
    out: List[str] = []
    for s in syms:
        u = s.upper()
        if u not in seen:
            seen.add(u)
            out.append(u)
        if len(out) >= 8:
            break
    return out


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
    return {
        "ticker": t,
        "sector": sector or "—",
        "industry": industry or "—",
        "averages": {
            "pe": _avg(pes),
            "pb": _avg(pbs),
            "ps": _avg(pss),
            "ev_ebitda": _avg(evs),
        },
        "peers": peers,
    }
