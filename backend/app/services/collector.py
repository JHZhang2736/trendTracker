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


async def _score_new_keywords(
    db: AsyncSession,
    hour_start: datetime,
    hour_end: datetime,
) -> None:
    """Score newly collected keywords for personal relevance via AI."""
    from app.config import settings as app_settings
    from app.services.relevance import score_relevance

    # Fetch keywords from the current hour that have no relevance score yet
    result = await db.execute(
        select(Trend).where(
            Trend.collected_at >= hour_start,
            Trend.collected_at < hour_end,
            Trend.relevance_score.is_(None),
        )
    )
    trends = result.scalars().all()
    if not trends:
        return

    # Deduplicate keywords for the API call
    unique_keywords = list({t.keyword for t in trends})
    logger.info("Scoring relevance for %d unique keywords", len(unique_keywords))

    try:
        scores = await score_relevance(unique_keywords, app_settings.user_profile)
    except Exception:
        logger.exception("Relevance scoring failed, skipping")
        return

    # Apply scores back to trend records
    for trend in trends:
        info = scores.get(trend.keyword)
        if info:
            trend.relevance_score = info["score"]
            trend.relevance_label = info["label"]

    await db.commit()
    relevant_count = sum(1 for t in trends if t.relevance_label == "relevant")
    logger.info(
        "Relevance scoring complete: %d/%d marked relevant",
        relevant_count,
        len(trends),
    )


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


async def run_all_collectors(
    db: AsyncSession,
    platforms: list[str] | None = None,
) -> dict:
    """Run collectors concurrently, persist results, return summary.

    Args:
        db: async database session.
        platforms: optional list of platform slugs to collect.
                   If None, all registered platforms are collected.

    Each platform uses replace-by-hour semantics: existing records for the same
    platform within the current clock-hour are deleted before inserting the fresh
    batch.  This prevents duplicate rows when collection is triggered more than
    once within the same hour (e.g. manual + scheduled), while preserving all
    cross-hour historical data for trend charts.

    Returns a dict with ``status`` and ``records_count``.
    """
    if platforms is None:
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

    # AI relevance scoring for newly collected keywords
    from app.config import settings as app_settings

    if app_settings.relevance_filter_enabled and total_records > 0:
        await _score_new_keywords(db, hour_start, hour_end)

    # Check keyword alert thresholds after each collection run
    from app.services.alerts import check_alerts

    await check_alerts(db)

    # Detect trend signals (rank jumps, new entries, heat surges)
    from app.services.signals import auto_analyze_signals, detect_signals

    signals = await detect_signals(db)

    # Auto-analyze top signals with AI (if configured)
    from app.config import settings

    if signals and settings.signal_auto_analyze_limit > 0:
        await auto_analyze_signals(db, signals, limit=settings.signal_auto_analyze_limit)

    return {"status": "ok", "records_count": total_records, "platforms": platform_results}
