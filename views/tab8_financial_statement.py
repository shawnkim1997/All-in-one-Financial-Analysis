"""
Tab 8 — Standardized Financial Statements
Sub-tabs for Highlights, Income Statement, Balance Sheet, Cash Flow with
YoY growth rates, conditional color coding (green/red), and AI summary.
"""
import streamlit as st
import pandas as pd
from config.constants import MARKET_OPTIONS
from utils.ticker import get_global_ticker
from data.financials import _get_annual_financials_balance_cashflow
from data.fundamentals import get_sector_industry
from views.financial_ai_summary import render_ai_summary


# ───────── Formatting ─────────

def _fmt_val(val) -> str:
    """Format raw number. Parentheses for negatives."""
    if val is None:
        return "N/A"
    try:
        f = float(val)
        if f != f:
            return "N/A"
        neg = f < 0
        af = abs(f)
        if af >= 1e9:
            s = f"{af / 1e9:,.1f}"
        elif af >= 1e6:
            s = f"{af / 1e6:,.1f}"
        elif af >= 1e3:
            s = f"{af / 1e3:,.1f}"
        else:
            s = f"{af:,.0f}"
        return f"({s})" if neg else s
    except (ValueError, TypeError):
        return "N/A"


def _calc_yoy(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate YoY growth rates between consecutive columns."""
    if df is None or df.empty or len(df.columns) < 2:
        return pd.DataFrame()
    yoy = pd.DataFrame(index=df.index)
    for i in range(len(df.columns) - 1):
        curr_col, prev_col = df.columns[i], df.columns[i + 1]
        vals = []
        for idx in df.index:
            try:
                c, p = float(df.loc[idx, curr_col]), float(df.loc[idx, prev_col])
                vals.append((c - p) / abs(p) * 100 if p != 0 and c == c and p == p else None)
            except (ValueError, TypeError):
                vals.append(None)
        yoy[f"{str(curr_col)[:10]} YoY"] = vals
    return yoy


def _build_display_df(raw_df: pd.DataFrame) -> pd.DataFrame:
    """Build display DF with interleaved YoY growth rows."""
    if raw_df is None or raw_df.empty:
        return pd.DataFrame()
    cols = raw_df.columns[:5]
    df = raw_df[cols].copy()
    yoy = _calc_yoy(df)
    rows = []
    for idx in df.index:
        row = {"Item": idx}
        for c in cols:
            row[str(c)[:10]] = _fmt_val(df.loc[idx, c])
        rows.append(row)
        yoy_row = {"Item": "  YoY Growth (%)"}
        has_yoy = False
        for yc in yoy.columns:
            period = yc.replace(" YoY", "")
            val = yoy.loc[idx, yc] if idx in yoy.index else None
            if val is not None and val == val:
                yoy_row[period] = f"{val:+.2f}%"
                has_yoy = True
            else:
                yoy_row[period] = ""
        if has_yoy:
            rows.append(yoy_row)
    result = pd.DataFrame(rows)
    if "Item" in result.columns:
        result = result.set_index("Item")
    return result


def _render_styled_table(df: pd.DataFrame):
    """Render financial statement as HTML with color-coded YoY rows."""
    if df is None or df.empty:
        st.warning("No data available.")
        return
    html = '<table style="width:100%;border-collapse:collapse;font-size:0.85rem;">'
    html += '<tr style="border-bottom:2px solid rgba(255,255,255,0.1);">'
    html += '<th style="text-align:left;padding:8px;color:#9CA3AF;min-width:200px;">Item</th>'
    for c in df.columns:
        html += f'<th style="text-align:right;padding:8px;color:#9CA3AF;">{c}</th>'
    html += '</tr>'
    for idx in df.index:
        is_yoy = "YoY" in str(idx)
        bg = "rgba(255,255,255,0.02)" if not is_yoy else "transparent"
        fs = "0.85rem" if not is_yoy else "0.75rem"
        bdr = "border-bottom:1px solid rgba(255,255,255,0.04);" if not is_yoy else ""
        lc = "#F3F4F6" if not is_yoy else "#6B7280"
        fw = "600" if not is_yoy else "400"
        html += f'<tr style="background:{bg};{bdr}">'
        html += f'<td style="padding:{"6" if not is_yoy else "4"}px 8px;color:{lc};font-size:{fs};font-weight:{fw};">{idx}</td>'
        for c in df.columns:
            val = str(df.loc[idx, c])
            if is_yoy and "%" in val:
                try:
                    num = float(val.replace("%", "").replace("+", ""))
                    cbg = "rgba(52,211,153,0.12)" if num > 0 else ("rgba(248,113,113,0.12)" if num < 0 else "transparent")
                    cc = "#34D399" if num > 0 else ("#F87171" if num < 0 else "#9CA3AF")
                except ValueError:
                    cbg, cc = "transparent", "#9CA3AF"
                html += f'<td style="text-align:right;padding:4px 8px;background:{cbg};color:{cc};font-size:{fs};border-radius:4px;">{val}</td>'
            elif not is_yoy and "(" in val:
                html += f'<td style="text-align:right;padding:6px 8px;color:#F87171;font-size:{fs};">{val}</td>'
            else:
                html += f'<td style="text-align:right;padding:{"6" if not is_yoy else "4"}px 8px;color:{lc};font-size:{fs};">{val}</td>'
        html += '</tr>'
    html += '</table>'
    st.markdown(html, unsafe_allow_html=True)


# ───────── Highlights ─────────

def _render_highlights(fin_df, bal_df, cf_df):
    """Quick financial highlights."""
    def _g(df, name):
        if df is None or df.empty or name not in df.index:
            return None
        try:
            return float(df.iloc[df.index.get_loc(name), 0])
        except Exception:
            return None

    rev, ni, gp = _g(fin_df, "Total Revenue"), _g(fin_df, "Net Income"), _g(fin_df, "Gross Profit")
    ta, tl = _g(bal_df, "Total Assets"), _g(bal_df, "Total Liabilities")
    eq, ocf = _g(bal_df, "Total Stockholder Equity"), _g(cf_df, "Operating Cash Flow")
    gm = (gp / rev * 100) if rev and gp and rev > 0 else None
    nm = (ni / rev * 100) if rev and ni and rev > 0 else None
    roe = (ni / eq * 100) if ni and eq and eq > 0 else None
    de = (tl / eq) if tl and eq and eq > 0 else None

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Revenue", f"${rev/1e9:,.1f}B" if rev else "N/A")
        st.metric("Net Income", f"${ni/1e9:,.1f}B" if ni else "N/A")
    with c2:
        st.metric("Gross Margin", f"{gm:.1f}%" if gm else "N/A")
        st.metric("Net Margin", f"{nm:.1f}%" if nm else "N/A")
    with c3:
        st.metric("ROE", f"{roe:.1f}%" if roe else "N/A")
        st.metric("D/E Ratio", f"{de:.2f}" if de else "N/A")
    with c4:
        st.metric("Total Assets", f"${ta/1e9:,.1f}B" if ta else "N/A")
        st.metric("Op. Cash Flow", f"${ocf/1e9:,.1f}B" if ocf else "N/A")


# ───────── Main ─────────

def render_tab8(ticker):
    """Render the Standardized Financial Statement tab."""
    market = st.session_state.get("market") or MARKET_OPTIONS[0]
    qt = get_global_ticker(ticker, market) if ticker else ""
    st.subheader("Standardized Financial Statements")
    if not ticker:
        st.info("Select a company from the sidebar.")
        return
    si = get_sector_industry(qt)
    st.caption(f"**{ticker}** · {si.get('sector','N/A')} · {si.get('industry','N/A')}")

    with st.spinner("Loading financial statements..."):
        fin_df, bal_df, cf_df = _get_annual_financials_balance_cashflow(qt)
    if fin_df is None and bal_df is None and cf_df is None:
        st.error("Could not retrieve financial data.")
        return

    t_hl, t_is, t_bs, t_cf, t_ai = st.tabs([
        "Highlights", "Income Statement", "Balance Sheet", "Cash Flow", "AI Summary",
    ])
    with t_hl:
        _render_highlights(fin_df, bal_df, cf_df)
    with t_is:
        _render_styled_table(_build_display_df(fin_df))
    with t_bs:
        _render_styled_table(_build_display_df(bal_df))
    with t_cf:
        _render_styled_table(_build_display_df(cf_df))
    with t_ai:
        render_ai_summary(ticker, fin_df, bal_df, cf_df)
