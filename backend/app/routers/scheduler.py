"""Scheduler router — exposes scheduler status via REST API."""

from __future__ import annotations

from fastapi import APIRouter

from app.services.scheduler import get_jobs_status, scheduler

router = APIRouter()


@router.get("/status", summary="查询调度器状态及任务列表")
async def scheduler_status() -> dict:
    """Return the scheduler running state and a list of all registered jobs."""
    return {
        "running": scheduler.running,
        "jobs": get_jobs_status(),
    }
