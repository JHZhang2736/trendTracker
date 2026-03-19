"""Integration tests for collector and trends routers."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

# ---------------------------------------------------------------------------
# POST /api/v1/collector/run
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_collector_run_returns_200():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/collector/run")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_collector_run_response_schema():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/collector/run")
    data = resp.json()
    assert "status" in data
    assert "records_count" in data
    assert isinstance(data["records_count"], int)


@pytest.mark.asyncio
async def test_collector_run_status_ok():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/collector/run")
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_collector_run_records_count_positive():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/collector/run")
    assert resp.json()["records_count"] > 0


# ---------------------------------------------------------------------------
# GET /api/v1/trends
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_trends_list_returns_200():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/trends")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_trends_list_response_schema():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/trends")
    data = resp.json()
    assert "total" in data
    assert "page" in data
    assert "page_size" in data
    assert "items" in data
    assert isinstance(data["items"], list)


@pytest.mark.asyncio
async def test_trends_list_item_schema():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/trends")
    items = resp.json()["items"]
    assert len(items) > 0
    required = {"platform", "keyword", "rank", "heat_score", "url", "collected_at"}
    for item in items:
        assert required <= set(item.keys())


@pytest.mark.asyncio
async def test_trends_list_default_pagination():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/trends")
    data = resp.json()
    assert data["page"] == 1
    assert data["page_size"] == 20


@pytest.mark.asyncio
async def test_trends_list_custom_pagination():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/trends?page=1&page_size=2")
    data = resp.json()
    assert data["page"] == 1
    assert data["page_size"] == 2
    assert len(data["items"]) <= 2


@pytest.mark.asyncio
async def test_trends_list_page_out_of_range():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/trends?page=999&page_size=20")
    data = resp.json()
    assert data["page"] == 999
    assert data["items"] == []


# ---------------------------------------------------------------------------
# GET /api/v1/trends/platforms
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_trends_platforms_returns_200():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/trends/platforms")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_trends_platforms_response_schema():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/trends/platforms")
    data = resp.json()
    assert "platforms" in data
    assert isinstance(data["platforms"], list)


@pytest.mark.asyncio
async def test_trends_platforms_contains_weibo():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/trends/platforms")
    assert "weibo" in resp.json()["platforms"]
