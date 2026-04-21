"""yfinance provider for the ATLAS Data Gateway."""

from __future__ import annotations

from datetime import date
from typing import Any

from server.core.data_gateway import Fundamentals, OHLCV, OHLCVBar, Profile, Quote
from server.core.providers.base import BaseProvider, ProviderError


class YFinanceProvider(BaseProvider):
    name = "yfinance"

    def _ticker(self, symbol: str) -> Any:
        try:
            import yfinance as yf
        except Exception as exc:  # pragma: no cover - dependency is expected in app runtime
            raise ProviderError(f"yfinance import failed: {exc}") from exc
        return yf.Ticker(symbol.strip().upper())

    async def quote(self, symbol: str) -> Quote:
        def fetch() -> Quote:
            ticker = self._ticker(symbol)
            info = ticker.info or {}
            price = info.get("regularMarketPrice") or info.get("currentPrice") or info.get("previousClose")
            prev = info.get("regularMarketPreviousClose") or info.get("previousClose")
            change = (price - prev) if isinstance(price, (int, float)) and isinstance(prev, (int, float)) else None
            change_pct = (change / prev * 100) if change is not None and prev else None
            return Quote(
                symbol=symbol.upper(),
                price=float(price) if isinstance(price, (int, float)) else None,
                currency=info.get("currency"),
                change=change,
                change_pct=change_pct,
                source=self.name,
                raw=info,
            )

        return await self._to_thread(fetch)

    async def profile(self, symbol: str) -> Profile:
        def fetch() -> Profile:
            info = self._ticker(symbol).info or {}
            return Profile(
                symbol=symbol.upper(),
                name=info.get("longName") or info.get("shortName"),
                description=info.get("longBusinessSummary"),
                sector=info.get("sector"),
                industry=info.get("industry"),
                country=info.get("country"),
                exchange=info.get("exchange"),
                currency=info.get("currency"),
                website=info.get("website"),
                employees=info.get("fullTimeEmployees"),
                market_cap=info.get("marketCap"),
                source=self.name,
                raw=info,
            )

        return await self._to_thread(fetch)

    async def fundamentals(self, symbol: str, period: str = "annual") -> Fundamentals:
        def fetch() -> Fundamentals:
            ticker = self._ticker(symbol)
            info = ticker.info or {}
            return Fundamentals(
                symbol=symbol.upper(),
                period=period,
                revenue=info.get("totalRevenue"),
                gross_profit=info.get("grossProfits"),
                operating_income=info.get("operatingMargins"),
                net_income=info.get("netIncomeToCommon"),
                ebitda=info.get("ebitda"),
                free_cash_flow=info.get("freeCashflow"),
                total_debt=info.get("totalDebt"),
                cash=info.get("totalCash"),
                shares=info.get("sharesOutstanding"),
                source=self.name,
                raw=info,
            )

        return await self._to_thread(fetch)

    async def history(self, symbol: str, range: str = "1y") -> OHLCV:
        def fetch() -> OHLCV:
            hist = self._ticker(symbol).history(period=range)
            bars: list[OHLCVBar] = []
            for idx, row in hist.iterrows():
                idx_date = idx.date() if hasattr(idx, "date") else date.fromisoformat(str(idx)[:10])
                bars.append(
                    OHLCVBar(
                        date=idx_date,
                        open=float(row["Open"]) if "Open" in row else None,
                        high=float(row["High"]) if "High" in row else None,
                        low=float(row["Low"]) if "Low" in row else None,
                        close=float(row["Close"]) if "Close" in row else None,
                        volume=float(row["Volume"]) if "Volume" in row else None,
                    )
                )
            return OHLCV(symbol=symbol.upper(), range=range, bars=bars, source=self.name)

        return await self._to_thread(fetch)
