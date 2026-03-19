"""Collector service — run all collectors and persist results to DB."""

from __future__ import annotations

import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.collectors.registry import registry
from app.models.platform import Platform
from app.models.trend import Trend


async def _ensure_platform(db: AsyncSession, slug: str) -> int:
    """Get or create a platform record; return its id."""
    result = await db.execute(select(Platform).where(Platform.slug == slug))
    platform = result.scalar_one_or_none()
    if platform is None:
        platform = Platform(name=slug.capitalize(), slug=slug)
        db.add(platform)
        await db.flush()
    return platform.id


async def _collect_one(platform_slug: str) -> tuple[str, list[dict]]:
    """Run a single collector and return (platform_slug, records). Never raises."""
    collector_cls = registry.get(platform_slug)
    try:
        records = await collector_cls().collect()
        return platform_slug, records or []
    except Exception:  # noqa: BLE001
        return platform_slug, []


async def run_all_collectors(db: AsyncSession) -> dict:
    """Run all registered collectors concurrently, persist results, return summary.

    Returns a dict with ``status`` and ``records_count``.
    """
    platforms = registry.list_platforms()

    # Collect from all platforms in parallel
    results = await asyncio.gather(*(_collect_one(slug) for slug in platforms))

    total_records = 0
    for platform_slug, records in results:
        if not records:
            continue
        platform_id = await _ensure_platform(db, platform_slug)
        for rec in records:
            db.add(
                Trend(
                    platform_id=platform_id,
                    platform=rec["platform"],
                    keyword=rec["keyword"],
                    rank=rec.get("rank"),
                    heat_score=rec.get("heat_score"),
                    url=rec.get("url"),
                    collected_at=rec["collected_at"],
                )
            )
        total_records += len(records)

    await db.commit()

    # Check keyword alert thresholds after each collection run
    from app.services.alerts import check_alerts

    await check_alerts(db)

    return {"status": "ok", "records_count": total_records}
