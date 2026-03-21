"""Crypto router -- live cryptocurrency prices from Bithumb (KRW) and Binance (USD)."""

from typing import List

from fastapi import APIRouter, HTTPException

from server.models.schemas import CryptoPrice

router = APIRouter()

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


def _fetch_binance_prices(symbols: List[str]) -> dict:
    """Fetch USD prices from Binance API for the given symbols."""
    import requests

    url = "https://api.binance.com/api/v3/ticker/price"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return {}

    # Build lookup: symbol (no USDT suffix) -> price
    prices = {}
    lookup = {item["symbol"]: float(item["price"]) for item in data}
    for sym in symbols:
        key = f"{sym.upper()}USDT"
        if key in lookup:
            prices[sym.upper()] = lookup[key]
    return prices


def _fetch_bithumb_prices(symbols: List[str]) -> dict:
    """Fetch KRW prices from Bithumb public API."""
    import requests

    prices = {}
    for sym in symbols:
        bithumb_sym = _BITHUMB_MAP.get(sym.upper(), sym.upper())
        url = f"https://api.bithumb.com/public/ticker/{bithumb_sym}_KRW"
        try:
            resp = requests.get(url, timeout=5)
            resp.raise_for_status()
            data = resp.json()
            if data.get("status") == "0000":
                closing = data.get("data", {}).get("closing_price")
                if closing:
                    prices[sym.upper()] = float(closing)
        except Exception:
            continue
    return prices


def _fetch_binance_24h_changes(symbols: List[str]) -> dict:
    """Fetch 24h percentage changes from Binance."""
    import requests

    url = "https://api.binance.com/api/v3/ticker/24hr"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception:
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
        usd_prices = _fetch_binance_prices(TOP_SYMBOLS)
        krw_prices = _fetch_bithumb_prices(TOP_SYMBOLS)
        changes = _fetch_binance_24h_changes(TOP_SYMBOLS)

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
        usd_prices = _fetch_binance_prices([sym])
        krw_prices = _fetch_bithumb_prices([sym])
        changes = _fetch_binance_24h_changes([sym])

        return CryptoPrice(
            symbol=sym,
            name=sym,
            price_usd=usd_prices.get(sym),
            price_krw=krw_prices.get(sym),
            change_24h_pct=changes.get(sym),
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Crypto price failed: {exc}") from exc
