"""
Ticker formatting and market inference utilities.
"""
from config.constants import MARKET_OPTIONS


def get_global_ticker(ticker: str, market: str) -> str:
    """Format ticker for Yahoo Finance by market. US: as-is. South Korea: .KS or .KQ. Japan: .T. UK: .L. If ticker already has suffix, return as-is."""
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
    """Infer market label from ticker suffix (for Deep-Dive routing when no Market selector)."""
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
