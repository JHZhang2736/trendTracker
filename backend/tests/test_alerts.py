"""Tests for keyword alert rules and threshold-triggered email alerts."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.trend import Trend


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _seed_trend(
    db: AsyncSession,
    keyword: str,
    heat: float,
    platform: str = "weibo",
    minutes_ago: int = 0,
) -> None:
    from datetime import timedelta

    collected = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=minutes_ago)
    db.add(Trend(platform=platform, keyword=keyword, rank=0, heat_score=heat, collected_at=collected))
    await db.commit()


def _patch_email(return_value: bool = True):
    return patch("app.services.alerts.send_email", new=AsyncMock(return_value=return_value))


# ---------------------------------------------------------------------------
# Unit tests: create_alert_rule / list_alert_rules
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_alert_rule_returns_response(db_session: AsyncSession):
    from app.services.alerts import create_alert_rule

    result = await create_alert_rule("AI大模型", 5000.0, "test@example.com", db_session)
    assert result.id is not None
    assert result.keyword == "AI大模型"
    assert result.threshold == 5000.0
    assert result.notify_email == "test@example.com"
    assert result.is_active is True


@pytest.mark.asyncio
async def test_create_alert_rule_reuses_existing_keyword(db_session: AsyncSession):
    from app.services.alerts import create_alert_rule

    r1 = await create_alert_rule("热词", 1000.0, "a@example.com", db_session)
    r2 = await create_alert_rule("热词", 2000.0, "b@example.com", db_session)
    # Different alert rows, but same keyword (different IDs on alert)
    assert r1.id != r2.id
    assert r1.keyword == r2.keyword == "热词"


@pytest.mark.asyncio
async def test_list_alert_rules_empty(db_session: AsyncSession):
    from app.services.alerts import list_alert_rules

    result = await list_alert_rules(db_session)
    assert result == []


@pytest.mark.asyncio
async def test_list_alert_rules_returns_created(db_session: AsyncSession):
    from app.services.alerts import create_alert_rule, list_alert_rules

    await create_alert_rule("词A", 1000.0, "x@example.com", db_session)
    await create_alert_rule("词B", 2000.0, "y@example.com", db_session)
    rules = await list_alert_rules(db_session)
    assert len(rules) == 2
    keywords = {r.keyword for r in rules}
    assert keywords == {"词A", "词B"}


# ---------------------------------------------------------------------------
# Unit tests: check_alerts
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_check_alerts_no_rules_returns_zero(db_session: AsyncSession):
    from app.services.alerts import check_alerts

    fired = await check_alerts(db_session)
    assert fired == 0


@pytest.mark.asyncio
async def test_check_alerts_fires_when_threshold_exceeded(db_session: AsyncSession):
    from app.services.alerts import check_alerts, create_alert_rule

    await create_alert_rule("双十一", 5000.0, "alert@example.com", db_session)
    await _seed_trend(db_session, "双十一", heat=9000.0)

    with _patch_email():
        fired = await check_alerts(db_session)

    assert fired == 1


@pytest.mark.asyncio
async def test_check_alerts_no_fire_below_threshold(db_session: AsyncSession):
    from app.services.alerts import check_alerts, create_alert_rule

    await create_alert_rule("双十一", 5000.0, "alert@example.com", db_session)
    await _seed_trend(db_session, "双十一", heat=3000.0)

    with _patch_email():
        fired = await check_alerts(db_session)

    assert fired == 0


@pytest.mark.asyncio
async def test_check_alerts_writes_alert_log(db_session: AsyncSession):
    from sqlalchemy import select

    from app.models.alert_log import AlertLog
    from app.services.alerts import check_alerts, create_alert_rule

    await create_alert_rule("新能源", 1000.0, "alert@example.com", db_session)
    await _seed_trend(db_session, "新能源", heat=8000.0)

    with _patch_email():
        await check_alerts(db_session)

    result = await db_session.execute(select(AlertLog))
    logs = result.scalars().all()
    assert len(logs) == 1
    assert "新能源" in logs[0].matched_keywords


@pytest.mark.asyncio
async def test_check_alerts_sends_email(db_session: AsyncSession):
    from app.services.alerts import check_alerts, create_alert_rule

    await create_alert_rule("元宇宙", 500.0, "alert@example.com", db_session)
    await _seed_trend(db_session, "元宇宙", heat=9999.0)

    mock_send = AsyncMock(return_value=True)
    with patch("app.services.alerts.send_email", new=mock_send):
        await check_alerts(db_session)

    mock_send.assert_called_once()
    call_kwargs = mock_send.call_args.kwargs
    assert "元宇宙" in call_kwargs.get("subject", "")


@pytest.mark.asyncio
async def test_check_alerts_marks_notified_true_on_email_success(db_session: AsyncSession):
    from sqlalchemy import select

    from app.models.alert_log import AlertLog
    from app.services.alerts import check_alerts, create_alert_rule

    await create_alert_rule("ChatGPT", 100.0, "alert@example.com", db_session)
    await _seed_trend(db_session, "ChatGPT", heat=5000.0)

    with patch("app.services.alerts.send_email", new=AsyncMock(return_value=True)):
        await check_alerts(db_session)

    result = await db_session.execute(select(AlertLog))
    log = result.scalars().first()
    assert log.notified is True


@pytest.mark.asyncio
async def test_check_alerts_ignores_old_trends(db_session: AsyncSession):
    from app.services.alerts import check_alerts, create_alert_rule

    await create_alert_rule("过时词", 1000.0, "alert@example.com", db_session)
    # 90 minutes old — outside the 1-hour window
    await _seed_trend(db_session, "过时词", heat=99999.0, minutes_ago=90)

    with _patch_email():
        fired = await check_alerts(db_session)

    assert fired == 0


# ---------------------------------------------------------------------------
# Integration tests: POST /api/v1/alerts/keywords and GET /api/v1/alerts/keywords
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_rule_endpoint_returns_200(test_client: AsyncClient):
    resp = await test_client.post(
        "/api/v1/alerts/keywords",
        json={"keyword": "AI", "threshold": 5000.0, "notify_email": "x@example.com"},
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_create_rule_endpoint_response_schema(test_client: AsyncClient):
    data = (
        await test_client.post(
            "/api/v1/alerts/keywords",
            json={"keyword": "AI", "threshold": 5000.0, "notify_email": "x@example.com"},
        )
    ).json()
    required = {"id", "keyword", "threshold", "notify_email", "is_active", "created_at"}
    assert required <= set(data.keys())
    assert data["keyword"] == "AI"
    assert data["threshold"] == 5000.0
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_create_rule_rejects_zero_threshold(test_client: AsyncClient):
    resp = await test_client.post(
        "/api/v1/alerts/keywords",
        json={"keyword": "AI", "threshold": 0.0, "notify_email": "x@example.com"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_list_rules_empty(test_client: AsyncClient):
    data = (await test_client.get("/api/v1/alerts/keywords")).json()
    assert data == {"items": []}


@pytest.mark.asyncio
async def test_list_rules_after_creation(test_client: AsyncClient):
    await test_client.post(
        "/api/v1/alerts/keywords",
        json={"keyword": "词X", "threshold": 1000.0, "notify_email": "x@example.com"},
    )
    data = (await test_client.get("/api/v1/alerts/keywords")).json()
    assert len(data["items"]) == 1
    assert data["items"][0]["keyword"] == "词X"


@pytest.mark.asyncio
async def test_collector_triggers_alert_check(test_client: AsyncClient, db_session: AsyncSession):
    """POST /collector/run should trigger check_alerts after persisting trends."""
    from app.services.alerts import create_alert_rule

    # The mock collector seeds weibo trends; set threshold low enough to fire
    await create_alert_rule("ChatGPT最新版", 100.0, "alert@example.com", db_session)

    mock_send = AsyncMock(return_value=True)
    with patch("app.services.alerts.send_email", new=mock_send):
        resp = await test_client.post("/api/v1/collector/run")

    assert resp.status_code == 200
    # Email should have been attempted for the matching keyword
    mock_send.assert_called()
