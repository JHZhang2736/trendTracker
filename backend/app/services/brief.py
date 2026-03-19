"""Daily brief service — AI-generated trend summary + optional email push."""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.base import ChatMessage
from app.ai.factory import LLMFactory
from app.models.daily_brief import DailyBrief
from app.services.email import send_email
from app.services.trends import get_top_trends

logger = logging.getLogger(__name__)

_BRIEF_SYSTEM_PROMPT = (
    "你是一个商业趋势分析师。根据用户提供的今日热门关键词列表，"
    "生成一份简洁的商业趋势简报，300字以内，突出关键机会与风险。"
)


async def generate_daily_brief(db: AsyncSession, send_mail: bool = True) -> DailyBrief:
    """Generate today's brief, persist it, and optionally email it.

    If a brief for today already exists it will be overwritten.
    """
    today = date.today()

    # Fetch top-20 keywords from the last 24h
    top = await get_top_trends(db=db, limit=20)
    keywords = [item["keyword"] for item in top]

    if keywords:
        keyword_list = "、".join(keywords)
        user_msg = f"今日热词（按热度排序）：{keyword_list}"
    else:
        user_msg = "今日暂无热词数据，请生成一份通用商业趋势展望简报。"

    provider = LLMFactory.create()
    response = await provider.chat(
        messages=[
            ChatMessage(role="system", content=_BRIEF_SYSTEM_PROMPT),
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

    if send_mail:
        await send_email(
            subject=f"TrendTracker 每日简报 {today}",
            body=content,
        )

    return brief


async def get_latest_brief(db: AsyncSession) -> DailyBrief | None:
    """Return the most recently created daily brief, or None if none exist."""
    result = await db.execute(select(DailyBrief).order_by(DailyBrief.created_at.desc()).limit(1))
    return result.scalar_one_or_none()
