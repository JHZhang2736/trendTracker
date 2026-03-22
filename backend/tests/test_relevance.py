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
    assert result["kw1"]["label"] == "relevant"
    assert result["kw2"]["label"] == "relevant"
    assert result["kw1"]["score"] == 50.0


def test_parse_missing_keywords_filled():
    content = json.dumps([{"keyword": "kw1", "score": 80, "label": "relevant"}])
    result = _parse_response(content, ["kw1", "kw2"])
    assert "kw1" in result
    assert "kw2" in result
    assert result["kw2"]["score"] == 50.0


def test_parse_score_clamped():
    content = json.dumps([{"keyword": "kw", "score": 150, "label": "relevant"}])
    result = _parse_response(content, ["kw"])
    assert result["kw"]["score"] == 100.0


def test_parse_invalid_label_derived_from_score():
    content = json.dumps([{"keyword": "kw", "score": 30, "label": "maybe"}])
    result = _parse_response(content, ["kw"])
    assert result["kw"]["label"] == "irrelevant"  # score < 50 → irrelevant


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
async def test_score_relevance_llm_failure_fallback(monkeypatch):
    """On LLM failure, all keywords should default to relevant."""

    class FailProvider:
        async def chat(self, messages, **kwargs):
            raise RuntimeError("API down")

    monkeypatch.setattr(
        "app.services.relevance.LLMFactory",
        type("MockFactory", (), {"create": classmethod(lambda cls: FailProvider())}),
    )

    result = await score_relevance(["kw1"], "profile")
    assert result["kw1"]["label"] == "relevant"
    assert result["kw1"]["score"] == 50.0
