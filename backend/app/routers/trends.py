"""Trends router — trend list and platform registry endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.trends import PlatformsResponse, TrendsListResponse
from app.services.trends import get_platforms, get_trends

router = APIRouter()


@router.get("", summary="获取趋势列表（分页）", response_model=TrendsListResponse)
async def list_trends(
    page: int = Query(default=1, ge=1, description="页码，从 1 开始"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页条数"),
    db: AsyncSession = Depends(get_db),
) -> TrendsListResponse:
    """Return a paginated list of trend records from the database."""
    data = await get_trends(db=db, page=page, page_size=page_size)
    return TrendsListResponse(**data)


@router.get("/platforms", summary="获取已注册平台列表", response_model=PlatformsResponse)
async def list_platforms() -> PlatformsResponse:
    """Return all registered platform slugs."""
    return PlatformsResponse(platforms=get_platforms())
