"""Collector router — manual trigger for data collection."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.collector import CollectorRunResponse
from app.services.collector import run_all_collectors

router = APIRouter()


@router.post("/run", summary="手动触发数据采集", response_model=CollectorRunResponse)
async def collector_run(
    platforms: str | None = Query(None, description="平台列表（逗号分隔），为空则采集全部平台"),
    db: AsyncSession = Depends(get_db),
) -> CollectorRunResponse:
    """Manually trigger collectors. Optionally specify platforms (comma-separated)."""
    platform_list = [p.strip() for p in platforms.split(",") if p.strip()] if platforms else None
    result = await run_all_collectors(db, platforms=platform_list)
    return CollectorRunResponse(**result)
