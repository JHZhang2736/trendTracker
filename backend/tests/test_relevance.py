"""Tests for AI relevance filter module."""

from __future__ import annotations

import json

import pytest

from app.services.relevance import _parse_index_list, score_relevance


# ---------------------------------------------------------------------------
# _parse_index_list — pure function tests
# ---------------------------------------------------------------------------


def test_parse_json_array():
    result = _parse_index_list("[1, 3]", ["AI芯片", "明星离婚", "比特币"])
    assert result["AI芯片"]["label"] == "relevant"
    assert result["明星离婚"]["label"] == "irrelevant"
    assert result["比特币"]["label"] == "relevant"


def test_parse_empty_array_all_irrelevant():
    result = _parse_index_list("[]", ["明星八卦", "综艺节目"])
    assert result["明星八卦"]["label"] == "irrelevant"
    assert result["综艺节目"]["label"] == "irrelevant"


def test_parse_with_code_fences():
    result = _parse_index_list("```json\n[2]\n```", ["娱乐", "区块链"])
    assert result["娱乐"]["label"] == "irrelevant"
    assert result["区块链"]["label"] == "relevant"


def test_parse_invalid_json_regex_fallback():
    result = _parse_index_list("relevant: 1, 3", ["AI", "明星", "电商"])
    assert result["AI"]["label"] == "relevant"
    assert result["明星"]["label"] == "irrelevant"
    assert result["电商"]["label"] == "relevant"


def test_parse_completely_unparseable():
    result = _parse_index_list("no numbers here", ["kw1"])
    assert result == {}


def test_parse_all_keywords_get_label():
    """Every input keyword should have an entry in the result."""
    result = _parse_index_list("[1]", ["AI", "明星", "电商"])
    assert len(result) == 3
    assert result["AI"]["label"] == "relevant"
    assert result["明星"]["label"] == "irrelevant"
    assert result["电商"]["label"] == "irrelevant"


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

    class MockProvider:
        async def chat(self, messages: list[ChatMessage], **kwargs) -> ChatResponse:
            return ChatResponse(content="[1]", model="mock")

    monkeypatch.setattr(
        "app.services.relevance.LLMFactory",
        type("MockFactory", (), {"create": classmethod(lambda cls: MockProvider())}),
    )

    result = await score_relevance(
        ["GPT-5发布", "某综艺收视率"],
        "CS毕业生，关注AI",
    )
    assert result["GPT-5发布"]["label"] == "relevant"
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
