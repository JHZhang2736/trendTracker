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
    convergence_score: float


class TopTrendItem(BaseModel):
    keyword: str
    platforms: list[str]
    max_heat_score: float | None
    latest_collected_at: datetime
    convergence_score: float


class TopTrendsResponse(BaseModel):
    items: list[TopTrendItem]


class TrendsListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[TrendItem]


class PlatformsResponse(BaseModel):
    platforms: list[str]


class PlatformTrendItem(BaseModel):
    keyword: str
    rank: int | None
    heat_score: float | None
    url: str | None
    collected_at: datetime
    convergence_score: float


class TopByPlatformResponse(BaseModel):
    platforms: dict[str, list[PlatformTrendItem]]


class HeatmapResponse(BaseModel):
    platforms: list[str]
    time_slots: list[str]
    data: list[list[float]]
    max_heat: float


class VelocityItem(BaseModel):
    platform: str
    keyword: str
    heat_score: float
    rank: int | None
    velocity: float | None
    acceleration: float | None


class VelocityResponse(BaseModel):
    items: list[VelocityItem]


class TrendsClearResponse(BaseModel):
    deleted: int


class TrendsCountResponse(BaseModel):
    total: int
