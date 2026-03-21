"""Tests for TikTokCollector."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.collectors.tiktok import TikTokCollector
from app.collectors.tiktok_mock import TikTokMockCollector

# ---------------------------------------------------------------------------
# Sample API response fixture
# ---------------------------------------------------------------------------

_API_RESPONSE = {
    "code": 0,
    "msg": "OK",
    "data": {
        "list": [
            {"hashtag_name": "fyp", "video_views": 50_000_000_000, "publish_cnt": 5_000_000},
            {"hashtag_name": "viral", "video_views": 30_000_000_000, "publish_cnt": 3_000_000},
            {"hashtag_name": "trending", "video_views": 20_000_000_000, "publish_cnt": 2_000_000},
            {"hashtag_name": "ai", "video_views": 10_000_000_000, "publish_cnt": 1_000_000},
            {"hashtag_name": "dance", "video_views": 8_000_000_000, "publish_cnt": 800_000},
        ]
    },
}


_FAKE_COOKIE = "csrftoken=testtoken; sessionid=abc123"


def _patch_httpx(response_body: dict = _API_RESPONSE):
    """Patch httpx.AsyncClient AND settings.tiktok_cookie for collector tests."""
    from contextlib import ExitStack
    from unittest.mock import patch as _patch

    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = response_body
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(return_value=mock_resp)

    class _Combined:
        def __enter__(self):
            self._stack = ExitStack()
            self._stack.enter_context(_patch("httpx.AsyncClient", return_value=mock_client))
            self._stack.enter_context(
                _patch("app.collectors.tiktok.settings.tiktok_cookie", _FAKE_COOKIE)
            )
            return mock_client

        def __exit__(self, *args):
            self._stack.__exit__(*args)

    return _Combined()


# ---------------------------------------------------------------------------
# Unit tests: TikTokCollector.collect (mocked HTTP)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_collect_returns_list():
    with _patch_httpx():
        results = await TikTokCollector().collect()
    assert isinstance(results, list)
    assert len(results) > 0


@pytest.mark.asyncio
async def test_collect_platform_is_tiktok():
    with _patch_httpx():
        results = await TikTokCollector().collect()
    assert all(r["platform"] == "tiktok" for r in results)


@pytest.mark.asyncio
async def test_collect_item_schema():
    with _patch_httpx():
        results = await TikTokCollector().collect()
    required = {"platform", "keyword", "rank", "heat_score", "url", "collected_at"}
    for item in results:
        assert required <= set(item.keys())


@pytest.mark.asyncio
async def test_collect_keyword_has_hash_prefix():
    with _patch_httpx():
        results = await TikTokCollector().collect()
    assert all(r["keyword"].startswith("#") for r in results)


@pytest.mark.asyncio
async def test_collect_keyword_matches_hashtag_name():
    with _patch_httpx():
        results = await TikTokCollector().collect()
    keywords = [r["keyword"] for r in results]
    assert "#fyp" in keywords
    assert "#viral" in keywords


@pytest.mark.asyncio
async def test_collect_heat_score_uses_video_views():
    with _patch_httpx():
        results = await TikTokCollector().collect()
    top = next(r for r in results if r["keyword"] == "#fyp")
    assert top["heat_score"] == 50_000_000_000.0


@pytest.mark.asyncio
async def test_collect_rank_is_zero_based():
    with _patch_httpx():
        results = await TikTokCollector().collect()
    assert results[0]["rank"] == 0
    assert results[1]["rank"] == 1


@pytest.mark.asyncio
async def test_collect_url_points_to_tiktok_tag():
    with _patch_httpx():
        results = await TikTokCollector().collect()
    for r in results:
        assert "tiktok.com/tag/" in r["url"]


@pytest.mark.asyncio
async def test_collect_collected_at_is_datetime():
    with _patch_httpx():
        results = await TikTokCollector().collect()
    for r in results:
        assert isinstance(r["collected_at"], datetime)


@pytest.mark.asyncio
async def test_collect_paginates_and_deduplicates():
    big_list = [
        {"hashtag_name": f"tag{i}", "video_views": 1_000_000 - i, "publish_cnt": 100}
        for i in range(25)
    ]
    body = {"code": 0, "msg": "OK", "data": {"list": big_list}}
    with _patch_httpx(body):
        results = await TikTokCollector().collect()
    # Mock returns same 25 tags for every region/page; after dedup = 25 unique
    assert len(results) == 25


@pytest.mark.asyncio
async def test_collect_returns_empty_on_api_error_code():
    error_body = {"code": 40001, "msg": "Unauthorized", "data": {}}
    with _patch_httpx(error_body):
        results = await TikTokCollector().collect()
    assert results == []


@pytest.mark.asyncio
async def test_collect_skips_empty_hashtag_name():
    body = {
        "code": 0,
        "msg": "OK",
        "data": {
            "list": [
                {"hashtag_name": "", "video_views": 1_000_000, "publish_cnt": 100},
                {"hashtag_name": "fyp", "video_views": 5_000_000, "publish_cnt": 500},
            ]
        },
    }
    with _patch_httpx(body):
        results = await TikTokCollector().collect()
    assert len(results) == 1
    assert results[0]["keyword"] == "#fyp"


@pytest.mark.asyncio
async def test_collect_custom_countries():
    collector = TikTokCollector(countries=("JP", "BR"))
    captured: list[str] = []

    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = _API_RESPONSE
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    async def fake_get(url, **kwargs):
        captured.append(url)
        return mock_resp

    mock_client.get = fake_get
    with (
        patch("httpx.AsyncClient", return_value=mock_client),
        patch("app.collectors.tiktok.settings.tiktok_cookie", _FAKE_COOKIE),
    ):
        await collector.collect()

    # 2 countries × 2 pages = 4 requests
    assert len(captured) == 4
    assert any("country_code=JP" in u for u in captured)
    assert any("country_code=BR" in u for u in captured)


@pytest.mark.asyncio
async def test_collect_returns_empty_when_cookie_not_configured():
    """Without TIKTOK_COOKIE configured, collector returns [] without hitting network."""
    with patch("app.collectors.tiktok.settings.tiktok_cookie", ""):
        results = await TikTokCollector().collect()
    assert results == []


@pytest.mark.asyncio
async def test_collect_sends_csrf_token_header():
    """csrftoken value from cookie is forwarded as X-CSRFToken header."""
    captured_headers: dict = {}

    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = _API_RESPONSE

    inner_client = AsyncMock()
    inner_client.get = AsyncMock(return_value=mock_resp)

    class FakeClient:
        def __init__(self, headers=None, **kwargs):
            captured_headers.update(headers or {})

        async def __aenter__(self):
            return inner_client

        async def __aexit__(self, *args):
            pass

    with (
        patch("httpx.AsyncClient", FakeClient),
        patch("app.collectors.tiktok.settings.tiktok_cookie", _FAKE_COOKIE),
    ):
        await TikTokCollector().collect()

    assert captured_headers.get("X-CSRFToken") == "testtoken"


@pytest.mark.asyncio
async def test_collect_falls_back_to_publish_cnt_when_no_views():
    body = {
        "code": 0,
        "msg": "OK",
        "data": {
            "list": [
                {"hashtag_name": "noviews", "video_views": None, "publish_cnt": 999_000},
            ]
        },
    }
    with _patch_httpx(body):
        results = await TikTokCollector().collect()
    assert results[0]["heat_score"] == 999_000.0


# ---------------------------------------------------------------------------
# Unit tests: TikTokMockCollector
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mock_collector_returns_list():
    results = await TikTokMockCollector().collect()
    assert isinstance(results, list)
    assert len(results) == 5


@pytest.mark.asyncio
async def test_mock_collector_platform_is_tiktok():
    results = await TikTokMockCollector().collect()
    assert all(r["platform"] == "tiktok" for r in results)


@pytest.mark.asyncio
async def test_mock_collector_keywords_have_hash():
    results = await TikTokMockCollector().collect()
    assert all(r["keyword"].startswith("#") for r in results)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


def test_tiktok_registered_in_registry():
    from app.collectors.registry import registry

    assert "tiktok" in registry.list_platforms()
