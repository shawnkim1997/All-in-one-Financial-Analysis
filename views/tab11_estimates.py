"""
Tab 11 — Earnings Estimates & Outlook
Analyst consensus estimates, revenue/EPS forecasts, earnings history, price targets.
"""
import streamlit as st
import pandas as pd
from config.constants import MARKET_OPTIONS
from utils.ticker import get_global_ticker
from data.estimates import get_analyst_estimates, get_earnings_dates, format_estimate_table
from data.fundamentals import get_sector_industry

try:
    import plotly.graph_objects as go
except ImportError:
    go = None


def _render_price_targets(targets: dict):
    """Render analyst price target visualization."""
    if not targets or not targets.get("mean"):
        return
    st.markdown("#### Analyst Price Targets")
    cur = targets.get("current") or 0
    mean = targets.get("mean") or 0
    high = targets.get("high") or 0
    low = targets.get("low") or 0
    median = targets.get("median") or 0
    rec = targets.get("recommendation", "N/A")
    n = targets.get("num_analysts") or 0

    # Recommendation badge color
    rec_colors = {
        "strongBuy": "#34D399", "buy": "#34D399", "overweight": "#34D399",
        "hold": "#FBBF24", "neutral": "#FBBF24",
        "sell": "#F87171", "underperform": "#F87171", "strongSell": "#F87171",
    }
    rec_color = rec_colors.get(rec, "#9CA3AF")
    upside = ((mean - cur) / cur * 100) if cur > 0 else 0

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Current Price", f"${cur:,.2f}" if cur else "N/A")
    with c2:
        st.metric("Target (Mean)", f"${mean:,.2f}" if mean else "N/A",
                  delta=f"{upside:+.1f}%")
    with c3:
        st.metric("Target (Median)", f"${median:,.2f}" if median else "N/A")
    with c4:
        st.markdown(
            f'<div style="padding:8px;text-align:center;">'
            f'<div style="color:#9CA3AF;font-size:0.8rem;">Recommendation</div>'
            f'<div style="color:{rec_color};font-size:1.4rem;font-weight:700;'
            f'text-transform:uppercase;">{rec}</div>'
            f'<div style="color:#6B7280;font-size:0.75rem;">{n} analysts</div></div>',
            unsafe_allow_html=True,
        )

    # Price target range bar
    if low and high and cur:
        st.markdown(
            f'<div style="padding:12px;background:rgba(255,255,255,0.03);border-radius:8px;margin:8px 0;">'
            f'<div style="display:flex;justify-content:space-between;margin-bottom:6px;">'
            f'<span style="color:#F87171;font-size:0.8rem;">Low: ${low:,.2f}</span>'
            f'<span style="color:#FBBF24;font-size:0.8rem;">Mean: ${mean:,.2f}</span>'
            f'<span style="color:#34D399;font-size:0.8rem;">High: ${high:,.2f}</span></div>'
            f'<div style="background:#374151;border-radius:4px;height:8px;position:relative;">'
            f'<div style="background:linear-gradient(90deg,#F87171,#FBBF24,#34D399);'
            f'border-radius:4px;height:100%;width:100%;"></div></div></div>',
            unsafe_allow_html=True,
        )


def _render_estimates_table(label: str, df):
    """Render an estimates DataFrame as a styled table."""
    if df is None or (hasattr(df, 'empty') and df.empty):
        return
    st.markdown(f"#### {label}")
    display = format_estimate_table(df) if isinstance(df, pd.DataFrame) else df
    st.dataframe(display, use_container_width=True)


def _render_earnings_history(dates_df: pd.DataFrame):
    """Render earnings history with surprise data."""
    if dates_df is None or dates_df.empty:
        st.caption("No earnings history available.")
        return
    st.markdown("#### Earnings History & Surprises")
    display = dates_df.copy()
    for col in display.columns:
        if display[col].dtype in ('float64', 'float32'):
            display[col] = display[col].apply(
                lambda v: f"{v:.4f}" if pd.notna(v) and abs(v) < 10
                else (f"{v:,.2f}" if pd.notna(v) else "N/A")
            )
    st.dataframe(display, use_container_width=True)


def _render_growth_estimates(ge):
    """Render growth estimates comparison table."""
    if ge is None or (hasattr(ge, 'empty') and ge.empty):
        return
    st.markdown("#### Growth Estimates")
    st.dataframe(ge, use_container_width=True)


def render_tab11(ticker):
    """Render the Estimates & Outlook tab."""
    market = st.session_state.get("market") or MARKET_OPTIONS[0]
    quant_ticker = get_global_ticker(ticker, market) if ticker else ""
    st.subheader("Earnings Estimates & Outlook")

    if not ticker:
        st.info("Select a company from the sidebar to view estimates.")
        return

    si = get_sector_industry(quant_ticker)
    st.caption(f"**{ticker}** · {si.get('sector', 'N/A')} · {si.get('industry', 'N/A')}")

    with st.spinner("Fetching analyst estimates..."):
        estimates = get_analyst_estimates(quant_ticker)
        earnings_dates = get_earnings_dates(quant_ticker)

    if not estimates:
        st.warning("No analyst estimates available for this ticker.")
        return

    # ── Price Targets ──
    _render_price_targets(estimates.get("targets", {}))
    st.markdown("---")

    # ── Estimates Tables ──
    left, right = st.columns(2)
    with left:
        _render_estimates_table("Revenue Estimates", estimates.get("revenue_estimate"))
        _render_estimates_table("EPS Trend", estimates.get("eps_trend"))
    with right:
        _render_estimates_table("Earnings Estimates", estimates.get("earnings_estimate"))
        _render_growth_estimates(estimates.get("growth_estimates"))

    st.markdown("---")

    # ── Earnings History ──
    _render_earnings_history(earnings_dates)
