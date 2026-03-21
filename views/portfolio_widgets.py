"""
Portfolio sidebar widgets — earnings calendar, dividends, news.
Split from tab9_portfolio.py to stay under 300-line limit.
"""
import streamlit as st
from data.portfolio import (
    get_earnings_calendar, get_dividend_schedule, get_portfolio_news,
)


def render_earnings(tickers: tuple):
    """Earnings calendar widget."""
    st.markdown("#### Earnings Calendar")
    events = get_earnings_calendar(tickers)
    if not events:
        st.caption("No upcoming earnings found.")
        return
    for ev in events[:8]:
        d = ev["days_until"]
        color = "#F87171" if d <= 3 else "#FBBF24" if d <= 7 else "#6B7280"
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:10px;padding:6px 0;'
            f'border-bottom:1px solid rgba(255,255,255,0.06);">'
            f'<span style="background:{color};color:#fff;padding:2px 8px;border-radius:4px;'
            f'font-size:0.75rem;font-weight:700;min-width:40px;text-align:center;">D-{d}</span>'
            f'<div><span style="color:#F3F4F6;font-weight:600;">{ev["name"]}</span>'
            f'<br><span style="color:#6B7280;font-size:0.75rem;">{ev["ticker"]} · {ev["date"]}</span></div>'
            f'</div>', unsafe_allow_html=True
        )


def render_dividends(tickers: tuple):
    """Dividend schedule widget."""
    st.markdown("#### Dividend Schedule")
    divs = get_dividend_schedule(tickers)
    if not divs:
        st.caption("No dividend data found.")
        return
    for d in divs[:8]:
        st.markdown(
            f'<div style="padding:6px 0;border-bottom:1px solid rgba(255,255,255,0.06);">'
            f'<span style="color:#F3F4F6;font-weight:600;">{d["name"]}</span>'
            f' <span style="color:#6B7280;font-size:0.8rem;">{d["ticker"]}</span><br>'
            f'<span style="color:#34D399;font-size:0.85rem;">Yield: {d["yield_pct"]}</span>'
            f' · <span style="color:#9CA3AF;font-size:0.8rem;">Ex-Date: {d["ex_date"]}</span>'
            f' · <span style="color:#9CA3AF;font-size:0.8rem;">Annual: {d["amount"]}</span>'
            f'</div>', unsafe_allow_html=True
        )


def render_news(tickers: tuple):
    """Recent news for portfolio stocks."""
    st.markdown("#### Portfolio News")
    news = get_portfolio_news(tickers, max_per_ticker=2)
    if not news:
        st.caption("No recent news.")
        return
    from datetime import datetime
    for n in news[:10]:
        ts = n.get("published", 0)
        date_str = datetime.fromtimestamp(ts).strftime("%m/%d") if ts else ""
        link = n.get("link", "#")
        st.markdown(
            f'<div style="padding:6px 0;border-bottom:1px solid rgba(255,255,255,0.06);">'
            f'<span style="color:#60A5FA;font-weight:600;font-size:0.8rem;">{n["ticker"]}</span>'
            f' <span style="color:#6B7280;font-size:0.75rem;">{n.get("publisher","")} · {date_str}</span><br>'
            f'<a href="{link}" target="_blank" style="color:#F3F4F6;text-decoration:none;font-size:0.85rem;">'
            f'{n["title"]}</a></div>', unsafe_allow_html=True
        )
