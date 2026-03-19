"""Tests for GET /api/v1/trends/heatmap endpoint."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.trend import Trend


async def _seed_trends(db: AsyncSession, count: int = 5) -> None:
    """Insert mock trend rows into the test DB."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    for i in range(count):
        db.add(
            Trend(
                platform="weibo",
                keyword=f"话题{i}",
                rank=i,
                heat_score=float((count - i) * 1000),
                url=None,
                collected_at=now - timedelta(minutes=i * 10),
            )
        )
    await db.commit()


@pytest.mark.asyncio
async def test_heatmap_returns_200(test_client: AsyncClient):
    resp = await test_client.get("/api/v1/trends/heatmap")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_heatmap_response_schema(test_client: AsyncClient):
    resp = await test_client.get("/api/v1/trends/heatmap")
    data = resp.json()
    assert "platforms" in data
    assert "time_slots" in data
    assert "data" in data
    assert "max_heat" in data
    assert isinstance(data["platforms"], list)
    assert isinstance(data["time_slots"], list)
    assert isinstance(data["data"], list)
    assert isinstance(data["max_heat"], float)


@pytest.mark.asyncio
async def test_heatmap_empty_db(test_client: AsyncClient):
    resp = await test_client.get("/api/v1/trends/heatmap")
    data = resp.json()
    assert data["platforms"] == []
    assert len(data["time_slots"]) == 24
    assert data["data"] == []
    assert data["max_heat"] == 0.0


@pytest.mark.asyncio
async def test_heatmap_time_slots_count(test_client: AsyncClient):
    data = (await test_client.get("/api/v1/trends/heatmap")).json()
    assert len(data["time_slots"]) == 24


@pytest.mark.asyncio
async def test_heatmap_with_data(test_client: AsyncClient, db_session: AsyncSession):
    await _seed_trends(db_session)
    data = (await test_client.get("/api/v1/trends/heatmap")).json()
    assert "weibo" in data["platforms"]
    assert len(data["data"]) > 0
    assert data["max_heat"] > 0


@pytest.mark.asyncio
async def test_heatmap_data_items_have_three_elements(
    test_client: AsyncClient, db_session: AsyncSession
):
    await _seed_trends(db_session)
    items = (await test_client.get("/api/v1/trends/heatmap")).json()["data"]
    for item in items:
        assert len(item) == 3


@pytest.mark.asyncio
async def test_heatmap_excludes_old_data(test_client: AsyncClient, db_session: AsyncSession):
    # Insert a trend older than 24 hours — should not appear
    old_time = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=25)
    db_session.add(
        Trend(platform="weibo", keyword="旧话题", rank=1, heat_score=9999.0, collected_at=old_time)
    )
    await db_session.commit()
    data = (await test_client.get("/api/v1/trends/heatmap")).json()
    assert data["platforms"] == []
    assert data["data"] == []
