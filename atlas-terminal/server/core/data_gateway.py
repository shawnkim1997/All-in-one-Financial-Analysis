"""Typed data gateway contract for market data access.

This module is intentionally provider-agnostic.  Routers should eventually
depend on this Protocol instead of reaching into yfinance/FMP/yahooquery
directly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Literal, Protocol


@dataclass(frozen=True)
class Quote:
    symbol: str
    price: float | None
    currency: str | None = None
    change: float | None = None
    change_pct: float | None = None
    market_time: datetime | None = None
    source: str = ""
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Profile:
    symbol: str
    name: str | None = None
    description: str | None = None
    sector: str | None = None
    industry: str | None = None
    country: str | None = None
    exchange: str | None = None
    currency: str | None = None
    website: str | None = None
    employees: int | None = None
    market_cap: float | None = None
    source: str = ""
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Fundamentals:
    symbol: str
    period: str
    revenue: float | None = None
    gross_profit: float | None = None
    operating_income: float | None = None
    net_income: float | None = None
    ebitda: float | None = None
    free_cash_flow: float | None = None
    total_assets: float | None = None
    total_debt: float | None = None
    cash: float | None = None
    shares: float | None = None
    source: str = ""
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class OHLCVBar:
    date: date
    open: float | None
    high: float | None
    low: float | None
    close: float | None
    volume: float | None = None


@dataclass(frozen=True)
class OHLCV:
    symbol: str
    range: str
    bars: list[OHLCVBar]
    source: str = ""


@dataclass(frozen=True)
class Article:
    title: str
    url: str
    source: str | None = None
    published_at: datetime | None = None
    summary: str | None = None
    symbols: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Segment:
    name: str
    revenue: float | None = None
    percent: float | None = None
    period: str | None = None


@dataclass(frozen=True)
class HoldersData:
    symbol: str
    institutions: list[dict[str, Any]] = field(default_factory=list)
    insiders: list[dict[str, Any]] = field(default_factory=list)
    source: str = ""


@dataclass(frozen=True)
class EarningEvent:
    symbol: str
    event_date: date
    fiscal_quarter: str | None = None
    eps_estimate: float | None = None
    revenue_estimate: float | None = None
    status: Literal["confirmed", "estimated"] = "estimated"
    source: str = ""


class DataGateway(Protocol):
    async def quote(self, symbol: str) -> Quote: ...

    async def profile(self, symbol: str) -> Profile: ...

    async def fundamentals(self, symbol: str, period: str = "annual") -> Fundamentals: ...

    async def history(self, symbol: str, range: str = "1y") -> OHLCV: ...

    async def news(self, symbols: list[str], limit: int = 20) -> list[Article]: ...

    async def peers(self, symbol: str) -> list[str]: ...

    async def segments(self, symbol: str) -> list[Segment]: ...

    async def holders(self, symbol: str) -> HoldersData: ...

    async def earnings_calendar(self, symbol: str) -> list[EarningEvent]: ...
