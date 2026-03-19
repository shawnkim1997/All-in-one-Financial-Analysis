import pandas as pd
import streamlit as st
from config.constants import MARKET_OPTIONS, DAMODARAN_ERP_PCT, DAMODARAN_RF_PCT
from utils.ticker import get_global_ticker
from utils.formatting import _format_shares_display
from utils.dcf import excel_style_dcf, _damodaran_wacc_for_sector
from utils.charts import _apply_dark_theme
from utils.ui_helpers import _render_analyst_consensus, _render_sensitivity_table
from data.fundamentals import get_sector_industry, get_5yr_financial_trend, get_dcf_inputs
from data.valuation import get_analyst_consensus, get_dcf_smart_defaults, get_fcff_fcfe_valuation
try:
    import plotly.express as px
except ImportError:
    px = None
try:
    import yfinance as yf
except ImportError:
    yf = None


def render_tab2(ticker):
    market_t2 = st.session_state.get("market") or MARKET_OPTIONS[0]
    quant_ticker_t2 = get_global_ticker(ticker, market_t2) if ticker else ""
    st.subheader("5-Year Financial Trend & DCF Valuation")
    if ticker:
        si_t2 = get_sector_industry(quant_ticker_t2)
        sector_t2 = (si_t2.get("sector") or "").lower()
        is_financial = "financial" in sector_t2 or "bank" in sector_t2 or "insurance" in sector_t2
    else:
        is_financial = False
    df_trend = get_5yr_financial_trend(quant_ticker_t2) if quant_ticker_t2 else pd.DataFrame()
    if not df_trend.empty and len(df_trend) >= 1:
        st.markdown("#### Key metrics (YoY % change)")
        latest = df_trend.iloc[0]
        prev = df_trend.iloc[1] if len(df_trend) >= 2 else None
        def _yoy_pct(cur, prev_val):
            if prev_val is None or cur is None or prev_val == 0:
                return None
            return (cur - prev_val) / abs(prev_val) * 100
        rev_yoy = _yoy_pct(latest.get("Revenue"), prev.get("Revenue") if prev is not None else None)
        ni_yoy = _yoy_pct(latest.get("Net Income"), prev.get("Net Income") if prev is not None else None)
        om_prev = prev.get("Operating Margin %") if prev is not None else None
        om_cur = latest.get("Operating Margin %")
        om_yoy = (om_cur - om_prev) if (om_cur is not None and om_prev is not None) else None
        fcf_yoy = _yoy_pct(latest.get("FCF"), prev.get("FCF") if prev is not None else None)
        m1, m2, m3, m4 = st.columns(4)
        rev_val = latest.get("Revenue")
        m1.metric("Revenue (latest yr)", f"${rev_val/1e9:.2f}B" if rev_val and rev_val >= 1e9 else (f"${rev_val/1e6:.0f}M" if rev_val else "\u2014"), f"{rev_yoy:+.1f}% YoY" if rev_yoy is not None else None)
        ni_val = latest.get("Net Income")
        m2.metric("Net Income", f"${ni_val/1e9:.2f}B" if ni_val and abs(ni_val) >= 1e9 else (f"${ni_val/1e6:.0f}M" if ni_val is not None else "\u2014"), f"{ni_yoy:+.1f}% YoY" if ni_yoy is not None else None)
        om_val = latest.get("Operating Margin %")
        m3.metric("Operating Margin %", f"{om_val:.1f}%" if om_val is not None else "\u2014", f"{om_yoy:+.1f}pp YoY" if om_yoy is not None else None)
        fcf_val = latest.get("FCF")
        m4.metric("FCF", f"${fcf_val/1e9:.2f}B" if fcf_val and abs(fcf_val) >= 1e9 else (f"${fcf_val/1e6:.0f}M" if fcf_val is not None else "\u2014"), f"{fcf_yoy:+.1f}% YoY" if fcf_yoy is not None else None)
        st.caption("FCF = Operating Cash Flow \u2212 Capital Expenditure." + (" For Financials, FCF/EBITDA are less relevant; see ROE/ROA in Tab 1 sector-specific metrics." if is_financial else ""))
        if len(df_trend) >= 2 and px is not None:
            st.markdown("#### 5-year trend: Revenue & FCF")
            df_plot = df_trend.copy()
            df_plot["Revenue_M"] = (df_plot["Revenue"] / 1e6).round(1)
            df_plot["FCF_M"] = (df_plot["FCF"] / 1e6).round(1)
            fig = px.line(df_plot, x="Year", y=["Revenue_M", "FCF_M"], title="Revenue & Free Cash Flow ($M)")
            fig.update_layout(yaxis_title="$M", legend_title="", hovermode="x unified")
            fig.update_traces(line=dict(width=2))
            _apply_dark_theme(fig)
            st.plotly_chart(fig, use_container_width=True)
    elif ticker:
        st.caption("5-year trend not available for this ticker. DCF section below uses latest FCF from yfinance.")
    st.markdown("---")
    st.markdown("#### DCF valuation (Excel-style): inputs & 3-scenario output")
    dcf_inputs = get_dcf_inputs(quant_ticker_t2) if quant_ticker_t2 else {"fcf": None, "total_debt": 0.0, "cash": 0.0, "shares": None}
    fcf_fetched = dcf_inputs.get("fcf")
    total_debt = float(dcf_inputs.get("total_debt") or 0.0)
    cash = float(dcf_inputs.get("cash") or 0.0)
    shares_fetched = dcf_inputs.get("shares")
    # Base FCF
    if fcf_fetched is None or fcf_fetched <= 0:
        fcf = st.number_input("Base FCF (manual \u2014 only if yfinance missing)", value=0.0, min_value=-1e12, step=1e8, format="%.0f", key="dcf_fcf_manual")
    else:
        fcf = float(fcf_fetched)
        st.caption(f"Base FCF (OCF \u2212 CapEx): **${fcf/1e9:.2f}B**" if abs(fcf) >= 1e9 else f"Base FCF (OCF \u2212 CapEx): **${fcf/1e6:.0f}M**")
    # Shares: auto-fetched (fast_info -> info -> balance); manual only as last resort
    if shares_fetched is not None and shares_fetched > 0:
        shares = float(shares_fetched)
        st.caption(f"Shares Outstanding: **{_format_shares_display(shares)}** (real-time, auto-fetched)")
    else:
        shares = st.number_input("Shares Outstanding (manual \u2014 only if all API sources failed)", value=1e9, min_value=1.0, step=1e7, format="%.0f", key="dcf_shares_manual")
    # Total Debt & Cash: manual only when both API sources completely failed
    if total_debt == 0 and cash == 0:
        c1, c2 = st.columns(2)
        with c1:
            total_debt = st.number_input("Total Debt (manual \u2014 only if all sources failed)", value=0.0, min_value=0.0, step=1e8, format="%.0f", key="dcf_debt_manual")
        with c2:
            cash = st.number_input("Cash & Equivalents (manual \u2014 only if all sources failed)", value=0.0, min_value=0.0, step=1e8, format="%.0f", key="dcf_cash_manual")
    else:
        st.caption(f"Total Debt: **${total_debt/1e9:.2f}B**" if total_debt >= 1e9 else f"Total Debt: **${total_debt/1e6:.0f}M**" if total_debt >= 1e6 else f"Total Debt: **${total_debt:,.0f}**")
        st.caption(f"Cash & Equivalents: **${cash/1e9:.2f}B**" if cash >= 1e9 else f"Cash & Equivalents: **${cash/1e6:.0f}M**" if cash >= 1e6 else f"Cash & Equivalents: **${cash:,.0f}**")
    dcf_defaults = get_dcf_smart_defaults(quant_ticker_t2) if quant_ticker_t2 else {"wacc_pct": 10.0, "term_growth_pct": 2.5, "fcf_growth_pct": 8.0}
    st.markdown("**Assumptions (sliders)**")
    st.caption("\U0001f4a1 Slider defaults are auto-generated based on the company's Beta (CAPM) and revenue growth estimates.")
    col1, col2, col3 = st.columns(3)
    with col1:
        wacc = st.slider("WACC (Discount Rate) %", 4.0, 20.0, float(dcf_defaults["wacc_pct"]), 0.5, key="dcf_wacc") / 100.0
    with col2:
        term_growth = st.slider("Terminal Growth Rate %", -2.0, 6.0, float(dcf_defaults["term_growth_pct"]), 0.25, key="dcf_term") / 100.0
    with col3:
        base_growth = st.slider("Projected FCF Growth (Stage 1, Y1\u20135) %", -10.0, 30.0, float(dcf_defaults["fcf_growth_pct"]), 0.5, key="dcf_fcf_growth") / 100.0
    bull_growth = base_growth + 0.02
    bear_growth = base_growth - 0.02
    with st.expander("Reference: Analyst & Macro Assumptions", expanded=False):
        left_col, right_col = st.columns(2)
        with left_col:
            st.markdown("**Analyst consensus (yfinance)**")
            analyst = get_analyst_consensus(quant_ticker_t2) if quant_ticker_t2 else {}
            _tmp = analyst.get('targetMeanPrice')
            st.markdown(f"- **Target mean price:** ${_tmp:,.2f}" if _tmp else "- **Target mean price:** N/A")
            st.markdown(f"- **Recommendation:** {analyst.get('recommendationKey', 'N/A')}")
            st.markdown(f"- **Revenue growth est.:** {analyst.get('revenueGrowth', 'N/A')}")
            st.markdown(f"- **Earnings growth est.:** {analyst.get('earningsGrowth', 'N/A')}")
        with right_col:
            st.markdown("**Aswath Damodaran \u2014 macro baseline**")
            sector_name = get_sector_industry(ticker).get("sector", "N/A") if ticker else "N/A"
            damodaran_wacc = _damodaran_wacc_for_sector(sector_name) if ticker else 8.0
            st.markdown(f"- **Sector WACC (ref.):** {damodaran_wacc:.1f}% (closest: {sector_name})")
            st.markdown(f"- **US equity risk premium (ERP):** {DAMODARAN_ERP_PCT}%")
            st.markdown(f"- **10Y risk-free rate:** {DAMODARAN_RF_PCT}%")
            st.markdown("[Data & methodology (Damodaran)](https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/wacc.htm) so users can verify.")
    res_base = excel_style_dcf(fcf, wacc, term_growth, base_growth, total_debt, cash, shares)
    res_bull = excel_style_dcf(fcf, wacc, term_growth, bull_growth, total_debt, cash, shares)
    res_bear = excel_style_dcf(fcf, wacc, term_growth, bear_growth, total_debt, cash, shares)
    price_base = res_base.get("value_per_share") or 0.0
    price_bull = res_bull.get("value_per_share") or 0.0
    price_bear = res_bear.get("value_per_share") or 0.0
    current_price = None
    if quant_ticker_t2 and yf:
        try:
            info = yf.Ticker(quant_ticker_t2.upper()).info or {}
            current_price = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose")
        except Exception:
            pass
    st.markdown("**Intrinsic value vs current price**")
    if current_price is not None and current_price > 0:
        st.metric("Current price", f"${current_price:.2f}", None)
    st.metric("Base case intrinsic value per share", f"${price_base:.2f}" if price_base else "N/A", f"vs current: {(price_base - current_price):.2f}" if (current_price and price_base) else None)
    c1, c2, c3 = st.columns(3)
    c1.metric("Bull (+2% FCF growth)", f"${price_bull:.2f}" if price_bull else "N/A", f"vs Base: +{(price_bull - price_base):.2f}" if (price_bull and price_base) else None)
    c2.metric("Base", f"${price_base:.2f}" if price_base else "N/A", "\u2014")
    c3.metric("Bear (\u22122% FCF growth)", f"${price_bear:.2f}" if price_bear else "N/A", f"vs Base: {(price_bear - price_base):.2f}" if (price_bear and price_base) else None)
    df_dcf = pd.DataFrame({
        "Scenario": ["Bull", "Base", "Bear"],
        "FCF Growth %": [f"{bull_growth*100:.1f}", f"{base_growth*100:.1f}", f"{bear_growth*100:.1f}"],
        "Intrinsic Value ($)": [round(price_bull, 2) if price_bull else "N/A", round(price_base, 2) if price_base else "N/A", round(price_bear, 2) if price_bear else "N/A"],
    })
    st.dataframe(df_dcf, use_container_width=True, hide_index=True)

    # --- Probability-Weighted Expected Return ---
    st.markdown("**Probability-Weighted Expected Return**")
    bull_prob, base_prob, bear_prob = 0.25, 0.55, 0.20
    pw_value = bull_prob * price_bull + base_prob * price_base + bear_prob * price_bear
    if current_price and current_price > 0 and pw_value > 0:
        pw_return = (pw_value - current_price) / current_price * 100
        st.markdown(f"""
        <div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06); border-radius: 10px; padding: 16px;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <div style="color: #6B7280; font-size: 0.7rem; font-weight: 600; letter-spacing: 1px;">PROBABILITY-WEIGHTED VALUE</div>
                    <div style="color: #F3F4F6; font-size: 1.4rem; font-family: JetBrains Mono, monospace; font-weight: 700;">${pw_value:,.2f}</div>
                </div>
                <div>
                    <div style="color: #6B7280; font-size: 0.7rem; font-weight: 600; letter-spacing: 1px;">EXPECTED RETURN</div>
                    <div style="color: {'#34D399' if pw_return > 0 else '#F87171'}; font-size: 1.4rem; font-family: JetBrains Mono, monospace; font-weight: 700;">{pw_return:+.1f}%</div>
                </div>
                <div style="color: #6B7280; font-size: 0.75rem; font-family: JetBrains Mono, monospace;">
                    Bull {bull_prob*100:.0f}% x ${price_bull:,.0f} + Base {base_prob*100:.0f}% x ${price_base:,.0f} + Bear {bear_prob*100:.0f}% x ${price_bear:,.0f}
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # --- Analyst Consensus ---
    st.markdown("---")
    st.markdown("#### Analyst Consensus")
    _render_analyst_consensus(quant_ticker_t2)

    # --- FCFF / FCFE Analysis ---
    st.markdown("---")
    st.markdown("#### FCFF / FCFE Analysis")
    fcff_data = get_fcff_fcfe_valuation(quant_ticker_t2) if quant_ticker_t2 else {}
    if fcff_data:
        c1_ff, c2_ff, c3_ff, c4_ff = st.columns(4)
        with c1_ff:
            fcff_val = fcff_data.get("fcff")
            st.metric("FCFF", f"${fcff_val/1e9:.2f}B" if fcff_val and abs(fcff_val) >= 1e9 else (f"${fcff_val/1e6:.0f}M" if fcff_val else "N/A"))
        with c2_ff:
            fcfe_val = fcff_data.get("fcfe")
            st.metric("FCFE", f"${fcfe_val/1e9:.2f}B" if fcfe_val and abs(fcfe_val) >= 1e9 else (f"${fcfe_val/1e6:.0f}M" if fcfe_val else "N/A"))
        with c3_ff:
            _da_v = fcff_data.get("depreciation")
            st.metric("D&A", f"${_da_v/1e9:.2f}B" if _da_v and abs(_da_v) >= 1e9 else (f"${_da_v/1e6:.0f}M" if _da_v else "N/A"))
        with c4_ff:
            _cx_v = fcff_data.get("capex")
            st.metric("CapEx", f"${_cx_v/1e9:.2f}B" if _cx_v and abs(_cx_v) >= 1e9 else (f"${_cx_v/1e6:.0f}M" if _cx_v else "N/A"))

        with st.expander("FCFF/FCFE Bridge Detail", expanded=False):
            def _fmt_b(v):
                if v is None: return "N/A"
                return f"${v/1e9:.2f}B" if abs(v) >= 1e9 else f"${v/1e6:.0f}M"
            _ebit = fcff_data.get('ebit') or 0
            _tr_pct = fcff_data.get('tax_rate') or 21
            _da = fcff_data.get('depreciation') or 0
            _cx = fcff_data.get('capex') or 0
            bridge_data = {
                "Component": ["EBIT", "x (1 - Tax Rate)", "= NOPAT", "+ D&A", "- CapEx", "= FCFF", "", "Net Income", "+ D&A", "- CapEx", "= FCFE"],
                "Value": [
                    _fmt_b(fcff_data.get('ebit')),
                    f"{_tr_pct:.1f}%",
                    _fmt_b(_ebit * (1 - _tr_pct/100)) if fcff_data.get('ebit') else "N/A",
                    _fmt_b(fcff_data.get('depreciation')),
                    _fmt_b(fcff_data.get('capex')),
                    _fmt_b(fcff_data.get('fcff')),
                    "---",
                    _fmt_b(fcff_data.get('net_income')),
                    _fmt_b(fcff_data.get('depreciation')),
                    _fmt_b(fcff_data.get('capex')),
                    _fmt_b(fcff_data.get('fcfe')),
                ]
            }
            st.dataframe(pd.DataFrame(bridge_data), use_container_width=True, hide_index=True)
    else:
        st.caption("FCFF/FCFE data not available for this ticker.")

    # --- DCF Sensitivity Analysis ---
    st.markdown("---")
    st.markdown("#### DCF Sensitivity Analysis")
    st.caption("Intrinsic value per share across WACC and Terminal Growth Rate assumptions")
    if fcf and fcf > 0 and shares and shares > 0:
        sens_df = _render_sensitivity_table(fcf, total_debt, cash, shares)
        st.dataframe(sens_df, use_container_width=True)
    else:
        st.caption("Sensitivity table requires positive FCF data.")
