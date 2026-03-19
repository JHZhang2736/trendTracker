"""Collector router — manual trigger for data collection."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.collector import CollectorRunResponse
from app.services.collector import run_all_collectors

router = APIRouter()


@router.post("/run", summary="手动触发全平台数据采集", response_model=CollectorRunResponse)
async def collector_run(db: AsyncSession = Depends(get_db)) -> CollectorRunResponse:
    """Manually trigger all registered collectors, persist results, and return summary."""
    result = await run_all_collectors(db)
    return CollectorRunResponse(**result)
