"""Alert service — keyword monitoring rules and threshold-triggered email alerts."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.alert_log import AlertLog
from app.models.keyword import Keyword
from app.models.keyword_alert import KeywordAlert
from app.models.trend import Trend
from app.schemas.alerts import AlertRuleResponse
from app.services.email import send_email

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# CRUD helpers
# ---------------------------------------------------------------------------


async def create_alert_rule(
    keyword: str,
    threshold: float,
    notify_email: str,
    db: AsyncSession,
) -> AlertRuleResponse:
    """Create (or reactivate) a keyword monitoring rule.

    If the keyword already exists in the ``keywords`` table it is reused.
    A new ``KeywordAlert`` row is always created.
    """
    # Upsert Keyword row
    result = await db.execute(select(Keyword).where(Keyword.keyword == keyword))
    kw_row = result.scalar_one_or_none()
    if kw_row is None:
        kw_row = Keyword(keyword=keyword)
        db.add(kw_row)
        await db.flush()

    alert = KeywordAlert(
        keyword_id=kw_row.id,
        threshold=threshold,
        notify_email=notify_email,
        is_active=True,
    )
    db.add(alert)
    await db.commit()
    await db.refresh(alert)

    return AlertRuleResponse(
        id=alert.id,
        keyword=kw_row.keyword,
        threshold=alert.threshold,
        notify_email=alert.notify_email,
        is_active=alert.is_active,
        created_at=kw_row.created_at,
    )


async def list_alert_rules(db: AsyncSession) -> list[AlertRuleResponse]:
    """Return all active alert rules with their keyword text."""
    result = await db.execute(
        select(KeywordAlert)
        .where(KeywordAlert.is_active == True)  # noqa: E712
        .options(selectinload(KeywordAlert.keyword_rel))
        .order_by(KeywordAlert.id)
    )
    rules = result.scalars().all()
    return [
        AlertRuleResponse(
            id=r.id,
            keyword=r.keyword_rel.keyword,
            threshold=r.threshold,
            notify_email=r.notify_email,
            is_active=r.is_active,
            created_at=r.keyword_rel.created_at,
        )
        for r in rules
    ]


# ---------------------------------------------------------------------------
# Threshold check — called after each collection run
# ---------------------------------------------------------------------------


async def check_alerts(db: AsyncSession) -> int:
    """Check all active alert rules against recent trend data.

    For each active rule, look at trends collected in the last hour.
    If any trend for that keyword exceeds the threshold, send an email and
    write an ``AlertLog`` row.

    Returns the number of alerts fired.
    """
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    since = now - timedelta(hours=1)

    # Load all active rules with their keywords
    result = await db.execute(
        select(KeywordAlert)
        .where(KeywordAlert.is_active == True)  # noqa: E712
        .options(selectinload(KeywordAlert.keyword_rel))
    )
    rules = result.scalars().all()
    if not rules:
        return 0

    fired = 0
    for rule in rules:
        kw_text = rule.keyword_rel.keyword

        # Find recent trends that match keyword and exceed threshold
        trend_result = await db.execute(
            select(Trend).where(
                Trend.keyword == kw_text,
                Trend.collected_at >= since,
                Trend.heat_score >= rule.threshold,
            )
        )
        matches = trend_result.scalars().all()
        if not matches:
            continue

        best = max(matches, key=lambda t: t.heat_score or 0)
        matched_info = f"{kw_text} heat={best.heat_score} platform={best.platform}"

        # Write alert log
        log = AlertLog(
            keyword_id=rule.keyword_rel.id,
            triggered_at=now,
            matched_keywords=matched_info,
            notified=False,
        )
        db.add(log)
        await db.flush()

        # Send email
        subject = "[TrendTracker] " + kw_text + " heat=" + str(best.heat_score)
        body = (
            "keyword="
            + kw_text
            + " platform="
            + best.platform
            + " heat="
            + str(best.heat_score)
            + " threshold="
            + str(rule.threshold)
            + "\ncollected_at="
            + str(best.collected_at)
        )
        notified = await send_email(subject=subject, body=body, to=rule.notify_email)
        log.notified = notified
        fired += 1
        logger.info("check_alerts: fired alert for keyword=%r heat=%s", kw_text, best.heat_score)

    await db.commit()
    return fired
