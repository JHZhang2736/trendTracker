"""AI router — keyword analysis and daily brief endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.ai import AnalyzeRequest, AnalyzeResult, BriefResponse
from app.services.ai import analyze_keyword
from app.services.brief import generate_daily_brief, get_latest_brief

router = APIRouter()


@router.post(
    "/analyze",
    summary="AI 趋势词分析（商业建议 + 情感极性 + 相关词）",
    response_model=AnalyzeResult,
)
async def analyze(
    body: AnalyzeRequest,
    db: AsyncSession = Depends(get_db),
) -> AnalyzeResult:
    """Analyze a trend keyword using the configured LLM provider.

    Returns business insight, sentiment polarity, and 5 related keywords.
    Result is persisted to the ``ai_insights`` table.
    """
    return await analyze_keyword(keyword=body.keyword, db=db)


@router.post("/brief", summary="手动触发每日简报生成", response_model=BriefResponse)
async def create_brief(db: AsyncSession = Depends(get_db)) -> BriefResponse:
    """Generate today's daily trend brief via AI and persist it.

    If a brief for today already exists it will be regenerated.
    Sends an email if SMTP is configured.
    """
    brief = await generate_daily_brief(db=db)
    return BriefResponse(
        id=brief.id,
        date=brief.date,
        content=brief.content,
        model=brief.model,
        created_at=brief.created_at,
    )


@router.get("/brief/latest", summary="获取最新每日简报", response_model=BriefResponse)
async def latest_brief(db: AsyncSession = Depends(get_db)) -> BriefResponse:
    """Return the most recently generated daily brief."""
    brief = await get_latest_brief(db=db)
    if brief is None:
        raise HTTPException(status_code=404, detail="No daily brief found")
    return BriefResponse(
        id=brief.id,
        date=brief.date,
        content=brief.content,
        model=brief.model,
        created_at=brief.created_at,
    )
