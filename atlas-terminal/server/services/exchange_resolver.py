"""Resolve multi-exchange tickers for OCR/import workflows."""

from __future__ import annotations

MULTI_EXCHANGE_TICKERS = {
    "SMSN": [
        {"exchange": "LSE (GDR)", "yf_ticker": "SMSN.L", "currency": "USD", "default": True},
        {"exchange": "KRX (Korea)", "yf_ticker": "005930.KS", "currency": "KRW"},
        {"exchange": "OTC (US)", "yf_ticker": "SSNLF", "currency": "USD"},
    ],
    "NOV": [
        {"exchange": "NYSE", "yf_ticker": "NVO", "currency": "USD", "default": True},
        {"exchange": "Copenhagen", "yf_ticker": "NOVO-B.CO", "currency": "DKK"},
    ],
    "NVO": [
        {"exchange": "NYSE", "yf_ticker": "NVO", "currency": "USD", "default": True},
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


def resolve_ticker_with_exchange(ticker: str, selected_exchange: str | None = None) -> str:
    t = (ticker or "").upper().strip()
    options = get_exchange_options(t)
    if not options:
        return T212_TICKER_MAP.get(t, t)
    if selected_exchange:
        for opt in options:
            if opt.get("exchange") == selected_exchange:
                return opt.get("yf_ticker", t)
    for opt in options:
        if opt.get("default"):
            return opt.get("yf_ticker", t)
    return options[0].get("yf_ticker", t)

