"""Smoke tests that keep the FastAPI shell safe during refactors."""

from fastapi.testclient import TestClient

from server.core.providers.base import DataUnavailable
from server.core.data_gateway import Fundamentals, HoldersData, Profile, Quote
from server.main import app


EXPECTED_PREFIXES = [
    "/api/analysis",
    "/api/chat",
    "/api/calendar",
    "/api/crypto",
    "/api/copilot",
    "/api/credentials",
    "/api/dart",
    "/api/earnings",
    "/api/edgar",
    "/api/edinet",
    "/api/estimates",
    "/api/financials",
    "/api/fmp",
    "/api/fx",
    "/api/insider",
    "/api/macro",
    "/api/market",
    "/api/markets",
    "/api/news",
    "/api/portfolio",
    "/api/research",
    "/api/screener",
    "/api/technical",
    "/api/valuation",
]


def test_health_endpoint_returns_ok() -> None:
    with TestClient(app) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_openapi_contains_all_router_prefixes() -> None:
    with TestClient(app) as client:
        response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"].keys()
    for prefix in EXPECTED_PREFIXES:
        assert any(path.startswith(prefix) for path in paths), prefix


def test_lightweight_asset_type_endpoint(monkeypatch) -> None:
    from server.routers import market_data

    monkeypatch.setattr(market_data, "detect_asset_type", lambda ticker: market_data.AssetType.EQUITY)

    with TestClient(app) as client:
        response = client.get("/api/market/asset-type/AAPL")

    assert response.status_code == 200
    assert response.json() == {"ticker": "AAPL", "asset_type": "equity"}


def test_quote_endpoint_can_use_gateway_flag(monkeypatch) -> None:
    from server.routers import market_data

    class FakeGateway:
        async def quote(self, ticker: str) -> Quote:
            return Quote(symbol=ticker.upper(), price=123.45, change_pct=1.234, source="fake")

    monkeypatch.setattr(market_data.core_flags, "new_data_gateway_enabled", lambda: True)
    monkeypatch.setattr(market_data, "get_data_gateway", lambda: FakeGateway())

    with TestClient(app) as client:
        response = client.get("/api/market/quote/AAPL")

    assert response.status_code == 200
    assert response.json() == {"ticker": "AAPL", "current_price": 123.45, "change_pct": 1.23}


def test_quote_endpoint_gateway_failure_degrades(monkeypatch) -> None:
    from server.routers import market_data

    class FailingGateway:
        async def quote(self, ticker: str) -> Quote:
            raise DataUnavailable(ticker, "quote")

    monkeypatch.setattr(market_data.core_flags, "new_data_gateway_enabled", lambda: True)
    monkeypatch.setattr(market_data, "get_data_gateway", lambda: FailingGateway())

    with TestClient(app) as client:
        response = client.get("/api/market/quote/AAPL")

    assert response.status_code == 200
    assert response.json() == {"ticker": "AAPL", "current_price": None, "change_pct": None}


def test_peer_endpoint_returns_gateway_matrix(monkeypatch) -> None:
    from server.routers import market_data

    class FakeGateway:
        async def profile(self, ticker: str) -> Profile:
            return Profile(symbol=ticker.upper(), sector="Technology", industry="Semiconductors", source="fake")

        async def peers(self, ticker: str) -> list[str]:
            return ["AMD", "NVDA"]

        async def fundamentals(self, ticker: str, period: str = "ttm") -> Fundamentals:
            rows = {
                "NVDA": Fundamentals(
                    symbol="NVDA",
                    period=period,
                    name="NVIDIA",
                    market_cap=3_000_000_000_000,
                    pe=40.0,
                    ev_ebitda=32.0,
                    roic=0.45,
                    gross_margin=0.72,
                    revenue_growth=0.6,
                    source="fake",
                ),
                "AMD": Fundamentals(
                    symbol="AMD",
                    period=period,
                    name="AMD",
                    market_cap=250_000_000_000,
                    pe=35.0,
                    ev_ebitda=25.0,
                    roic=0.12,
                    gross_margin=0.5,
                    revenue_growth=0.1,
                    source="fake",
                ),
            }
            return rows[ticker.upper()]

    monkeypatch.setattr(market_data, "get_data_gateway", lambda: FakeGateway())

    with TestClient(app) as client:
        response = client.get("/api/market/peers/NVDA?metrics=pe,ev_ebitda,roic,gross_margin")

    assert response.status_code == 200
    data = response.json()
    assert data["primary"] == "NVDA"
    assert data["peer_symbols"] == ["AMD"]
    assert data["metrics"] == ["pe", "ev_ebitda", "roic", "gross_margin"]
    assert [row["ticker"] for row in data["matrix"]] == ["NVDA", "AMD"]
    assert data["averages"]["pe"] == 37.5


def test_transcript_delta_degrades_without_fmp_key(monkeypatch) -> None:
    monkeypatch.delenv("FMP_API_KEY", raising=False)

    with TestClient(app) as client:
        response = client.get("/api/earnings/NVDA/transcript-delta")

    assert response.status_code == 200
    assert response.json()["available"] is False


def test_calendar_degrades_without_fmp_key(monkeypatch) -> None:
    monkeypatch.delenv("FMP_API_KEY", raising=False)

    with TestClient(app) as client:
        response = client.get("/api/calendar/economic")

    assert response.status_code == 200
    data = response.json()
    assert data["available"] is False
    assert data["grouped"] == {}


def test_financial_statement_table_uses_gateway(monkeypatch) -> None:
    from server.routers import financials

    class FakeGateway:
        async def financials(self, ticker: str, statement: str = "income", period: str = "annual") -> dict:
            return {
                "ticker": ticker.upper(),
                "statement": statement,
                "period": period,
                "source": "fake",
                "periods": ["2025", "2024"],
                "line_items": {"revenue": [120.0, 100.0]},
            }

    monkeypatch.setattr(financials, "get_data_gateway", lambda: FakeGateway())

    with TestClient(app) as client:
        response = client.get("/api/financials/AAPL/table?statement=income&period=annual")

    assert response.status_code == 200
    assert response.json()["line_items"]["revenue"] == [120.0, 100.0]


def test_ownership_endpoint_normalizes_gateway_rows(monkeypatch) -> None:
    from server.routers import market_data

    class FakeGateway:
        async def holders(self, ticker: str) -> HoldersData:
            return HoldersData(
                symbol=ticker.upper(),
                institutions=[
                    {"Holder": "Vanguard", "Shares": 1000, "pctHeld": 0.12, "Value": 250000, "Change": 25},
                ],
                insiders=[
                    {"Name": "CEO Example", "Shares Owned Directly": 100, "change": -5},
                ],
                source="fake",
            )

    monkeypatch.setattr(market_data, "get_data_gateway", lambda: FakeGateway())

    with TestClient(app) as client:
        response = client.get("/api/market/ownership/NVDA")

    assert response.status_code == 200
    data = response.json()
    assert data["available"] is True
    assert data["institutional_pct"] == 12.0
    assert data["institutions"][0]["name"] == "Vanguard"
    assert data["insiders"][0]["name"] == "CEO Example"
