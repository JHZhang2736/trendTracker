"""Pydantic schemas for AI analysis endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class AnalyzeRequest(BaseModel):
    keyword: str


class AnalyzeResult(BaseModel):
    id: int
    keyword: str
    business_insight: str
    sentiment: Literal["positive", "negative", "neutral"]
    related_keywords: list[str]
    model: str | None
    created_at: datetime
