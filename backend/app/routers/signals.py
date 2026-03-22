"""Signals router — trend signal detection and query endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.signals import DetectResponse, SignalItem, SignalListResponse
from app.services.signals import detect_signals, get_recent_signals

router = APIRouter()


@router.get("/recent", summary="获取最近趋势信号", response_model=SignalListResponse)
async def recent_signals(
    hours: int = Query(24, ge=1, le=168, description="回溯时间窗口（小时）"),
    limit: int = Query(50, ge=1, le=200, description="返回条数上限"),
    db: AsyncSession = Depends(get_db),
) -> SignalListResponse:
    """Return recent trend signals (rank jumps, new entries, heat surges)."""
    rows = await get_recent_signals(db, hours=hours, limit=limit)
    items = [
        SignalItem(
            id=r.id,
            signal_type=r.signal_type,
            platform=r.platform,
            keyword=r.keyword,
            description=r.description,
            value=r.value,
            detected_at=r.detected_at,
        )
        for r in rows
    ]
    return SignalListResponse(items=items, total=len(items))


@router.post("/detect", summary="手动触发信号检测", response_model=DetectResponse)
async def trigger_detect(
    db: AsyncSession = Depends(get_db),
) -> DetectResponse:
    """Manually trigger signal detection on current data."""
    signals = await detect_signals(db)
    items = [
        SignalItem(
            id=s.id,
            signal_type=s.signal_type,
            platform=s.platform,
            keyword=s.keyword,
            description=s.description,
            value=s.value,
            detected_at=s.detected_at,
        )
        for s in signals
    ]
    return DetectResponse(signals_detected=len(items), items=items)
