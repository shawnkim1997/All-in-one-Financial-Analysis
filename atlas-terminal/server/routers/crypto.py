"""Crypto router -- live cryptocurrency prices from Bithumb (KRW) and Binance (USD)."""

import asyncio
import logging
from typing import List

import httpx
from fastapi import APIRouter, HTTPException

from server.models.schemas import CryptoPrice

router = APIRouter()
logger = logging.getLogger(__name__)

# Top 20 symbols tracked by default
TOP_SYMBOLS = [
    "BTC", "ETH", "BNB", "XRP", "SOL", "ADA", "DOGE", "AVAX", "DOT", "MATIC",
    "LINK", "SHIB", "TRX", "UNI", "ATOM", "LTC", "ETC", "XLM", "NEAR", "APT",
]

# Bithumb uses different ticker names for some coins
_BITHUMB_MAP = {
    "MATIC": "MATIC",
    "NEAR": "NEAR",
    "APT": "APT",
}


async def _fetch_binance_prices(client: httpx.AsyncClient, symbols: List[str]) -> dict:
    """Fetch USD prices from Binance API for the given symbols."""
    url = "https://api.binance.com/api/v3/ticker/price"
    try:
        resp = await client.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("Binance prices fetch failed: %s", exc)
        return {}

    prices = {}
    lookup = {item["symbol"]: float(item["price"]) for item in data}
    for sym in symbols:
        key = f"{sym.upper()}USDT"
        if key in lookup:
            prices[sym.upper()] = lookup[key]
    return prices


async def _fetch_bithumb_prices(client: httpx.AsyncClient, symbols: List[str]) -> dict:
    """Fetch KRW prices from Bithumb public API (parallel)."""
    async def _one(sym: str):
        bithumb_sym = _BITHUMB_MAP.get(sym.upper(), sym.upper())
        url = f"https://api.bithumb.com/public/ticker/{bithumb_sym}_KRW"
        try:
            resp = await client.get(url, timeout=5)
            resp.raise_for_status()
            data = resp.json()
            if data.get("status") == "0000":
                closing = data.get("data", {}).get("closing_price")
                if closing:
                    return sym.upper(), float(closing)
        except (httpx.HTTPError, ValueError) as exc:
            logger.debug("Bithumb %s failed: %s", sym, exc)
        return None

    results = await asyncio.gather(*[_one(s) for s in symbols], return_exceptions=True)
    prices = {}
    for r in results:
        if isinstance(r, tuple):
            prices[r[0]] = r[1]
    return prices


async def _fetch_binance_24h_changes(client: httpx.AsyncClient, symbols: List[str]) -> dict:
    """Fetch 24h percentage changes from Binance."""
    url = "https://api.binance.com/api/v3/ticker/24hr"
    try:
        resp = await client.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("Binance 24h changes fetch failed: %s", exc)
        return {}

    changes = {}
    lookup = {item["symbol"]: float(item.get("priceChangePercent", 0)) for item in data}
    for sym in symbols:
        key = f"{sym.upper()}USDT"
        if key in lookup:
            changes[sym.upper()] = lookup[key]
    return changes


@router.get(
    "/prices",
    response_model=List[CryptoPrice],
    summary="Top 20 crypto prices (Bithumb KRW + Binance USD)",
)
async def crypto_prices():
    """Return current prices for the top 20 cryptocurrencies.

    USD prices come from Binance; KRW prices from Bithumb.
    """
    try:
        async with httpx.AsyncClient() as client:
            usd_prices, krw_prices, changes = await asyncio.gather(
                _fetch_binance_prices(client, TOP_SYMBOLS),
                _fetch_bithumb_prices(client, TOP_SYMBOLS),
                _fetch_binance_24h_changes(client, TOP_SYMBOLS),
            )

        results: List[CryptoPrice] = []
        for sym in TOP_SYMBOLS:
            results.append(CryptoPrice(
                symbol=sym,
                name=sym,
                price_usd=usd_prices.get(sym),
                price_krw=krw_prices.get(sym),
                change_24h_pct=changes.get(sym),
            ))
        return results
    except Exception as exc:
        logger.exception("Crypto prices endpoint failed")
        raise HTTPException(status_code=500, detail=f"Crypto prices failed: {exc}") from exc


@router.get(
    "/price/{symbol}",
    response_model=CryptoPrice,
    summary="Single crypto price",
)
async def crypto_price(symbol: str):
    """Return current price for a single cryptocurrency symbol."""
    try:
        sym = symbol.upper()
        async with httpx.AsyncClient() as client:
            usd_prices, krw_prices, changes = await asyncio.gather(
                _fetch_binance_prices(client, [sym]),
                _fetch_bithumb_prices(client, [sym]),
                _fetch_binance_24h_changes(client, [sym]),
            )

        return CryptoPrice(
            symbol=sym,
            name=sym,
            price_usd=usd_prices.get(sym),
            price_krw=krw_prices.get(sym),
            change_24h_pct=changes.get(sym),
        )
    except Exception as exc:
        logger.exception("Crypto price endpoint failed")
        raise HTTPException(status_code=500, detail=f"Crypto price failed: {exc}") from exc
