"""APScheduler integration — scheduled jobs for TrendTracker."""

from __future__ import annotations

import logging
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)

# Global scheduler instance reused across the application lifecycle.
scheduler = AsyncIOScheduler()


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
