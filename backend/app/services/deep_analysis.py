"""Deep analysis service — web search + AI for structured business reports.

Stage 3 of the AI pipeline: takes the highest-scored keywords, searches the
web for context, and generates a structured deep analysis report.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.base import ChatMessage
from app.ai.factory import LLMFactory
from app.config import settings
from app.models.ai_insight import AIInsight
from app.search.base import SearchResult
from app.search.factory import SearchFactory

logger = logging.getLogger(__name__)

_DEEP_ANALYSIS_SYSTEM_PROMPT = (
    "你是一个资深商业趋势分析师。根据用户提供的热搜关键词和网络搜索结果，"
    "进行深度商业分析。\n\n"
    "严格以如下 JSON 格式返回（不要有任何额外文字）：\n"
    "{\n"
    '  "background": "事件背景，100-200字",\n'
    '  "opportunity": "商业机会分析，100-200字",\n'
    '  "risk": "潜在风险，50-100字",\n'
    '  "action": "建议行动，50-100字",\n'
    '  "sentiment": "positive 或 negative 或 neutral"\n'
    "}"
)


async def deep_analyze_keyword(
    keyword: str,
    db: AsyncSession,
    analysis_type: str = "manual",
) -> dict | None:
    """Perform deep analysis on a keyword with web search context.

    Returns the analysis result dict, or None if the keyword was recently
    analyzed (within cooldown window).
    """
    # Check 24h cooldown
    cooldown_hours = settings.deep_analysis_cooldown_hours
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=cooldown_hours)
    existing = await db.execute(
        select(AIInsight).where(
            AIInsight.keyword == keyword,
            AIInsight.deep_analysis.isnot(None),
            AIInsight.created_at >= cutoff,
        )
    )
    cached = existing.scalar_one_or_none()
    if cached:
        logger.info("Deep analysis cache hit for '%s' (id=%d)", keyword, cached.id)
        return _insight_to_dict(cached, cached=True)

    # Step 1: Web search
    search_results = await _web_search(keyword)

    # Step 2: LLM deep analysis
    analysis = await _llm_analyze(keyword, search_results)
    if analysis is None:
        return None

    # Step 3: Persist to AIInsight
    source_urls = [r.url for r in search_results if r.url]
    insight = AIInsight(
        keyword=keyword,
        insight_type="deep_analysis",
        content=json.dumps(analysis, ensure_ascii=False),
        model=settings.llm_provider,
        search_context=json.dumps(
            [{"title": r.title, "snippet": r.snippet, "url": r.url} for r in search_results],
            ensure_ascii=False,
        ),
        deep_analysis=json.dumps(analysis, ensure_ascii=False),
        source_urls=json.dumps(source_urls, ensure_ascii=False),
        analysis_type=analysis_type,
    )
    db.add(insight)
    await db.commit()
    await db.refresh(insight)

    logger.info(
        "Deep analysis completed for '%s' (id=%d, type=%s)",
        keyword,
        insight.id,
        analysis_type,
    )
    return _insight_to_dict(insight, cached=False)


async def auto_deep_analyze(
    db: AsyncSession,
    scored_keywords: dict[str, dict],
    limit: int | None = None,
) -> list[dict]:
    """Automatically deep-analyze top-scored keywords after collection.

    Args:
        db: Database session.
        scored_keywords: Dict from score_relevance() with {keyword: {score, label, reason}}.
        limit: Max keywords to analyze. Defaults to settings.deep_analysis_auto_limit.

    Returns:
        List of analysis result dicts.
    """
    if limit is None:
        limit = settings.deep_analysis_auto_limit

    if limit <= 0:
        return []

    # Sort by score descending, take top N relevant keywords
    relevant = [
        (kw, info)
        for kw, info in scored_keywords.items()
        if info.get("label") == "relevant" and info.get("score", 0) > 0
    ]
    relevant.sort(key=lambda x: x[1].get("score", 0), reverse=True)
    top_keywords = [kw for kw, _ in relevant[:limit]]

    if not top_keywords:
        return []

    logger.info("Auto deep analysis: analyzing %d keywords: %s", len(top_keywords), top_keywords)

    results = []
    for kw in top_keywords:
        try:
            result = await deep_analyze_keyword(kw, db, analysis_type="auto")
            if result:
                results.append(result)
        except Exception:
            logger.exception("Auto deep analysis failed for '%s'", kw)

    return results


async def get_deep_analysis(keyword: str, db: AsyncSession) -> dict | None:
    """Retrieve the most recent deep analysis for a keyword."""
    result = await db.execute(
        select(AIInsight)
        .where(
            AIInsight.keyword == keyword,
            AIInsight.deep_analysis.isnot(None),
        )
        .order_by(AIInsight.created_at.desc())
        .limit(1)
    )
    insight = result.scalar_one_or_none()
    if insight is None:
        return None
    return _insight_to_dict(insight, cached=True)


async def list_deep_analyses(db: AsyncSession, limit: int = 50) -> list[dict]:
    """Return all deep analyses, most recent first."""
    result = await db.execute(
        select(AIInsight)
        .where(AIInsight.deep_analysis.isnot(None))
        .order_by(AIInsight.created_at.desc())
        .limit(limit)
    )
    insights = result.scalars().all()
    return [_insight_to_dict(ins, cached=True) for ins in insights]


async def _web_search(keyword: str) -> list[SearchResult]:
    """Search the web for context about a keyword."""
    try:
        provider = SearchFactory.create()
        results = await provider.search(keyword, max_results=5)
        logger.info("Web search for '%s': got %d results", keyword, len(results))
        return results
    except Exception:
        logger.exception("Web search failed for '%s'", keyword)
        return []


async def _llm_analyze(keyword: str, search_results: list[SearchResult]) -> dict | None:
    """Call LLM with keyword + search context for deep analysis."""
    # Build context from search results
    if search_results:
        context_lines = []
        for i, r in enumerate(search_results, 1):
            context_lines.append(f"{i}. {r.title}\n   {r.snippet}\n   来源: {r.url}")
        search_context = "\n\n".join(context_lines)
    else:
        search_context = "（无搜索结果，请基于你已有的知识进行分析）"

    user_content = (
        f"## 热搜关键词\n{keyword}\n\n"
        f"## 网络搜索结果\n{search_context}\n\n"
        "请基于以上信息进行深度商业分析。"
    )

    try:
        provider = LLMFactory.create()
        response = await provider.chat(
            messages=[
                ChatMessage(role="system", content=_DEEP_ANALYSIS_SYSTEM_PROMPT),
                ChatMessage(role="user", content=user_content),
            ],
            temperature=0.3,
            max_tokens=2048,
        )

        raw = response.content.strip()
        logger.warning("Deep analysis LLM raw response: %s", raw[:500])

        # Strip code fences
        if raw.startswith("```"):
            lines = raw.split("\n")
            lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            raw = "\n".join(lines).strip()

        parsed = json.loads(raw)

        # Normalize
        sentiment = parsed.get("sentiment", "neutral")
        if sentiment not in {"positive", "negative", "neutral"}:
            sentiment = "neutral"

        return {
            "background": parsed.get("background", ""),
            "opportunity": parsed.get("opportunity", ""),
            "risk": parsed.get("risk", ""),
            "action": parsed.get("action", ""),
            "sentiment": sentiment,
        }
    except json.JSONDecodeError:
        logger.warning("Deep analysis: LLM response not valid JSON for '%s'", keyword)
        return None
    except Exception:
        logger.exception("Deep analysis LLM call failed for '%s'", keyword)
        return None


def _insight_to_dict(insight: AIInsight, cached: bool = False) -> dict:
    """Convert an AIInsight record to a response dict."""
    deep = {}
    if insight.deep_analysis:
        try:
            deep = json.loads(insight.deep_analysis)
        except json.JSONDecodeError:
            deep = {"background": insight.deep_analysis}

    source_urls = []
    if insight.source_urls:
        try:
            source_urls = json.loads(insight.source_urls)
        except json.JSONDecodeError:
            pass

    search_count = 0
    if insight.search_context:
        try:
            search_count = len(json.loads(insight.search_context))
        except (json.JSONDecodeError, TypeError):
            pass

    return {
        "id": insight.id,
        "keyword": insight.keyword,
        "deep_analysis": deep,
        "source_urls": source_urls,
        "search_results_count": search_count,
        "analysis_type": insight.analysis_type,
        "model": insight.model,
        "created_at": insight.created_at.isoformat() if insight.created_at else None,
        "cached": cached,
    }
