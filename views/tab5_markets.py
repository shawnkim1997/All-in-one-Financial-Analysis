import streamlit as st
try:
    import yfinance as yf
except ImportError:
    yf = None


def render_tab5():
    st.subheader("Markets & Foreign Exchange")
    # FX Rates
    st.markdown("#### \U0001f4b1 FX Rates")
    fx_pairs = {"USD/KRW": "USDKRW=X", "GBP/USD": "GBPUSD=X", "EUR/USD": "EURUSD=X", "USD/JPY": "USDJPY=X"}
    fx_cols = st.columns(len(fx_pairs))
    for i, (label, sym) in enumerate(fx_pairs.items()):
        with fx_cols[i]:
            try:
                t = yf.Ticker(sym)
                info = t.info or {}
                price = info.get("regularMarketPrice") or info.get("previousClose") or 0
                prev = info.get("regularMarketPreviousClose") or price
                chg = ((price - prev) / prev * 100) if prev else 0
                color = "#34D399" if chg >= 0 else "#F87171"
                st.markdown(f"""
                <div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06); border-radius: 8px; padding: 16px; text-align: center;">
                    <div style="color: #6B7280; font-size: 0.75rem; font-weight: 600;">{label}</div>
                    <div style="color: #F3F4F6; font-size: 1.4rem; font-family: 'JetBrains Mono', monospace; font-weight: 700;">{price:,.2f}</div>
                    <div style="color: {color}; font-size: 0.8rem;">{chg:+.2f}%</div>
                </div>
                """, unsafe_allow_html=True)
            except Exception:
                st.markdown(f"<div style='background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06); border-radius: 8px; padding: 16px; text-align: center;'><div style='color: #6B7280;'>{label}</div><div style='color: #F87171;'>N/A</div></div>", unsafe_allow_html=True)

    # Market Sector Heatmap
    st.markdown("---")
    st.markdown("#### \U0001f5fa\ufe0f Sector Performance")
    sector_tickers = {"Technology": "XLK", "Healthcare": "XLV", "Financials": "XLF", "Energy": "XLE", "Consumer": "XLY", "Industrial": "XLI", "Utilities": "XLU", "Materials": "XLB", "Real Estate": "XLRE", "Communication": "XLC"}
    sector_data = []
    for name, sym in sector_tickers.items():
        try:
            t = yf.Ticker(sym)
            info = t.info or {}
            price = info.get("regularMarketPrice") or 0
            prev = info.get("regularMarketPreviousClose") or price
            chg = ((price - prev) / prev * 100) if prev else 0
            sector_data.append({"sector": name, "change": chg})
        except Exception:
            sector_data.append({"sector": name, "change": 0})
    # Render as colored grid
    heatmap_cols = st.columns(5)
    for i, s in enumerate(sector_data):
        with heatmap_cols[i % 5]:
            bg = f"rgba(52, 211, 153, {min(abs(s['change'])/3, 0.6)})" if s['change'] >= 0 else f"rgba(248, 113, 113, {min(abs(s['change'])/3, 0.6)})"
            st.markdown(f"""
            <div style="background: {bg}; border: 1px solid rgba(255,255,255,0.06); border-radius: 8px; padding: 12px; text-align: center; margin-bottom: 8px;">
                <div style="color: #F3F4F6; font-weight: 600; font-size: 0.85rem;">{s['sector']}</div>
                <div style="color: {'#34D399' if s['change'] >= 0 else '#F87171'}; font-family: 'JetBrains Mono', monospace; font-size: 1.1rem; font-weight: 700;">{s['change']:+.2f}%</div>
            </div>
            """, unsafe_allow_html=True)
