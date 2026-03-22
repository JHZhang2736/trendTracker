"""Tests for AI analysis — MiniMaxProvider, LLMFactory, and /ai/analyze endpoint."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.ai.base import AnalyzeResponse, BaseLLMProvider, ChatMessage, ChatResponse
from app.ai.factory import LLMFactory
from app.ai.minimax_provider import MiniMaxProvider

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_MOCK_ANALYSIS = {
    "business_insight": "该词展示出强劲的商业潜力，建议重点关注电商与内容营销方向。",
    "sentiment": "positive",
    "related_keywords": ["电商", "营销", "流量", "品牌", "推广"],
}

_MINIMAX_RESPONSE = {
    "choices": [
        {
            "message": {
                "role": "assistant",
                "content": json.dumps(_MOCK_ANALYSIS, ensure_ascii=False),
            },
            "finish_reason": "stop",
        }
    ],
    "usage": {"prompt_tokens": 50, "completion_tokens": 100, "total_tokens": 150},
    "model": "abab6.5s-chat",
}


def _mock_http_client(response_body: dict):
    """Return a patched httpx.AsyncClient that returns response_body."""
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = response_body

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=mock_resp)
    return mock_client


# ---------------------------------------------------------------------------
# BaseLLMProvider — abstract interface
# ---------------------------------------------------------------------------


def test_base_provider_is_abstract():
    with pytest.raises(TypeError):
        BaseLLMProvider()  # type: ignore[abstract]


def test_concrete_provider_must_implement_both_methods():
    class PartialProvider(BaseLLMProvider):
        provider_name = "partial"

        async def chat(self, messages, **kwargs):
            return ChatResponse(content="ok", model="m")

    with pytest.raises(TypeError):
        PartialProvider()  # type: ignore[abstract]


# ---------------------------------------------------------------------------
# Dataclass smoke tests
# ---------------------------------------------------------------------------


def test_chat_message_fields():
    msg = ChatMessage(role="user", content="hello")
    assert msg.role == "user"
    assert msg.content == "hello"


def test_chat_response_defaults():
    resp = ChatResponse(content="hi", model="gpt")
    assert resp.usage == {}


def test_analyze_response_defaults():
    resp = AnalyzeResponse(insight_type="business", content="text", model="m")
    assert resp.extra == {}


# ---------------------------------------------------------------------------
# MiniMaxProvider — mocked HTTP
# ---------------------------------------------------------------------------


def test_minimax_provider_name():
    assert MiniMaxProvider.provider_name == "minimax"


@pytest.mark.asyncio
async def test_minimax_chat_returns_chat_response():
    provider = MiniMaxProvider()
    with patch("httpx.AsyncClient", return_value=_mock_http_client(_MINIMAX_RESPONSE)):
        resp = await provider.chat([ChatMessage(role="user", content="你好")])
    assert isinstance(resp, ChatResponse)
    assert resp.content
    assert resp.model == "abab6.5s-chat"


@pytest.mark.asyncio
async def test_minimax_analyze_returns_structured_data():
    provider = MiniMaxProvider()
    with patch("httpx.AsyncClient", return_value=_mock_http_client(_MINIMAX_RESPONSE)):
        result = await provider.analyze(keyword="双十一")
    parsed = json.loads(result.content)
    assert parsed["sentiment"] == "positive"
    assert isinstance(parsed["related_keywords"], list)
    assert len(parsed["related_keywords"]) == 5


@pytest.mark.asyncio
async def test_minimax_analyze_returns_analyze_response_type():
    provider = MiniMaxProvider()
    with patch("httpx.AsyncClient", return_value=_mock_http_client(_MINIMAX_RESPONSE)):
        result = await provider.analyze(keyword="AI大模型", insight_type="business")
    assert isinstance(result, AnalyzeResponse)
    assert result.insight_type == "business"
    assert result.model == "abab6.5s-chat"


@pytest.mark.asyncio
async def test_minimax_analyze_normalises_invalid_sentiment():
    provider = MiniMaxProvider()
    bad_body = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": json.dumps(
                        {"business_insight": "ok", "sentiment": "mixed", "related_keywords": []}
                    ),
                }
            }
        ],
        "usage": {},
    }
    with patch("httpx.AsyncClient", return_value=_mock_http_client(bad_body)):
        result = await provider.analyze(keyword="测试词")
    parsed = json.loads(result.content)
    assert parsed["sentiment"] == "neutral"


@pytest.mark.asyncio
async def test_minimax_analyze_handles_non_json_response():
    provider = MiniMaxProvider()
    non_json_body = {
        "choices": [{"message": {"role": "assistant", "content": "普通文字，不是JSON。"}}],
        "usage": {},
    }
    with patch("httpx.AsyncClient", return_value=_mock_http_client(non_json_body)):
        result = await provider.analyze(keyword="测试词")
    parsed = json.loads(result.content)
    assert parsed["sentiment"] == "neutral"
    assert "business_insight" in parsed


# ---------------------------------------------------------------------------
# LLMFactory
# ---------------------------------------------------------------------------


def test_llm_factory_creates_minimax():
    provider = LLMFactory.create("minimax")
    assert isinstance(provider, MiniMaxProvider)


def test_llm_factory_case_insensitive():
    provider = LLMFactory.create("MiniMax")
    assert isinstance(provider, MiniMaxProvider)


def test_llm_factory_unknown_provider_raises():
    with pytest.raises(ValueError, match="Unknown LLM provider"):
        LLMFactory.create("openai")


def test_llm_factory_default_uses_settings(monkeypatch):
    monkeypatch.setattr("app.config.settings.llm_provider", "minimax")
    provider = LLMFactory.create()
    assert isinstance(provider, MiniMaxProvider)


# ---------------------------------------------------------------------------
# Integration tests: POST /api/v1/ai/analyze
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_analyze_endpoint_returns_200(test_client: AsyncClient):
    with patch("httpx.AsyncClient", return_value=_mock_http_client(_MINIMAX_RESPONSE)):
        resp = await test_client.post("/api/v1/ai/analyze", json={"keyword": "双十一"})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_analyze_endpoint_response_schema(test_client: AsyncClient):
    with patch("httpx.AsyncClient", return_value=_mock_http_client(_MINIMAX_RESPONSE)):
        data = (await test_client.post("/api/v1/ai/analyze", json={"keyword": "双十一"})).json()
    required = {"id", "keyword", "business_insight", "sentiment", "related_keywords", "model", "created_at"}
    assert required <= set(data.keys())
    assert data["keyword"] == "双十一"
    assert data["sentiment"] in {"positive", "negative", "neutral"}
    assert isinstance(data["related_keywords"], list)


@pytest.mark.asyncio
async def test_analyze_endpoint_persists_to_db(test_client: AsyncClient):
    with patch("httpx.AsyncClient", return_value=_mock_http_client(_MINIMAX_RESPONSE)):
        resp1 = (await test_client.post("/api/v1/ai/analyze", json={"keyword": "春节"})).json()
    with patch("httpx.AsyncClient", return_value=_mock_http_client(_MINIMAX_RESPONSE)):
        resp2 = (await test_client.post("/api/v1/ai/analyze", json={"keyword": "春节"})).json()
    # Two separate calls → two rows → distinct IDs
    assert resp1["id"] != resp2["id"]


@pytest.mark.asyncio
async def test_analyze_endpoint_related_keywords_max_5(test_client: AsyncClient):
    long_body = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": json.dumps(
                        {
                            "business_insight": "商业建议",
                            "sentiment": "positive",
                            "related_keywords": ["a", "b", "c", "d", "e", "f", "g"],
                        }
                    ),
                }
            }
        ],
        "usage": {},
    }
    with patch("httpx.AsyncClient", return_value=_mock_http_client(long_body)):
        data = (await test_client.post("/api/v1/ai/analyze", json={"keyword": "测试"})).json()
    assert len(data["related_keywords"]) <= 5
