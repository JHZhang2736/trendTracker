"""Tests for deep analysis service."""

from __future__ import annotations

import json

import pytest

from app.services.deep_analysis import _insight_to_dict, _llm_analyze, _web_search


@pytest.mark.asyncio
async def test_web_search_returns_list(monkeypatch):
    """Web search should return a list (even on failure)."""
    from app.search.base import SearchResult

    class MockProvider:
        provider_name = "mock"

        async def search(self, query, max_results=5):
            return [
                SearchResult(title="T1", snippet="S1", url="https://a.com"),
                SearchResult(title="T2", snippet="S2", url="https://b.com"),
            ]

    monkeypatch.setattr(
        "app.services.deep_analysis.SearchFactory",
        type("MockFactory", (), {"create": classmethod(lambda cls: MockProvider())}),
    )

    results = await _web_search("AI芯片")
    assert len(results) == 2
    assert results[0].title == "T1"


@pytest.mark.asyncio
async def test_web_search_failure_returns_empty(monkeypatch):
    """On search failure, should return empty list."""

    class FailProvider:
        provider_name = "fail"

        async def search(self, query, max_results=5):
            raise RuntimeError("Search down")

    monkeypatch.setattr(
        "app.services.deep_analysis.SearchFactory",
        type("MockFactory", (), {"create": classmethod(lambda cls: FailProvider())}),
    )

    results = await _web_search("AI芯片")
    assert results == []


@pytest.mark.asyncio
async def test_llm_analyze_success(monkeypatch):
    """LLM analyze should return structured dict on success."""
    from app.ai.base import ChatMessage, ChatResponse
    from app.search.base import SearchResult

    llm_response = json.dumps(
        {
            "background": "背景信息",
            "opportunity": "商业机会",
            "risk": "潜在风险",
            "action": "建议行动",
            "sentiment": "positive",
        },
        ensure_ascii=False,
    )

    class MockProvider:
        async def chat(self, messages: list[ChatMessage], **kwargs) -> ChatResponse:
            return ChatResponse(content=llm_response, model="mock")

    monkeypatch.setattr(
        "app.services.deep_analysis.LLMFactory",
        type("MockFactory", (), {"create": classmethod(lambda cls: MockProvider())}),
    )

    search_results = [SearchResult(title="T", snippet="S", url="https://a.com")]
    result = await _llm_analyze("AI芯片", search_results)
    assert result is not None
    assert result["background"] == "背景信息"
    assert result["sentiment"] == "positive"


@pytest.mark.asyncio
async def test_llm_analyze_invalid_json(monkeypatch):
    """LLM analyze should return None on invalid JSON."""
    from app.ai.base import ChatMessage, ChatResponse

    class MockProvider:
        async def chat(self, messages: list[ChatMessage], **kwargs) -> ChatResponse:
            return ChatResponse(content="not json", model="mock")

    monkeypatch.setattr(
        "app.services.deep_analysis.LLMFactory",
        type("MockFactory", (), {"create": classmethod(lambda cls: MockProvider())}),
    )

    result = await _llm_analyze("test", [])
    assert result is None


@pytest.mark.asyncio
async def test_llm_analyze_failure(monkeypatch):
    """LLM analyze should return None on exception."""

    class FailProvider:
        async def chat(self, messages, **kwargs):
            raise RuntimeError("API down")

    monkeypatch.setattr(
        "app.services.deep_analysis.LLMFactory",
        type("MockFactory", (), {"create": classmethod(lambda cls: FailProvider())}),
    )

    result = await _llm_analyze("test", [])
    assert result is None


def test_insight_to_dict():
    """Test the AIInsight → dict conversion."""

    class FakeInsight:
        id = 1
        keyword = "AI芯片"
        deep_analysis = json.dumps(
            {
                "background": "bg",
                "opportunity": "opp",
                "risk": "risk",
                "action": "act",
                "sentiment": "positive",
            }
        )
        source_urls = json.dumps(["https://a.com", "https://b.com"])
        search_context = json.dumps([{"title": "T", "snippet": "S", "url": "https://a.com"}])
        analysis_type = "manual"
        model = "mock"
        created_at = None

    result = _insight_to_dict(FakeInsight(), cached=False)
    assert result["keyword"] == "AI芯片"
    assert result["deep_analysis"]["background"] == "bg"
    assert len(result["source_urls"]) == 2
    assert result["search_results_count"] == 1
    assert result["cached"] is False


def test_insight_to_dict_empty_fields():
    """Should handle None/empty fields gracefully."""

    class FakeInsight:
        id = 2
        keyword = "test"
        deep_analysis = None
        source_urls = None
        search_context = None
        analysis_type = None
        model = None
        created_at = None

    result = _insight_to_dict(FakeInsight(), cached=True)
    assert result["deep_analysis"] == {}
    assert result["source_urls"] == []
    assert result["search_results_count"] == 0
    assert result["cached"] is True
