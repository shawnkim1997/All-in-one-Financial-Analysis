"""Peer universe helpers shared by gateway providers and legacy services."""

from __future__ import annotations

from typing import List, Optional, Tuple

from server.utils.ticker_utils import SECTORS

_BUCKET_KEYWORDS: list[tuple[str, list[str]]] = [
    ("Semiconductors & Hardware", ["semiconductor", "semiconductors", "semi ", "hardware"]),
    ("Software & Cloud", ["software", "cloud", "saas", "internet content"]),
    ("Consumer Retail", ["retail", "consumer", "restaurant", "specialty retail"]),
    ("Financial Services", ["financial", "bank", "insurance", "capital market"]),
    ("Healthcare", ["health", "drug", "biotech", "medical"]),
]


def match_peer_bucket(sector: str, industry: str) -> Optional[str]:
    text = f"{sector} {industry}".lower()
    for bucket, keywords in _BUCKET_KEYWORDS:
        if any(keyword in text for keyword in keywords):
            return bucket
    for bucket_name in SECTORS:
        parts = bucket_name.lower().replace("&", " ").split()
        if any(part in text for part in parts if len(part) > 3):
            return bucket_name
    return None


def fallback_large_caps(sector: str) -> list[str]:
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


def peer_symbols_for_profile(ticker: str, sector: str, industry: str, cap: int = 8) -> List[str]:
    t = ticker.upper().strip()
    bucket = match_peer_bucket(sector, industry)
    syms = list(SECTORS[bucket]) if bucket and bucket in SECTORS else fallback_large_caps(sector)
    if t not in syms:
        syms = [t] + [symbol for symbol in syms if symbol != t]

    seen: set[str] = set()
    out: list[str] = []
    for symbol in syms:
        normalized = symbol.upper()
        if normalized not in seen:
            seen.add(normalized)
            out.append(normalized)
        if len(out) >= cap:
            break
    return out


def peer_symbols(ticker: str, sector: str, industry: str) -> List[str]:
    """Backward-compatible alias used by older services."""

    return peer_symbols_for_profile(ticker, sector, industry)
