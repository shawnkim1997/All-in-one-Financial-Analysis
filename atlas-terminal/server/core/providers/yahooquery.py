"""YahooQuery provider for the ATLAS Data Gateway."""

from __future__ import annotations

from typing import Any

from server.core.data_gateway import Profile, Quote
from server.core.providers.base import BaseProvider, ProviderError


class YahooQueryProvider(BaseProvider):
    name = "yahooquery"

    def _ticker(self, symbol: str) -> Any:
        try:
            from yahooquery import Ticker
        except Exception as exc:  # pragma: no cover - dependency is expected in app runtime
            raise ProviderError(f"yahooquery import failed: {exc}") from exc
        return Ticker(symbol.strip().upper())

    async def quote(self, symbol: str) -> Quote:
        def fetch() -> Quote:
            normalized = symbol.strip().upper()
            data = self._ticker(normalized).price
            row = data.get(normalized) if isinstance(data, dict) else None
            if not isinstance(row, dict):
                raise ProviderError("missing price payload")
            price = row.get("regularMarketPrice") or row.get("postMarketPrice")
            prev = row.get("regularMarketPreviousClose")
            change = (price - prev) if isinstance(price, (int, float)) and isinstance(prev, (int, float)) else None
            change_pct = (change / prev * 100) if change is not None and prev else None
            return Quote(
                symbol=normalized,
                price=float(price) if isinstance(price, (int, float)) else None,
                currency=row.get("currency"),
                change=change,
                change_pct=change_pct,
                source=self.name,
                raw=row,
            )

        return await self._to_thread(fetch)

    async def profile(self, symbol: str) -> Profile:
        def fetch() -> Profile:
            normalized = symbol.strip().upper()
            ticker = self._ticker(normalized)
            profiles = ticker.asset_profile
            row = profiles.get(normalized) if isinstance(profiles, dict) else None
            if not isinstance(row, dict):
                raise ProviderError("missing asset_profile payload")
            return Profile(
                symbol=normalized,
                name=row.get("longName") or row.get("shortName"),
                description=row.get("longBusinessSummary"),
                sector=row.get("sector"),
                industry=row.get("industry"),
                country=row.get("country"),
                exchange=row.get("exchange"),
                website=row.get("website"),
                employees=row.get("fullTimeEmployees"),
                source=self.name,
                raw=row,
            )

        return await self._to_thread(fetch)
