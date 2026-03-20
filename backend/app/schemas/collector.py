"""Pydantic schemas for collector endpoints."""

from __future__ import annotations

from pydantic import BaseModel


class PlatformResult(BaseModel):
    platform: str
    count: int
    error: str | None = None


class CollectorRunResponse(BaseModel):
    status: str
    records_count: int
    platforms: list[PlatformResult] = []
