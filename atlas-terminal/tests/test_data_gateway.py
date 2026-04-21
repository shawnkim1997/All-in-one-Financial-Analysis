"""Unit tests for the v2 Data Gateway foundation."""

from __future__ import annotations

import asyncio

import pytest

from server.core.cache import CachedGateway
from server.core.chained_gateway import ChainedGateway
from server.core.data_gateway import Quote
from server.core.provider_metrics import provider_metrics
from server.core.providers.base import BaseProvider, DataUnavailable, ProviderError


class FailingProvider(BaseProvider):
    name = "failing"

    async def quote(self, symbol: str) -> Quote:
        raise ProviderError("boom")


class CountingProvider(BaseProvider):
    name = "counting"

    def __init__(self) -> None:
        self.calls = 0

    async def quote(self, symbol: str) -> Quote:
        self.calls += 1
        return Quote(symbol=symbol.upper(), price=123.45, currency="USD", source=self.name)


class ExplodingProvider(BaseProvider):
    name = "exploding"

    async def quote(self, symbol: str) -> Quote:
        raise RuntimeError("sdk timeout")


def test_chained_gateway_falls_back_to_next_provider() -> None:
    provider_metrics.clear()
    gateway = ChainedGateway([FailingProvider(), CountingProvider()])

    quote = asyncio.run(gateway.quote("aapl"))

    assert quote.symbol == "AAPL"
    assert quote.price == 123.45
    assert quote.source == "counting"
    rows = provider_metrics.snapshot()
    assert {(row.provider, row.method, row.attempts, row.successes, row.failures) for row in rows} == {
        ("counting", "quote", 1, 1, 0),
        ("failing", "quote", 1, 0, 1),
    }


def test_chained_gateway_raises_after_all_providers_fail() -> None:
    gateway = ChainedGateway([FailingProvider()])

    with pytest.raises(DataUnavailable):
        asyncio.run(gateway.quote("AAPL"))


def test_chained_gateway_falls_back_after_unexpected_provider_exception() -> None:
    provider_metrics.clear()
    gateway = ChainedGateway([ExplodingProvider(), CountingProvider()])

    quote = asyncio.run(gateway.quote("AAPL"))

    assert quote.price == 123.45
    rows = provider_metrics.snapshot()
    assert any(row.provider == "exploding" and row.failures == 1 for row in rows)


def test_cached_gateway_reuses_quote_result() -> None:
    provider_metrics.clear()
    provider = CountingProvider()
    gateway = CachedGateway(ChainedGateway([provider]))

    first = asyncio.run(gateway.quote("AAPL"))
    second = asyncio.run(gateway.quote("aapl"))

    assert first is second
    assert provider.calls == 1
