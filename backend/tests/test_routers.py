"""Integration tests for collector and trends routers."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.trend import Trend

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
    assert "platforms" in data
    assert isinstance(data["platforms"], list)
    for entry in data["platforms"]:
        assert "platform" in entry
        assert "count" in entry
        assert "error" in entry


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


@pytest.mark.asyncio
async def test_trends_list_sorted_by_convergence_score(test_client: AsyncClient):
    """Items must be returned in descending convergence_score order."""
    await test_client.post("/api/v1/collector/run")
    items = (await test_client.get("/api/v1/trends?page_size=100")).json()["items"]
    assert len(items) > 1
    scores = [item["convergence_score"] for item in items]
    assert scores == sorted(scores, reverse=True), "Items not sorted by convergence_score desc"


@pytest.mark.asyncio
async def test_trends_list_total_reflects_24h_window(
    test_client: AsyncClient, db_session: AsyncSession
):
    """total must count only records within the last 24 hours."""
    from datetime import timedelta

    from sqlalchemy import insert

    from app.models.trend import Trend

    # Insert one old record (outside 24h window)
    old_time = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=48)
    await db_session.execute(
        insert(Trend).values(
            platform="weibo",
            keyword="old_keyword",
            rank=0,
            heat_score=1000.0,
            url="",
            collected_at=old_time,
        )
    )
    await db_session.commit()

    await test_client.post("/api/v1/collector/run")
    data = (await test_client.get("/api/v1/trends")).json()
    # The old record must not be counted
    assert all(item["keyword"] != "old_keyword" for item in data["items"])


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


# ---------------------------------------------------------------------------
# Dedup: repeat collection within same hour should not grow record count
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_repeat_collection_same_hour_does_not_duplicate(
    test_client: AsyncClient, db_session: AsyncSession
):
    """Two collection runs within the same hour should yield the same row count."""
    await test_client.post("/api/v1/collector/run")
    count_result = await db_session.execute(select(func.count()).select_from(Trend))
    count_after_first = count_result.scalar_one()

    await test_client.post("/api/v1/collector/run")
    count_result = await db_session.execute(select(func.count()).select_from(Trend))
    count_after_second = count_result.scalar_one()

    assert count_after_second == count_after_first


@pytest.mark.asyncio
async def test_cross_hour_data_is_preserved(
    test_client: AsyncClient, db_session: AsyncSession
):
    """Records from a previous hour must survive a new collection run."""
    # Manually insert a record from 2 hours ago
    old_time = datetime.now(timezone.utc).replace(tzinfo=None, minute=0, second=0, microsecond=0)
    from datetime import timedelta
    old_time = old_time - timedelta(hours=2)
    db_session.add(
        Trend(platform="weibo", keyword="历史词", rank=0, heat_score=999.0, collected_at=old_time)
    )
    await db_session.commit()

    # Run collection (current hour) — should not touch the old record
    await test_client.post("/api/v1/collector/run")

    result = await db_session.execute(
        select(Trend).where(Trend.keyword == "历史词")
    )
    old_rows = result.scalars().all()
    assert len(old_rows) == 1, "Cross-hour historical record should not be deleted"


# ---------------------------------------------------------------------------
# DELETE /api/v1/trends/all
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_clear_all_trends_returns_200(test_client: AsyncClient):
    await test_client.post("/api/v1/collector/run")
    resp = await test_client.delete("/api/v1/trends/all")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_clear_all_trends_response_schema(test_client: AsyncClient):
    resp = await test_client.delete("/api/v1/trends/all")
    data = resp.json()
    assert "deleted" in data
    assert isinstance(data["deleted"], int)


@pytest.mark.asyncio
async def test_clear_all_trends_removes_records(
    test_client: AsyncClient, db_session: AsyncSession
):
    await test_client.post("/api/v1/collector/run")
    count_before = (
        await db_session.execute(select(func.count()).select_from(Trend))
    ).scalar_one()
    assert count_before > 0

    resp = await test_client.delete("/api/v1/trends/all")
    assert resp.json()["deleted"] == count_before

    count_after = (
        await db_session.execute(select(func.count()).select_from(Trend))
    ).scalar_one()
    assert count_after == 0


# ---------------------------------------------------------------------------
# GET /api/v1/system/config
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_system_config_returns_200(test_client: AsyncClient):
    resp = await test_client.get("/api/v1/system/config")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_system_config_schema(test_client: AsyncClient):
    data = (await test_client.get("/api/v1/system/config")).json()
    assert "ai" in data
    assert "provider" in data["ai"]
    assert "configured" in data["ai"]
    assert "tiktok" in data
    assert "configured" in data["tiktok"]
    assert "scheduler" in data
    assert "collect_cron" in data["scheduler"]
