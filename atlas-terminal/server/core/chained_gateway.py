"""Chain-of-responsibility gateway implementation."""

from __future__ import annotations

from typing import Awaitable, Callable, TypeVar

from server.core.data_gateway import Article, DataGateway, EarningEvent, Fundamentals, HoldersData, OHLCV, Profile, Quote, Segment
from server.core.provider_metrics import provider_metrics
from server.core.providers.base import BaseProvider, DataUnavailable, ProviderError

T = TypeVar("T")


class ChainedGateway(DataGateway):
    """Try providers in order until one returns usable data."""

    def __init__(self, providers: list[BaseProvider]) -> None:
        self.providers = providers

    def _order_for(self, symbol: str) -> list[BaseProvider]:
        normalized = symbol.strip().upper()
        supported = [provider for provider in self.providers if provider.supports_symbol(normalized)]
        korean = normalized.endswith(".KS") or normalized.endswith(".KQ") or normalized[:6].isdigit()

        if not korean:
            return supported

        # KIS gets first shot at Korean tickers when present; otherwise preserve
        # configured order.  This keeps the rule declarative without hard-coding
        # imports here.
        return sorted(supported, key=lambda provider: 0 if provider.name == "kis" else 1)

    async def _try(self, symbol: str, method: str, call: Callable[[BaseProvider], Awaitable[T]]) -> T:
        errors: list[str] = []
        for provider in self._order_for(symbol):
            provider_metrics.record_attempt(provider.name, method)
            try:
                result = await call(provider)
                provider_metrics.record_success(provider.name, method)
                return result
            except ProviderError as exc:
                provider_metrics.record_failure(provider.name, method)
                errors.append(f"{provider.name}: {exc}")
                continue
            except Exception as exc:
                provider_metrics.record_failure(provider.name, method)
                errors.append(f"{provider.name}: unexpected {type(exc).__name__}: {exc}")
                continue
        raise DataUnavailable(symbol, method, errors)

    async def quote(self, symbol: str) -> Quote:
        return await self._try(symbol, "quote", lambda provider: provider.quote(symbol))

    async def profile(self, symbol: str) -> Profile:
        return await self._try(symbol, "profile", lambda provider: provider.profile(symbol))

    async def fundamentals(self, symbol: str, period: str = "annual") -> Fundamentals:
        return await self._try(symbol, "fundamentals", lambda provider: provider.fundamentals(symbol, period))

    async def history(self, symbol: str, range: str = "1y") -> OHLCV:
        return await self._try(symbol, "history", lambda provider: provider.history(symbol, range))

    async def news(self, symbols: list[str], limit: int = 20) -> list[Article]:
        key = ",".join(symbols)
        return await self._try(key, "news", lambda provider: provider.news(symbols, limit))

    async def peers(self, symbol: str) -> list[str]:
        return await self._try(symbol, "peers", lambda provider: provider.peers(symbol))

    async def segments(self, symbol: str) -> list[Segment]:
        return await self._try(symbol, "segments", lambda provider: provider.segments(symbol))

    async def holders(self, symbol: str) -> HoldersData:
        return await self._try(symbol, "holders", lambda provider: provider.holders(symbol))

    async def earnings_calendar(self, symbol: str) -> list[EarningEvent]:
        return await self._try(symbol, "earnings_calendar", lambda provider: provider.earnings_calendar(symbol))
