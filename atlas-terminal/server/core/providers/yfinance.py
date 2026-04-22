"""yfinance provider for the ATLAS Data Gateway."""

from __future__ import annotations

from datetime import date
from typing import Any

from server.core.data_gateway import Fundamentals, HoldersData, OHLCV, OHLCVBar, Profile, Quote
from server.core.providers.base import BaseProvider, ProviderError
from server.utils.peer_universe import peer_symbols_for_profile


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
                name=info.get("shortName") or info.get("longName"),
                market_cap=info.get("marketCap"),
                revenue=info.get("totalRevenue"),
                revenue_growth=info.get("revenueGrowth"),
                gross_profit=info.get("grossProfits"),
                gross_margin=info.get("grossMargins"),
                operating_income=info.get("operatingMargins"),
                net_income=info.get("netIncomeToCommon"),
                ebitda=info.get("ebitda"),
                free_cash_flow=info.get("freeCashflow"),
                total_debt=info.get("totalDebt"),
                cash=info.get("totalCash"),
                shares=info.get("sharesOutstanding"),
                pe=info.get("trailingPE") or info.get("forwardPE"),
                pb=info.get("priceToBook"),
                ps=info.get("priceToSalesTrailing12Months"),
                ev_ebitda=info.get("enterpriseToEbitda"),
                roic=info.get("returnOnInvestedCapital") or info.get("returnOnCapital"),
                source=self.name,
                raw=info,
            )

        return await self._to_thread(fetch)

    async def peers(self, symbol: str) -> list[str]:
        def fetch() -> list[str]:
            normalized = symbol.strip().upper()
            info = self._ticker(normalized).info or {}
            syms = peer_symbols_for_profile(
                normalized,
                str(info.get("sector") or ""),
                str(info.get("industry") or ""),
                cap=6,
            )
            return [peer for peer in syms if peer != normalized]

        return await self._to_thread(fetch)

    async def financials(self, symbol: str, statement: str = "income", period: str = "annual") -> dict[str, Any]:
        def fetch() -> dict[str, Any]:
            import pandas as pd

            normalized = symbol.strip().upper()
            ticker = self._ticker(normalized)
            statement_key = statement.strip().lower()
            quarterly = period.strip().lower().startswith("q")
            if statement_key == "income":
                df = ticker.quarterly_income_stmt if quarterly else ticker.income_stmt
            elif statement_key == "balance":
                df = ticker.quarterly_balance_sheet if quarterly else ticker.balance_sheet
            elif statement_key in {"cashflow", "cash_flow"}:
                df = ticker.quarterly_cashflow if quarterly else ticker.cashflow
            else:
                raise ProviderError(f"unsupported statement: {statement}")
            if df is None or not isinstance(df, pd.DataFrame) or df.empty:
                raise ProviderError("missing financial statement dataframe")
            sliced = df.iloc[:, :5]
            periods = [str(col)[:10] for col in sliced.columns]
            line_items: dict[str, list[float | None]] = {}
            for idx, row in sliced.iterrows():
                values: list[float | None] = []
                for value in row.tolist():
                    try:
                        if pd.isna(value):
                            values.append(None)
                        else:
                            values.append(float(value))
                    except (TypeError, ValueError):
                        values.append(None)
                line_items[str(idx).replace(" ", "")] = values
            return {
                "ticker": normalized,
                "statement": statement_key,
                "period": "quarter" if quarterly else "annual",
                "source": self.name,
                "periods": periods,
                "line_items": line_items,
            }

        return await self._to_thread(fetch)

    async def holders(self, symbol: str) -> HoldersData:
        def fetch() -> HoldersData:
            import pandas as pd

            normalized = symbol.strip().upper()
            ticker = self._ticker(normalized)
            institutions: list[dict[str, Any]] = []
            insiders: list[dict[str, Any]] = []
            inst_df = getattr(ticker, "institutional_holders", None)
            if isinstance(inst_df, pd.DataFrame) and not inst_df.empty:
                institutions = inst_df.where(inst_df.notna(), None).to_dict(orient="records")
            insider_df = getattr(ticker, "insider_roster_holders", None)
            if isinstance(insider_df, pd.DataFrame) and not insider_df.empty:
                insiders = insider_df.where(insider_df.notna(), None).to_dict(orient="records")
            return HoldersData(symbol=normalized, institutions=institutions[:25], insiders=insiders[:25], source=self.name)

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
