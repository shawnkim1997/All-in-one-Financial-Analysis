"""Provider primitives for the ATLAS Data Gateway."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, TypeVar

from server.core.data_gateway import Article, EarningEvent, Fundamentals, HoldersData, OHLCV, Profile, Quote, Segment

T = TypeVar("T")
logger = logging.getLogger(__name__)


class ProviderError(Exception):
    """Base class for recoverable provider failures."""


class ProviderNotImplemented(ProviderError):
    """Provider does not implement this data shape yet."""


class ProviderNotConfigured(ProviderError):
    """Provider requires credentials or environment that are not configured."""


class DataUnavailable(Exception):
    """Raised after every provider in a chain fails."""

    def __init__(self, symbol: str, method: str, errors: list[str] | None = None) -> None:
        self.symbol = symbol
        self.method = method
        self.errors = errors or []
        suffix = f": {'; '.join(self.errors)}" if self.errors else ""
        super().__init__(f"Data unavailable for {symbol} via {method}{suffix}")


class BaseProvider:
    """Small async facade around concrete market-data providers."""

    name = "base"

    def supports_symbol(self, symbol: str) -> bool:
        return bool(symbol.strip())

    async def _to_thread(self, fn: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        return await asyncio.to_thread(fn, *args, **kwargs)

    async def quote(self, symbol: str) -> Quote:
        raise ProviderNotImplemented(f"{self.name}.quote")

    async def profile(self, symbol: str) -> Profile:
        raise ProviderNotImplemented(f"{self.name}.profile")

    async def fundamentals(self, symbol: str, period: str = "annual") -> Fundamentals:
        raise ProviderNotImplemented(f"{self.name}.fundamentals")

    async def financials(self, symbol: str, statement: str = "income", period: str = "annual") -> dict[str, Any]:
        raise ProviderNotImplemented(f"{self.name}.financials")

    async def history(self, symbol: str, range: str = "1y") -> OHLCV:
        raise ProviderNotImplemented(f"{self.name}.history")

    async def news(self, symbols: list[str], limit: int = 20) -> list[Article]:
        raise ProviderNotImplemented(f"{self.name}.news")

    async def peers(self, symbol: str) -> list[str]:
        raise ProviderNotImplemented(f"{self.name}.peers")

    async def segments(self, symbol: str) -> list[Segment]:
        raise ProviderNotImplemented(f"{self.name}.segments")

    async def holders(self, symbol: str) -> HoldersData:
        raise ProviderNotImplemented(f"{self.name}.holders")

    async def earnings_calendar(self, symbol: str) -> list[EarningEvent]:
        raise ProviderNotImplemented(f"{self.name}.earnings_calendar")
