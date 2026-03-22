"""Tests for AI — MiniMaxProvider, LLMFactory, and chat functionality."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ai.base import BaseLLMProvider, ChatMessage, ChatResponse
from app.ai.factory import LLMFactory
from app.ai.minimax_provider import MiniMaxProvider

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_MINIMAX_RESPONSE = {
    "choices": [
        {
            "message": {
                "role": "assistant",
                "content": "这是一个测试回复。",
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
