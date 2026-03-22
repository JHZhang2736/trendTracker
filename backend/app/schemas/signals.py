"""Pydantic schemas for signal detection endpoints."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class SignalItem(BaseModel):
    id: int
    signal_type: str
    platform: str
    keyword: str
    description: str
    value: float | None
    detected_at: datetime


class SignalListResponse(BaseModel):
    items: list[SignalItem]
    total: int


class DetectResponse(BaseModel):
    signals_detected: int
    items: list[SignalItem]
