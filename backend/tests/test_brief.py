"""Tests for daily brief generation and /ai/brief endpoints."""

from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.base import ChatResponse
from app.models.daily_brief import DailyBrief
from app.models.trend import Trend

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_BRIEF_CONTENT = "今日热词聚焦于科技与消费领域，建议关注相关赛道投资机会。"
_MOCK_CHAT_RESPONSE = ChatResponse(
    content=_BRIEF_CONTENT,
    model="abab6.5s-chat",
    usage={"prompt_tokens": 80, "completion_tokens": 60},
)


def _patch_llm():
    """Patch LLMFactory.create() to return a mock provider."""
    mock_provider = MagicMock()
    mock_provider.chat = AsyncMock(return_value=_MOCK_CHAT_RESPONSE)
    return patch("app.services.brief.LLMFactory.create", return_value=mock_provider)


def _patch_email():
    """Patch send_email to avoid real SMTP calls."""
    return patch("app.services.brief.send_email", new=AsyncMock(return_value=False))


async def _seed_trend(db: AsyncSession, keyword: str) -> None:
    from datetime import datetime, timezone

    db.add(
        Trend(
            platform="weibo",
            keyword=keyword,
            rank=0,
            heat_score=9000.0,
            collected_at=datetime.now(timezone.utc).replace(tzinfo=None),
            relevance_label="relevant",
            relevance_score=90.0,
        )
    )
    await db.commit()


# ---------------------------------------------------------------------------
# Unit tests: generate_daily_brief
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_brief_returns_daily_brief(db_session: AsyncSession):
    with _patch_llm(), _patch_email():
        from app.services.brief import generate_daily_brief

        brief = await generate_daily_brief(db=db_session, send_mail=False)

    assert isinstance(brief, DailyBrief)
    assert brief.id is not None
    assert brief.date == date.today()
    assert brief.content == _BRIEF_CONTENT


@pytest.mark.asyncio
async def test_generate_brief_uses_top_keywords(db_session: AsyncSession):
    await _seed_trend(db_session, "人工智能")
    await _seed_trend(db_session, "新能源")

    captured_messages = []

    async def capture_chat(messages, **kwargs):
        captured_messages.extend(messages)
        return _MOCK_CHAT_RESPONSE

    mock_provider = MagicMock()
    mock_provider.chat = capture_chat

    with patch("app.services.brief.LLMFactory.create", return_value=mock_provider), _patch_email():
        from app.services.brief import generate_daily_brief

        await generate_daily_brief(db=db_session, send_mail=False)

    user_msg = next(m for m in captured_messages if m.role == "user")
    assert "人工智能" in user_msg.content
    assert "新能源" in user_msg.content


@pytest.mark.asyncio
async def test_generate_brief_upserts_on_same_day(db_session: AsyncSession):
    with _patch_llm(), _patch_email():
        from app.services.brief import generate_daily_brief

        brief1 = await generate_daily_brief(db=db_session, send_mail=False)
        brief2 = await generate_daily_brief(db=db_session, send_mail=False)

    # Same row updated, not a second row
    assert brief1.id == brief2.id


@pytest.mark.asyncio
async def test_generate_brief_sends_email_when_configured(db_session: AsyncSession):
    mock_send = AsyncMock(return_value=True)
    with _patch_llm(), patch("app.services.brief.send_email", new=mock_send):
        from app.services.brief import generate_daily_brief

        await generate_daily_brief(db=db_session, send_mail=True)

    mock_send.assert_called_once()
    call_kwargs = mock_send.call_args
    assert "TrendTracker" in call_kwargs.kwargs.get("subject", "") or "TrendTracker" in str(
        call_kwargs
    )


@pytest.mark.asyncio
async def test_generate_brief_skips_email_when_send_mail_false(db_session: AsyncSession):
    mock_send = AsyncMock(return_value=False)
    with _patch_llm(), patch("app.services.brief.send_email", new=mock_send):
        from app.services.brief import generate_daily_brief

        await generate_daily_brief(db=db_session, send_mail=False)

    mock_send.assert_not_called()


@pytest.mark.asyncio
async def test_get_latest_brief_returns_none_when_empty(db_session: AsyncSession):
    from app.services.brief import get_latest_brief

    result = await get_latest_brief(db=db_session)
    assert result is None


@pytest.mark.asyncio
async def test_get_latest_brief_returns_most_recent(db_session: AsyncSession):
    with _patch_llm(), _patch_email():
        from app.services.brief import generate_daily_brief, get_latest_brief

        await generate_daily_brief(db=db_session, send_mail=False)
        latest = await get_latest_brief(db=db_session)

    assert latest is not None
    assert latest.content == _BRIEF_CONTENT


# ---------------------------------------------------------------------------
# Integration tests: POST /api/v1/ai/brief and GET /api/v1/ai/brief/latest
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_brief_endpoint_returns_200(test_client: AsyncClient):
    with _patch_llm(), _patch_email():
        resp = await test_client.post("/api/v1/ai/brief")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_create_brief_endpoint_response_schema(test_client: AsyncClient):
    with _patch_llm(), _patch_email():
        data = (await test_client.post("/api/v1/ai/brief")).json()
    required = {"id", "date", "content", "model", "created_at"}
    assert required <= set(data.keys())
    assert data["content"] == _BRIEF_CONTENT


@pytest.mark.asyncio
async def test_latest_brief_returns_404_when_none(test_client: AsyncClient):
    resp = await test_client.get("/api/v1/ai/brief/latest")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_latest_brief_returns_200_after_creation(test_client: AsyncClient):
    with _patch_llm(), _patch_email():
        await test_client.post("/api/v1/ai/brief")
        resp = await test_client.get("/api/v1/ai/brief/latest")
    assert resp.status_code == 200
    data = resp.json()
    assert data["content"] == _BRIEF_CONTENT


@pytest.mark.asyncio
async def test_latest_brief_date_is_today(test_client: AsyncClient):
    with _patch_llm(), _patch_email():
        await test_client.post("/api/v1/ai/brief")
        data = (await test_client.get("/api/v1/ai/brief/latest")).json()
    assert data["date"] == date.today().isoformat()


# ---------------------------------------------------------------------------
# Scheduler registration test
# ---------------------------------------------------------------------------


def test_scheduler_registers_daily_brief_job():
    from app.services.scheduler import setup_scheduler

    sched = setup_scheduler()
    job = sched.get_job("daily_brief")
    assert job is not None
    assert "08" in str(job.trigger) or "CronTrigger" in type(job.trigger).__name__
