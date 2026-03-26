"""EDINET (Japan) — optional API download + link fallbacks."""

from __future__ import annotations

import io
import json
import os
import re
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
from bs4 import BeautifulSoup

from server.utils.ticker_utils import japanese_sec_code_from_ticker

_DATA_DIR: Path = Path(__file__).resolve().parents[3] / "data"
_EDINET_API = "https://api.edinet-fsa.go.jp/api/v2"
# Annual securities report (有価証券報告書)
_DOCTYPE_YUKASHOKEN = "120"


def edinet_is_configured() -> bool:
    return bool((os.getenv("EDINET_SUBSCRIPTION_KEY") or "").strip())


def get_edinet_links(ticker: str) -> Dict[str, str]:
    """Public EDINET URLs when API key is unavailable."""
    t = (ticker or "").strip().upper()
    sec5 = japanese_sec_code_from_ticker(t) or ""
    code4 = sec5[:4] if len(sec5) >= 4 else ""
    return {
        "edinet_portal": "https://disclosure.edinet-fsa.go.jp/",
        "edinet_guide_en": "https://www.fsa.go.jp/en/search/EDINET.html",
        "ticker": t,
        "sec_code_5": sec5,
        "search_note": (
            f"証券コード {code4} — Open EDINET portal and search 有価証券報告書 for this issuer."
            if code4
            else "Use a 4-digit Tokyo ticker with .T (e.g. 7203.T)."
        ),
    }


def _clean_jp_text(raw: str) -> str:
    if not raw or not raw.strip():
        return ""
    try:
        soup = BeautifulSoup(raw, "lxml")
        for tag in soup.find_all(["script", "style"]):
            tag.decompose()
        text = soup.get_text(separator="\n")
    except Exception:
        text = re.sub(r"<[^>]+>", "\n", raw)
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    return "\n".join(lines).strip()


def _text_from_xbrl_zip(content: bytes) -> str:
    chunks: List[str] = []
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            for name in zf.namelist():
                if not name.lower().endswith((".htm", ".html", ".xml", ".xhtml")):
                    continue
                try:
                    raw = zf.read(name)
                    for enc in ("utf-8", "utf-16", "cp932", "euc-jp", "latin-1"):
                        try:
                            chunks.append(_clean_jp_text(raw.decode(enc)))
                            break
                        except Exception:
                            continue
                except Exception:
                    continue
    except Exception:
        return ""
    return "\n\n".join(c for c in chunks if c)


def _split_edinet_sections(full: str) -> Dict[str, str]:
    """Map Japanese filing prose into SEC-like keys (rough)."""
    if len(full) < 200:
        return {
            "item1a": "",
            "item3": "",
            "item7": full,
            "item8": "",
            "item9a": "",
        }
    item7 = ""
    for pat in [
        r"第２\s*事業の状況",
        r"事業の状況",
        r"経営者による財政状態等の分析",
    ]:
        m = re.search(pat, full)
        if m:
            item7 = full[m.start() : m.start() + 150_000]
            break
    if not item7:
        item7 = full[:120_000]

    item8 = ""
    m8 = re.search(r"第５\s*経理の状況|財務諸表", full)
    if m8:
        item8 = full[m8.start() : m8.start() + 200_000]

    item1a = ""
    m1 = re.search(r"第２\s*事業のリスク|リスク情報", full)
    if m1:
        item1a = full[m1.start() : m1.start() + 80_000]

    return {
        "item1a": item1a,
        "item3": "",
        "item7": item7,
        "item8": item8,
        "item9a": "",
    }


def _cache_path(ticker: str) -> Path:
    safe = (ticker or "").strip().upper().replace(".", "_")
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    return _DATA_DIR / f"{safe}_edinet_latest.json"


def _edinet_headers() -> Dict[str, str]:
    key = (os.getenv("EDINET_SUBSCRIPTION_KEY") or "").strip()
    return {
        "Subscription-Key": key,
        "Accept": "application/json",
    }


def _find_yukashoken_doc(
    sec_code_5: str,
    max_days: int = 60,
) -> Optional[Tuple[str, str]]:
    """Return (doc_id, date_str) for latest 有価証券報告書 or None."""
    key = (os.getenv("EDINET_SUBSCRIPTION_KEY") or "").strip()
    if not key:
        return None

    today = datetime.now().date()
    for i in range(max_days):
        day = today - timedelta(days=i)
        ds = day.strftime("%Y-%m-%d")
        try:
            r = requests.get(
                f"{_EDINET_API}/documents.json",
                params={"date": ds, "type": 2},
                headers=_edinet_headers(),
                timeout=45,
            )
        except requests.RequestException:
            continue
        if r.status_code == 401:
            return None
        if not r.ok:
            continue
        try:
            data = r.json()
        except Exception:
            continue
        results = data.get("results")
        if not isinstance(results, list):
            continue
        for doc in results:
            if not isinstance(doc, dict):
                continue
            if str(doc.get("docTypeCode")) != _DOCTYPE_YUKASHOKEN:
                continue
            if str(doc.get("secCode") or "") == sec_code_5:
                doc_id = doc.get("docID")
                if doc_id:
                    return str(doc_id), ds
    return None


def _download_edinet_document(doc_id: str) -> bytes:
    key = (os.getenv("EDINET_SUBSCRIPTION_KEY") or "").strip()
    r = requests.get(
        f"{_EDINET_API}/documents/{doc_id}",
        params={"type": 5},
        headers={"Subscription-Key": key},
        timeout=120,
    )
    r.raise_for_status()
    return r.content


def get_edinet_sections(ticker: str) -> Tuple[Dict[str, str], str, str, Dict[str, Any]]:
    """Return sections dict, status, html, meta (links, doc_id, etc.)."""
    t = (ticker or "").strip().upper()
    sec5 = japanese_sec_code_from_ticker(t)
    if not sec5:
        raise ValueError("Ticker must be a Tokyo listing (e.g. 7203.T).")

    links = get_edinet_links(t)
    meta: Dict[str, Any] = {"links": links, "sec_code": sec5}

    if not edinet_is_configured():
        empty = {"item1a": "", "item3": "", "item7": "", "item8": "", "item9a": ""}
        return empty, "unconfigured", "", {**meta, "configured": False}

    cache_p = _cache_path(t)
    if cache_p.exists():
        try:
            cached = json.loads(cache_p.read_text(encoding="utf-8"))
            if isinstance(cached, dict) and cached.get("sections"):
                sec = cached["sections"]
                if isinstance(sec, dict):
                    return (
                        sec,
                        "cache",
                        cached.get("html") or "",
                        {**meta, **cached.get("meta", {}), "configured": True},
                    )
        except Exception:
            pass

    found = _find_yukashoken_doc(sec5)
    if not found:
        raise FileNotFoundError(
            "No recent 有価証券報告書 found in EDINET for this security (try more history or verify ticker).",
        )
    doc_id, filing_date = found
    meta["doc_id"] = doc_id
    meta["filing_date"] = filing_date

    raw = _download_edinet_document(doc_id)
    full_text = _text_from_xbrl_zip(raw)
    if not full_text or len(full_text) < 100:
        raise ValueError("Could not extract text from EDINET document.")

    sections = _split_edinet_sections(full_text)

    def _esc(s: str) -> str:
        return (
            (s or "")
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

    html = (
        '<div class="edinet-filing" style="color:#e5e7eb;">'
        f'<section id="edinet-item-1a"><pre style="white-space:pre-wrap;font:inherit;">{_esc(sections.get("item1a", ""))}</pre></section>'
        f'<section id="edinet-item-3"><pre style="white-space:pre-wrap;font:inherit;">{_esc(sections.get("item3", ""))}</pre></section>'
        f'<section id="edinet-item-7"><pre style="white-space:pre-wrap;font:inherit;">{_esc(sections.get("item7", ""))}</pre></section>'
        f'<section id="edinet-item-8"><pre style="white-space:pre-wrap;font:inherit;">{_esc(sections.get("item8", ""))}</pre></section>'
        f'<section id="edinet-item-9a"><pre style="white-space:pre-wrap;font:inherit;">{_esc(sections.get("item9a", ""))}</pre></section>'
        "</div>"
    )
    try:
        cache_p.write_text(
            json.dumps(
                {
                    "sections": sections,
                    "html": html,
                    "meta": meta,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
    except Exception:
        pass

    return sections, "downloaded", html, {**meta, "configured": True}
