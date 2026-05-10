from fastapi.testclient import TestClient

from server.main import app
from server.services.korean_stock_universe import (
    get_korean_stock_record,
    korean_stock_universe_metadata,
    load_korean_stock_universe,
    search_korean_stock_universe,
)


def test_load_korean_stock_universe_has_seed_rows() -> None:
    rows = load_korean_stock_universe()

    assert rows
    assert any(row.ticker == "005930" and row.market == "KOSPI" for row in rows)
    assert any(row.ticker == "247540" and row.market == "KOSDAQ" for row in rows)


def test_search_by_korean_name_and_alias() -> None:
    samsung = search_korean_stock_universe("삼성전자", limit=5)
    hynix = search_korean_stock_universe("sk hynix", limit=5)

    assert samsung[0].ticker == "005930"
    assert hynix[0].ticker == "000660"


def test_lookup_by_bare_and_yfinance_ticker() -> None:
    bare = get_korean_stock_record("005930")
    qualified = get_korean_stock_record("000660.KS")

    assert bare is not None
    assert bare.name_ko == "삼성전자"
    assert qualified is not None
    assert qualified.name_ko == "SK하이닉스"


def test_metadata_reports_local_artifact() -> None:
    metadata = korean_stock_universe_metadata()

    assert metadata["count"] >= 10
    assert "KOSPI" in metadata["markets"]
    assert "KOSDAQ" in metadata["markets"]
    assert str(metadata["source_path"]).endswith(".json")


def test_search_endpoint_returns_normalized_fields() -> None:
    with TestClient(app) as client:
        response = client.get("/api/market/korean-universe/search", params={"q": "하이닉스", "limit": 3})

    assert response.status_code == 200
    body = response.json()
    assert body["count"] >= 1
    item = body["items"][0]
    assert set(item) == {"ticker", "market", "name_ko", "name_en", "aliases", "yfinance_ticker"}
    assert item["ticker"] == "000660"
    assert item["yfinance_ticker"] == "000660.KS"


def test_lookup_endpoint_supports_yfinance_ticker() -> None:
    with TestClient(app) as client:
        response = client.get("/api/market/korean-universe/247540.KQ")

    assert response.status_code == 200
    body = response.json()
    assert body["item"]["ticker"] == "247540"
    assert body["item"]["market"] == "KOSDAQ"
