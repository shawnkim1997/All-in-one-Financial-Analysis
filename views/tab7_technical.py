import pandas as pd
import streamlit as st
from config.constants import MARKET_OPTIONS
from utils.ticker import get_global_ticker
from data.market import get_technical_indicators, get_risk_analysis


def render_tab7(ticker):
    st.subheader("Technical Setup & Risk Analysis")
    market_t7 = st.session_state.get("market") or MARKET_OPTIONS[0]
    quant_ticker_t7 = get_global_ticker(ticker, market_t7) if ticker else ""

    st.markdown("#### Technical Indicators")
    tech = get_technical_indicators(quant_ticker_t7) if quant_ticker_t7 else {}
    if tech.get("current_price"):
        tc1, tc2, tc3, tc4 = st.columns(4)
        price_t7 = tech["current_price"]
        with tc1:
            rsi = tech.get("rsi_14")
            rsi_color = "#F87171" if rsi and rsi > 70 else ("#34D399" if rsi and rsi < 30 else "#FBBF24")
            rsi_label = "Overbought" if rsi and rsi > 70 else ("Oversold" if rsi and rsi < 30 else "Neutral")
            st.markdown(f'<div class="stat-card"><div class="stat-label">RSI (14)</div><div class="stat-value" style="color:{rsi_color};">{rsi if rsi else "N/A"}</div><div style="color:{rsi_color};font-size:0.75rem;">{rsi_label}</div></div>', unsafe_allow_html=True)
        with tc2:
            sma50 = tech.get("sma_50")
            above_50 = price_t7 > sma50 if sma50 else None
            st.markdown(f'<div class="stat-card"><div class="stat-label">SMA (50)</div><div class="stat-value">{"${:,.2f}".format(sma50) if sma50 else "N/A"}</div><div class="stat-delta {"delta-up" if above_50 else "delta-down"}">{"Above" if above_50 else "Below"} SMA50</div></div>', unsafe_allow_html=True)
        with tc3:
            sma200 = tech.get("sma_200")
            above_200 = price_t7 > sma200 if sma200 else None
            st.markdown(f'<div class="stat-card"><div class="stat-label">SMA (200)</div><div class="stat-value">{"${:,.2f}".format(sma200) if sma200 else "N/A"}</div><div class="stat-delta {"delta-up" if above_200 else "delta-down"}">{"Above" if above_200 else "Below"} SMA200</div></div>', unsafe_allow_html=True)
        with tc4:
            h52 = tech.get("52w_high", 0)
            l52 = tech.get("52w_low", 0)
            st.markdown(f'<div class="stat-card"><div class="stat-label">52W Range</div><div class="stat-value">${l52:,.2f} \u2014 ${h52:,.2f}</div><div style="color:#6B7280;font-size:0.75rem;">Current: ${price_t7:,.2f}</div></div>', unsafe_allow_html=True)

        st.markdown("---")
        sr1, sr2 = st.columns(2)
        with sr1:
            st.markdown(f'<div class="stat-card"><div class="stat-label">Support (20D Low)</div><div class="stat-value delta-up">${tech.get("support", 0):,.2f}</div></div>', unsafe_allow_html=True)
        with sr2:
            st.markdown(f'<div class="stat-card"><div class="stat-label">Resistance (20D High)</div><div class="stat-value delta-down">${tech.get("resistance", 0):,.2f}</div></div>', unsafe_allow_html=True)

        sma50_v = tech.get("sma_50")
        sma200_v = tech.get("sma_200")
        if sma50_v and sma200_v:
            if sma50_v > sma200_v:
                st.markdown('<div style="background:rgba(52,211,153,0.1);border:1px solid rgba(52,211,153,0.3);border-radius:8px;padding:12px;text-align:center;color:#34D399;font-weight:600;margin-top:12px;">Golden Cross: SMA50 > SMA200 \u2014 Bullish Signal</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div style="background:rgba(248,113,113,0.1);border:1px solid rgba(248,113,113,0.3);border-radius:8px;padding:12px;text-align:center;color:#F87171;font-weight:600;margin-top:12px;">Death Cross: SMA50 < SMA200 \u2014 Bearish Signal</div>', unsafe_allow_html=True)
    else:
        st.caption("Technical data not available. Enter a valid ticker.")

    st.markdown("---")
    st.markdown("#### Risk Analysis Matrix")
    risks = get_risk_analysis(quant_ticker_t7) if quant_ticker_t7 else []
    if risks:
        risk_rows = []
        for r in risks:
            risk_rows.append({"Risk Factor": r["risk"], "Severity": r["severity"], "Est. EPS Impact": r["eps_impact"], "Description": r["description"]})
        df_risks = pd.DataFrame(risk_rows)
        def style_severity(val):
            if val == "High":
                return "background-color: rgba(248,113,113,0.2); color: #F87171; font-weight: 700"
            elif val == "Medium":
                return "background-color: rgba(251,191,36,0.2); color: #FBBF24; font-weight: 700"
            return "background-color: rgba(52,211,153,0.2); color: #34D399; font-weight: 700"
        styled_risks = df_risks.style.map(style_severity, subset=["Severity"])
        st.dataframe(styled_risks, use_container_width=True, hide_index=True)
        total_impact = sum(float(r["eps_impact"].replace("$", "").replace("-", "")) for r in risks)
        st.markdown(f"""
        <div style="background:rgba(248,113,113,0.05);border:1px solid rgba(248,113,113,0.2);border-radius:8px;padding:12px;text-align:center;">
            <span style="color:#9CA3AF;font-size:0.8rem;">Cumulative Worst-Case EPS Impact:</span>
            <span style="color:#F87171;font-family:'JetBrains Mono',monospace;font-size:1.1rem;font-weight:700;margin-left:8px;">-${total_impact:.2f}</span>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.caption("Risk analysis requires a valid ticker with financial data.")
