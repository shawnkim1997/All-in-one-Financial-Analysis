"""
Tab 10 — Company Valuation
PER, PBR, PSR, P/OCF cards with 5Y history, industry comparison, historical chart.
"""
import streamlit as st
from config.constants import MARKET_OPTIONS
from utils.ticker import get_global_ticker
from data.valuation_metrics import (
    get_valuation_multiples, get_historical_multiples,
    get_industry_avg_multiples, get_pe_history_chart_data,
)
from data.fundamentals import get_sector_industry

try:
    import plotly.graph_objects as go
except ImportError:
    go = None


def _metric_card(label, value, sub_items: dict, col):
    """Render a single valuation metric card."""
    with col:
        val_str = f"{value:.2f}" if isinstance(value, (int, float)) and value == value else "N/A"
        st.markdown(
            f'<div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.08);'
            f'border-radius:10px;padding:16px 20px;min-height:160px;">'
            f'<div style="color:#9CA3AF;font-size:0.8rem;font-weight:600;">{label}</div>'
            f'<div style="color:#F3F4F6;font-size:2rem;font-weight:700;margin:4px 0;">{val_str}</div>',
            unsafe_allow_html=True,
        )
        for k, v in sub_items.items():
            v_str = f"{v:.2f}" if isinstance(v, (int, float)) and v == v else "N/A"
            color = "#9CA3AF"
            st.markdown(
                f'<div style="color:{color};font-size:0.75rem;padding:1px 0;">'
                f'{k}: <b>{v_str}</b></div>', unsafe_allow_html=True,
            )
        st.markdown('</div>', unsafe_allow_html=True)


def _render_pe_chart(ticker: str, quant_ticker: str):
    """Render 5Y price chart with PE overlay."""
    if not go:
        return
    df = get_pe_history_chart_data(quant_ticker)
    if df.empty:
        return
    st.markdown("#### Historical Price (5Y)")
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["Date"], y=df["Close"], mode="lines",
        name="Price", line=dict(color="#34D399", width=2),
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font_color="#E5E7EB", height=300,
        margin=dict(t=20, b=30, l=50, r=20),
        xaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
        yaxis=dict(gridcolor="rgba(255,255,255,0.05)", title="Price ($)"),
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_comparison_bar(label, current, avg_5y, industry_avg):
    """Render a horizontal comparison bar for a metric."""
    vals = {"Current": current, "5Y Avg": avg_5y, "Industry": industry_avg}
    items = []
    for k, v in vals.items():
        if v and isinstance(v, (int, float)) and v == v:
            items.append(f'<span style="color:#9CA3AF;font-size:0.8rem;">{k}: </span>'
                        f'<span style="color:#F3F4F6;font-weight:600;">{v:.2f}</span>')
    if items:
        st.markdown(
            f'<div style="padding:8px 0;border-bottom:1px solid rgba(255,255,255,0.06);">'
            f'<span style="color:#60A5FA;font-weight:600;min-width:80px;display:inline-block;">{label}</span>'
            f'{"  ·  ".join(items)}</div>', unsafe_allow_html=True,
        )


def render_tab10(ticker):
    """Render the Company Valuation tab."""
    market = st.session_state.get("market") or MARKET_OPTIONS[0]
    quant_ticker = get_global_ticker(ticker, market) if ticker else ""
    st.subheader("Company Valuation")

    if not ticker:
        st.info("Select a company from the sidebar to view valuation metrics.")
        return

    si = get_sector_industry(quant_ticker)
    sector = si.get("sector", "N/A")
    industry = si.get("industry", "N/A")
    st.caption(f"**{ticker}** · {sector} · {industry}")

    with st.spinner("Fetching valuation data..."):
        multiples = get_valuation_multiples(quant_ticker)
        hist = get_historical_multiples(quant_ticker)
        ind_avg = get_industry_avg_multiples(quant_ticker)

    if not multiples:
        st.warning("Could not fetch valuation data for this ticker.")
        return

    # ── Metric Cards: PER, PBR, PSR, P/OCF ──
    c1, c2, c3, c4 = st.columns(4)
    _metric_card("PER (Trailing)", multiples.get("PER"), {
        "Forward": multiples.get("Forward PER"),
        "5Y Avg": hist.get("5Y Avg PER"),
        "Industry": ind_avg.get("Industry Avg PER"),
    }, c1)
    _metric_card("PBR", multiples.get("PBR"), {
        "5Y Avg": hist.get("5Y Avg PBR"),
        "Industry": ind_avg.get("Industry Avg PBR"),
    }, c2)
    _metric_card("PSR", multiples.get("PSR"), {
        "Industry": ind_avg.get("Industry Avg PSR"),
        "EV/Revenue": multiples.get("EV/Revenue"),
    }, c3)
    _metric_card("P/OCF", multiples.get("P/OCF"), {
        "EV/EBITDA": multiples.get("EV/EBITDA"),
        "PEG Ratio": multiples.get("PEG"),
    }, c4)

    st.markdown("---")

    # ── Comparison Table ──
    left, right = st.columns([3, 2])
    with left:
        st.markdown("#### Valuation Comparison")
        _render_comparison_bar("PER", multiples.get("PER"),
                              hist.get("5Y Avg PER"), ind_avg.get("Industry Avg PER"))
        _render_comparison_bar("PBR", multiples.get("PBR"),
                              hist.get("5Y Avg PBR"), ind_avg.get("Industry Avg PBR"))
        _render_comparison_bar("PSR", multiples.get("PSR"), None,
                              ind_avg.get("Industry Avg PSR"))
        _render_comparison_bar("EV/EBITDA", multiples.get("EV/EBITDA"), None, None)

        # Premium/Discount indicator
        pe_cur = multiples.get("PER")
        pe_5y = hist.get("5Y Avg PER")
        if pe_cur and pe_5y and pe_5y > 0:
            prem = (pe_cur - pe_5y) / pe_5y * 100
            color = "#F87171" if prem > 0 else "#34D399"
            word = "premium" if prem > 0 else "discount"
            st.markdown(
                f'<div style="margin-top:12px;padding:10px;background:rgba(255,255,255,0.03);'
                f'border-radius:8px;"><span style="color:{color};font-weight:700;">'
                f'{abs(prem):.1f}% {word}</span>'
                f' <span style="color:#9CA3AF;">vs 5Y average PER</span></div>',
                unsafe_allow_html=True,
            )

    with right:
        _render_pe_chart(ticker, quant_ticker)

    # ── Additional Metrics Table ──
    st.markdown("---")
    st.markdown("#### Additional Metrics")
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        beta = multiples.get("Beta")
        st.metric("Beta", f"{beta:.2f}" if beta else "N/A")
    with m2:
        dy = multiples.get("Dividend Yield")
        st.metric("Div Yield", f"{dy*100:.2f}%" if dy else "N/A")
    with m3:
        h52 = multiples.get("52W High")
        st.metric("52W High", f"${h52:,.2f}" if h52 else "N/A")
    with m4:
        l52 = multiples.get("52W Low")
        st.metric("52W Low", f"${l52:,.2f}" if l52 else "N/A")

    # ── KPI Analysis ──
    from views.tab10_kpi import render_kpi_section
    render_kpi_section(ticker, sector, industry)
