"""DART 사업보고서 다운로드·섹션 매핑 (Open DART API + dart-fss)."""

from __future__ import annotations

import json
import os
import re
import tempfile
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from bs4 import BeautifulSoup

from server.utils.ticker_utils import korean_stock_code_from_ticker

_DATA_DIR: Path = Path(__file__).resolve().parents[3] / "data"

# 사업보고서 (연)
_PBLNTF_DETAIL_ANNUAL = "A001"


def _dart_data_dir() -> Path:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    return _DATA_DIR


def _clean_korean_text(raw: str) -> str:
    """Preserve Hangul; strip tags and collapse whitespace (no ASCII-only strip)."""
    if not raw or not raw.strip():
        return ""
    try:
        soup = BeautifulSoup(raw, "lxml")
        for tag in soup.find_all(["script", "style"]):
            tag.decompose()
        text = soup.get_text(separator="\n")
    except Exception:
        text = re.sub(r"<[^>]+>", "\n", raw)
    lines = [ln.strip() for ln in text.splitlines()]
    lines = [ln for ln in lines if ln]
    out = "\n".join(lines)
    out = re.sub(r"\n{3,}", "\n\n", out)
    return out.strip()


def _cache_paths(stock_code: str) -> Tuple[Path, Path]:
    base = _dart_data_dir()
    return (
        base / f"{stock_code}_dart_latest.json",
        base / f"{stock_code}_dart_slice.html",
    )


def _extract_sections_from_plain(full: str) -> Dict[str, str]:
    """Map Korean annual report prose into SEC-like keys (best effort)."""
    text = full
    if len(text) < 200:
        return {
            "item1a": "",
            "item3": "",
            "item7": text,
            "item8": "",
            "item9a": "",
        }

    def _slice_between(patterns_start: List[str], end_markers: List[re.Pattern]) -> str:
        start_idx = -1
        for p in patterns_start:
            m = re.search(p, text, re.IGNORECASE | re.MULTILINE)
            if m:
                start_idx = m.start()
                break
        if start_idx < 0:
            return ""
        rest = text[start_idx:]
        end_idx = len(rest)
        for em in end_markers:
            m2 = em.search(rest[1:])
            if m2:
                end_idx = min(end_idx, m2.start() + 1)
        return rest[:end_idx].strip()

    # End markers for major sections (next Roman section or 제N장)
    next_section = re.compile(
        r"(?=\n\s*(?:IV\.|III\.|II\.|Ⅳ\.|Ⅲ\.|Ⅱ\.|제\s*[0-9]+\s*부|제\s*[0-9]+\s*장))",
        re.MULTILINE,
    )

    item1a = _slice_between(
        [r"II\.\s*투자위험", r"투자위험요소", r"투자\s*위험"],
        [next_section, re.compile(r"\n\s*III\.", re.MULTILINE)],
    )
    item7 = _slice_between(
        [
            r"경영자의\s*분석\s*의견",
            r"II\.\s*사업의\s*내용",
            r"사업의\s*내용",
        ],
        [next_section, re.compile(r"\n\s*III\.\s*재무", re.MULTILINE)],
    )
    if not item7:
        item7 = _slice_between(
            [r"II\.\s*사업의\s*내용"],
            [next_section],
        )

    item8 = _slice_between(
        [r"III\.\s*재무에\s*관한\s*사항", r"재무제표\s*등", r"연\s*결\s*재무제표"],
        [next_section, re.compile(r"\n\s*IV\.", re.MULTILINE)],
    )

    item3 = _slice_between(
        [r"법적\s*소송", r"소송", r"주요\s*사건", r"중요한\s*소송"],
        [next_section],
    )
    item9a = _slice_between(
        [r"내부\s*통제", r"내부회계관리제도", r"대표이사의\s*평가"],
        [next_section],
    )

    if not any([item1a, item7, item8, item3, item9a]):
        half = min(120_000, len(text))
        item7 = text[:half]

    return {
        "item1a": item1a[:80_000] if item1a else "",
        "item3": item3[:40_000] if item3 else "",
        "item7": item7[:120_000] if item7 else text[:120_000],
        "item8": item8[:200_000] if item8 else "",
        "item9a": item9a[:40_000] if item9a else "",
    }


def _read_zip_text(zip_path: Path) -> str:
    """Concatenate text from XML/HTML inside DART document zip."""
    chunks: List[str] = []
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            names = zf.namelist()
            # Prefer main document XML / HTM
            ordered = sorted(
                names,
                key=lambda n: (
                    0 if n.lower().endswith((".xml", ".htm", ".html")) else 1,
                    -len(n),
                ),
            )
            for name in ordered[:50]:
                if not name.lower().endswith((".xml", ".htm", ".html")):
                    continue
                try:
                    data = zf.read(name)
                    encodings = ("utf-8", "cp949", "euc-kr", "latin-1")
                    decoded = ""
                    for enc in encodings:
                        try:
                            decoded = data.decode(enc)
                            break
                        except Exception:
                            continue
                    if decoded:
                        chunks.append(_clean_korean_text(decoded))
                except Exception:
                    continue
    except zipfile.BadZipFile:
        raw = zip_path.read_bytes()
        for enc in ("utf-8", "cp949", "euc-kr"):
            try:
                chunks.append(_clean_korean_text(raw.decode(enc)))
                break
            except Exception:
                continue
    combined = "\n\n".join(c for c in chunks if c)
    return combined if combined else ""


def _load_xml_or_raw(downloaded_path: Path) -> str:
    p = downloaded_path
    if p.suffix.lower() == ".zip" or zipfile.is_zipfile(p):
        return _read_zip_text(p)
    if p.suffix.lower() in (".xml", ".htm", ".html"):
        raw = p.read_text(encoding="utf-8", errors="replace")
        return _clean_korean_text(raw)
    # Try zip anyway
    try:
        return _read_zip_text(p)
    except Exception:
        raw = p.read_bytes()
        return _clean_korean_text(raw.decode("utf-8", errors="replace"))


def _xml_escape(s: str) -> str:
    return (
        (s or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _build_html_fragment(sections: Dict[str, str]) -> str:
    parts = [
        '<div class="dart-filing" style="color:#e5e7eb;">',
        f'<section id="dart-item-1a"><h2>투자위험 / Risk</h2><pre style="white-space:pre-wrap;font:inherit;">{_xml_escape(sections.get("item1a", ""))}</pre></section>',
        f'<section id="dart-item-3"><h2>소송</h2><pre style="white-space:pre-wrap;font:inherit;">{_xml_escape(sections.get("item3", ""))}</pre></section>',
        f'<section id="dart-item-7"><h2>사업의 내용 / MD&amp;A</h2><pre style="white-space:pre-wrap;font:inherit;">{_xml_escape(sections.get("item7", ""))}</pre></section>',
        f'<section id="dart-item-8"><h2>재무</h2><pre style="white-space:pre-wrap;font:inherit;">{_xml_escape(sections.get("item8", ""))}</pre></section>',
        f'<section id="dart-item-9a"><h2>내부통제</h2><pre style="white-space:pre-wrap;font:inherit;">{_xml_escape(sections.get("item9a", ""))}</pre></section>',
        "</div>",
    ]
    return "\n".join(parts)


def dart_filing_is_configured() -> bool:
    return bool((os.getenv("DART_API_KEY") or "").strip())


def get_dart_sections(ticker: str) -> Tuple[Dict[str, str], str, str, str]:
    """Return (sections, status, html_fragment, rcept_no_or_empty).

    status is ``cache`` or ``downloaded``.
    """
    stock = korean_stock_code_from_ticker(ticker)
    if not stock:
        raise ValueError("Ticker must be a Korean listing (e.g. 005930.KS).")

    if not dart_filing_is_configured():
        raise ValueError("DART_API_KEY is not set.")

    json_path, html_path = _cache_paths(stock)
    if json_path.exists():
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and data.get("sections"):
                sec = data["sections"]
                html = data.get("html") or ""
                if isinstance(sec, dict):
                    return sec, "cache", html, data.get("rcept_no") or ""
        except Exception:
            pass

    import dart_fss as dart  # noqa: WPS433
    from dart_fss.api.filings.document import download_document
    from dart_fss.api.filings import search_filings

    dart.set_api_key((os.getenv("DART_API_KEY") or "").strip())
    corp_list = dart.get_corp_list()
    corp = corp_list.find_by_stock_code(stock)
    if corp is None:
        raise ValueError(f"No DART company for stock code {stock}.")

    end_de = datetime.now().strftime("%Y%m%d")
    bgn_de = (datetime.now() - timedelta(days=550)).strftime("%Y%m%d")

    resp = search_filings(
        corp_code=corp.corp_code,
        bgn_de=bgn_de,
        end_de=end_de,
        pblntf_detail_ty=_PBLNTF_DETAIL_ANNUAL,
        last_reprt_at="Y",
        page_count=100,
        page_no=1,
        sort="date",
        sort_mth="desc",
    )
    lst = resp.get("list") or []
    if not lst:
        resp = search_filings(
            corp_code=corp.corp_code,
            bgn_de=bgn_de,
            end_de=end_de,
            pblntf_detail_ty=_PBLNTF_DETAIL_ANNUAL,
            last_reprt_at="N",
            page_count=100,
            page_no=1,
            sort="date",
            sort_mth="desc",
        )
        lst = resp.get("list") or []
    if not lst:
        raise FileNotFoundError("No 사업보고서 (annual) found in DART for this company.")

    rcept_no = lst[0].get("rcept_no") or lst[0].get("rcp_no")
    if not rcept_no:
        raise FileNotFoundError("DART search returned no rcept_no.")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        full_path = download_document(str(tmp_path), str(rcept_no))
        path_obj = Path(full_path)
        full_text = _load_xml_or_raw(path_obj)
    if not full_text or len(full_text) < 100:
        raise ValueError("Could not extract text from DART document.")

    sections = _extract_sections_from_plain(full_text)
    html_frag = _build_html_fragment(sections)

    payload = {
        "sections": sections,
        "html": html_frag,
        "rcept_no": rcept_no,
        "ticker": ticker.upper(),
        "stock_code": stock,
    }
    try:
        json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        html_path.write_text(html_frag, encoding="utf-8")
    except Exception:
        pass

    return sections, "downloaded", html_frag, str(rcept_no)
