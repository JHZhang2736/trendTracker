"""Collector service — run all collectors and persist results to DB."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.collectors.registry import registry
from app.models.platform import Platform
from app.models.trend import Trend

logger = logging.getLogger(__name__)


async def _ensure_platform(db: AsyncSession, slug: str) -> int:
    """Get or create a platform record; return its id."""
    result = await db.execute(select(Platform).where(Platform.slug == slug))
    platform = result.scalar_one_or_none()
    if platform is None:
        platform = Platform(name=slug.capitalize(), slug=slug)
        db.add(platform)
        await db.flush()
    return platform.id


async def _collect_one(platform_slug: str) -> tuple[str, list[dict], str | None]:
    """Run a single collector and return (platform_slug, records, error). Never raises."""
    collector_cls = registry.get(platform_slug)
    try:
        records = await collector_cls().collect()
        return platform_slug, records or [], None
    except Exception as exc:  # noqa: BLE001
        logger.error("_collect_one[%s]: failed — %s: %s", platform_slug, type(exc).__name__, exc)
        return platform_slug, [], str(exc)


async def run_all_collectors(db: AsyncSession) -> dict:
    """Run all registered collectors concurrently, persist results, return summary.

    Each platform uses replace-by-hour semantics: existing records for the same
    platform within the current clock-hour are deleted before inserting the fresh
    batch.  This prevents duplicate rows when collection is triggered more than
    once within the same hour (e.g. manual + scheduled), while preserving all
    cross-hour historical data for trend charts.

    Returns a dict with ``status`` and ``records_count``.
    """
    platforms = registry.list_platforms()

    # Current hour bucket (naive UTC, matching DB storage)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    hour_start = now.replace(minute=0, second=0, microsecond=0)
    hour_end = hour_start + timedelta(hours=1)

    # Collect from all platforms in parallel
    results = await asyncio.gather(*(_collect_one(slug) for slug in platforms))

    total_records = 0
    platform_results = []
    for platform_slug, records, error in results:
        platform_results.append({"platform": platform_slug, "count": len(records), "error": error})
        if not records:
            continue

        # Replace-by-hour: remove stale records in the current hour bucket
        await db.execute(
            delete(Trend).where(
                Trend.platform == platform_slug,
                Trend.collected_at >= hour_start,
                Trend.collected_at < hour_end,
            )
        )

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

    return {"status": "ok", "records_count": total_records, "platforms": platform_results}
