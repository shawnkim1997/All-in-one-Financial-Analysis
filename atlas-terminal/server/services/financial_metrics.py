"""Financial health metrics: DuPont, Altman Z, Piotroski F-Score, radar, and sector-specific.

All functions return pure data (dicts, DataFrames) with no presentation logic.
Consumers (API routers, Streamlit UI) handle display and charting.
"""

from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from server.utils.safe_float import _safe_float
from server.services.market_fetcher import (
    _get_annual_financials_balance_cashflow,
    _get_row_series,
)

try:
    import yfinance as yf
except ImportError:
    yf = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Radar normalisation
# ---------------------------------------------------------------------------

def _radar_norm(
    roe_pct: Optional[float],
    current_ratio: Optional[float],
    asset_turnover: Optional[float],
    equity_mult: Optional[float],
    rev_yoy_pct: Optional[float],
) -> List[float]:
    """Normalise five raw metrics to 0-100 for radar chart display."""
    def n_roe(x: Optional[float]) -> float:
        return min(100, max(0, (x + 10) / 40 * 100)) if x is not None else 50
    def n_cr(x: Optional[float]) -> float:
        return min(100, max(0, x / 3 * 100)) if x is not None else 50
    def n_at(x: Optional[float]) -> float:
        return min(100, max(0, x * 50)) if x is not None else 50
    def n_em(x: Optional[float]) -> float:
        return min(100, max(0, (x - 0.5) / 2.5 * 100)) if x is not None else 50
    def n_yoy(x: Optional[float]) -> float:
        return min(100, max(0, (x + 20) / 50 * 100)) if x is not None else 50
    return [n_roe(roe_pct), n_cr(current_ratio), n_at(asset_turnover), n_em(equity_mult), n_yoy(rev_yoy_pct)]


# ---------------------------------------------------------------------------
# DuPont / Altman Z / Red Flags / YoY
# ---------------------------------------------------------------------------

def get_dupont_altman_redflags_yoy(ticker: str) -> Dict[str, Any]:
    """DuPont 3-step ROE, Altman Z-Score, red flags, and YoY ratio changes.

    Returns
    -------
    dict
        Keys: ``dupont`` (DataFrame), ``yoy`` (list), ``altman_z`` (float|None),
        ``red_flags`` (list of dicts).
    """
    try:
        fin, bal, _ = _get_annual_financials_balance_cashflow(ticker)
        if fin is None or fin.empty or bal is None or bal.empty:
            return {}
        t = yf.Ticker(ticker.upper())
        info = t.info or {}
        col_list = fin.columns.tolist()
        if col_list and str(col_list[0]).startswith("TTM"):
            dates = col_list[:3]
        else:
            dates = sorted(col_list, reverse=True)[:3]
        if not dates:
            return {}

        rev = _get_row_series(fin, "Total Revenue", "Revenue", "Net Revenue")
        ni = _get_row_series(fin, "Net Income", "Net Income Common Stockholders")
        ebit = _get_row_series(fin, "Operating Income", "EBIT")
        gross = _get_row_series(fin, "Gross Profit")
        interest = _get_row_series(fin, "Interest Expense", "Interest Expense Net")
        total_assets = _get_row_series(bal, "Total Assets")
        total_equity = _get_row_series(bal, "Total Stockholder Equity", "Stockholders Equity", "Total Equity Gross Minority Interest")
        current_assets = _get_row_series(bal, "Current Assets")
        current_liab = _get_row_series(bal, "Current Liabilities")
        retained = _get_row_series(bal, "Retained Earnings")
        total_liab = _get_row_series(bal, "Total Liabilities")
        market_cap = info.get("marketCap") or info.get("Market Cap")

        def _v(s: Optional[pd.Series], d: Any) -> Optional[float]:
            if s is None or d not in s.index:
                return None
            return _safe_float(s.get(d))

        rows: List[Dict[str, Any]] = []
        for i, d in enumerate(dates):
            yr = int(str(d)[:4]) if (isinstance(d, str) and str(d)[:4].isdigit()) else (d.year if hasattr(d, "year") else (2024 - i))
            r = _v(rev, d)
            net_i = _v(ni, d)
            ta = _v(total_assets, d)
            te = _v(total_equity, d)
            if ta and ta > 0 and te and te > 0 and r and r != 0:
                npm = (net_i / r * 100) if net_i is not None else None
                at = r / ta
                em = ta / te
                roe = (net_i / te * 100) if net_i else None
            else:
                npm = at = em = roe = None
            gross_p = _v(gross, d)
            gross_margin = (gross_p / r * 100) if (gross_p and r and r != 0) else None
            op_inc = _v(ebit, d)
            op_margin = (op_inc / r * 100) if (op_inc and r and r != 0) else None
            ca = _v(current_assets, d)
            cl = _v(current_liab, d)
            current_ratio = (ca / cl) if (ca and cl and cl != 0) else None
            int_exp = _v(interest, d)
            interest_cov: Optional[float] = None
            if op_inc is not None and int_exp is not None and int_exp != 0:
                _ic = op_inc / int_exp
                interest_cov = round(_ic, 2) if (_ic == _ic and not pd.isna(_ic)) else None
            rows.append({
                "Year": yr, "Revenue": r, "Net Income": net_i,
                "NPM %": round(npm, 2) if npm is not None else None,
                "Asset Turnover": round(at, 4) if at is not None else None,
                "Equity Mult.": round(em, 2) if em is not None else None,
                "ROE %": round(roe, 2) if roe is not None else None,
                "Gross Margin %": round(gross_margin, 2) if gross_margin is not None else None,
                "Operating Margin %": round(op_margin, 2) if op_margin is not None else None,
                "Current Ratio": round(current_ratio, 2) if current_ratio is not None else None,
                "Interest Coverage": interest_cov,
            })

        dupont_df = pd.DataFrame(rows)

        # YoY
        yoy: List[Dict[str, Any]] = []
        if len(dupont_df) >= 2:
            for col in ["NPM %", "ROE %", "Gross Margin %", "Operating Margin %", "Current Ratio", "Interest Coverage"]:
                if col not in dupont_df.columns:
                    continue
                cur = dupont_df[col].iloc[0]
                prev = dupont_df[col].iloc[1]
                if cur is None or prev is None or prev == 0 or pd.isna(cur) or pd.isna(prev):
                    continue
                if "Margin" in col or "NPM" in col or "ROE" in col:
                    chg_pp = cur - prev
                    if pd.isna(chg_pp):
                        continue
                    yoy.append({"Ratio": col, "Latest": cur, "Prior": prev, "YoY (pp)": round(chg_pp, 2),
                                "Comment": f"{'Improved' if chg_pp > 0 else 'Declined'} by {abs(chg_pp):.1f}% YoY"})
                else:
                    pct = (cur - prev) / abs(prev) * 100
                    if pd.isna(pct):
                        continue
                    yoy.append({"Ratio": col, "Latest": cur, "Prior": prev, "YoY %": round(pct, 1),
                                "Comment": f"{'Up' if pct > 0 else 'Down'} {abs(round(pct, 1))}% YoY"})

        # Altman Z
        latest_bal_d = bal.columns[0]
        wc = (_v(current_assets, latest_bal_d) or 0) - (_v(current_liab, latest_bal_d) or 0)
        ta_l = _v(total_assets, latest_bal_d)
        re_l = _v(retained, latest_bal_d)
        tl_l = _v(total_liab, latest_bal_d)
        ebit_l = _v(ebit, fin.columns[0])
        sales_l = _v(rev, fin.columns[0])
        altman_z: Optional[float] = None
        if ta_l and ta_l > 0 and market_cap is not None and tl_l and tl_l != 0 and sales_l:
            a = wc / ta_l
            b = (re_l or 0) / ta_l
            c = (ebit_l or 0) / ta_l
            dd = market_cap / tl_l
            e = sales_l / ta_l
            altman_z = 1.2 * a + 1.4 * b + 3.3 * c + 0.6 * dd + 1.0 * e

        # Red flags
        red_flags: List[Dict[str, Any]] = []
        if len(dupont_df) > 0:
            row0 = dupont_df.iloc[0]
            cr = row0.get("Current Ratio")
            if cr is not None and cr < 1.0:
                red_flags.append({"metric": "Current Ratio", "value": cr, "threshold": 1.0, "flag": "WARNING",
                                  "comment": "Current assets do not cover current liabilities; liquidity risk."})
            ic = row0.get("Interest Coverage")
            if ic is not None and ic < 1.5:
                red_flags.append({"metric": "Interest Coverage", "value": ic, "threshold": 1.5, "flag": "WARNING",
                                  "comment": "EBIT barely covers interest; default risk."})

        return {"dupont": dupont_df, "yoy": yoy, "altman_z": round(altman_z, 2) if altman_z is not None else None, "red_flags": red_flags}
    except Exception:
        return {}
