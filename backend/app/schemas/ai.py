"""Pydantic schemas for AI analysis endpoints."""

from __future__ import annotations

from datetime import date, datetime
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


class DeepAnalysisRequest(BaseModel):
    keyword: str


class DeepAnalysisContent(BaseModel):
    background: str = ""
    opportunity: str = ""
    risk: str = ""
    action: str = ""
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
