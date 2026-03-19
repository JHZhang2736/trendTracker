"""APScheduler integration — scheduled jobs for TrendTracker."""

from __future__ import annotations

import logging
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)

# Global scheduler instance reused across the application lifecycle.
scheduler = AsyncIOScheduler()


async def cleanup_old_trends_job() -> None:
    """Scheduled job: delete trend records older than 90 days."""
    logger.info("cleanup_old_trends_job: starting cleanup")
    try:
        from datetime import datetime, timedelta, timezone

        from sqlalchemy import delete

        from app.database import AsyncSessionLocal
        from app.models.trend import Trend

        cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=90)
        async with AsyncSessionLocal() as db:
            result = await db.execute(delete(Trend).where(Trend.collected_at < cutoff))
            await db.commit()
            deleted = result.rowcount
        logger.info("cleanup_old_trends_job: deleted %d records older than 90 days", deleted)
    except Exception as exc:  # noqa: BLE001
        logger.error("cleanup_old_trends_job: error — %s", exc)


async def daily_brief_job() -> None:
    """Scheduled job: generate daily brief and send email."""
    logger.info("daily_brief_job: starting daily brief generation")
    try:
        from app.database import AsyncSessionLocal

        async with AsyncSessionLocal() as db:
            from app.services.brief import generate_daily_brief

            brief = await generate_daily_brief(db=db, send_mail=True)
            logger.info("daily_brief_job: brief generated id=%d date=%s", brief.id, brief.date)
    except Exception as exc:  # noqa: BLE001
        logger.error("daily_brief_job: error — %s", exc)


async def collect_trends_job() -> None:
    """Scheduled job: trigger all registered collectors and persist results.

    In the MVP phase this logs a placeholder message.  Future implementation
    will iterate :data:`~app.collectors.registry` and save to the database.
    """
    logger.info("collect_trends_job: starting trend collection run")
    from app.collectors import registry

    for platform in registry.list_platforms():
        try:
            collector_cls = registry.get(platform)
            collector = collector_cls()
            results = await collector.collect()
            logger.info("collect_trends_job: collected %d records from %s", len(results), platform)
        except Exception as exc:  # noqa: BLE001
            logger.error("collect_trends_job: error collecting from %s: %s", platform, exc)


def setup_scheduler() -> AsyncIOScheduler:
    """Register all recurring jobs and return the scheduler (not yet started)."""
    if scheduler.get_job("collect_trends") is None:
        scheduler.add_job(
            collect_trends_job,
            trigger=IntervalTrigger(hours=1),
            id="collect_trends",
            name="Collect trends from all platforms",
            replace_existing=True,
        )
        logger.info("setup_scheduler: registered 'collect_trends' job (every 1 hour)")

    if scheduler.get_job("daily_brief") is None:
        scheduler.add_job(
            daily_brief_job,
            trigger=CronTrigger(hour=8, minute=0),
            id="daily_brief",
            name="Generate daily AI brief",
            replace_existing=True,
        )
        logger.info("setup_scheduler: registered 'daily_brief' job (daily 08:00)")

    if scheduler.get_job("cleanup_old_trends") is None:
        scheduler.add_job(
            cleanup_old_trends_job,
            trigger=CronTrigger(hour=3, minute=0),
            id="cleanup_old_trends",
            name="Delete trend records older than 90 days",
            replace_existing=True,
        )
        logger.info("setup_scheduler: registered 'cleanup_old_trends' job (daily 03:00)")

    return scheduler


def get_jobs_status() -> list[dict[str, Any]]:
    """Return a serialisable snapshot of all scheduled jobs."""
    jobs = []
    for job in scheduler.get_jobs():
        try:
            nrt = job.next_run_time
            next_run = nrt.isoformat() if nrt else None
        except AttributeError:
            next_run = None
        jobs.append(
            {
                "id": job.id,
                "name": job.name,
                "next_run_time": next_run,
                "trigger": str(job.trigger),
            }
        )
    return jobs
