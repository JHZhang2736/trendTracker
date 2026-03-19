"""Unit and integration tests for APScheduler integration."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.services.scheduler import collect_trends_job, get_jobs_status, setup_scheduler


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


def test_setup_scheduler_job_trigger_is_interval():
    from apscheduler.triggers.interval import IntervalTrigger

    sched = setup_scheduler()
    job = sched.get_job("collect_trends")
    assert isinstance(job.trigger, IntervalTrigger)


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
    """The job should complete without raising even when the DB is unavailable."""
    await collect_trends_job()


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


@pytest.mark.asyncio
async def test_health_endpoint_still_works():
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
