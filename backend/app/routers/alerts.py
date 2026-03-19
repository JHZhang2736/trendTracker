"""Alerts router — keyword monitoring rule endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.alerts import AlertRuleCreate, AlertRuleResponse, AlertRulesResponse
from app.services.alerts import create_alert_rule, list_alert_rules

router = APIRouter()


@router.post("/keywords", summary="创建关键词监控规则", response_model=AlertRuleResponse)
async def create_rule(
    body: AlertRuleCreate,
    db: AsyncSession = Depends(get_db),
) -> AlertRuleResponse:
    """Create a keyword alert rule. Fires an email when heat_score exceeds threshold."""
    return await create_alert_rule(
        keyword=body.keyword,
        threshold=body.threshold,
        notify_email=body.notify_email,
        db=db,
    )


@router.get("/keywords", summary="列出所有监控规则", response_model=AlertRulesResponse)
async def list_rules(db: AsyncSession = Depends(get_db)) -> AlertRulesResponse:
    """Return all active keyword alert rules."""
    items = await list_alert_rules(db=db)
    return AlertRulesResponse(items=items)
