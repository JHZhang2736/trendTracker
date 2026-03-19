"""Integration tests for collector and trends routers."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

# ---------------------------------------------------------------------------
# POST /api/v1/collector/run
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_collector_run_returns_200(test_client: AsyncClient):
    resp = await test_client.post("/api/v1/collector/run")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_collector_run_response_schema(test_client: AsyncClient):
    resp = await test_client.post("/api/v1/collector/run")
    data = resp.json()
    assert "status" in data
    assert "records_count" in data
    assert isinstance(data["records_count"], int)


@pytest.mark.asyncio
async def test_collector_run_status_ok(test_client: AsyncClient):
    resp = await test_client.post("/api/v1/collector/run")
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_collector_run_records_count_positive(test_client: AsyncClient):
    resp = await test_client.post("/api/v1/collector/run")
    assert resp.json()["records_count"] > 0


# ---------------------------------------------------------------------------
# GET /api/v1/trends
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_trends_list_returns_200(test_client: AsyncClient):
    resp = await test_client.get("/api/v1/trends")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_trends_list_response_schema(test_client: AsyncClient):
    resp = await test_client.get("/api/v1/trends")
    data = resp.json()
    assert "total" in data
    assert "page" in data
    assert "page_size" in data
    assert "items" in data
    assert isinstance(data["items"], list)


@pytest.mark.asyncio
async def test_trends_list_item_schema(test_client: AsyncClient):
    # Seed data via collector, then check list schema
    await test_client.post("/api/v1/collector/run")
    items = (await test_client.get("/api/v1/trends")).json()["items"]
    assert len(items) > 0
    required = {"platform", "keyword", "rank", "heat_score", "url", "collected_at"}
    for item in items:
        assert required <= set(item.keys())


@pytest.mark.asyncio
async def test_trends_list_default_pagination(test_client: AsyncClient):
    resp = await test_client.get("/api/v1/trends")
    data = resp.json()
    assert data["page"] == 1
    assert data["page_size"] == 20


@pytest.mark.asyncio
async def test_trends_list_custom_pagination(test_client: AsyncClient):
    await test_client.post("/api/v1/collector/run")
    data = (await test_client.get("/api/v1/trends?page=1&page_size=2")).json()
    assert data["page"] == 1
    assert data["page_size"] == 2
    assert len(data["items"]) <= 2


@pytest.mark.asyncio
async def test_trends_list_page_out_of_range(test_client: AsyncClient):
    data = (await test_client.get("/api/v1/trends?page=999&page_size=20")).json()
    assert data["page"] == 999
    assert data["items"] == []


# ---------------------------------------------------------------------------
# GET /api/v1/trends/platforms
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_trends_platforms_returns_200(test_client: AsyncClient):
    resp = await test_client.get("/api/v1/trends/platforms")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_trends_platforms_response_schema(test_client: AsyncClient):
    resp = await test_client.get("/api/v1/trends/platforms")
    data = resp.json()
    assert "platforms" in data
    assert isinstance(data["platforms"], list)


@pytest.mark.asyncio
async def test_trends_platforms_contains_weibo(test_client: AsyncClient):
    resp = await test_client.get("/api/v1/trends/platforms")
    assert "weibo" in resp.json()["platforms"]
