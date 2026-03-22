"""Tests for AI relevance filter module (upgraded with scores + reasons)."""

from __future__ import annotations

import pytest

from app.services.relevance import (
    _parse_scored_response,
    _try_parse_index_list,
    _try_parse_scored_json,
    _try_regex_scored,
    score_relevance,
)

# ---------------------------------------------------------------------------
# _try_parse_scored_json — full JSON parsing
# ---------------------------------------------------------------------------


def test_parse_scored_json_valid():
    result = _try_parse_scored_json('[{"i":1,"s":85,"r":"AI相关"},{"i":3,"s":60,"r":"电商"}]')
    assert len(result) == 2
    assert result[0] == {"i": 1, "s": 85.0, "r": "AI相关"}
    assert result[1] == {"i": 3, "s": 60.0, "r": "电商"}


def test_parse_scored_json_empty():
    result = _try_parse_scored_json("[]")
    assert result == []


def test_parse_scored_json_pure_index_list():
    """Pure index list [1, 3] should also parse (with default score)."""
    result = _try_parse_scored_json("[1, 3]")
    assert len(result) == 2
    assert result[0] == {"i": 1, "s": 80.0, "r": ""}


def test_parse_scored_json_invalid():
    result = _try_parse_scored_json("not json")
    assert result is None


# ---------------------------------------------------------------------------
# _try_regex_scored — regex fallback
# ---------------------------------------------------------------------------


def test_regex_scored_with_reasons():
    text = '{"i":1,"s":85,"r":"AI芯片"},{"i":3,"s":60,"r":"电商"}'
    result = _try_regex_scored(text)
    assert len(result) == 2
    assert result[0]["i"] == 1
    assert result[0]["s"] == 85.0
    assert result[0]["r"] == "AI芯片"


def test_regex_scored_without_reasons():
    text = '"i":1,"s":85 and "i":3,"s":60'
    result = _try_regex_scored(text)
    assert len(result) == 2
    assert result[0]["r"] == ""


def test_regex_scored_no_match():
    result = _try_regex_scored("no numbers here")
    assert result == []


# ---------------------------------------------------------------------------
# _try_parse_index_list — pure index fallback
# ---------------------------------------------------------------------------


def test_parse_index_list_json():
    result = _try_parse_index_list("[1, 3, 7]")
    assert result == {1, 3, 7}


def test_parse_index_list_empty():
    result = _try_parse_index_list("[]")
    assert result == set()


def test_parse_index_list_regex():
    result = _try_parse_index_list("relevant: 1, 3")
    assert 1 in result
    assert 3 in result


# ---------------------------------------------------------------------------
# _parse_scored_response — full pipeline
# ---------------------------------------------------------------------------


def test_parse_scored_response_full():
    raw = '[{"i":1,"s":85,"r":"AI相关"},{"i":3,"s":60,"r":"电商"}]'
    result = _parse_scored_response(raw, ["AI芯片", "明星离婚", "比特币"])
    assert result["AI芯片"]["label"] == "relevant"
    assert result["AI芯片"]["score"] == 85.0
    assert result["AI芯片"]["reason"] == "AI相关"
    assert result["明星离婚"]["label"] == "irrelevant"
    assert result["明星离婚"]["score"] == 0.0
    assert result["比特币"]["label"] == "relevant"
    assert result["比特币"]["score"] == 60.0


def test_parse_scored_response_empty_all_irrelevant():
    result = _parse_scored_response("[]", ["明星八卦", "综艺节目"])
    assert result["明星八卦"]["label"] == "irrelevant"
    assert result["综艺节目"]["label"] == "irrelevant"


def test_parse_scored_response_code_fences():
    raw = '```json\n[{"i":2,"s":70,"r":"区块链"}]\n```'
    result = _parse_scored_response(raw, ["娱乐", "区块链"])
    assert result["娱乐"]["label"] == "irrelevant"
    assert result["区块链"]["label"] == "relevant"
    assert result["区块链"]["score"] == 70.0


def test_parse_scored_response_fallback_to_index():
    """If LLM returns pure index list, fall back with default scores."""
    result = _parse_scored_response("[1, 3]", ["AI", "明星", "电商"])
    assert result["AI"]["label"] == "relevant"
    assert result["AI"]["score"] == 80.0
    assert result["明星"]["label"] == "irrelevant"
    assert result["电商"]["label"] == "relevant"


def test_parse_scored_response_unparseable():
    result = _parse_scored_response("no numbers here", ["kw1"])
    assert result == {}


def test_parse_scored_response_score_clamping():
    """Scores should be clamped to 0-100."""
    raw = '[{"i":1,"s":150,"r":"test"}]'
    result = _parse_scored_response(raw, ["kw1"])
    assert result["kw1"]["score"] == 100.0


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
            return ChatResponse(
                content='[{"i":1,"s":90,"r":"AI发布"}]',
                model="mock",
            )

    monkeypatch.setattr(
        "app.services.relevance.LLMFactory",
        type("MockFactory", (), {"create": classmethod(lambda cls: MockProvider())}),
    )

    result = await score_relevance(
        ["GPT-5发布", "某综艺收视率"],
        "CS毕业生，关注AI",
    )
    assert result["GPT-5发布"]["label"] == "relevant"
    assert result["GPT-5发布"]["score"] == 90.0
    assert result["GPT-5发布"]["reason"] == "AI发布"
    assert result["某综艺收视率"]["label"] == "irrelevant"
    assert result["某综艺收视率"]["score"] == 0.0


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
