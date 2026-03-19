"""
ATLAS Terminal — Thin Orchestrator
All-in-One Financial Analysis Dashboard — Hybrid Architecture
- Tab 1: 10-K & MD&A Insights (Item 7 + Item 1A → Gemini, qualitative only).
- Tab 2: 3-Scenario DCF Valuation (yfinance + sliders, no LLM).
- Tab 3: Industry Comps (yfinance multiples: Forward P/E, EV/EBITDA, P/B).
- Cost-effective: Gemini only for text; all numbers from yfinance.
"""
import os
os.environ["OBJC_DISABLE_INITIALIZE_FORK_SAFETY"] = "YES"

import streamlit as st

from config.constants import MARKET_OPTIONS
from config.theme import SOFT_NAVY_CSS, HEADER_HTML
from utils.ticker import get_global_ticker
from data.market import _get_ticker_bar_data
from data.fundamentals import get_sector_industry
from views.sidebar import render_sidebar
from views.tab1_quant import render_tab1_quantitative
from views.tab1_ai import render_tab1_ai_analysis
from views.tab1_filings import render_tab1_filings
from views.tab2_dcf import render_tab2
from views.tab3_comps import render_tab3
from views.tab4_news import render_tab4
from views.tab5_markets import render_tab5
from views.tab6_crypto import render_tab6
from views.tab7_technical import render_tab7

try:
    import yfinance as yf
except ImportError:
    yf = None

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ---------- Page config & theme ----------
st.set_page_config(page_title="ATLAS Terminal", layout="wide", initial_sidebar_state="expanded")
st.markdown(SOFT_NAVY_CSS, unsafe_allow_html=True)
st.markdown(HEADER_HTML, unsafe_allow_html=True)

# ---------- Ticker bar — major indices & crypto ----------
ticker_data = _get_ticker_bar_data() if yf else []
if ticker_data:
    _cells = ""
    for item in ticker_data:
        _c = "#34D399" if item["change"] >= 0 else "#F87171"
        _a = "\u25b2" if item["change"] >= 0 else "\u25bc"
        _cells += (
            f'<div style="flex:1;text-align:center;padding:10px 6px;background:rgba(255,255,255,0.03);'
            f'border-radius:6px;border:1px solid rgba(255,255,255,0.06);min-width:100px;">'
            f'<div style="color:#6B7280;font-size:0.65rem;font-weight:600;letter-spacing:1px;">{item["label"]}</div>'
            f'<div style="color:#F3F4F6;font-size:1.05rem;font-family:\'Inter\',JetBrains Mono,monospace;font-weight:700;margin:2px 0;">{item["price"]:,.2f}</div>'
            f'<div style="color:{_c};font-size:0.75rem;font-family:\'Inter\',JetBrains Mono,monospace;">{_a} {item["change"]:+.2f}%</div>'
            f'</div>'
        )
    st.markdown(f'<div style="display:flex;gap:8px;margin-bottom:16px;overflow-x:auto;">{_cells}</div>', unsafe_allow_html=True)

# ---------- Sidebar ----------
ticker = render_sidebar()

# ---------- Tabs ----------
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "\U0001f4ca 10-K & MD&A Insights",
    "\U0001f4b0 DCF Valuation",
    "\U0001f3ed Industry Comps",
    "\U0001f4f0 News Feed",
    "\U0001f30d Markets & FX",
    "\u20bf Crypto",
    "\U0001f6e1 Technical & Risk",
])

# ----- Tab 1: 10-K & MD&A Insights -----
with tab1:
    market = st.session_state.get("market") or MARKET_OPTIONS[0]
    quant_ticker = get_global_ticker(ticker, market) if ticker else ""
    st.subheader("10-K & MD&A Insights — Qualitative and Quantitative")
    if ticker:
        si = get_sector_industry(quant_ticker)
        sector, industry = si.get("sector", "N/A"), si.get("industry", "N/A")
        st.caption(
            f"Sector: **{sector}**  ·  Industry: **{industry}**"
            + (f"  ·  Ticker: **{quant_ticker}**" if quant_ticker != ticker else "")
        )
    if ticker:
        google_api_key = (st.session_state.get("google_api_key") or "").strip()
        sec_email = (st.session_state.get("sec_email") or "").strip()
        render_tab1_quantitative(ticker, quant_ticker, market, sector, industry, google_api_key, sec_email)
        render_tab1_ai_analysis(ticker, quant_ticker, market)
        render_tab1_filings(ticker, market)

# ----- Tab 2: DCF Valuation -----
with tab2:
    render_tab2(ticker)

# ----- Tab 3: Industry Comps -----
with tab3:
    render_tab3(ticker)

# ----- Tab 4: News Feed -----
with tab4:
    render_tab4(ticker)

# ----- Tab 5: Markets & FX -----
with tab5:
    render_tab5()

# ----- Tab 6: Crypto -----
with tab6:
    render_tab6()

# ----- Tab 7: Technical & Risk -----
with tab7:
    render_tab7(ticker)
