"""Unit and integration tests for APScheduler integration."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.services.scheduler import (
    cleanup_old_trends_job,
    collect_trends_job,
    get_jobs_status,
    setup_scheduler,
)

# ---------------------------------------------------------------------------
# setup_scheduler
# ---------------------------------------------------------------------------


def test_setup_scheduler_registers_collect_trends_job():
    sched = setup_scheduler()
    job = sched.get_job("collect_trends")
    assert job is not None
    assert job.id == "collect_trends"


def test_setup_scheduler_idempotent():
    """Calling setup_scheduler twice should not duplicate jobs."""
    setup_scheduler()
    setup_scheduler()
    sched = setup_scheduler()
    job_ids = [j.id for j in sched.get_jobs()]
    assert job_ids.count("collect_trends") == 1


def test_setup_scheduler_job_trigger_is_cron():
    from apscheduler.triggers.cron import CronTrigger

    sched = setup_scheduler()
    job = sched.get_job("collect_trends")
    assert isinstance(job.trigger, CronTrigger)


def test_setup_scheduler_collect_cron_is_configurable():
    """COLLECT_CRON env var must be respected — custom cron expression is parsed."""
    from unittest.mock import patch

    from apscheduler.triggers.cron import CronTrigger

    from app.services import scheduler as sched_module

    # Reset so setup_scheduler re-registers the job with a fresh trigger
    sched_module.scheduler.remove_all_jobs()

    with patch("app.config.settings.collect_cron", "0 */2 * * *"):
        sched = sched_module.setup_scheduler()

    job = sched.get_job("collect_trends")
    assert isinstance(job.trigger, CronTrigger)
    assert "*/2" in str(job.trigger)


# ---------------------------------------------------------------------------
# get_jobs_status
# ---------------------------------------------------------------------------


def test_get_jobs_status_returns_list():
    setup_scheduler()
    status = get_jobs_status()
    assert isinstance(status, list)


def test_get_jobs_status_contains_collect_trends():
    setup_scheduler()
    status = get_jobs_status()
    ids = [j["id"] for j in status]
    assert "collect_trends" in ids


def test_get_jobs_status_record_schema():
    setup_scheduler()
    status = get_jobs_status()
    for job in status:
        assert "id" in job
        assert "name" in job
        assert "trigger" in job
        assert "next_run_time" in job


# ---------------------------------------------------------------------------
# collect_trends_job
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_collect_trends_job_runs_without_error():
    """Job should not raise even when the DB is unavailable (exception is caught)."""
    await collect_trends_job()


@pytest.mark.asyncio
async def test_collect_trends_job_calls_run_all_collectors():
    """collect_trends_job must delegate to run_all_collectors (data is actually saved)."""
    from unittest.mock import AsyncMock, MagicMock, patch

    mock_run = AsyncMock(return_value={"status": "ok", "records_count": 7})
    mock_db = AsyncMock()
    mock_ctx = MagicMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_db)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)

    with (
        patch("app.database.AsyncSessionLocal", return_value=mock_ctx),
        patch("app.services.collector.run_all_collectors", mock_run),
    ):
        await collect_trends_job()

    mock_run.assert_called_once_with(mock_db, platforms=None)


# ---------------------------------------------------------------------------
# /api/v1/scheduler/status endpoint (integration)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_scheduler_status_endpoint():
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/scheduler/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "running" in data
    assert "jobs" in data
    assert isinstance(data["jobs"], list)


def test_setup_scheduler_registers_cleanup_job():
    sched = setup_scheduler()
    job = sched.get_job("cleanup_old_trends")
    assert job is not None
    assert job.id == "cleanup_old_trends"


def test_cleanup_job_trigger_is_cron():
    from apscheduler.triggers.cron import CronTrigger

    sched = setup_scheduler()
    job = sched.get_job("cleanup_old_trends")
    assert isinstance(job.trigger, CronTrigger)


def test_get_jobs_status_contains_cleanup():
    setup_scheduler()
    status = get_jobs_status()
    ids = [j["id"] for j in status]
    assert "cleanup_old_trends" in ids


@pytest.mark.asyncio
async def test_cleanup_old_trends_job_runs_without_error():
    """The cleanup job should not raise even when the DB has no old records."""
    await cleanup_old_trends_job()


# ---------------------------------------------------------------------------
# Per-platform scheduler jobs
# ---------------------------------------------------------------------------


def test_setup_scheduler_registers_per_platform_jobs():
    sched = setup_scheduler()
    for platform in ("weibo", "douyin", "toutiao"):
        job = sched.get_job(f"collect_{platform}")
        assert job is not None, f"collect_{platform} job not registered"


def test_per_platform_jobs_have_cron_trigger():
    from apscheduler.triggers.cron import CronTrigger

    sched = setup_scheduler()
    for platform in ("weibo", "douyin", "toutiao"):
        job = sched.get_job(f"collect_{platform}")
        assert isinstance(job.trigger, CronTrigger)


def test_per_platform_weibo_uses_custom_cron():
    """Weibo should use its own cron (every 2h), not the global default."""
    sched = setup_scheduler()
    job = sched.get_job("collect_weibo")
    # Default weibo_cron = "0 */2 * * *"
    assert "*/2" in str(job.trigger)


def test_get_jobs_status_contains_per_platform_jobs():
    setup_scheduler()
    status = get_jobs_status()
    ids = [j["id"] for j in status]
    for platform in ("weibo", "douyin", "toutiao"):
        assert f"collect_{platform}" in ids


@pytest.mark.asyncio
async def test_collect_trends_job_with_platforms_param():
    """collect_trends_job should pass platforms arg to run_all_collectors."""
    from unittest.mock import AsyncMock, MagicMock, patch

    mock_run = AsyncMock(return_value={"status": "ok", "records_count": 5})
    mock_db = AsyncMock()
    mock_ctx = MagicMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_db)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)

    with (
        patch("app.database.AsyncSessionLocal", return_value=mock_ctx),
        patch("app.services.collector.run_all_collectors", mock_run),
    ):
        await collect_trends_job(platforms=["weibo"])

    mock_run.assert_called_once_with(mock_db, platforms=["weibo"])


@pytest.mark.asyncio
async def test_health_endpoint_still_works():
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
