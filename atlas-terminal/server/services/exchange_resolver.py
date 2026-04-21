"""Resolve multi-exchange tickers for OCR/import workflows."""

from __future__ import annotations

MULTI_EXCHANGE_TICKERS = {
    "SMSN": [
        {"exchange": "LSE (GDR)", "yf_ticker": "SMSN.L", "currency": "USD", "default": True},
        {"exchange": "KRX (Korea)", "yf_ticker": "005930.KS", "currency": "KRW"},
        {"exchange": "OTC (US)", "yf_ticker": "SSNLF", "currency": "USD"},
    ],
    "NOV": [
        {"exchange": "Frankfurt / Trading 212", "yf_ticker": "NOV.F", "currency": "EUR", "default": True},
        {"exchange": "NYSE", "yf_ticker": "NVO", "currency": "USD"},
        {"exchange": "Copenhagen", "yf_ticker": "NOVO-B.CO", "currency": "DKK"},
    ],
    "NVO": [
        {"exchange": "NYSE", "yf_ticker": "NVO", "currency": "USD", "default": True},
        {"exchange": "Frankfurt / Trading 212", "yf_ticker": "NOV.F", "currency": "EUR"},
        {"exchange": "Copenhagen", "yf_ticker": "NOVO-B.CO", "currency": "DKK"},
    ],
}

T212_TICKER_MAP = {
    "SMSN": "SMSN.L",
    "SMSN.L": "SMSN.L",
    "NOV": "NVO",
    "NVDA": "NVDA",
    "TSLA": "TSLA",
    "NVO": "NVO",
    "PLTR": "PLTR",
    "IONQ": "IONQ",
    "IREN": "IREN",
}


def get_exchange_options(ticker: str) -> list[dict]:
    return MULTI_EXCHANGE_TICKERS.get((ticker or "").upper(), [])


def resolve_exchange_option(
    ticker: str,
    selected_exchange: str | None = None,
    preferred_currency: str | None = None,
) -> dict | None:
    t = (ticker or "").upper().strip()
    options = get_exchange_options(t)
    if not options:
        mapped = T212_TICKER_MAP.get(t, t)
        return {"exchange": "", "yf_ticker": mapped, "currency": ""}
    if selected_exchange:
        for opt in options:
            if opt.get("exchange") == selected_exchange:
                return opt
    pref = (preferred_currency or "").upper().strip()
    if pref:
        for opt in options:
            if (opt.get("currency") or "").upper() == pref:
                return opt
    for opt in options:
        if opt.get("default"):
            return opt
    return options[0]


def resolve_ticker_with_exchange(
    ticker: str,
    selected_exchange: str | None = None,
    preferred_currency: str | None = None,
) -> str:
    t = (ticker or "").upper().strip()
    option = resolve_exchange_option(t, selected_exchange, preferred_currency)
    return (option or {}).get("yf_ticker", T212_TICKER_MAP.get(t, t))
