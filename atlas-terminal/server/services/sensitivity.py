"""Sensitivity analysis for DCF valuation.

Provides:
- WACC vs Terminal Growth sensitivity matrix
- Tornado chart data (variable impact ranking)
"""

from typing import Dict, List, Any

from server.services.dcf_engine import excel_style_dcf


def build_sensitivity_matrix(
    fcf: float,
    total_debt: float,
    cash: float,
    shares: float,
    base_wacc: float,
    base_tg: float,
    fcf_growth: float,
    wacc_steps: int = 6,
    tg_steps: int = 5,
    wacc_range: float = 0.02,
    tg_range: float = 0.01,
) -> Dict[str, Any]:
    """Build a 2-D sensitivity matrix: WACC (rows) x Terminal Growth (cols).

    Returns
    -------
    dict
        wacc_values : list[float]  – row headers (percentages, e.g. 8.0)
        tg_values   : list[float]  – column headers (percentages, e.g. 2.5)
        matrix      : list[list[float | None]]  – per-share intrinsic values
    """
    # Generate evenly-spaced WACC and TG values centred on base
    wacc_values = [
        round(base_wacc - wacc_range + (2 * wacc_range / max(wacc_steps - 1, 1)) * i, 4)
        for i in range(wacc_steps)
    ]
    tg_values = [
        round(base_tg - tg_range + (2 * tg_range / max(tg_steps - 1, 1)) * i, 4)
        for i in range(tg_steps)
    ]

    matrix: List[List[Any]] = []
    for w in wacc_values:
        row: List[Any] = []
        for tg in tg_values:
            if w <= tg or w <= 0 or shares <= 0:
                row.append(None)
            else:
                result = excel_style_dcf(fcf, w, tg, fcf_growth, total_debt, cash, shares)
                vps = result.get("value_per_share")
                row.append(round(vps, 2) if vps is not None else None)
        matrix.append(row)

    return {
        "wacc_values": [round(w * 100, 2) for w in wacc_values],
        "tg_values": [round(tg * 100, 2) for tg in tg_values],
        "matrix": matrix,
    }


def build_tornado_data(
    fcf: float,
    wacc: float,
    tg: float,
    growth: float,
    debt: float,
    cash: float,
    shares: float,
) -> List[Dict[str, Any]]:
    """Compute tornado-chart data by varying each input ±10 %.

    Returns a list sorted descending by impact range (high − low).
    Each entry: {"variable", "low", "high", "base"}.
    """
    if shares <= 0:
        return []

    def _val(f, w, t, g, d, c) -> float | None:
        if w <= t or w <= 0:
            return None
        r = excel_style_dcf(f, w, t, g, d, c, shares)
        return r.get("value_per_share")

    base_val = _val(fcf, wacc, tg, growth, debt, cash)
    if base_val is None:
        return []

    variables = [
        ("WACC", lambda sign: _val(fcf, wacc * (1 + sign * 0.10), tg, growth, debt, cash)),
        ("FCF Growth", lambda sign: _val(fcf, wacc, tg, growth * (1 + sign * 0.10), debt, cash)),
        ("Terminal Growth", lambda sign: _val(fcf, wacc, tg * (1 + sign * 0.10), growth, debt, cash)),
        ("Base FCF", lambda sign: _val(fcf * (1 + sign * 0.10), wacc, tg, growth, debt, cash)),
        ("Total Debt", lambda sign: _val(fcf, wacc, tg, growth, debt * (1 + sign * 0.10), cash)),
        ("Cash", lambda sign: _val(fcf, wacc, tg, growth, debt, cash * (1 + sign * 0.10))),
    ]

    results: List[Dict[str, Any]] = []
    for name, func in variables:
        val_up = func(0.10)
        val_dn = func(-0.10)
        if val_up is None or val_dn is None:
            continue
        low = round(min(val_up, val_dn), 2)
        high = round(max(val_up, val_dn), 2)
        results.append({
            "variable": name,
            "low": low,
            "high": high,
            "base": round(base_val, 2),
        })

    results.sort(key=lambda d: d["high"] - d["low"], reverse=True)
    return results
