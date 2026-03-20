"""Trends router — trend list, top trends, heatmap, and platform registry endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.trend import Trend
from app.schemas.trends import (
    HeatmapResponse,
    PlatformsResponse,
    TopByPlatformResponse,
    TopTrendsResponse,
    TrendsClearResponse,
    TrendsListResponse,
)
from app.services.trends import (
    get_heatmap,
    get_platforms,
    get_top_trends,
    get_top_trends_by_platform,
    get_trends,
)

router = APIRouter()


@router.get("", summary="获取趋势列表（分页，含收敛评分）", response_model=TrendsListResponse)
async def list_trends(
    page: int = Query(default=1, ge=1, description="页码，从 1 开始"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页条数"),
    platform: str | None = Query(default=None, description="按平台过滤，如 weibo / google / tiktok"),  # noqa: E501
    db: AsyncSession = Depends(get_db),
) -> TrendsListResponse:
    """Return a paginated list of trend records with convergence_score.

    Pass *platform* to restrict results to a single platform.
    """
    data = await get_trends(db=db, page=page, page_size=page_size, platform=platform)
    return TrendsListResponse(**data)


@router.get("/top", summary="按收敛评分排序的 Top 20 趋势", response_model=TopTrendsResponse)
async def top_trends(
    limit: int = Query(default=20, ge=1, le=100, description="返回条数"),
    db: AsyncSession = Depends(get_db),
) -> TopTrendsResponse:
    """Return top trending keywords ranked by convergence score (last 24 hours)."""
    items = await get_top_trends(db=db, limit=limit)
    return TopTrendsResponse(items=items)


@router.get(
    "/top-by-platform",
    summary="各平台独立 Top N 趋势（按平台内收敛评分）",
    response_model=TopByPlatformResponse,
)
async def top_trends_by_platform(
    limit: int = Query(default=10, ge=1, le=50, description="每个平台返回条数"),
    db: AsyncSession = Depends(get_db),
) -> TopByPlatformResponse:
    """Return top-N keywords per platform, scored independently within each platform."""
    data = await get_top_trends_by_platform(db=db, limit=limit)
    return TopByPlatformResponse(platforms=data)


@router.get("/heatmap", summary="获取热力图数据（最近24小时）", response_model=HeatmapResponse)
async def trends_heatmap(db: AsyncSession = Depends(get_db)) -> HeatmapResponse:
    """Return heatmap data grouped by platform × hour for the last 24 hours."""
    data = await get_heatmap(db=db)
    return HeatmapResponse(**data)


@router.get("/platforms", summary="获取已注册平台列表", response_model=PlatformsResponse)
async def list_platforms() -> PlatformsResponse:
    """Return all registered platform slugs."""
    return PlatformsResponse(platforms=get_platforms())


@router.delete("/all", summary="清空所有趋势数据", response_model=TrendsClearResponse)
async def clear_all_trends(db: AsyncSession = Depends(get_db)) -> TrendsClearResponse:
    """Delete every trend record from the database. This action is irreversible."""
    from sqlalchemy import delete as sql_delete

    result = await db.execute(sql_delete(Trend))
    await db.commit()
    return TrendsClearResponse(deleted=result.rowcount)
