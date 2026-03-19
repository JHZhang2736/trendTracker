"""Pydantic schemas for collector endpoints."""

from __future__ import annotations

from pydantic import BaseModel


class CollectorRunResponse(BaseModel):
    status: str
    records_count: int
