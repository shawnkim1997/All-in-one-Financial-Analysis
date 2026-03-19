"""
Small formatting/type-safety helpers used across multiple modules.
"""
from typing import Optional

import pandas as pd


def _safe_float(x) -> Optional[float]:
    if x is None or (isinstance(x, float) and (x != x or pd.isna(x))):
        return None
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _format_shares_display(shares: float) -> str:
    """Format share count for UI, e.g. 15.42B Shares or 1.2B Shares."""
    if shares is None or shares <= 0:
        return "N/A"
    s = float(shares)
    if s >= 1e9:
        return f"{s / 1e9:.2f}B Shares"
    if s >= 1e6:
        return f"{s / 1e6:.2f}M Shares"
    if s >= 1e3:
        return f"{s / 1e3:.2f}K Shares"
    return f"{s:.0f} Shares"


def _na(x):
    """Return N/A for None/NaN, else value (for display)."""
    if x is None or (isinstance(x, float) and (pd.isna(x) or x != x)):
        return "N/A"
    return x
