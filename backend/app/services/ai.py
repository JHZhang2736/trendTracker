"""AI service — keyword analysis via LLM, persisted to ai_insights table."""

from __future__ import annotations

import json
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.factory import LLMFactory
from app.models.ai_insight import AIInsight
from app.schemas.ai import AnalyzeResult

logger = logging.getLogger(__name__)


async def analyze_keyword(keyword: str, db: AsyncSession) -> AnalyzeResult:
    """Call the configured LLM provider to analyze a trend keyword.

    Persists the result to the ``ai_insights`` table and returns a structured
    :class:`~app.schemas.ai.AnalyzeResult`.
    """
    provider = LLMFactory.create()
    response = await provider.analyze(keyword=keyword)

    # response.content is JSON-encoded structured data
    try:
        structured = json.loads(response.content)
    except json.JSONDecodeError:
        structured = {
            "business_insight": response.content,
            "sentiment": "neutral",
            "related_keywords": [],
        }

    insight = AIInsight(
        keyword=keyword,
        insight_type=response.insight_type,
        content=response.content,
        model=response.model,
    )
    db.add(insight)
    await db.commit()
    await db.refresh(insight)

    sentiment = structured.get("sentiment", "neutral")
    if sentiment not in {"positive", "negative", "neutral"}:
        sentiment = "neutral"

    return AnalyzeResult(
        id=insight.id,
        keyword=keyword,
        business_insight=structured.get("business_insight", ""),
        sentiment=sentiment,
        related_keywords=structured.get("related_keywords", [])[:5],
        model=insight.model,
        created_at=insight.created_at,
    )
