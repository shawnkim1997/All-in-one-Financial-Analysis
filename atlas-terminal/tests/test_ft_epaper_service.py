import asyncio
from datetime import date, datetime, timedelta, timezone

from fastapi.testclient import TestClient

from server.main import app
from server.routers import daily_news
from server.services import ft_epaper_service


def test_fetch_headlines_filters_to_requested_date(monkeypatch) -> None:
    target = date(2026, 4, 23)
    store: dict[str, object] = {}

    async def fake_cache_get(key: str):
        return store.get(key)

    async def fake_cache_set(key: str, value, ttl: int = 86400):
        store[key] = value

    async def fake_feed_entries(client, section: str, url: str):
        return [
            {
                "url": f"https://www.ft.com/content/{section.lower()}-today",
                "title_en": f"{section} Today",
                "lede_en": None,
                "section": section,
                "published_at": datetime(2026, 4, 23, 8, 0, tzinfo=timezone.utc).isoformat(),
            },
            {
                "url": f"https://www.ft.com/content/{section.lower()}-old",
                "title_en": f"{section} Old",
                "lede_en": None,
                "section": section,
                "published_at": datetime(2026, 4, 22, 8, 0, tzinfo=timezone.utc).isoformat(),
            },
        ]

    async def fake_meta(client, url: str):
        return {"lede_en": f"Meta for {url}", "image": "https://images.ft.com/example.jpg"}

    monkeypatch.setattr(ft_epaper_service.repo, "cache_get", fake_cache_get)
    monkeypatch.setattr(ft_epaper_service.repo, "cache_set", fake_cache_set)
    monkeypatch.setattr(ft_epaper_service, "_fetch_feed_entries", fake_feed_entries)
    monkeypatch.setattr(ft_epaper_service, "_fetch_article_meta", fake_meta)

    items = asyncio.run(ft_epaper_service.fetch_headlines(target, limit=10))

    assert items
    assert all(datetime.fromisoformat(item["published_at"]).date() == target for item in items)
    assert all(item["image"] == "https://images.ft.com/example.jpg" for item in items)


def test_translate_headlines_uses_cache_on_second_call(monkeypatch) -> None:
    store: dict[str, object] = {}
    gemini_calls = {"count": 0}
    item = {
        "url": "https://www.ft.com/content/test-article",
        "title_en": "Fed holds rates steady",
        "title_ko": None,
        "lede_en": "Bond yields eased after the decision.",
        "lede_ko": None,
        "section": "Markets",
        "published_at": datetime(2026, 4, 23, 7, 0, tzinfo=timezone.utc).isoformat(),
        "image": None,
    }

    async def fake_cache_get(key: str):
        return store.get(key)

    async def fake_cache_set(key: str, value, ttl: int = 86400):
        store[key] = value

    async def fake_generate_text(
        prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 1200,
        api_key: str | None = None,
    ) -> str:
        gemini_calls["count"] += 1
        return (
            '[{"url":"https://www.ft.com/content/test-article",'
            '"title_ko":"연준, 금리 동결","lede_ko":"결정 이후 채권 수익률이 완화됐다."}]'
        )

    monkeypatch.setattr(ft_epaper_service.repo, "cache_get", fake_cache_get)
    monkeypatch.setattr(ft_epaper_service.repo, "cache_set", fake_cache_set)
    monkeypatch.setattr(ft_epaper_service, "generate_text", fake_generate_text)

    first = asyncio.run(ft_epaper_service.translate_headlines([item]))
    second = asyncio.run(ft_epaper_service.translate_headlines([item]))

    assert gemini_calls["count"] == 1
    assert first[0]["title_ko"] == "연준, 금리 동결"
    assert second[0]["title_ko"] == "연준, 금리 동결"


def test_daily_news_rejects_dates_older_than_seven_days() -> None:
    too_old = (date.today() - timedelta(days=8)).isoformat()

    with TestClient(app) as client:
        response = client.get(f"/api/daily-news/{too_old}")

    assert response.status_code == 400
    assert "most recent 7 days" in response.json()["detail"]


def test_daily_news_forwards_browser_gemini_key(monkeypatch) -> None:
    captured: dict[str, object] = {}

    async def fake_fetch_headlines(target_date, limit: int = 30):
        return [
            {
                "url": "https://www.ft.com/content/test-article",
                "title_en": "Fed holds rates steady",
                "title_ko": None,
                "lede_en": "Bond yields eased after the decision.",
                "lede_ko": None,
                "section": "Markets",
                "published_at": datetime(2026, 4, 24, 7, 0, tzinfo=timezone.utc).isoformat(),
                "image": None,
            }
        ]

    async def fake_translate_headlines(items, api_key=None):
        captured["api_key"] = api_key
        return [{**items[0], "title_ko": "연준, 금리 동결", "lede_ko": "결정 이후 채권 수익률이 완화됐다."}]

    monkeypatch.setattr(daily_news, "fetch_headlines", fake_fetch_headlines)
    monkeypatch.setattr(daily_news, "translate_headlines", fake_translate_headlines)

    with TestClient(app) as client:
        response = client.get(
            "/api/daily-news/2026-04-24",
            headers={"x-gemini-api-key": "test-browser-key"},
        )

    assert response.status_code == 200
    assert captured["api_key"] == "test-browser-key"
    assert response.json()[0]["title_ko"] == "연준, 금리 동결"
