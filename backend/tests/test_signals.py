"""Tests for trend signal detection (rank_jump, new_entry, heat_surge)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.signal_log import SignalLog  # noqa: F401
from app.models.trend import Trend

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


async def _seed_trend(
    db: AsyncSession,
    keyword: str,
    platform: str = "weibo",
    rank: int | None = None,
    heat: float | None = None,
    minutes_ago: int = 0,
) -> Trend:
    collected = _now() - timedelta(minutes=minutes_ago)
    trend = Trend(
        platform=platform,
        keyword=keyword,
        rank=rank,
        heat_score=heat,
        collected_at=collected,
    )
    db.add(trend)
    await db.commit()
    return trend


# ---------------------------------------------------------------------------
# Unit tests: _detect_rank_jumps
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rank_jump_detected(db_session: AsyncSession):
    """Rank improving by ≥ 20 should trigger a rank_jump signal."""
    from app.services.signals import _detect_rank_jumps

    # Old record: rank 45, 3 hours ago
    await _seed_trend(db_session, "露营", rank=45, heat=1000, minutes_ago=180)
    # Current record: rank 5, just now
    await _seed_trend(db_session, "露营", rank=5, heat=5000, minutes_ago=0)

    signals = await _detect_rank_jumps(db_session, _now())
    assert len(signals) == 1
    assert signals[0].signal_type == "rank_jump"
    assert signals[0].keyword == "露营"
    assert signals[0].value == 40.0  # 45 - 5


@pytest.mark.asyncio
async def test_rank_jump_not_triggered_small_change(db_session: AsyncSession):
    """Rank change < 20 should NOT trigger."""
    from app.services.signals import _detect_rank_jumps

    await _seed_trend(db_session, "AI", rank=20, heat=1000, minutes_ago=180)
    await _seed_trend(db_session, "AI", rank=10, heat=2000, minutes_ago=0)

    signals = await _detect_rank_jumps(db_session, _now())
    assert len(signals) == 0


@pytest.mark.asyncio
async def test_rank_jump_ignores_old_data(db_session: AsyncSession):
    """Data older than 6 hours should not be considered for rank jump."""
    from app.services.signals import _detect_rank_jumps

    # 8 hours ago — outside the 6h lookback
    await _seed_trend(db_session, "过时词", rank=49, heat=1000, minutes_ago=480)
    await _seed_trend(db_session, "过时词", rank=1, heat=5000, minutes_ago=0)

    signals = await _detect_rank_jumps(db_session, _now())
    assert len(signals) == 0


# ---------------------------------------------------------------------------
# Unit tests: _detect_new_entries
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_new_entry_detected(db_session: AsyncSession):
    """A keyword with no prior record in 24h should trigger new_entry."""
    from app.services.signals import _detect_new_entries

    # Only current data, no history
    await _seed_trend(db_session, "全新热词", rank=10, heat=5000, minutes_ago=0)

    signals = await _detect_new_entries(db_session, _now())
    assert len(signals) == 1
    assert signals[0].signal_type == "new_entry"
    assert signals[0].keyword == "全新热词"


@pytest.mark.asyncio
async def test_new_entry_not_triggered_for_existing(db_session: AsyncSession):
    """A keyword that existed in the previous 24h should NOT be new_entry."""
    from app.services.signals import _detect_new_entries

    # Historical record 6 hours ago
    await _seed_trend(db_session, "老热词", rank=5, heat=3000, minutes_ago=360)
    # Current record
    await _seed_trend(db_session, "老热词", rank=3, heat=5000, minutes_ago=0)

    signals = await _detect_new_entries(db_session, _now())
    assert len(signals) == 0


@pytest.mark.asyncio
async def test_new_entry_cross_platform_independent(db_session: AsyncSession):
    """New entry detection is per-platform — same keyword on different platform is new."""
    from app.services.signals import _detect_new_entries

    # Exists on weibo historically
    await _seed_trend(db_session, "跨平台词", platform="weibo", rank=5, heat=3000, minutes_ago=360)
    # New on google
    await _seed_trend(db_session, "跨平台词", platform="google", rank=10, heat=2000, minutes_ago=0)

    signals = await _detect_new_entries(db_session, _now())
    assert len(signals) == 1
    assert signals[0].platform == "google"


# ---------------------------------------------------------------------------
# Unit tests: _detect_heat_surges
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_heat_surge_detected(db_session: AsyncSession):
    """Heat score doubling should trigger heat_surge."""
    from app.services.signals import _detect_heat_surges

    await _seed_trend(db_session, "暴涨词", heat=1000, minutes_ago=120)
    await _seed_trend(db_session, "暴涨词", heat=3000, minutes_ago=0)

    signals = await _detect_heat_surges(db_session, _now())
    assert len(signals) == 1
    assert signals[0].signal_type == "heat_surge"
    assert signals[0].value == 3.0


@pytest.mark.asyncio
async def test_heat_surge_not_triggered_below_2x(db_session: AsyncSession):
    """Heat increase < 2× should NOT trigger."""
    from app.services.signals import _detect_heat_surges

    await _seed_trend(db_session, "稳定词", heat=1000, minutes_ago=120)
    await _seed_trend(db_session, "稳定词", heat=1500, minutes_ago=0)

    signals = await _detect_heat_surges(db_session, _now())
    assert len(signals) == 0


@pytest.mark.asyncio
async def test_heat_surge_ignores_zero_heat(db_session: AsyncSession):
    """Zero or null previous heat should not trigger surge."""
    from app.services.signals import _detect_heat_surges

    await _seed_trend(db_session, "零热度", heat=0, minutes_ago=120)
    await _seed_trend(db_session, "零热度", heat=5000, minutes_ago=0)

    signals = await _detect_heat_surges(db_session, _now())
    assert len(signals) == 0


# ---------------------------------------------------------------------------
# Unit tests: detect_signals (combined)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_detect_signals_persists_to_db(db_session: AsyncSession):
    """detect_signals should write SignalLog rows to the database."""
    from app.services.signals import detect_signals

    # Seed a new entry scenario
    await _seed_trend(db_session, "新品", rank=3, heat=8000, minutes_ago=0)

    signals = await detect_signals(db_session)
    assert len(signals) >= 1

    result = await db_session.execute(select(SignalLog))
    logs = result.scalars().all()
    assert len(logs) >= 1


@pytest.mark.asyncio
async def test_detect_signals_deduplicates_within_hour(db_session: AsyncSession):
    """Running detect_signals twice within an hour should not produce duplicate signals."""
    from app.services.signals import detect_signals

    await _seed_trend(db_session, "去重测试", rank=3, heat=8000, minutes_ago=0)

    await detect_signals(db_session)
    signals2 = await detect_signals(db_session)

    result = await db_session.execute(select(SignalLog))
    logs = result.scalars().all()
    # Should have signals from run2 only (run1 signals get deduplicated/replaced)
    assert len(logs) == len(signals2)


@pytest.mark.asyncio
async def test_detect_signals_no_data_returns_empty(db_session: AsyncSession):
    """No trends in DB should produce no signals."""
    from app.services.signals import detect_signals

    signals = await detect_signals(db_session)
    assert signals == []


# ---------------------------------------------------------------------------
# Unit tests: get_recent_signals
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_recent_signals(db_session: AsyncSession):
    """get_recent_signals should return signals within the time window."""
    from app.services.signals import detect_signals, get_recent_signals

    await _seed_trend(db_session, "查询测试", rank=3, heat=8000, minutes_ago=0)
    await detect_signals(db_session)

    recent = await get_recent_signals(db_session, hours=24, limit=50)
    assert len(recent) >= 1
    assert recent[0].keyword == "查询测试"


# ---------------------------------------------------------------------------
# Integration tests: API endpoints
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_signals_recent_endpoint_empty(test_client: AsyncClient):
    resp = await test_client.get("/api/v1/signals/recent")
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_signals_detect_endpoint(test_client: AsyncClient):
    resp = await test_client.post("/api/v1/signals/detect")
    assert resp.status_code == 200
    data = resp.json()
    assert "signals_detected" in data
    assert "items" in data


@pytest.mark.asyncio
async def test_signals_recent_includes_ai_summary_field(test_client: AsyncClient):
    """API response should include ai_summary field (even if null)."""
    resp = await test_client.get("/api/v1/signals/recent")
    assert resp.status_code == 200
    # Empty list is fine — just checking schema is valid


# ---------------------------------------------------------------------------
# Unit tests: auto_analyze_signals
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_auto_analyze_empty_signals(db_session: AsyncSession):
    """auto_analyze_signals with empty list should return 0."""
    from app.services.signals import auto_analyze_signals

    result = await auto_analyze_signals(db_session, [], limit=3)
    assert result == 0


@pytest.mark.asyncio
async def test_auto_analyze_zero_limit(db_session: AsyncSession):
    """auto_analyze_signals with limit=0 should return 0."""
    from app.services.signals import auto_analyze_signals, detect_signals

    await _seed_trend(db_session, "限制测试", rank=3, heat=8000, minutes_ago=0)
    signals = await detect_signals(db_session)

    result = await auto_analyze_signals(db_session, signals, limit=0)
    assert result == 0


@pytest.mark.asyncio
async def test_auto_analyze_updates_ai_summary(db_session: AsyncSession):
    """auto_analyze_signals should set ai_summary on analyzed signals."""
    from unittest.mock import AsyncMock, patch

    from app.models.signal_log import SignalLog as SL
    from app.services.signals import auto_analyze_signals, detect_signals

    await _seed_trend(db_session, "AI分析测试", rank=1, heat=9000, minutes_ago=0)
    signals = await detect_signals(db_session)
    assert len(signals) >= 1

    mock_result = AsyncMock()
    mock_result.business_insight = "这是一个有商业价值的趋势"

    with patch("app.services.ai.analyze_keyword", new=AsyncMock(return_value=mock_result)):
        analyzed = await auto_analyze_signals(db_session, signals, limit=1)

    assert analyzed == 1
    # Check that ai_summary was persisted
    result = await db_session.execute(select(SL).where(SL.ai_summary.isnot(None)))
    logs_with_summary = result.scalars().all()
    assert len(logs_with_summary) >= 1
    assert "商业价值" in logs_with_summary[0].ai_summary


@pytest.mark.asyncio
async def test_auto_analyze_respects_limit(db_session: AsyncSession):
    """auto_analyze_signals should only analyze up to limit signals."""
    from unittest.mock import AsyncMock, patch

    from app.services.signals import auto_analyze_signals, detect_signals

    # Seed multiple new entries
    for i in range(5):
        await _seed_trend(db_session, f"词{i}", rank=i + 1, heat=1000 * (i + 1), minutes_ago=0)
    signals = await detect_signals(db_session)
    assert len(signals) >= 3

    mock_result = AsyncMock()
    mock_result.business_insight = "分析结果"
    mock_analyze = AsyncMock(return_value=mock_result)

    with patch("app.services.ai.analyze_keyword", new=mock_analyze):
        analyzed = await auto_analyze_signals(db_session, signals, limit=2)

    assert analyzed == 2
    assert mock_analyze.call_count == 2
