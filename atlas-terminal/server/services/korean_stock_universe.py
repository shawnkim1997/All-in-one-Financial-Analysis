"""Local Korean stock universe loader and search helpers.

This module provides a reusable KOSPI/KOSDAQ universe foundation that reads
from a local normalized artifact.  The loader prefers a generated artifact when
present and falls back to a checked-in seed file, so the rest of the backend can
depend on a stable interface regardless of how the universe was built.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from functools import lru_cache
from pathlib import Path
import unicodedata


_DATA_DIR = Path(__file__).resolve().parents[1] / "data"
_ARTIFACT_CANDIDATES = (
    _DATA_DIR / "krx_universe.generated.json",
    _DATA_DIR / "krx_universe.seed.json",
)


@dataclass(frozen=True)
class KoreanStockRecord:
    ticker: str
    market: str
    name_ko: str
    name_en: str | None
    aliases: tuple[str, ...]
    yfinance_ticker: str

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["aliases"] = list(self.aliases)
        return data


def _normalize_text(value: str) -> str:
    return (
        unicodedata.normalize("NFKC", value or "")
        .lower()
        .replace("&", " and ")
        .replace("_", " ")
        .replace("-", " ")
        .replace(".", " ")
    )


def _collapse_text(value: str) -> str:
    return "".join(_normalize_text(value).split())


def _artifact_path() -> Path:
    for candidate in _ARTIFACT_CANDIDATES:
        if candidate.exists():
            return candidate
    raise FileNotFoundError("No Korean stock universe artifact found.")


def _normalize_row(row: dict[str, object]) -> KoreanStockRecord:
    ticker = str(row.get("ticker", "")).strip()
    market = str(row.get("market", "")).strip().upper()
    name_ko = str(row.get("name_ko", "")).strip()
    name_en_raw = str(row.get("name_en", "") or "").strip()
    name_en = name_en_raw or None
    aliases = tuple(str(alias).strip() for alias in (row.get("aliases", []) or []) if str(alias).strip())
    yfinance_ticker = str(row.get("yfinance_ticker", "")).strip().upper()

    if len(ticker) != 6 or not ticker.isdigit():
        raise ValueError(f"Invalid KRX ticker code: {ticker!r}")
    if market not in {"KOSPI", "KOSDAQ"}:
        raise ValueError(f"Invalid Korean market: {market!r}")
    if not name_ko:
        raise ValueError(f"Missing Korean company name for ticker {ticker}")
    if not yfinance_ticker:
        raise ValueError(f"Missing yfinance ticker for ticker {ticker}")

    return KoreanStockRecord(
        ticker=ticker,
        market=market,
        name_ko=name_ko,
        name_en=name_en,
        aliases=aliases,
        yfinance_ticker=yfinance_ticker,
    )


@lru_cache(maxsize=1)
def load_korean_stock_universe() -> tuple[KoreanStockRecord, ...]:
    path = _artifact_path()
    rows = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(rows, list):
        raise ValueError("Korean stock universe artifact must be a JSON list.")
    return tuple(_normalize_row(row) for row in rows if isinstance(row, dict))


def _search_terms(record: KoreanStockRecord) -> tuple[str, ...]:
    parts = [record.ticker, record.yfinance_ticker, record.name_ko]
    if record.name_en:
        parts.append(record.name_en)
    parts.extend(record.aliases)
    return tuple(parts)


def get_korean_stock_record(identifier: str) -> KoreanStockRecord | None:
    query = (identifier or "").strip().upper()
    if not query:
        return None

    for record in load_korean_stock_universe():
        if query in {record.ticker, record.yfinance_ticker.upper()}:
            return record
    return None


def search_korean_stock_universe(
    query: str = "",
    *,
    market: str | None = None,
    limit: int = 20,
) -> list[KoreanStockRecord]:
    normalized_market = (market or "").strip().upper() or None
    rows = [
        record
        for record in load_korean_stock_universe()
        if normalized_market is None or record.market == normalized_market
    ]
    if not query.strip():
        return rows[: max(1, limit)]

    norm_query = _normalize_text(query)
    collapsed_query = _collapse_text(query)

    def score(record: KoreanStockRecord) -> int:
        best = 0
        for term in _search_terms(record):
            normalized = _normalize_text(term)
            collapsed = _collapse_text(term)
            if normalized == norm_query or collapsed == collapsed_query:
                best = max(best, 1000)
            elif normalized.startswith(norm_query) or collapsed.startswith(collapsed_query):
                best = max(best, 700)
            elif norm_query in normalized or collapsed_query in collapsed:
                best = max(best, 400)
        return best

    ranked = [(score(record), record) for record in rows]
    ranked = [item for item in ranked if item[0] > 0]
    ranked.sort(key=lambda item: (-item[0], item[1].market, item[1].ticker))
    return [record for _, record in ranked[: max(1, limit)]]


def korean_stock_universe_metadata() -> dict[str, object]:
    path = _artifact_path()
    rows = load_korean_stock_universe()
    return {
        "source_path": str(path),
        "count": len(rows),
        "markets": sorted({record.market for record in rows}),
    }
