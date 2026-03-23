"""Daily brief service — AI-generated trend summary + optional email push."""

from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.base import ChatMessage
from app.ai.factory import LLMFactory
from app.config import settings
from app.models.ai_insight import AIInsight
from app.models.daily_brief import DailyBrief
from app.services.email import send_email
from app.services.signals import get_recent_signals
from app.services.trends import get_top_trends

logger = logging.getLogger(__name__)

_BRIEF_SYSTEM_PROMPT_TEMPLATE = (
    "你是一个商业趋势分析师。根据用户提供的趋势信号和热门关键词，"
    "生成一份简洁的商业趋势简报，300字以内，突出关键机会与风险。"
    "优先分析趋势信号中标注的突增、新面孔和排名跃升词。"
    "{user_profile_section}"
    "{deep_analysis_instruction}"
)


def _build_system_prompt(has_deep_analyses: bool) -> str:
    """Build the system prompt with optional user profile and deep analysis instructions."""
    if settings.user_profile:
        user_profile_section = (
            f"\n\n用户画像：{settings.user_profile}\n"
            "请结合用户的背景和兴趣，给出与其实际情况相关的商业建议。"
        )
    else:
        user_profile_section = ""

    if has_deep_analyses:
        deep_analysis_instruction = (
            "\n\n用户还提供了部分关键词的深度分析结果，请优先引用这些已有分析，"
            "在此基础上补充整合，避免重复分析。"
        )
    else:
        deep_analysis_instruction = ""

    return _BRIEF_SYSTEM_PROMPT_TEMPLATE.format(
        user_profile_section=user_profile_section,
        deep_analysis_instruction=deep_analysis_instruction,
    )


async def _get_recent_deep_analyses(db: AsyncSession, hours: int = 24) -> list[dict]:
    """Fetch recent deep analysis summaries for brief context."""
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=hours)
    result = await db.execute(
        select(AIInsight)
        .where(
            AIInsight.deep_analysis.isnot(None),
            AIInsight.created_at >= cutoff,
        )
        .order_by(AIInsight.created_at.desc())
        .limit(5)
    )
    insights = result.scalars().all()

    summaries = []
    for ins in insights:
        try:
            deep = json.loads(ins.deep_analysis)
        except (json.JSONDecodeError, TypeError):
            continue

        # Extract concise summary from the structured analysis
        background = deep.get("background", "")
        action = deep.get("action", "")
        sentiment = deep.get("sentiment", "")
        opportunities = deep.get("opportunities", [])
        opp_text = "；".join(
            o.get("idea", "") for o in opportunities if isinstance(o, dict) and o.get("idea")
        )

        summary = f"关键词「{ins.keyword}」：{background}"
        if opp_text:
            summary += f" 机会：{opp_text}"
        if action:
            summary += f" 建议行动：{action}"
        if sentiment:
            summary += f"（情感：{sentiment}）"

        summaries.append(summary)

    return summaries


async def generate_daily_brief(db: AsyncSession) -> DailyBrief:
    """Generate today's brief and persist it.

    Signal-driven: prioritizes recent signals, falls back to top keywords.
    Injects user_profile for personalized advice and references recent deep analyses.
    If a brief for today already exists it will be overwritten.
    """
    today = date.today()

    # Whether to only use relevant content (based on AI relevance filter config)
    use_relevant = settings.relevance_filter_enabled

    # 1. Try signal-driven: use recent 24h signals as primary input
    signals = await get_recent_signals(db, hours=24, limit=10)
    # Filter signals to only include relevant keywords when relevance filter is on
    if use_relevant:
        signals = await _filter_relevant_signals(db, signals)
    signal_lines = []
    for sig in signals:
        line = f"[{sig.signal_type}] {sig.platform}: {sig.keyword} — {sig.description}"
        signal_lines.append(line)

    # 2. Fallback: top-20 keywords from the last 24h (relevant only when filter is on)
    top = await get_top_trends(db=db, limit=20, relevant_only=use_relevant)
    keywords = [item["keyword"] for item in top]

    # 3. Fetch recent deep analyses as additional context
    deep_summaries = await _get_recent_deep_analyses(db)

    if signal_lines:
        signals_text = "\n".join(signal_lines)
        keyword_text = "、".join(keywords[:10]) if keywords else "无"
        user_msg = f"今日趋势信号：\n{signals_text}\n\n热门关键词：{keyword_text}"
    elif keywords:
        keyword_list = "、".join(keywords)
        user_msg = f"今日热词（按热度排序）：{keyword_list}"
    else:
        user_msg = "今日暂无热词数据，请生成一份通用商业趋势展望简报。"

    if deep_summaries:
        deep_text = "\n".join(f"- {s}" for s in deep_summaries)
        user_msg += f"\n\n已有深度分析：\n{deep_text}"

    system_prompt = _build_system_prompt(has_deep_analyses=bool(deep_summaries))

    provider = LLMFactory.create()
    response = await provider.chat(
        messages=[
            ChatMessage(role="system", content=system_prompt),
            ChatMessage(role="user", content=user_msg),
        ]
    )
    content = response.content
    model = response.model

    # Upsert: update if today's row exists, otherwise insert
    result = await db.execute(select(DailyBrief).where(DailyBrief.date == today))
    brief = result.scalar_one_or_none()
    if brief is None:
        brief = DailyBrief(
            date=today,
            content=content,
            model=model,
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        db.add(brief)
    else:
        brief.content = content
        brief.model = model
        brief.created_at = datetime.now(timezone.utc).replace(tzinfo=None)

    await db.commit()
    await db.refresh(brief)

    # Send email notification with the brief content
    await send_email(
        subject=f"TrendTracker 每日简报 — {today}",
        body=content,
    )

    return brief


async def get_latest_brief(db: AsyncSession) -> DailyBrief | None:
    """Return the most recently created daily brief, or None if none exist."""
    result = await db.execute(select(DailyBrief).order_by(DailyBrief.created_at.desc()).limit(1))
    return result.scalar_one_or_none()


async def _filter_relevant_signals(
    db: AsyncSession,
    signals: list,
) -> list:
    """Keep only signals whose keyword is marked 'relevant' in the Trend table."""
    from app.models.trend import Trend

    filtered = []
    for sig in signals:
        result = await db.execute(
            select(Trend.relevance_label)
            .where(Trend.keyword == sig.keyword, Trend.platform == sig.platform)
            .order_by(Trend.collected_at.desc())
            .limit(1)
        )
        label = result.scalar()
        if label == "relevant":
            filtered.append(sig)
    return filtered
