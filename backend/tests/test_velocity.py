"""Tests for trend velocity & acceleration indicators."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.trend import Trend
from app.services.trends import _avg_heat, _pct_change, get_keyword_velocity

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


async def _seed(
    db: AsyncSession,
    keyword: str = "test",
    platform: str = "weibo",
    heat: float = 100.0,
    rank: int | None = 0,
    hours_ago: float = 0,
) -> Trend:
    t = Trend(
        platform=platform,
        keyword=keyword,
        heat_score=heat,
        rank=rank,
        collected_at=_now() - timedelta(hours=hours_ago),
    )
    db.add(t)
    await db.commit()
    return t


# ---------------------------------------------------------------------------
# Pure function tests
# ---------------------------------------------------------------------------


def test_avg_heat_empty():
    assert _avg_heat([]) == 0.0


def test_avg_heat_values():
    assert _avg_heat([(10.0, 1), (20.0, 2)]) == 15.0


def test_pct_change_normal():
    assert _pct_change(100, 150) == 50.0


def test_pct_change_decrease():
    assert _pct_change(200, 100) == -50.0


def test_pct_change_from_zero_to_positive():
    assert _pct_change(0, 50) == 100.0


def test_pct_change_zero_to_zero():
    assert _pct_change(0, 0) == 0.0


# ---------------------------------------------------------------------------
# Integration tests — get_keyword_velocity
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_velocity_rising_keyword(db_session: AsyncSession):
    """Keyword with increasing heat should have positive velocity."""
    # T0 period (16-24h ago): heat 100
    await _seed(db_session, keyword="rising", heat=100, hours_ago=20)
    # T1 period (8-16h ago): heat 150  (+50%)
    await _seed(db_session, keyword="rising", heat=150, hours_ago=12)
    # T2 period (0-8h ago): heat 400   (+167%)
    await _seed(db_session, keyword="rising", heat=400, hours_ago=4)

    items = await get_keyword_velocity(db_session, hours=24)
    assert len(items) == 1
    item = items[0]
    assert item["keyword"] == "rising"
    assert item["velocity"] is not None
    assert item["velocity"] > 0  # heat increased: positive velocity
    assert item["acceleration"] is not None
    assert item["acceleration"] > 0  # velocity increased: positive acceleration


@pytest.mark.asyncio
async def test_velocity_falling_keyword(db_session: AsyncSession):
    """Keyword with decreasing heat should have negative velocity."""
    await _seed(db_session, keyword="falling", heat=400, hours_ago=20)
    await _seed(db_session, keyword="falling", heat=200, hours_ago=12)
    await _seed(db_session, keyword="falling", heat=100, hours_ago=4)

    items = await get_keyword_velocity(db_session, hours=24)
    assert len(items) == 1
    assert items[0]["velocity"] < 0


@pytest.mark.asyncio
async def test_velocity_no_t2_data_excluded(db_session: AsyncSession):
    """Keywords with no data in the latest period should be excluded."""
    # Only old data, nothing in T2
    await _seed(db_session, keyword="old", heat=100, hours_ago=20)
    await _seed(db_session, keyword="old", heat=100, hours_ago=12)

    items = await get_keyword_velocity(db_session, hours=24)
    assert len(items) == 0


@pytest.mark.asyncio
async def test_velocity_platform_filter(db_session: AsyncSession):
    """Platform filter should only return matching keywords."""
    await _seed(db_session, keyword="kw", platform="weibo", heat=100, hours_ago=4)
    await _seed(db_session, keyword="kw", platform="google", heat=200, hours_ago=4)

    items = await get_keyword_velocity(db_session, platform="weibo", hours=24)
    assert len(items) == 1
    assert items[0]["platform"] == "weibo"


@pytest.mark.asyncio
async def test_velocity_limit(db_session: AsyncSession):
    """Limit parameter should cap results."""
    for i in range(5):
        await _seed(db_session, keyword=f"kw{i}", heat=100 + i * 50, hours_ago=4)

    items = await get_keyword_velocity(db_session, hours=24, limit=2)
    assert len(items) == 2


@pytest.mark.asyncio
async def test_velocity_endpoint(test_client: AsyncClient):
    """GET /api/v1/trends/velocity should return valid response."""
    resp = await test_client.get("/api/v1/trends/velocity")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert isinstance(data["items"], list)
