"""Tests for DailyHot collectors."""

from __future__ import annotations

import json

import httpx
import pytest

from app.collectors.dailyhot import ZhihuCollector, BilibiliCollector, Kr36Collector


def _mock_response(data: list[dict], name: str = "zhihu") -> dict:
    return {"code": 200, "name": name, "total": len(data), "data": data}


@pytest.mark.asyncio
async def test_zhihu_collector_success(monkeypatch):
    """ZhihuCollector should parse DailyHotApi response correctly."""
    payload = _mock_response(
        [
            {"title": "热搜话题1", "hot": 5000000, "url": "https://zhihu.com/q/1"},
            {"title": "热搜话题2", "hot": 3000000, "url": "https://zhihu.com/q/2"},
            {"title": "", "hot": 100},  # empty title should be skipped
        ]
    )

    async def mock_get(self, url, **kwargs):
        return httpx.Response(200, json=payload, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    collector = ZhihuCollector()
    results = await collector.collect()

    assert len(results) == 2
    assert results[0]["platform"] == "zhihu"
    assert results[0]["keyword"] == "热搜话题1"
    assert results[0]["rank"] == 1
    assert results[0]["heat_score"] == 5000000.0
    assert results[0]["url"] == "https://zhihu.com/q/1"
    assert results[1]["rank"] == 2


@pytest.mark.asyncio
async def test_bilibili_collector_success(monkeypatch):
    """BilibiliCollector should work with the same DailyHot format."""
    payload = _mock_response(
        [{"title": "B站视频", "hot": 1000000, "url": "https://b23.tv/xxx"}],
        name="bilibili",
    )

    async def mock_get(self, url, **kwargs):
        return httpx.Response(200, json=payload, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    collector = BilibiliCollector()
    results = await collector.collect()

    assert len(results) == 1
    assert results[0]["platform"] == "bilibili"
    assert results[0]["keyword"] == "B站视频"


@pytest.mark.asyncio
async def test_collector_non_200_code(monkeypatch):
    """Should return empty list when API returns non-200 code."""
    payload = {"code": 500, "message": "error"}

    async def mock_get(self, url, **kwargs):
        return httpx.Response(200, json=payload, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    collector = Kr36Collector()
    results = await collector.collect()
    assert results == []


@pytest.mark.asyncio
async def test_collector_http_error(monkeypatch):
    """Should raise on HTTP errors (letting retry logic handle it)."""

    async def mock_get(self, url, **kwargs):
        resp = httpx.Response(500, request=httpx.Request("GET", url))
        resp.raise_for_status()
        return resp

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    collector = ZhihuCollector()
    with pytest.raises(httpx.HTTPStatusError):
        await collector.collect()


@pytest.mark.asyncio
async def test_collector_caps_at_50(monkeypatch):
    """Should only return up to 50 items."""
    payload = _mock_response(
        [{"title": f"Item {i}", "hot": i * 100, "url": f"https://x.com/{i}"} for i in range(100)]
    )

    async def mock_get(self, url, **kwargs):
        return httpx.Response(200, json=payload, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    collector = ZhihuCollector()
    results = await collector.collect()
    assert len(results) == 50
