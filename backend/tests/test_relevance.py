"""Tests for AI relevance filter module."""

from __future__ import annotations

import json

import pytest

from app.services.relevance import _parse_response, score_relevance


# ---------------------------------------------------------------------------
# _parse_response — pure function tests
# ---------------------------------------------------------------------------


def test_parse_valid_json():
    content = json.dumps([
        {"keyword": "AI芯片", "score": 85, "label": "relevant"},
        {"keyword": "明星离婚", "score": 10, "label": "irrelevant"},
    ])
    result = _parse_response(content, ["AI芯片", "明星离婚"])
    assert result["AI芯片"]["score"] == 85.0
    assert result["AI芯片"]["label"] == "relevant"
    assert result["明星离婚"]["score"] == 10.0
    assert result["明星离婚"]["label"] == "irrelevant"


def test_parse_with_code_fences():
    content = '```json\n[{"keyword": "比特币", "score": 90, "label": "relevant"}]\n```'
    result = _parse_response(content, ["比特币"])
    assert result["比特币"]["score"] == 90.0


def test_parse_invalid_json_fallback():
    result = _parse_response("this is not json", ["kw1", "kw2"])
    assert result == {}


def test_parse_missing_keywords_not_filled():
    content = json.dumps([{"keyword": "kw1", "score": 80, "label": "relevant"}])
    result = _parse_response(content, ["kw1", "kw2"])
    assert "kw1" in result
    assert "kw2" not in result  # LLM didn't return kw2 → left unscored


def test_parse_score_clamped():
    content = json.dumps([{"keyword": "kw", "score": 150, "label": "relevant"}])
    result = _parse_response(content, ["kw"])
    assert result["kw"]["score"] == 100.0


def test_parse_invalid_label_derived_from_score():
    content = json.dumps([{"keyword": "kw", "score": 30, "label": "maybe"}])
    result = _parse_response(content, ["kw"])
    assert result["kw"]["label"] == "irrelevant"  # score < 50 → irrelevant


def test_parse_index_based_matching():
    """LLM returns index instead of keyword — should match by position."""
    content = json.dumps([
        {"index": 1, "score": 90, "label": "relevant"},
        {"index": 2, "score": 5, "label": "irrelevant"},
    ])
    result = _parse_response(content, ["AI大模型", "某明星离婚"])
    assert result["AI大模型"]["label"] == "relevant"
    assert result["某明星离婚"]["label"] == "irrelevant"


def test_parse_fuzzy_keyword_matching():
    """LLM returns slightly different keyword — should fuzzy match."""
    content = json.dumps([
        {"keyword": "AI芯片技术", "score": 85, "label": "relevant"},
    ])
    result = _parse_response(content, ["AI芯片"])
    assert "AI芯片" in result
    assert result["AI芯片"]["label"] == "relevant"


# ---------------------------------------------------------------------------
# score_relevance — integration (mocked LLM)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_score_relevance_empty():
    result = await score_relevance([], "any profile")
    assert result == {}


@pytest.mark.asyncio
async def test_score_relevance_with_mock(monkeypatch):
    """Mock LLM provider to test the full scoring flow."""
    from app.ai.base import ChatMessage, ChatResponse

    mock_response = json.dumps([
        {"keyword": "GPT-5发布", "score": 95, "label": "relevant"},
        {"keyword": "某综艺收视率", "score": 5, "label": "irrelevant"},
    ])

    class MockProvider:
        async def chat(self, messages: list[ChatMessage], **kwargs) -> ChatResponse:
            return ChatResponse(content=mock_response, model="mock")

    monkeypatch.setattr(
        "app.services.relevance.LLMFactory",
        type("MockFactory", (), {"create": classmethod(lambda cls: MockProvider())}),
    )

    result = await score_relevance(
        ["GPT-5发布", "某综艺收视率"],
        "CS毕业生，关注AI",
    )
    assert result["GPT-5发布"]["label"] == "relevant"
    assert result["GPT-5发布"]["score"] == 95.0
    assert result["某综艺收视率"]["label"] == "irrelevant"


@pytest.mark.asyncio
async def test_score_relevance_llm_failure_returns_empty(monkeypatch):
    """On LLM failure, return empty dict so items stay unscored."""

    class FailProvider:
        async def chat(self, messages, **kwargs):
            raise RuntimeError("API down")

    monkeypatch.setattr(
        "app.services.relevance.LLMFactory",
        type("MockFactory", (), {"create": classmethod(lambda cls: FailProvider())}),
    )

    result = await score_relevance(["kw1"], "profile")
    assert result == {}
