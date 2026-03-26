"""Ticker formatting, market inference, and company/sector reference data.

Centralises the mapping logic that converts bare ticker symbols into
Yahoo Finance-compatible identifiers with the correct market suffix,
and provides the static lookup tables for companies and sectors.
"""

from enum import Enum
from typing import List, Literal, Optional, Tuple

FilingJurisdiction = Literal["SEC", "DART", "EDINET"]

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


class AssetType(str, Enum):
    EQUITY = "equity"
    ETF = "etf"
    COMMODITY_FUTURE = "commodity_future"
    CRYPTO = "crypto"
    INDEX = "index"


COMMODITY_FUTURES: dict[str, str] = {
    "GC=F": "Gold", "SI=F": "Silver", "PL=F": "Platinum", "PA=F": "Palladium",
    "CL=F": "Crude Oil (WTI)", "BZ=F": "Brent Crude", "NG=F": "Natural Gas",
    "HO=F": "Heating Oil", "RB=F": "Gasoline",
    "ZC=F": "Corn", "ZS=F": "Soybeans", "ZW=F": "Wheat",
    "KC=F": "Coffee", "CT=F": "Cotton", "SB=F": "Sugar",
    "CC=F": "Cocoa", "OJ=F": "Orange Juice",
    "LE=F": "Live Cattle", "HE=F": "Lean Hogs",
    "HG=F": "Copper", "ALI=F": "Aluminum",
}

POPULAR_COMMODITY_ETFS: dict[str, str] = {
    "GLD": "SPDR Gold Trust", "IAU": "iShares Gold Trust", "SLV": "iShares Silver Trust",
    "PPLT": "abrdn Platinum ETF", "USO": "United States Oil Fund", "UNG": "United States Natural Gas Fund",
    "XLE": "Energy Select Sector SPDR", "VDE": "Vanguard Energy ETF", "DBC": "Invesco DB Commodity Tracking",
    "GSG": "iShares S&P GSCI Commodity", "PDBC": "Invesco Optimum Yield Diversified Commodity",
    "COM": "Direxion Auspice Broad Commodity", "DBA": "Invesco DB Agriculture Fund",
    "WEAT": "Teucrium Wheat Fund", "CORN": "Teucrium Corn Fund", "SOYB": "Teucrium Soybean Fund",
    "SPY": "S&P 500 ETF", "QQQ": "Nasdaq 100 ETF", "IWM": "Russell 2000 ETF",
    "EEM": "Emerging Markets ETF", "VWO": "Vanguard FTSE Emerging Markets",
    "TLT": "20+ Year Treasury Bond ETF", "HYG": "High Yield Corporate Bond ETF",
    "LQD": "Investment Grade Corporate Bond ETF", "ARKK": "ARK Innovation ETF",
    "XLK": "Technology Select Sector SPDR", "XLF": "Financial Select Sector SPDR",
    "XLV": "Health Care Select Sector SPDR",
}

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


def infer_filing_jurisdiction(ticker: str) -> FilingJurisdiction:
    """Route Filings UI: Korean listings use DART, Japanese use EDINET, else SEC."""
    t = (ticker or "").strip().upper()
    if t.endswith(".KS") or t.endswith(".KQ"):
        return "DART"
    if t.endswith(".T"):
        return "EDINET"
    return "SEC"


def korean_stock_code_from_ticker(ticker: str) -> Optional[str]:
    """Return 6-digit KRX stock code from ``005930.KS`` / ``005930.KQ``, else None."""
    t = (ticker or "").strip().upper()
    if not (t.endswith(".KS") or t.endswith(".KQ")):
        return None
    base = t.rsplit(".", 1)[0].strip()
    if base.isdigit() and len(base) == 6:
        return base
    return None


def japanese_sec_code_from_ticker(ticker: str) -> Optional[str]:
    """Return EDINET 5-digit security code from ``7203.T`` → ``72030`` (4-digit + 0)."""
    t = (ticker or "").strip().upper()
    if not t.endswith(".T"):
        return None
    base = t.rsplit(".", 1)[0].strip()
    if base.isdigit() and len(base) == 4:
        return base + "0"
    return None


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


def detect_asset_type(ticker: str) -> AssetType:
    """Detect asset type by ticker pattern and quoteType fallback."""
    t = (ticker or "").strip().upper()
    if not t:
        return AssetType.EQUITY
    if t.endswith("=F") or t in COMMODITY_FUTURES:
        return AssetType.COMMODITY_FUTURE
    if t.endswith("-USD") or t.endswith("-KRW"):
        return AssetType.CRYPTO
    if t.startswith("^"):
        return AssetType.INDEX
    try:
        import yfinance as yf

        info = yf.Ticker(t).info or {}
        quote_type = str(info.get("quoteType", "")).upper()
        if quote_type in {"ETF", "MUTUALFUND"}:
            return AssetType.ETF
    except Exception:
        pass
    if t in POPULAR_COMMODITY_ETFS:
        return AssetType.ETF
    return AssetType.EQUITY
