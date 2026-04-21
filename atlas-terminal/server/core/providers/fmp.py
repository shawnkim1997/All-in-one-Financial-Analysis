"""Financial Modeling Prep provider for the ATLAS Data Gateway."""

from __future__ import annotations

from server.core.data_gateway import Profile, Quote, Segment
from server.core.providers.base import BaseProvider, ProviderError, ProviderNotConfigured, ProviderNotImplemented
from server.services import fmp_client


class FMPProvider(BaseProvider):
    name = "fmp"

    async def _get_json(self, path: str, params: dict[str, object]) -> object:
        if not fmp_client.fmp_is_configured():
            raise ProviderNotConfigured("FMP_API_KEY is not set")
        data = await fmp_client._fmp_get_json(path, params)  # noqa: SLF001 - temporary bridge until public FMP gateway helpers exist.
        if data is None:
            raise ProviderError(f"empty response for {path}")
        return data

    async def quote(self, symbol: str) -> Quote:
        normalized = symbol.strip().upper()
        data = await self._get_json(f"/quote/{normalized}", {})
        row = data[0] if isinstance(data, list) and data else None
        if not isinstance(row, dict):
            raise ProviderError("missing quote row")
        price = row.get("price")
        return Quote(
            symbol=normalized,
            price=float(price) if isinstance(price, (int, float)) else None,
            change=row.get("change"),
            change_pct=row.get("changesPercentage"),
            source=self.name,
            raw=row,
        )

    async def profile(self, symbol: str) -> Profile:
        normalized = symbol.strip().upper()
        data = await self._get_json(f"/profile/{normalized}", {})
        row = data[0] if isinstance(data, list) and data else None
        if not isinstance(row, dict):
            raise ProviderError("missing profile row")
        hq = ", ".join(str(row.get(key)) for key in ("city", "state", "country") if row.get(key))
        return Profile(
            symbol=normalized,
            name=row.get("companyName"),
            description=row.get("description"),
            sector=row.get("sector"),
            industry=row.get("industry"),
            country=row.get("country"),
            exchange=row.get("exchangeShortName") or row.get("exchange"),
            currency=row.get("currency"),
            website=row.get("website"),
            employees=row.get("fullTimeEmployees"),
            market_cap=row.get("mktCap"),
            source=self.name,
            raw={**row, "hq": hq},
        )

    async def segments(self, symbol: str) -> list[Segment]:
        raise ProviderNotImplemented("FMP segments parser is planned for Phase 1.4")
