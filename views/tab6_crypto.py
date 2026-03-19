import pandas as pd
import streamlit as st
try:
    import yfinance as yf
except ImportError:
    yf = None


def render_tab6():
    st.subheader("Cryptocurrency Prices")
    crypto_list = [
        ("Bitcoin", "BTC-USD"), ("Ethereum", "ETH-USD"), ("BNB", "BNB-USD"),
        ("Solana", "SOL-USD"), ("XRP", "XRP-USD"), ("Cardano", "ADA-USD"),
        ("Avalanche", "AVAX-USD"), ("Dogecoin", "DOGE-USD"), ("Polkadot", "DOT-USD"),
        ("Chainlink", "LINK-USD"), ("Polygon", "MATIC-USD"), ("Litecoin", "LTC-USD"),
    ]
    crypto_rows = []
    for name, sym in crypto_list:
        try:
            t = yf.Ticker(sym)
            info = t.info or {}
            price = info.get("regularMarketPrice") or info.get("previousClose") or 0
            prev = info.get("regularMarketPreviousClose") or price
            chg = ((price - prev) / prev * 100) if prev else 0
            mcap = info.get("marketCap") or 0
            crypto_rows.append({
                "Coin": name,
                "Symbol": sym.replace("-USD", ""),
                "Price (USD)": f"${price:,.2f}",
                "24h Change": f"{chg:+.2f}%",
                "Market Cap": f"${mcap/1e9:.1f}B" if mcap >= 1e9 else (f"${mcap/1e6:.0f}M" if mcap else "N/A"),
                "_change": chg,
            })
        except Exception:
            crypto_rows.append({"Coin": name, "Symbol": sym.replace("-USD", ""), "Price (USD)": "N/A", "24h Change": "N/A", "Market Cap": "N/A", "_change": 0})
    if crypto_rows:
        df_crypto = pd.DataFrame(crypto_rows)
        def style_crypto(row):
            chg = row.get("_change", 0)
            color = "#34D399" if chg >= 0 else "#F87171"
            return [f"color: {color}" if col == "24h Change" else "" for col in row.index]
        display_df = df_crypto.drop(columns=["_change"])
        st.dataframe(display_df.style.apply(style_crypto, axis=1), use_container_width=True, hide_index=True)
