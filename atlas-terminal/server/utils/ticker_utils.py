"""Ticker formatting, market inference, and company/sector reference data.

Centralises the mapping logic that converts bare ticker symbols into
Yahoo Finance-compatible identifiers with the correct market suffix,
and provides the static lookup tables for companies and sectors.
"""

from typing import List, Tuple

# ---------------------------------------------------------------------------
# Company reference data
# ---------------------------------------------------------------------------

COMPANY_LIST: List[Tuple[str, str]] = [
    ("NVIDIA Corporation", "NVDA"), ("Apple Inc.", "AAPL"), ("Microsoft Corporation", "MSFT"),
    ("Amazon.com Inc.", "AMZN"), ("Alphabet Inc.", "GOOGL"), ("Meta Platforms Inc.", "META"),
    ("AMD", "AMD"), ("Intel Corporation", "INTC"), ("Qualcomm Inc.", "QCOM"), ("Tesla Inc.", "TSLA"),
    ("Berkshire Hathaway", "BRK.B"), ("JPMorgan Chase", "JPM"), ("Visa Inc.", "V"),
    ("UnitedHealth", "UNH"), ("Procter & Gamble", "PG"), ("Exxon Mobil", "XOM"),
    ("Johnson & Johnson", "JNJ"), ("Mastercard", "MA"), ("Chevron", "CVX"),
    ("Home Depot", "HD"), ("Merck", "MRK"), ("AbbVie", "ABBV"), ("Costco", "COST"),
    ("PepsiCo", "PEP"), ("Coca-Cola", "KO"), ("Pfizer", "PFE"), ("Walmart", "WMT"),
    ("Netflix", "NFLX"), ("Adobe", "ADBE"), ("Salesforce", "CRM"), ("Comcast", "CMCSA"),
    ("Cisco", "CSCO"), ("Oracle", "ORCL"), ("American Express", "AXP"),
    ("Bank of America", "BAC"), ("Wells Fargo", "WFC"), ("Verizon", "VZ"),
    ("AT&T", "T"), ("Walt Disney", "DIS"), ("Nike", "NKE"), ("McDonald's", "MCD"),
    ("Starbucks", "SBUX"), ("Goldman Sachs", "GS"), ("Morgan Stanley", "MS"),
    ("Target", "TGT"), ("Boeing", "BA"), ("IBM", "IBM"),
]

COMPANY_OPTIONS: List[str] = [f"{t} - {n}" for n, t in COMPANY_LIST]
"""Pre-formatted ``'TICKER - Company Name'`` strings for dropdowns."""

COMPANY_TICKER_MAP: dict[str, str] = {t: n for n, t in COMPANY_LIST}
"""Mapping from ticker symbol to full company name."""

MARKET_OPTIONS: List[str] = [
    "US (S&P/Dow/Nasdaq)",
    "South Korea (KOSPI/KOSDAQ)",
    "Japan (Nikkei)",
    "UK (LSE)",
]

# ---------------------------------------------------------------------------
# Sector / industry peer groups (top-down analysis)
# ---------------------------------------------------------------------------

SECTORS: dict[str, List[str]] = {
    "Semiconductors & Hardware": ["NVDA", "AMD", "INTC", "TSM", "AVGO"],
    "Software & Cloud": ["MSFT", "ADBE", "CRM", "PANW", "CRWD"],
    "Consumer Retail": ["AMZN", "SBUX", "MCD", "WMT", "HD"],
    "Financial Services": ["JPM", "BAC", "GS", "MS", "V"],
    "Healthcare": ["LLY", "UNH", "JNJ", "ABBV", "MRK"],
}


# ---------------------------------------------------------------------------
# Ticker helpers
# ---------------------------------------------------------------------------

def get_global_ticker(ticker: str, market: str) -> str:
    """Append the correct Yahoo Finance suffix based on the selected market.

    US tickers are returned as-is.  If the ticker already carries a known
    suffix (``.KS``, ``.KQ``, ``.T``, ``.L``) it is returned unchanged
    regardless of the *market* argument.

    Parameters
    ----------
    ticker:
        Raw ticker string entered by the user.
    market:
        One of the values in :data:`MARKET_OPTIONS`.

    Returns
    -------
    str
        The ticker with an appropriate suffix (or unchanged for US).
    """
    if not (ticker or "").strip():
        return (ticker or "").strip()
    t = (ticker or "").strip()
    if t.upper().endswith((".KS", ".KQ", ".T", ".L")):
        return t
    m = (market or "").strip()
    if "US" in m or not m:
        return t
    if "Korea" in m or "KOSPI" in m or "KOSDAQ" in m:
        return t + ".KS"
    if "Japan" in m or "Nikkei" in m:
        return t + ".T"
    if "UK" in m or "LSE" in m:
        return t + ".L"
    return t


def infer_market_from_ticker(ticker: str) -> str:
    """Guess the market label from a ticker's suffix.

    Useful when the caller has a fully-qualified ticker (e.g. ``005930.KS``)
    but no explicit market selection.

    Parameters
    ----------
    ticker:
        A ticker string that may include a market suffix.

    Returns
    -------
    str
        The best-matching entry from :data:`MARKET_OPTIONS`.
    """
    if not (ticker or "").strip():
        return MARKET_OPTIONS[0]
    t = (ticker or "").strip().upper()
    if t.endswith(".KS") or t.endswith(".KQ"):
        return "South Korea (KOSPI/KOSDAQ)"
    if t.endswith(".T"):
        return "Japan (Nikkei)"
    if t.endswith(".L"):
        return "UK (LSE)"
    return "US (S&P/Dow/Nasdaq)"
