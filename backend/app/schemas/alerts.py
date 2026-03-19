"""Pydantic schemas for alert keyword endpoints."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, field_validator


class AlertRuleCreate(BaseModel):
    keyword: str
    threshold: float
    notify_email: str

    @field_validator("threshold")
    @classmethod
    def threshold_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("threshold must be positive")
        return v


class AlertRuleResponse(BaseModel):
    id: int
    keyword: str
    threshold: float
    notify_email: str | None
    is_active: bool
    created_at: datetime


class AlertRulesResponse(BaseModel):
    items: list[AlertRuleResponse]
