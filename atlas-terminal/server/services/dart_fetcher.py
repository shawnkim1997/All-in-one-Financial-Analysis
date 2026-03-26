"""DART (Korea disclosure) helpers via dart-fss (requires ``DART_API_KEY``)."""

from __future__ import annotations

import os
from typing import Any, Dict, List


def dart_is_configured() -> bool:
    return bool((os.getenv("DART_API_KEY") or "").strip())


def search_corporations(query: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Search listed companies by Korean/English name (best effort)."""
    key = (os.getenv("DART_API_KEY") or "").strip()
    q = (query or "").strip()
    if not key or not q:
        return []

    try:
        import dart_fss as dart  # noqa: WPS433
    except ImportError:
        return []

    try:
        dart.set_api_key(key)
        corp_list = dart.get_corp_list()
        found = corp_list.find_by_corp_name(q, exactly=False)
    except Exception:
        return []

    if found is None:
        return []

    out: List[Dict[str, Any]] = []
    for item in list(found)[:limit]:
        row: Dict[str, Any] = {}
        for attr in (
            "corp_name",
            "corp_eng_name",
            "corp_code",
            "stock_code",
            "modify_date",
        ):
            if hasattr(item, attr):
                row[attr] = getattr(item, attr)
        if not row:
            row["repr"] = repr(item)
        out.append(row)
    return out
