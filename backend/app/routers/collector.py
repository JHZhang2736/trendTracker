"""Collector router — manual trigger for data collection."""

from __future__ import annotations

from fastapi import APIRouter

from app.schemas.collector import CollectorRunResponse
from app.services.collector import run_all_collectors

router = APIRouter()


@router.post("/run", summary="手动触发全平台数据采集", response_model=CollectorRunResponse)
async def collector_run() -> CollectorRunResponse:
    """Manually trigger all registered collectors and return the result."""
    result = await run_all_collectors()
    return CollectorRunResponse(**result)
