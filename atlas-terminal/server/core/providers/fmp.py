"""Financial Modeling Prep provider for the ATLAS Data Gateway."""

from __future__ import annotations

from server.core.data_gateway import HoldersData, Profile, Quote, Segment
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

    async def financials(self, symbol: str, statement: str = "income", period: str = "annual") -> dict[str, object]:
        normalized = symbol.strip().upper()
        statement_key = statement.strip().lower()
        path_map = {
            "income": "income-statement",
            "balance": "balance-sheet-statement",
            "cashflow": "cash-flow-statement",
            "cash_flow": "cash-flow-statement",
        }
        path = path_map.get(statement_key)
        if not path:
            raise ProviderError(f"unsupported statement: {statement}")
        period_key = "quarter" if period.strip().lower().startswith("q") else "annual"
        data = await self._get_json(f"/{path}/{normalized}", {"period": period_key, "limit": 5})
        rows = data if isinstance(data, list) else []
        if not rows:
            raise ProviderError("missing financial statement rows")
        periods = [str(row.get("date") or row.get("calendarYear") or idx) for idx, row in enumerate(rows)]
        line_items: dict[str, list[float | int | None]] = {}
        for row in rows:
            if not isinstance(row, dict):
                continue
            for key, value in row.items():
                if key in {"date", "symbol", "reportedCurrency", "cik", "fillingDate", "acceptedDate", "calendarYear", "period", "link", "finalLink"}:
                    continue
                if isinstance(value, (int, float)) or value is None:
                    line_items.setdefault(key, []).append(value)
        return {
            "ticker": normalized,
            "statement": statement_key,
            "period": period_key,
            "source": self.name,
            "periods": periods,
            "line_items": line_items,
        }

    async def holders(self, symbol: str) -> HoldersData:
        normalized = symbol.strip().upper()
        inst: object = []
        insider: object = []
        try:
            inst = await self._get_json(f"/institutional-holder/{normalized}", {})
        except ProviderError:
            inst = []
        try:
            insider = await self._get_json("/insider-trading", {"symbol": normalized, "limit": 25})
        except ProviderError:
            insider = []
        institutions = inst if isinstance(inst, list) else []
        insiders = insider if isinstance(insider, list) else []
        if not institutions and not insiders:
            raise ProviderError("missing holders rows")
        return HoldersData(
            symbol=normalized,
            institutions=institutions[:25],
            insiders=insiders[:25],
            source=self.name,
        )
