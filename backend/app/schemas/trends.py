"""Pydantic schemas for trends endpoints."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class TrendItem(BaseModel):
    platform: str
    keyword: str
    rank: int | None
    heat_score: float | None
    url: str | None
    collected_at: datetime


class TrendsListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[TrendItem]


class PlatformsResponse(BaseModel):
    platforms: list[str]
