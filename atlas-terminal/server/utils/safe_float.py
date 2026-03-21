"""Numeric safety utilities for the ATLAS Terminal backend.

Provides safe type-coercion helpers used across all services to handle
None, NaN, and non-numeric values gracefully without raising exceptions.
"""

from typing import Optional

import pandas as pd


def _safe_float(x: object) -> Optional[float]:
    """Convert *x* to ``float``, returning ``None`` for unconvertible values.

    Handles ``None``, ``NaN`` (both Python ``float('nan')`` and pandas
    ``pd.NA``), and arbitrary objects whose ``float()`` conversion fails.

    Parameters
    ----------
    x:
        Any value that might be numeric.

    Returns
    -------
    Optional[float]
        The float representation, or ``None`` if conversion is impossible.
    """
    if x is None or (isinstance(x, float) and (x != x or pd.isna(x))):
        return None
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _na(x: object) -> object:
    """Return the string ``'N/A'`` for ``None``/``NaN``, otherwise *x* unchanged.

    Useful when building display-ready dictionaries or DataFrames where
    missing numeric values should appear as a human-readable sentinel.

    Parameters
    ----------
    x:
        Any value.

    Returns
    -------
    object
        ``'N/A'`` when *x* is ``None`` or ``NaN``; *x* otherwise.
    """
    if x is None or (isinstance(x, float) and (pd.isna(x) or x != x)):
        return "N/A"
    return x


def _format_shares_display(shares: Optional[float]) -> str:
    """Format a share count for human-friendly display.

    Examples
    --------
    >>> _format_shares_display(15_420_000_000)
    '15.42B Shares'
    >>> _format_shares_display(1_200_000)
    '1.20M Shares'
    >>> _format_shares_display(None)
    'N/A'

    Parameters
    ----------
    shares:
        Raw share count (absolute number, not in millions/billions).

    Returns
    -------
    str
        A concise string such as ``'15.42B Shares'`` or ``'N/A'``.
    """
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
