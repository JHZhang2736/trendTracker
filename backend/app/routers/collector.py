"""Collector router — manual trigger for data collection."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.collector import CollectorRunResponse
from app.services.collector import run_all_collectors, run_all_collectors_stream

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


@router.post("/run-stream", summary="手动触发数据采集（SSE 实时进度）")
async def collector_run_stream(
    platforms: str | None = Query(None, description="平台列表（逗号分隔），为空则采集全部平台"),
    db: AsyncSession = Depends(get_db),
):
    """Trigger collectors with SSE progress streaming.

    Returns a stream of ``text/event-stream`` events.  Each event is a JSON
    object with at least ``stage`` and ``message`` fields.
    """
    platform_list = [p.strip() for p in platforms.split(",") if p.strip()] if platforms else None

    async def event_generator():
        async for event in run_all_collectors_stream(db, platforms=platform_list):
            yield f"data: {json.dumps(event, ensure_ascii=False, default=str)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
