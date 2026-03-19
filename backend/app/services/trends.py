"""Trends service — DB queries for trend data."""

from __future__ import annotations

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
