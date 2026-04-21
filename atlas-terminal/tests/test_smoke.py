"""Smoke tests that keep the FastAPI shell safe during refactors."""

from fastapi.testclient import TestClient

from server.core.providers.base import DataUnavailable
from server.core.data_gateway import Quote
from server.main import app


EXPECTED_PREFIXES = [
    "/api/analysis",
    "/api/chat",
    "/api/crypto",
    "/api/copilot",
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
