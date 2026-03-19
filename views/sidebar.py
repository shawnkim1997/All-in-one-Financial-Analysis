import os
import streamlit as st
from utils.prefs import _load_prefs, _save_prefs, _PREFS_PATH
from utils.ticker import infer_market_from_ticker

try:
    from yahooquery import search as yq_search
except ImportError:
    yq_search = None


def render_sidebar():
    with st.sidebar:
        st.markdown("""
<div style="display: flex; align-items: center; gap: 8px; margin-bottom: 16px; padding-bottom: 12px; border-bottom: 1px solid rgba(255,255,255,0.06);">
    <span style="font-size: 1.3rem; font-weight: 800; color: #60A5FA; font-family: 'JetBrains Mono', monospace;">ATLAS</span>
    <span style="font-size: 1.3rem; font-weight: 300; color: #6B7280;">TERMINAL</span>
</div>
""", unsafe_allow_html=True)
        st.markdown('<div style="color: #6B7280; font-size: 0.7rem; font-weight: 600; letter-spacing: 2px; margin-bottom: 8px;">SETTINGS</div>', unsafe_allow_html=True)
        _prefs = _load_prefs()
        # Restore last selected company on refresh (session_state is empty after reload)
        if _prefs.get("last_ticker") and not st.session_state.get("company_search_options"):
            _lt = _prefs["last_ticker"]
            _opts = _prefs.get("last_company_options") or []
            _syms = _prefs.get("last_company_symbols") or []
            if not _opts and _lt:
                _opts = [f"[Saved] {_lt}"]
                _syms = [_lt]
            st.session_state["ticker"] = _lt
            st.session_state["company_search_options"] = _opts
            st.session_state["company_search_symbols"] = _syms
        _default_key = _prefs.get("google_api_key") or os.environ.get("GOOGLE_API_KEY", "")
        _default_email = _prefs.get("sec_email") or os.environ.get("SEC_EDGAR_EMAIL", "")
        google_api_key = st.text_input(
            "Google API Key (Gemini)",
            value=_default_key,
            help="Required for Tab 1 (10-K insights).",
            key="input_google_api_key",
        )
        sec_email = st.text_input(
            "SEC EDGAR Email",
            value=_default_email,
            help="Required for 10-K download.",
            key="input_sec_email",
        )
        remember_me = st.checkbox(
            "Remember API key & email (save locally)",
            value=bool(_prefs),
            help="Store in .app_prefs.json in this project. Uncheck to clear and stop saving.",
            key="remember_me",
        )
        if remember_me and (google_api_key or sec_email):
            _save_prefs(google_api_key, sec_email)
        elif not remember_me and _PREFS_PATH.exists():
            # Clear only API keys in prefs; keep last_ticker so company selection persists on refresh
            try:
                _cur = _load_prefs()
                _save_prefs("", "", last_ticker=_cur.get("last_ticker"), last_company_options=_cur.get("last_company_options"), last_company_symbols=_cur.get("last_company_symbols"))
            except Exception:
                pass
        st.markdown('<div style="color: #6B7280; font-size: 0.7rem; font-weight: 600; letter-spacing: 2px; margin: 16px 0 8px;">COMPANY SEARCH</div>', unsafe_allow_html=True)
        search_query = st.text_input(
            "Search Company Name (e.g., Apple, 삼성, Mitsubishi)",
            value=st.session_state.get("company_search_input", ""),
            key="company_search_input",
            placeholder="e.g. Apple, 삼성, Mitsubishi",
        )
        if st.button("Search Company", key="search_company_btn"):
            query = (search_query or "").strip()
            if not query:
                st.warning("Enter a company name to search.")
            elif yq_search is None:
                st.warning("yahooquery is not installed; search is unavailable.")
            else:
                try:
                    raw_results = yq_search(query)
                    if not isinstance(raw_results, dict):
                        raw_results = {}
                    quotes = raw_results.get("quotes", []) or []
                    skip_types = ("INDEX", "MUTUALFUND")
                    quotes = [
                        q for q in quotes
                        if q.get("symbol") and q.get("shortname")
                        and (q.get("quoteType") or "EQUITY") not in skip_types
                    ]
                    if not quotes:
                        st.session_state["company_search_options"] = []
                        st.session_state["company_search_symbols"] = []
                        st.warning("No valid equities found. Try typing the English name (e.g., 'Samsung' instead of '삼성').")
                    else:
                        options = []
                        symbols = []
                        for q in quotes[:50]:
                            sym = (q.get("symbol") or "").strip()
                            options.append(f"[{q.get('exchange', 'N/A')}] {q.get('symbol')} - {q.get('shortname', 'Unknown')}")
                            symbols.append(sym)
                        st.session_state["company_search_options"] = options
                        st.session_state["company_search_symbols"] = symbols
                        st.session_state["ticker"] = symbols[0]
                        st.success(f"Found {len(options)} result(s). Select below.")
                except Exception:
                    st.warning("No valid equities found. Try typing the English name (e.g., 'Samsung' instead of '삼성').")
                    st.session_state["company_search_options"] = []
                    st.session_state["company_search_symbols"] = []

        search_options = st.session_state.get("company_search_options") or []
        search_symbols = st.session_state.get("company_search_symbols") or []
        placeholder = "— Click the search button above —"
        options_for_select = [placeholder] if not search_options else search_options
        current_ticker = st.session_state.get("ticker", "NVDA")
        default_idx = 0
        if search_symbols and current_ticker:
            for i, sym in enumerate(search_symbols):
                if sym == current_ticker:
                    default_idx = i
                    break
        selected_option = st.selectbox(
            "Select company (ticker - name)",
            options=options_for_select,
            index=0 if not search_options else min(default_idx, len(search_options) - 1),
            key="company_select",
        )
        if search_options and selected_option and selected_option != placeholder and " - " in selected_option:
            first_part = selected_option.split(" - ", 1)[0].strip()
            sym = first_part.split("]", 1)[-1].strip() if "]" in first_part else first_part
            st.session_state["ticker"] = sym
        ticker = st.session_state.get("ticker") or (search_symbols[0] if search_symbols else "NVDA")
        st.session_state["google_api_key"] = google_api_key
        st.session_state["sec_email"] = sec_email
        st.session_state["ticker"] = ticker
        st.session_state["market"] = infer_market_from_ticker(ticker)
        # Persist selected company so it survives page refresh
        _save_prefs(
            google_api_key if st.session_state.get("remember_me") else "",
            sec_email if st.session_state.get("remember_me") else "",
            last_ticker=ticker,
            last_company_options=search_options,
            last_company_symbols=search_symbols,
        )
        st.caption("Search by name (any language), then select. Ticker suffix is set automatically.")
    return ticker
