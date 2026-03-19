"""Trends service — DB queries for trend data."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.collectors.registry import registry
from app.models.trend import Trend


async def get_trends(db: AsyncSession, page: int = 1, page_size: int = 20) -> dict:
    """Return paginated trends from the database, ordered by collected_at desc then rank."""
    offset = (page - 1) * page_size

    count_result = await db.execute(select(func.count()).select_from(Trend))
    total = count_result.scalar_one()

    result = await db.execute(
        select(Trend)
        .order_by(Trend.collected_at.desc(), Trend.rank)
        .offset(offset)
        .limit(page_size)
    )
    trends = result.scalars().all()

    items = [
        {
            "platform": t.platform,
            "keyword": t.keyword,
            "rank": t.rank,
            "heat_score": t.heat_score,
            "url": t.url,
            "collected_at": t.collected_at,
        }
        for t in trends
    ]
    return {"total": total, "page": page, "page_size": page_size, "items": items}


def get_platforms() -> list[str]:
    """Return all registered platform slugs."""
    return registry.list_platforms()


async def get_heatmap(db: AsyncSession) -> dict:
    """Build heatmap data for the last 24 hours, grouped by platform × hour.

    Returns:
        platforms: sorted list of platform slugs found in data
        time_slots: 24 hour labels ("HH:MM") from oldest to newest
        data: list of [platform_idx, slot_idx, max_heat_score]
        max_heat: global maximum heat score (for visualMap scaling)
    """
    now = datetime.now(timezone.utc).replace(tzinfo=None)  # naive UTC, matches DB storage
    since = now - timedelta(hours=24)

    # Generate 24 ordered time slots (oldest → newest)
    slots: list[datetime] = [
        (now - timedelta(hours=23 - i)).replace(minute=0, second=0, microsecond=0)
        for i in range(24)
    ]
    slot_index: dict[str, int] = {s.strftime("%Y-%m-%d %H"): i for i, s in enumerate(slots)}

    result = await db.execute(
        select(Trend.platform, Trend.collected_at, Trend.heat_score).where(
            Trend.collected_at >= since
        )
    )
    rows = result.all()

    # Collect unique platforms (sorted for stable ordering)
    platforms = sorted({row.platform for row in rows if row.platform})
    platform_index = {p: i for i, p in enumerate(platforms)}

    # Aggregate: cell[platform_idx][slot_idx] = max heat_score
    cells: dict[tuple[int, int], float] = {}
    for row in rows:
        if row.heat_score is None:
            continue
        p_idx = platform_index.get(row.platform)
        if p_idx is None:
            continue
        # Strip timezone if present (DB returns naive datetimes)
        collected = row.collected_at
        if hasattr(collected, "tzinfo") and collected.tzinfo is not None:
            collected = collected.replace(tzinfo=None)
        hour_key = collected.strftime("%Y-%m-%d %H")
        s_idx = slot_index.get(hour_key)
        if s_idx is None:
            continue
        key = (p_idx, s_idx)
        cells[key] = max(cells.get(key, 0.0), float(row.heat_score))

    data = [[float(p), float(s), v] for (p, s), v in cells.items()]
    max_heat = max(cells.values(), default=0.0)
    time_labels = [s.strftime("%H:%M") for s in slots]

    return {
        "platforms": platforms,
        "time_slots": time_labels,
        "data": data,
        "max_heat": max_heat,
    }
