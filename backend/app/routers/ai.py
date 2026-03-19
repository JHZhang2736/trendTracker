"""AI router — keyword analysis endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.ai import AnalyzeRequest, AnalyzeResult
from app.services.ai import analyze_keyword

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
