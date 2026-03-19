from typing import Optional
import pandas as pd
import streamlit as st
from utils.formatting import _safe_float, _na
from data.financials import _get_row_series, _get_annual_financials_balance_cashflow

try:
    import yfinance as yf
except ImportError:
    yf = None


@st.cache_data(ttl=300)
def get_comps_data(tickers: tuple) -> pd.DataFrame:
    """Fetch Forward P/E, EV/EBITDA, P/B using forwardPE, enterpriseToEbitda, priceToBook. Missing → None (display as N/A). Robust per-ticker error handling."""
    if not yf:
        return pd.DataFrame()
    rows = []
    for sym in tickers:
        sym = str(sym).strip().upper()
        if not sym:
            continue
        try:
            t = yf.Ticker(sym)
            info = t.info or {}
            forward_pe = info.get("forwardPE") or info.get("Forward PE") or info.get("trailingPE") or info.get("Trailing PE")
            ev_ebitda = info.get("enterpriseToEbitda")
            if ev_ebitda is None:
                ev, ebitda = info.get("enterpriseValue"), info.get("ebitda")
                if ev is not None and ebitda is not None and ebitda != 0:
                    ev_ebitda = ev / ebitda
            pb = info.get("priceToBook") or info.get("Price To Book")
            rows.append({
                "Ticker": sym,
                "Forward P/E": round(float(forward_pe), 2) if forward_pe is not None and _safe_float(forward_pe) is not None else None,
                "EV/EBITDA": round(float(ev_ebitda), 2) if ev_ebitda is not None and _safe_float(ev_ebitda) is not None else None,
                "P/B": round(float(pb), 2) if pb is not None and _safe_float(pb) is not None else None,
            })
        except Exception:
            rows.append({"Ticker": sym, "Forward P/E": None, "EV/EBITDA": None, "P/B": None})
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows)


@st.cache_data(ttl=300)
def get_dupont_altman_redflags_yoy(ticker: str) -> dict:
    """Returns DuPont (3-step ROE), Altman Z-Score, red flags, YoY. Uses yahooquery then yfinance with TTM fallback."""
    try:
        fin, bal, _ = _get_annual_financials_balance_cashflow(ticker)
        if fin is None or fin.empty or bal is None or bal.empty:
            return {}
        t = yf.Ticker(ticker.upper())
        info = t.info or {}
        # TTM columns: keep order TTM0 (current), TTM1 (prior). Else use date sort (newest first).
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
        def _v(s, d):
            if s is None or d not in s.index:
                return None
            return _safe_float(s.get(d))
        rows = []
        for i, d in enumerate(dates):
            yr = int(str(d)[:4]) if (isinstance(d, str) and str(d)[:4].isdigit()) else (d.year if hasattr(d, "year") else (2024 - i))
            r = _v(rev, d)
            net_i = _v(ni, d)
            ta = _v(total_assets, d)
            te = _v(total_equity, d)
            if ta and ta > 0 and te and te > 0 and r and r != 0:
                npm = (net_i / r * 100) if net_i is not None else None
                at = r / ta if r and ta else None
                em = ta / te if ta and te else None
                roe = (net_i / te * 100) if (net_i and te) else (npm * at * em / 100 if (npm and at and em) else None)
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
            if op_inc is not None and int_exp is not None and int_exp != 0:
                _ic = op_inc / int_exp
                interest_cov = round(_ic, 2) if (_ic == _ic and not (isinstance(_ic, float) and (pd.isna(_ic) or _ic != _ic))) else None
            else:
                interest_cov = None  # N/A when Interest Expense is 0 or missing (avoid nan%)
            rows.append({
                "Year": yr,
                "Revenue": r, "Net Income": net_i,
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
        yoy = []
        if len(dupont_df) >= 2:
            for col in ["NPM %", "ROE %", "Gross Margin %", "Operating Margin %", "Current Ratio", "Interest Coverage"]:
                if col not in dupont_df.columns:
                    continue
                cur = dupont_df[col].iloc[0]
                prev = dupont_df[col].iloc[1]
                if cur is not None and prev is not None and prev != 0 and not (pd.isna(cur) or pd.isna(prev)):
                    if "Margin" in col or "NPM" in col or "ROE" in col:
                        chg_pp = (cur - prev)  # percentage point change (e.g. 7.0 = 7%)
                        if pd.isna(chg_pp) or chg_pp != chg_pp:
                            continue
                        yoy.append({"Ratio": col, "Latest": cur, "Prior": prev, "YoY (pp)": round(chg_pp, 2), "Comment": f"{'Improved' if chg_pp > 0 else 'Declined'} by {abs(chg_pp):.1f}% YoY"})
                    else:
                        pct = (cur - prev) / abs(prev) * 100
                        if pd.isna(pct) or pct != pct:
                            continue
                        yoy.append({"Ratio": col, "Latest": cur, "Prior": prev, "YoY %": round(pct, 1), "Comment": f"{'Up' if pct > 0 else 'Down'} {abs(round(pct, 1))}% YoY"})
        latest_bal_d = bal.columns[0]
        wc = (_v(current_assets, latest_bal_d) or 0) - (_v(current_liab, latest_bal_d) or 0)
        ta_l = _v(total_assets, latest_bal_d)
        re_l = _v(retained, latest_bal_d)
        tl_l = _v(total_liab, latest_bal_d)
        ebit_l = _v(ebit, fin.columns[0])
        sales_l = _v(rev, fin.columns[0])
        altman_z = None
        if ta_l and ta_l > 0 and market_cap is not None and tl_l and tl_l != 0 and sales_l:
            a = wc / ta_l
            b = (re_l or 0) / ta_l
            c = (ebit_l or 0) / ta_l
            d = market_cap / tl_l
            e = sales_l / ta_l
            altman_z = 1.2 * a + 1.4 * b + 3.3 * c + 0.6 * d + 1.0 * e
        red_flags = []
        if len(dupont_df) > 0:
            row0 = dupont_df.iloc[0]
            cr = row0.get("Current Ratio")
            if cr is not None and cr < 1.0:
                red_flags.append({"metric": "Current Ratio", "value": cr, "threshold": 1.0, "flag": "WARNING", "comment": "Current assets do not cover current liabilities; liquidity risk."})
            ic = row0.get("Interest Coverage")
            if ic is not None and ic < 1.5:
                red_flags.append({"metric": "Interest Coverage", "value": ic, "threshold": 1.5, "flag": "WARNING", "comment": "EBIT barely covers interest; default risk."})
        return {
            "dupont": dupont_df,
            "yoy": yoy,
            "altman_z": round(altman_z, 2) if altman_z is not None else None,
            "red_flags": red_flags,
        }
    except (KeyError, TypeError, ZeroDivisionError, IndexError) as e:
        return {}
    except Exception:
        return {}


@st.cache_data(ttl=300)
def get_quarterly_momentum(ticker: str) -> dict:
    """Last 4 quarters Revenue and Net Income from quarterly_financials; QoQ growth for most recent quarter. Returns {df, qoq_revenue_pct, qoq_ni_pct} or empty."""
    out = {"df": None, "qoq_revenue_pct": None, "qoq_ni_pct": None}
    if not yf or not ticker:
        return out
    try:
        t = yf.Ticker(ticker.upper())
        qfin = getattr(t, "quarterly_financials", None)
        if qfin is None or qfin.empty or len(qfin.columns) < 2:
            return out
        rev = _get_row_series(qfin, "Total Revenue", "Revenue", "Net Revenue")
        ni = _get_row_series(qfin, "Net Income", "Net Income Common Stockholders")
        if rev is None and ni is None:
            return out
        cols = list(qfin.columns)[:4]
        rows = []
        for c in cols:
            try:
                if hasattr(c, "strftime"):
                    q = (c.month - 1) // 3 + 1 if hasattr(c, "month") else 1
                    label = c.strftime("%Y") + f"-Q{q}"
                else:
                    label = str(c)[:12]
            except Exception:
                label = str(c)[:12]
            r_val = _safe_float(rev.loc[c]) if rev is not None and c in rev.index else None
            n_val = _safe_float(ni.loc[c]) if ni is not None and c in ni.index else None
            rows.append({"Quarter": label, "Revenue": r_val, "Net Income": n_val})
        out["df"] = pd.DataFrame(rows)
        if len(rows) >= 2:
            r0, r1 = rows[0].get("Revenue"), rows[1].get("Revenue")
            n0, n1 = rows[0].get("Net Income"), rows[1].get("Net Income")
            if r0 is not None and r1 is not None and r1 != 0:
                out["qoq_revenue_pct"] = round((r0 - r1) / abs(r1) * 100, 1)
            if n0 is not None and n1 is not None and n1 != 0:
                out["qoq_ni_pct"] = round((n0 - n1) / abs(n1) * 100, 1)
        return out
    except Exception:
        return out


@st.cache_data(ttl=300)
def get_quarterly_ratio_changes(ticker: str) -> list:
    """QoQ ratio changes: NPM %, ROE %, Gross Margin %, Operating Margin %, Current Ratio, Interest Coverage. Latest quarter vs previous. Returns list of {Metric, Current, Change, Trend}."""
    out = []
    if not yf or not ticker:
        return out
    try:
        t = yf.Ticker(ticker.upper())
        qf = getattr(t, "quarterly_financials", None)
        qb = getattr(t, "quarterly_balance_sheet", None)
        if qf is None or qf.empty or qb is None or qb.empty or len(qf.columns) < 2 or len(qb.columns) < 2:
            return out
        rev = _get_row_series(qf, "Total Revenue", "Revenue", "Net Revenue")
        ni = _get_row_series(qf, "Net Income", "Net Income Common Stockholders")
        gross = _get_row_series(qf, "Gross Profit")
        ebit = _get_row_series(qf, "Operating Income", "EBIT")
        interest = _get_row_series(qf, "Interest Expense", "Interest Expense Net")
        ta = _get_row_series(qb, "Total Assets")
        te = _get_row_series(qb, "Total Stockholder Equity", "Stockholders Equity", "Total Equity Gross Minority Interest")
        ca = _get_row_series(qb, "Current Assets")
        cl = _get_row_series(qb, "Current Liabilities")
        def v(s, col):
            if s is None or col not in s.index:
                return None
            return _safe_float(s.get(col))
        c0, c1 = qf.columns[0], qf.columns[1]
        b0, b1 = qb.columns[0], qb.columns[1]
        r0, r1 = v(rev, c0), v(rev, c1)
        n0, n1 = v(ni, c0), v(ni, c1)
        g0, g1 = v(gross, c0), v(gross, c1)
        e0, e1 = v(ebit, c0), v(ebit, c1)
        i0, i1 = v(interest, c0), v(interest, c1)
        ta0, ta1 = v(ta, b0), v(ta, b1)
        te0, te1 = v(te, b0), v(te, b1)
        ca0, ca1 = v(ca, b0), v(ca, b1)
        cl0, cl1 = v(cl, b0), v(cl, b1)
        npm0 = (n0 / r0 * 100) if (n0 is not None and r0 and r0 != 0) else None
        npm1 = (n1 / r1 * 100) if (n1 is not None and r1 and r1 != 0) else None
        roe0 = (n0 / te0 * 100) if (n0 is not None and te0 and te0 != 0) else None
        roe1 = (n1 / te1 * 100) if (n1 is not None and te1 and te1 != 0) else None
        gm0 = (g0 / r0 * 100) if (g0 is not None and r0 and r0 != 0) else None
        gm1 = (g1 / r1 * 100) if (g1 is not None and r1 and r1 != 0) else None
        om0 = (e0 / r0 * 100) if (e0 is not None and r0 and r0 != 0) else None
        om1 = (e1 / r1 * 100) if (e1 is not None and r1 and r1 != 0) else None
        cr0 = (ca0 / cl0) if (ca0 is not None and cl0 and cl0 != 0) else None
        cr1 = (ca1 / cl1) if (ca1 is not None and cl1 and cl1 != 0) else None
        ic0 = (e0 / i0) if (e0 is not None and i0 and i0 != 0) else None
        ic1 = (e1 / i1) if (e1 is not None and i1 and i1 != 0) else None
        def row(metric, cur, prev, is_pct_point=False):
            if cur is None:
                return None
            cur_str = f"{round(cur, 2):.2f}"
            if prev is None or (is_pct_point and prev != prev):
                return {"Metric": metric, "Current Value": cur_str, "Change": "—", "Trend": "—"}
            if is_pct_point:
                chg = cur - prev
            else:
                chg = ((cur - prev) / abs(prev) * 100) if prev != 0 else 0
            trend = "↑" if chg > 0 else ("↓" if chg < 0 else "—")
            chg_str = f"{chg:+.1f}%" if not is_pct_point else f"{chg:+.1f} pp"
            return {"Metric": metric, "Current Value": cur_str, "Change": chg_str, "Trend": trend}
        for name, cur, prev, is_pp in [
            ("NPM %", npm0, npm1, True), ("ROE %", roe0, roe1, True), ("Gross Margin %", gm0, gm1, True),
            ("Operating Margin %", om0, om1, True), ("Current Ratio", cr0, cr1, False), ("Interest Coverage", ic0, ic1, False),
        ]:
            r = row(name, cur, prev, is_pp)
            if r:
                out.append(r)
        return out
    except Exception:
        return out
