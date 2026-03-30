"""Deep analysis service — web search + AI for structured business reports.

Stage 3 of the AI pipeline: takes the highest-scored keywords, searches the
web for context, and generates a structured deep analysis report.
"""

from __future__ import annotations

import asyncio
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

_DEEP_ANALYSIS_SYSTEM_PROMPT_TEMPLATE = (
    "你是一个资深新闻分析师和商业顾问。根据用户提供的热搜关键词和网络搜索结果，"
    "先客观概述事件，再从多个商业视角分析机会。\n\n"
    "用户画像：{user_profile}\n\n"
    "请结合用户的实际情况（资源、能力、阶段）给出切实可行的建议，"
    "不要建议需要大量资金或资源的方案。\n\n"
    "严格以如下 JSON 格式返回（不要有任何额外文字）：\n"
    "{{\n"
    '  "summary": "新闻概述，200-300字，客观陈述事件经过和影响",\n'
    '  "key_facts": ["核心要点1", "核心要点2", "核心要点3"],\n'
    '  "opportunities": [\n'
    '    {{"angle": "视角名称", "idea": "具体分析，50-100字"}}\n'
    "  ],\n"
    '  "risk": "潜在风险，50-100字",\n'
    '  "action": "用户当前最值得尝试的1-2个具体行动，50-100字",\n'
    '  "sentiment": "positive 或 negative 或 neutral"\n'
    "}}\n\n"
    "要求：\n"
    "- summary 以新闻报道风格撰写，客观中立，包含时间、人物、事件等要素\n"
    "- key_facts 提取 3-5 个最重要的事实要点，每条 20-40 字\n"
    "- opportunities 必须包含以下视角（跳过明显不适用的）：\n"
    "  · 技术/产品：能否开发工具、插件、SaaS、小程序\n"
    "  · 内容/传播：能否做自媒体、短视频、教程、知识付费\n"
    "  · 电商/选品：能否在电商平台卖相关产品或服务\n"
    "  · 投资/市场：对投资决策、市场走势有什么启示"
)

# Runtime display mode — controls frontend visibility of business analysis section
_runtime_show_business: bool | None = None


def get_show_business() -> bool:
    """Return whether the business analysis section should be displayed."""
    if _runtime_show_business is not None:
        return _runtime_show_business
    return settings.deep_analysis_mode != "news"


def set_show_business(show: bool) -> None:
    """Set the runtime display mode for business analysis."""
    global _runtime_show_business  # noqa: PLW0603
    _runtime_show_business = show


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
) -> list[dict]:
    """Automatically deep-analyze top-scored keywords after collection.

    Selects the top ``deep_analysis_auto_ratio`` fraction of relevant keywords,
    capped at ``deep_analysis_auto_max``.

    Args:
        db: Database session.
        scored_keywords: Dict from score_relevance() with {keyword: {score, label, reason}}.

    Returns:
        List of analysis result dicts.
    """
    ratio = settings.deep_analysis_auto_ratio
    max_cap = settings.deep_analysis_auto_max

    if ratio <= 0 or max_cap <= 0:
        return []

    # Sort by score descending
    relevant = [
        (kw, info)
        for kw, info in scored_keywords.items()
        if info.get("label") == "relevant" and info.get("score", 0) > 0
    ]
    relevant.sort(key=lambda x: x[1].get("score", 0), reverse=True)

    # Take top ratio%, capped at max
    count = max(1, int(len(relevant) * ratio)) if relevant else 0
    count = min(count, max_cap)
    top_keywords = [kw for kw, _ in relevant[:count]]

    if not top_keywords:
        return []

    logger.info("Auto deep analysis: analyzing %d keywords: %s", len(top_keywords), top_keywords)

    # Concurrent analysis via asyncio.Queue worker pool
    _da_workers = 3
    queue: asyncio.Queue[str] = asyncio.Queue()
    for kw in top_keywords:
        queue.put_nowait(kw)

    results: list[dict] = []
    lock = asyncio.Lock()

    async def worker() -> None:
        while True:
            kw = await queue.get()
            try:
                result = await deep_analyze_keyword(kw, db, analysis_type="auto")
                if result:
                    async with lock:
                        results.append(result)
            except Exception:
                logger.exception("Auto deep analysis failed for '%s'", kw)
            finally:
                queue.task_done()

    workers = [asyncio.create_task(worker()) for _ in range(min(_da_workers, len(top_keywords)))]
    await queue.join()
    for w in workers:
        w.cancel()

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
    """Search the web for context about a keyword.

    Uses fallback chain: if the primary provider returns 0 results (after its
    own retries), the next provider in the chain is tried automatically.
    """
    try:
        results = await SearchFactory.search_with_fallback(keyword, max_results=5)
        if results:
            logger.info("Web search for '%s': got %d results", keyword, len(results))
        else:
            logger.warning("Web search for '%s': all providers returned 0 results", keyword)
        return results
    except Exception:
        logger.exception("Web search failed for '%s'", keyword)
        return []


async def _llm_analyze(keyword: str, search_results: list[SearchResult]) -> dict | None:
    """Call LLM with keyword + search context — returns both summary and business analysis."""
    # Build context from search results
    if search_results:
        context_lines = []
        for i, r in enumerate(search_results, 1):
            context_lines.append(f"{i}. {r.title}\n   {r.snippet}\n   来源: {r.url}")
        search_context = "\n\n".join(context_lines)
    else:
        search_context = "（无搜索结果，请基于你已有的知识进行分析）"

    system_prompt = _DEEP_ANALYSIS_SYSTEM_PROMPT_TEMPLATE.format(
        user_profile=settings.user_profile,
    )

    user_content = (
        f"## 热搜关键词\n{keyword}\n\n"
        f"## 网络搜索结果\n{search_context}\n\n"
        "请基于以上信息进行分析。"
    )

    try:
        provider = LLMFactory.create()
        response = await provider.chat(
            messages=[
                ChatMessage(role="system", content=system_prompt),
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

        # Normalize sentiment
        sentiment = parsed.get("sentiment", "neutral")
        if sentiment not in {"positive", "negative", "neutral"}:
            sentiment = "neutral"

        # Normalize key_facts
        key_facts = parsed.get("key_facts", [])
        if not isinstance(key_facts, list):
            key_facts = []

        # Normalize opportunities
        raw_opps = parsed.get("opportunities", [])
        if isinstance(raw_opps, list):
            opportunities = [
                {"angle": o.get("angle", ""), "idea": o.get("idea", "")}
                for o in raw_opps
                if isinstance(o, dict)
            ]
        else:
            opportunities = []

        # Backward compat: if old "opportunity" string exists and no array
        legacy_opp = parsed.get("opportunity", "")
        if not opportunities and legacy_opp:
            opportunities = [{"angle": "综合", "idea": legacy_opp}]

        return {
            "summary": parsed.get("summary", ""),
            "key_facts": key_facts,
            "opportunities": opportunities,
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
    deep: dict = {}
    if insight.deep_analysis:
        try:
            deep = json.loads(insight.deep_analysis)
        except json.JSONDecodeError:
            deep = {"summary": insight.deep_analysis}

    # Remove legacy mode field if present
    deep.pop("mode", None)

    # Normalize legacy "opportunity" string → "opportunities" array
    if "opportunity" in deep and "opportunities" not in deep:
        opp = deep.pop("opportunity", "")
        deep["opportunities"] = [{"angle": "综合", "idea": opp}] if opp else []
    if "opportunities" not in deep:
        deep["opportunities"] = []
    if "key_facts" not in deep:
        deep["key_facts"] = []
    # Backward compat: old records without summary — use background as fallback
    if not deep.get("summary") and deep.get("background"):
        deep["summary"] = deep["background"]

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
