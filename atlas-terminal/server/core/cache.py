"""TTL cache wrapper for DataGateway implementations."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from server.core.data_gateway import Article, DataGateway, EarningEvent, Fundamentals, HoldersData, OHLCV, Profile, Quote, Segment

T = TypeVar("T")


class CachedGateway(DataGateway):
    """Process-local cache for expensive provider calls.

    This is deliberately thin and replaceable.  The contract gives us a single
    seam where Redis/Vercel Runtime Cache/Supabase cache can later slot in
    without rewriting routers.
    """

    TTLS = {
        "quote": 30,
        "profile": 86_400,
        "fundamentals": 43_200,
        "segments": 604_800,
        "history": 300,
        "news": 300,
        "peers": 86_400,
        "holders": 43_200,
        "earnings_calendar": 3_600,
    }

    def __init__(self, inner: DataGateway) -> None:
        self.inner = inner
        self._lock = asyncio.Lock()
        self._store: dict[str, tuple[float, Any]] = {}

    def _key(self, method: str, *parts: Any) -> str:
        normalized = ":".join(str(part).strip().upper() for part in parts)
        return f"{method}:{normalized}"

    async def _cached(self, method: str, key_parts: tuple[Any, ...], fetcher: Callable[[], Awaitable[T]]) -> T:
        key = self._key(method, *key_parts)
        ttl = self.TTLS[method]
        now = time.monotonic()
        async with self._lock:
            cached = self._store.get(key)
            if cached and now - cached[0] < ttl:
                return cached[1]

        result = await fetcher()
        async with self._lock:
            self._store[key] = (time.monotonic(), result)
        return result

    async def quote(self, symbol: str) -> Quote:
        return await self._cached("quote", (symbol,), lambda: self.inner.quote(symbol))

    async def profile(self, symbol: str) -> Profile:
        return await self._cached("profile", (symbol,), lambda: self.inner.profile(symbol))

    async def fundamentals(self, symbol: str, period: str = "annual") -> Fundamentals:
        return await self._cached("fundamentals", (symbol, period), lambda: self.inner.fundamentals(symbol, period))

    async def history(self, symbol: str, range: str = "1y") -> OHLCV:
        return await self._cached("history", (symbol, range), lambda: self.inner.history(symbol, range))

    async def news(self, symbols: list[str], limit: int = 20) -> list[Article]:
        return await self._cached("news", (",".join(symbols), limit), lambda: self.inner.news(symbols, limit))

    async def peers(self, symbol: str) -> list[str]:
        return await self._cached("peers", (symbol,), lambda: self.inner.peers(symbol))

    async def segments(self, symbol: str) -> list[Segment]:
        return await self._cached("segments", (symbol,), lambda: self.inner.segments(symbol))

    async def holders(self, symbol: str) -> HoldersData:
        return await self._cached("holders", (symbol,), lambda: self.inner.holders(symbol))

    async def earnings_calendar(self, symbol: str) -> list[EarningEvent]:
        return await self._cached("earnings_calendar", (symbol,), lambda: self.inner.earnings_calendar(symbol))

    async def clear(self) -> None:
        async with self._lock:
            self._store.clear()
