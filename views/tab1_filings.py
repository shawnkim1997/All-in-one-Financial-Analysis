"""Tab 1 — SEC/DART Original Filing Viewer (Native HTML rendering)."""

import streamlit as st
import streamlit.components.v1 as components_v1

from data.sec_fetcher import fetch_sec_filing_html, _wrap_edgar_html_for_iframe


def render_tab1_filings(ticker, market):
    """Render the SEC / DART original filing viewer section of Tab 1."""
    st.markdown("---")
    st.markdown("#### 공시 원본 뷰어 (SEC Filing / DART)")

    is_us_filing = market and "US" in market
    is_kr_filing = market and ("Korea" in market or "KOSPI" in market or "KOSDAQ" in market)

    if is_us_filing:
        # ── [4] Filing type selector ──
        _filing_col1, _filing_col2, _filing_col3 = st.columns([1.5, 2, 1.5])
        with _filing_col1:
            _sec_filing_type = st.selectbox(
                "SEC Filing Type",
                ["10-K", "10-Q", "8-K", "20-F", "6-K"],
                index=0,
                key="sec_filing_type_select",
            )
        with _filing_col2:
            st.caption("")  # spacer
            _edgar_search_url = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={ticker}&type={_sec_filing_type}&dateb=&owner=include&count=10"
            st.markdown(
                f'<a href="{_edgar_search_url}" target="_blank" style="font-size:0.8rem;color:#60A5FA;">↗ SEC EDGAR에서 {_sec_filing_type} 검색</a>',
                unsafe_allow_html=True,
            )
        with _filing_col3:
            _fetch_btn = st.button(f"📄 {_sec_filing_type} 원본 가져오기", key="fetch_sec_filing_btn")

        # ── [5] Fetch with selected filing type ──
        if _fetch_btn or st.session_state.get("_last_sec_filing_html"):
            if _fetch_btn:
                with st.spinner(f"EDGAR에서 {ticker} {_sec_filing_type} 원본 HTML을 가져오는 중..."):
                    _result = fetch_sec_filing_html(ticker, _sec_filing_type)
                st.session_state["_last_sec_filing_html"] = _result.get("html")
                st.session_state["_last_sec_filing_error"] = _result.get("error")
                st.session_state["_last_sec_filing_source"] = _result.get("source")
                st.session_state["_last_sec_filing_url"] = _result.get("doc_url")
                st.session_state["_last_sec_filing_type"] = _sec_filing_type

            _raw_html = st.session_state.get("_last_sec_filing_html")
            _fetch_error = st.session_state.get("_last_sec_filing_error")
            _html_source = st.session_state.get("_last_sec_filing_source")
            _doc_url = st.session_state.get("_last_sec_filing_url")

            # ── [3] Show errors explicitly — never silently swallow ──
            if _fetch_error:
                st.error(f"SEC API Error: {_fetch_error}")
                if _doc_url:
                    st.code(_doc_url, language="text")

            if _raw_html:
                _doc_size_mb = len(_raw_html.encode("utf-8")) / 1e6
                _src_label = "디스크 캐시" if _html_source == "cache" else "EDGAR API"
                st.caption(f"원본 HTML 렌더링 · {_doc_size_mb:.1f} MB · 출처: {_src_label}")
                _wrapped = _wrap_edgar_html_for_iframe(_raw_html, ticker)
                components_v1.html(_wrapped, height=900, scrolling=True)
                if _doc_size_mb > 5:
                    st.caption(f"⚠ 문서가 큽니다({_doc_size_mb:.1f} MB). 느릴 경우 위 EDGAR 링크에서 원본 페이지를 여세요.")
        else:
            st.info(f"위 버튼을 클릭하면 {ticker}의 최신 {_sec_filing_type} 원본 문서를 SEC EDGAR에서 가져옵니다.")

    elif is_kr_filing:
        # ── [6] Korean DART direct links ──
        st.markdown("##### 🇰🇷 DART 공시 원본")
        _dart_code = ticker.replace(".KS", "").replace(".KQ", "").strip()
        _dart_col1, _dart_col2 = st.columns(2)
        with _dart_col1:
            _dart_company_url = f"https://dart.fss.or.kr/dsab001/main.do?autoSearch=true&textCrpNm={_dart_code}"
            st.markdown(
                f'<a href="{_dart_company_url}" target="_blank" '
                f'style="display:inline-block;padding:8px 16px;background:#1E40AF;color:white;border-radius:6px;'
                f'text-decoration:none;font-size:0.85rem;font-weight:600;">'
                f'📋 DART 전체 공시 보기 ({_dart_code})</a>',
                unsafe_allow_html=True,
            )
        with _dart_col2:
            _dart_annual_url = f"https://dart.fss.or.kr/dsab001/main.do?autoSearch=true&textCrpNm={_dart_code}&rghtBbstp=L"
            st.markdown(
                f'<a href="{_dart_annual_url}" target="_blank" '
                f'style="display:inline-block;padding:8px 16px;background:#065F46;color:white;border-radius:6px;'
                f'text-decoration:none;font-size:0.85rem;font-weight:600;">'
                f'📊 DART 사업보고서 바로가기</a>',
                unsafe_allow_html=True,
            )
        st.caption("DART 전자공시시스템에서 사업보고서, 분기보고서, 주요사항보고서 등 원본을 열람할 수 있습니다.")
    else:
        st.caption("공시 뷰어: US 종목(SEC EDGAR) 또는 한국 종목(DART)을 선택하세요.")
