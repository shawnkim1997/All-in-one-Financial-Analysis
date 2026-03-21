"""FX router -- foreign exchange rates and historical data via yfinance."""

from typing import Dict, List

from fastapi import APIRouter, HTTPException

from server.models.schemas import FXRateResponse, FXHistoryResponse

router = APIRouter()

# Major FX pairs tracked by default (Yahoo Finance format: XXXYYY=X)
MAJOR_PAIRS = [
    "USDKRW", "USDJPY", "EURUSD", "GBPUSD", "USDCNY",
    "USDCHF", "AUDUSD", "USDCAD", "NZDUSD", "EURGBP",
]


def _yf_fx_symbol(pair: str) -> str:
    """Convert a pair like 'USDKRW' to the Yahoo Finance symbol 'USDKRW=X'."""
    p = pair.upper().replace("=X", "").replace("/", "")
    return f"{p}=X"


def _fetch_fx_rate(pair: str) -> float | None:
    """Fetch the latest FX rate for a single pair via yfinance."""
    try:
        import yfinance as yf

        symbol = _yf_fx_symbol(pair)
        ticker = yf.Ticker(symbol)
        fast = getattr(ticker, "fast_info", None)
        if fast:
            price = getattr(fast, "last_price", None)
            if price and float(price) > 0:
                return float(price)
        hist = ticker.history(period="1d")
        if hist is not None and not hist.empty:
            return float(hist["Close"].iloc[-1])
    except Exception:
        pass
    return None


@router.get(
    "/rates",
    response_model=FXRateResponse,
    summary="FX conversion matrix for major currencies",
)
async def fx_rates():
    """Return conversion matrix (USD/GBP/EUR/JPY/KRW)."""
    try:
        gbp_usd = _fetch_fx_rate("GBPUSD") or 1.27
        eur_usd = _fetch_fx_rate("EURUSD") or 1.08
        usd_jpy = _fetch_fx_rate("USDJPY") or 149.5
        usd_krw = _fetch_fx_rate("USDKRW") or 1370.0

        rates = {
            "USD_USD": 1.0,
            "USD_GBP": 1 / gbp_usd,
            "USD_EUR": 1 / eur_usd,
            "USD_JPY": usd_jpy,
            "USD_KRW": usd_krw,
            "GBP_USD": gbp_usd,
            "GBP_GBP": 1.0,
            "GBP_EUR": gbp_usd / eur_usd,
            "GBP_JPY": gbp_usd * usd_jpy,
            "GBP_KRW": gbp_usd * usd_krw,
            "EUR_USD": eur_usd,
            "EUR_GBP": eur_usd / gbp_usd,
            "EUR_EUR": 1.0,
            "EUR_JPY": eur_usd * usd_jpy,
            "EUR_KRW": eur_usd * usd_krw,
            "JPY_USD": 1 / usd_jpy,
            "JPY_GBP": 1 / (gbp_usd * usd_jpy),
            "JPY_EUR": 1 / (eur_usd * usd_jpy),
            "JPY_JPY": 1.0,
            "JPY_KRW": usd_krw / usd_jpy,
            "KRW_USD": 1 / usd_krw,
            "KRW_GBP": 1 / (gbp_usd * usd_krw),
            "KRW_EUR": 1 / (eur_usd * usd_krw),
            "KRW_JPY": usd_jpy / usd_krw,
            "KRW_KRW": 1.0,
        }
        return FXRateResponse(pair="MATRIX", rates=rates)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"FX rates failed: {exc}") from exc


@router.get(
    "/history/{pair}",
    response_model=FXHistoryResponse,
    summary="1-year FX history",
)
async def fx_history(pair: str):
    """Return ~1 year of daily closing rates for the given currency pair.

    *pair* should be in the format ``USDKRW``, ``EURUSD``, etc.
    """
    try:
        import yfinance as yf

        symbol = _yf_fx_symbol(pair)
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="1y")

        if hist is None or hist.empty:
            raise HTTPException(status_code=404, detail=f"No history found for pair {pair}")

        dates: List[str] = [d.strftime("%Y-%m-%d") for d in hist.index]
        rates: List[float] = [round(float(v), 4) for v in hist["Close"]]

        return FXHistoryResponse(pair=pair.upper(), dates=dates, rates=rates)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"FX history failed: {exc}") from exc
