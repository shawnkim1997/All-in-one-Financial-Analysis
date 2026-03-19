import streamlit as st
from config.constants import COMPANY_TICKER_MAP
from data.market import _fetch_news_rss


def render_tab4(ticker):
    st.subheader("News Feed")
    st.caption(f"Latest news for **{ticker}**")
    try:
        import feedparser
        news_items = _fetch_news_rss(ticker, COMPANY_TICKER_MAP.get(ticker, ""))
        if news_items:
            for item in news_items:
                st.markdown(f"""
                <div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06); border-radius: 8px; padding: 12px 16px; margin-bottom: 8px;">
                    <a href="{item['url']}" target="_blank" style="color: #F3F4F6; text-decoration: none; font-weight: 600; font-size: 0.95rem;">
                        {item['title']}
                    </a>
                    <div style="color: #6B7280; font-size: 0.75rem; margin-top: 4px;">
                        {item['source']} \u00b7 {item['published'][:25] if item['published'] else ''}
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No news found. Try a different ticker.")
    except ImportError:
        st.warning("Install `feedparser` to enable news feed: `pip install feedparser`")
