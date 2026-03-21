"""
Tab 9 — Portfolio Management
Full-featured portfolio dashboard: holdings table, sector pie chart,
earnings calendar, dividends, key events, news, AI OCR import.
"""
import streamlit as st
import pandas as pd
from data.portfolio import get_portfolio_prices, get_sector_allocation
from views.portfolio_widgets import render_earnings, render_dividends, render_news

try:
    import plotly.express as px
except ImportError:
    px = None


# ───────── Session State Init ─────────

def _init_portfolio():
    if "portfolio_holdings" not in st.session_state:
        st.session_state["portfolio_holdings"] = []


# ───────── Manual Entry Form ─────────

def _render_add_form():
    """Manual stock entry form."""
    st.markdown("#### Add Holding")
    cols = st.columns([2, 1, 1, 1])
    with cols[0]:
        ticker = st.text_input("Ticker", placeholder="AAPL", key="pf_add_ticker")
    with cols[1]:
        name = st.text_input("Name", placeholder="Apple Inc", key="pf_add_name")
    with cols[2]:
        shares = st.number_input("Shares", min_value=0.0, step=0.01, key="pf_add_shares")
    with cols[3]:
        avg_cost = st.number_input("Avg Cost ($)", min_value=0.0, step=0.01, key="pf_add_avg")
    if st.button("Add to Portfolio", key="pf_add_btn"):
        if ticker.strip():
            st.session_state["portfolio_holdings"].append({
                "ticker": ticker.strip().upper(),
                "name": name.strip() or ticker.strip().upper(),
                "shares": shares, "avg_cost": avg_cost,
            })
            st.rerun()


# ───────── AI OCR Import ─────────

def _render_ai_import():
    """AI-powered screenshot import for Trading 212 / IBKR."""
    st.markdown("#### Import from Brokerage Screenshot")
    google_api_key = (st.session_state.get("google_api_key") or "").strip()
    if not google_api_key:
        st.info("Enter your Google API Key in the sidebar to enable AI portfolio import.")
        return
    broker = st.selectbox("Broker", ["Trading 212", "IBKR", "Other"], key="pf_broker")
    uploaded = st.file_uploader(
        "Upload screenshot", type=["png", "jpg", "jpeg", "webp"],
        key="pf_screenshot", help="Upload a screenshot of your portfolio holdings"
    )
    if uploaded and st.button("Extract Holdings with AI", key="pf_extract_btn", type="primary"):
        with st.spinner("Gemini is analyzing your screenshot..."):
            from ai.gemini_portfolio import extract_portfolio_from_image
            holdings = extract_portfolio_from_image(google_api_key, uploaded.read(), broker)
            if holdings:
                for h in holdings:
                    st.session_state["portfolio_holdings"].append({
                        "ticker": h["ticker"], "name": h.get("name", h["ticker"]),
                        "shares": h.get("shares") or 0,
                        "avg_cost": h.get("avg_cost") or h.get("current_price") or 0,
                    })
                st.success(f"Extracted {len(holdings)} holdings!")
                st.rerun()
            else:
                st.warning("No holdings found. Try a clearer screenshot.")


# ───────── Portfolio Overview Cards ─────────

def _render_overview(holdings: list, prices: dict):
    """Total asset value, daily P&L, total P&L cards."""
    total_value, total_cost, daily_pnl = 0.0, 0.0, 0.0
    for h in holdings:
        p = prices.get(h["ticker"], {})
        cur = p.get("price") or h.get("avg_cost") or 0
        prev = p.get("prev_close") or cur
        shares = h.get("shares", 0)
        total_value += cur * shares
        total_cost += h.get("avg_cost", 0) * shares
        daily_pnl += (cur - prev) * shares
    total_pnl = total_value - total_cost
    pnl_pct = (total_pnl / total_cost * 100) if total_cost > 0 else 0
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Total Portfolio Value", f"${total_value:,.2f}")
    with c2:
        st.metric("Daily P&L", f"${daily_pnl:,.2f}", delta=f"{daily_pnl:+,.2f}")
    with c3:
        st.metric("Total P&L", f"${total_pnl:,.2f}", delta=f"{pnl_pct:+.2f}%")


# ───────── Holdings Table ─────────

def _render_holdings_table(holdings: list, prices: dict):
    """Display holdings with current price, change, P&L."""
    if not holdings:
        return
    st.markdown("#### Holdings")
    rows = []
    for i, h in enumerate(holdings):
        sym = h["ticker"]
        p = prices.get(sym, {})
        cur = p.get("price")
        chg = p.get("change_pct", 0)
        shares, avg = h.get("shares", 0), h.get("avg_cost", 0)
        mkt = (cur or 0) * shares
        pnl = (cur - avg) * shares if cur and avg else 0
        pnl_p = ((cur - avg) / avg * 100) if cur and avg and avg > 0 else 0
        rows.append({
            "": i, "Ticker": sym, "Name": h.get("name", sym),
            "Shares": f"{shares:,.2f}" if shares != int(shares) else f"{int(shares):,}",
            "Avg Cost": f"${avg:,.2f}" if avg else "N/A",
            "Current": f"${cur:,.2f}" if cur else "N/A",
            "Day Chg": f"{chg:+.2f}%", "P&L": f"${pnl:+,.2f}",
            "P&L %": f"{pnl_p:+.2f}%", "Mkt Value": f"${mkt:,.2f}",
        })
    df = pd.DataFrame(rows).set_index("")
    st.dataframe(df, use_container_width=True, height=min(40 * len(rows) + 38, 500))
    with st.expander("Remove Holdings"):
        for i, h in enumerate(holdings):
            if st.button(f"Remove {h['ticker']}", key=f"pf_del_{i}"):
                st.session_state["portfolio_holdings"].pop(i)
                st.rerun()


# ───────── Sector Pie Chart ─────────

def _render_sector_pie(holdings: list):
    """Sector allocation donut chart."""
    if not holdings or not px:
        return
    tickers = tuple(h["ticker"] for h in holdings)
    sectors = get_sector_allocation(tickers)
    agg = {}
    for h in holdings:
        sec = sectors.get(h["ticker"], "Other")
        agg[sec] = agg.get(sec, 0) + h.get("shares", 0) * h.get("avg_cost", 0)
    if not agg:
        return
    fig = px.pie(
        names=list(agg.keys()), values=list(agg.values()),
        title="Sector Allocation", hole=0.4,
        color_discrete_sequence=px.colors.qualitative.Set3,
    )
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font_color="#E5E7EB", height=350, margin=dict(t=40, b=20, l=20, r=20),
    )
    st.plotly_chart(fig, use_container_width=True)


# ───────── Main Render ─────────

def render_tab9():
    """Render the Portfolio Management tab."""
    _init_portfolio()
    st.subheader("Portfolio Management")
    holdings = st.session_state["portfolio_holdings"]

    with st.expander("Add / Import Holdings", expanded=not bool(holdings)):
        t1, t2 = st.tabs(["Manual Entry", "AI Screenshot Import"])
        with t1:
            _render_add_form()
        with t2:
            _render_ai_import()

    if not holdings:
        st.info("Add holdings above to see your portfolio dashboard.")
        return

    tickers = tuple(h["ticker"] for h in holdings)
    with st.spinner("Fetching live prices..."):
        prices = get_portfolio_prices(tickers)

    _render_overview(holdings, prices)
    st.markdown("---")

    left, right = st.columns([3, 2])
    with left:
        _render_holdings_table(holdings, prices)
        _render_sector_pie(holdings)
    with right:
        render_earnings(tickers)
        st.markdown("---")
        render_dividends(tickers)
        st.markdown("---")
        render_news(tickers)
