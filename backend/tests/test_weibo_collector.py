"""Unit tests for WeiboCollector — real HTTP calls mocked via unittest.mock."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.collectors.weibo import WeiboCollector

_MOCK_WEIBO_RESPONSE = {
    "ok": 1,
    "data": {
        "realtime": [
            {"word": "话题A", "num": 9876543, "rank": 0},
            {"word": "话题B", "num": 5432100, "rank": 1},
            {"word": "话题C", "num": 1234567, "rank": 2},
        ]
    },
}


def _make_mock_response(json_data: dict, status_code: int = 200):
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.json.return_value = json_data
    mock_resp.raise_for_status = MagicMock()
    return mock_resp


@pytest.mark.asyncio
async def test_weibo_collector_returns_list():
    mock_resp = _make_mock_response(_MOCK_WEIBO_RESPONSE)
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.collectors.weibo.httpx.AsyncClient", return_value=mock_client):
        collector = WeiboCollector()
        results = await collector.collect()

    assert isinstance(results, list)
    assert len(results) == 3


@pytest.mark.asyncio
async def test_weibo_collector_item_schema():
    mock_resp = _make_mock_response(_MOCK_WEIBO_RESPONSE)
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.collectors.weibo.httpx.AsyncClient", return_value=mock_client):
        collector = WeiboCollector()
        results = await collector.collect()

    required = {"platform", "keyword", "rank", "heat_score", "url", "collected_at"}
    for item in results:
        assert required <= set(item.keys())


@pytest.mark.asyncio
async def test_weibo_collector_platform_is_weibo():
    mock_resp = _make_mock_response(_MOCK_WEIBO_RESPONSE)
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.collectors.weibo.httpx.AsyncClient", return_value=mock_client):
        collector = WeiboCollector()
        results = await collector.collect()

    assert all(r["platform"] == "weibo" for r in results)


@pytest.mark.asyncio
async def test_weibo_collector_keyword_matches_word():
    mock_resp = _make_mock_response(_MOCK_WEIBO_RESPONSE)
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.collectors.weibo.httpx.AsyncClient", return_value=mock_client):
        collector = WeiboCollector()
        results = await collector.collect()

    words = [r["keyword"] for r in results]
    assert words == ["话题A", "话题B", "话题C"]


@pytest.mark.asyncio
async def test_weibo_collector_heat_score_from_num():
    mock_resp = _make_mock_response(_MOCK_WEIBO_RESPONSE)
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.collectors.weibo.httpx.AsyncClient", return_value=mock_client):
        collector = WeiboCollector()
        results = await collector.collect()

    assert results[0]["heat_score"] == 9876543.0
    assert results[1]["heat_score"] == 5432100.0


@pytest.mark.asyncio
async def test_weibo_collector_collected_at_is_datetime():
    mock_resp = _make_mock_response(_MOCK_WEIBO_RESPONSE)
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.collectors.weibo.httpx.AsyncClient", return_value=mock_client):
        collector = WeiboCollector()
        results = await collector.collect()

    for item in results:
        assert isinstance(item["collected_at"], datetime)


@pytest.mark.asyncio
async def test_weibo_collector_empty_realtime():
    mock_resp = _make_mock_response({"ok": 1, "data": {"realtime": []}})
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.collectors.weibo.httpx.AsyncClient", return_value=mock_client):
        collector = WeiboCollector()
        results = await collector.collect()

    assert results == []


@pytest.mark.asyncio
async def test_weibo_collector_truncates_at_50():
    realtime = [{"word": f"话题{i}", "num": i * 1000, "rank": i} for i in range(60)]
    mock_resp = _make_mock_response({"ok": 1, "data": {"realtime": realtime}})
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.collectors.weibo.httpx.AsyncClient", return_value=mock_client):
        collector = WeiboCollector()
        results = await collector.collect()

    assert len(results) == 50
