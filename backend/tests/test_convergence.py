"""Tests for convergence score algorithm and /trends/top endpoint."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.trend import Trend
from app.services.trends import compute_convergence_score


# ---------------------------------------------------------------------------
# Unit tests: compute_convergence_score (pure function)
# ---------------------------------------------------------------------------


def test_score_is_between_0_and_100():
    score = compute_convergence_score(
        heat_score=5000.0, rank=0, platform_count=1, age_hours=0.0, max_heat=10000.0
    )
    assert 0.0 <= score <= 100.0


def test_rank_1_scores_higher_than_rank_50():
    score_top = compute_convergence_score(
        heat_score=5000.0, rank=0, platform_count=1, age_hours=0.0, max_heat=10000.0
    )
    score_bottom = compute_convergence_score(
        heat_score=5000.0, rank=49, platform_count=1, age_hours=0.0, max_heat=10000.0
    )
    assert score_top > score_bottom


def test_higher_heat_scores_higher():
    score_high = compute_convergence_score(
        heat_score=9000.0, rank=5, platform_count=1, age_hours=0.0, max_heat=10000.0
    )
    score_low = compute_convergence_score(
        heat_score=1000.0, rank=5, platform_count=1, age_hours=0.0, max_heat=10000.0
    )
    assert score_high > score_low


def test_more_platforms_scores_higher():
    score_single = compute_convergence_score(
        heat_score=5000.0, rank=5, platform_count=1, age_hours=0.0, max_heat=10000.0
    )
    score_multi = compute_convergence_score(
        heat_score=5000.0, rank=5, platform_count=3, age_hours=0.0, max_heat=10000.0
    )
    assert score_multi > score_single


def test_older_trend_decays():
    score_fresh = compute_convergence_score(
        heat_score=5000.0, rank=5, platform_count=1, age_hours=0.0, max_heat=10000.0
    )
    score_old = compute_convergence_score(
        heat_score=5000.0, rank=5, platform_count=1, age_hours=24.0, max_heat=10000.0
    )
    assert score_fresh > score_old


def test_12h_old_trend_roughly_half_score():
    score_fresh = compute_convergence_score(
        heat_score=10000.0, rank=0, platform_count=1, age_hours=0.0, max_heat=10000.0
    )
    score_12h = compute_convergence_score(
        heat_score=10000.0, rank=0, platform_count=1, age_hours=12.0, max_heat=10000.0
    )
    # After 12h (one half-life), score should be roughly half
    assert abs(score_12h - score_fresh / 2) < 5.0


def test_none_heat_score_does_not_crash():
    score = compute_convergence_score(
        heat_score=None, rank=1, platform_count=1, age_hours=0.0, max_heat=10000.0
    )
    assert 0.0 <= score <= 100.0


def test_none_rank_does_not_crash():
    score = compute_convergence_score(
        heat_score=5000.0, rank=None, platform_count=1, age_hours=0.0, max_heat=10000.0
    )
    assert 0.0 <= score <= 100.0


def test_zero_max_heat_returns_zero_or_low():
    score = compute_convergence_score(
        heat_score=5000.0, rank=None, platform_count=1, age_hours=0.0, max_heat=0.0
    )
    assert 0.0 <= score <= 100.0


def test_score_capped_at_100():
    score = compute_convergence_score(
        heat_score=10000.0, rank=0, platform_count=5, age_hours=0.0, max_heat=10000.0
    )
    assert score <= 100.0


# ---------------------------------------------------------------------------
# Integration tests: GET /api/v1/trends and /api/v1/trends/top
# ---------------------------------------------------------------------------


async def _seed(db: AsyncSession, keyword: str, platform: str, rank: int, heat: float) -> None:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    db.add(Trend(platform=platform, keyword=keyword, rank=rank, heat_score=heat, collected_at=now))
    await db.commit()


@pytest.mark.asyncio
async def test_trends_list_includes_convergence_score(test_client: AsyncClient, db_session: AsyncSession):
    await _seed(db_session, "热词A", "weibo", 0, 9000.0)
    data = (await test_client.get("/api/v1/trends")).json()
    for item in data["items"]:
        assert "convergence_score" in item
        assert isinstance(item["convergence_score"], float)
        assert 0.0 <= item["convergence_score"] <= 100.0


@pytest.mark.asyncio
async def test_top_trends_returns_200(test_client: AsyncClient):
    resp = await test_client.get("/api/v1/trends/top")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_top_trends_response_schema(test_client: AsyncClient):
    data = (await test_client.get("/api/v1/trends/top")).json()
    assert "items" in data
    assert isinstance(data["items"], list)


@pytest.mark.asyncio
async def test_top_trends_item_schema(test_client: AsyncClient, db_session: AsyncSession):
    await _seed(db_session, "热词A", "weibo", 0, 9000.0)
    items = (await test_client.get("/api/v1/trends/top")).json()["items"]
    assert len(items) > 0
    required = {"keyword", "platforms", "max_heat_score", "latest_collected_at", "convergence_score"}
    for item in items:
        assert required <= set(item.keys())


@pytest.mark.asyncio
async def test_top_trends_sorted_descending(test_client: AsyncClient, db_session: AsyncSession):
    await _seed(db_session, "热词High", "weibo", 0, 9000.0)
    await _seed(db_session, "热词Low", "weibo", 49, 100.0)
    items = (await test_client.get("/api/v1/trends/top")).json()["items"]
    scores = [item["convergence_score"] for item in items]
    assert scores == sorted(scores, reverse=True)


@pytest.mark.asyncio
async def test_top_trends_merges_cross_platform(test_client: AsyncClient, db_session: AsyncSession):
    await _seed(db_session, "爆款词", "weibo", 0, 9000.0)
    await _seed(db_session, "爆款词", "google", 1, 8000.0)
    items = (await test_client.get("/api/v1/trends/top")).json()["items"]
    match = next((i for i in items if i["keyword"] == "爆款词"), None)
    assert match is not None
    assert len(match["platforms"]) == 2


@pytest.mark.asyncio
async def test_top_trends_excludes_old_data(test_client: AsyncClient, db_session: AsyncSession):
    old_time = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=25)
    db_session.add(Trend(platform="weibo", keyword="过时词", rank=1, heat_score=9000.0, collected_at=old_time))
    await db_session.commit()
    items = (await test_client.get("/api/v1/trends/top")).json()["items"]
    assert not any(i["keyword"] == "过时词" for i in items)


@pytest.mark.asyncio
async def test_top_trends_respects_limit(test_client: AsyncClient, db_session: AsyncSession):
    for i in range(10):
        await _seed(db_session, f"词{i}", "weibo", i, float((10 - i) * 1000))
    items = (await test_client.get("/api/v1/trends/top?limit=3")).json()["items"]
    assert len(items) <= 3
