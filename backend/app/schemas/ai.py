"""Pydantic schemas for AI analysis endpoints."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel


class DeepAnalysisRequest(BaseModel):
    keyword: str


class OpportunityAngle(BaseModel):
    angle: str = ""
    idea: str = ""


class DeepAnalysisContent(BaseModel):
    mode: str = "business"
    # Business mode fields
    background: str = ""
    opportunities: list[OpportunityAngle] = []
    risk: str = ""
    action: str = ""
    # News mode fields
    summary: str = ""
    key_facts: list[str] = []
    # Common
    sentiment: Literal["positive", "negative", "neutral"] = "neutral"


class DeepAnalysisResponse(BaseModel):
    id: int
    keyword: str
    deep_analysis: DeepAnalysisContent
    source_urls: list[str]
    search_results_count: int
    analysis_type: str | None
    model: str | None
    created_at: datetime | None
    cached: bool


class BriefResponse(BaseModel):
    id: int
    date: date
    content: str
    model: str | None
    created_at: datetime
