"""Unit tests for BaseLLMProvider, LLMFactory, and MiniMaxProvider."""

from __future__ import annotations

import pytest

from app.ai.base import AnalyzeResponse, BaseLLMProvider, ChatMessage, ChatResponse
from app.ai.factory import LLMFactory
from app.ai.minimax_provider import MiniMaxProvider


# ---------------------------------------------------------------------------
# BaseLLMProvider — abstract interface
# ---------------------------------------------------------------------------


def test_base_provider_is_abstract():
    """Cannot instantiate BaseLLMProvider directly."""
    with pytest.raises(TypeError):
        BaseLLMProvider()  # type: ignore[abstract]


def test_concrete_provider_must_implement_both_methods():
    """A subclass that implements only chat() remains abstract."""

    class PartialProvider(BaseLLMProvider):
        provider_name = "partial"

        async def chat(self, messages, **kwargs):
            return ChatResponse(content="ok", model="m")

    with pytest.raises(TypeError):
        PartialProvider()  # type: ignore[abstract]


# ---------------------------------------------------------------------------
# ChatMessage / ChatResponse / AnalyzeResponse dataclasses
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
# MiniMaxProvider stub
# ---------------------------------------------------------------------------


def test_minimax_provider_name():
    assert MiniMaxProvider.provider_name == "minimax"


@pytest.mark.asyncio
async def test_minimax_chat_returns_chat_response():
    provider = MiniMaxProvider()
    messages = [ChatMessage(role="user", content="Tell me about AI trends")]
    resp = await provider.chat(messages)
    assert isinstance(resp, ChatResponse)
    assert resp.content  # non-empty
    assert resp.model


@pytest.mark.asyncio
async def test_minimax_chat_echoes_user_message():
    provider = MiniMaxProvider()
    messages = [ChatMessage(role="user", content="Hello stub")]
    resp = await provider.chat(messages)
    assert "Hello stub" in resp.content


@pytest.mark.asyncio
async def test_minimax_analyze_returns_analyze_response():
    provider = MiniMaxProvider()
    resp = await provider.analyze(keyword="AI大模型", insight_type="business")
    assert isinstance(resp, AnalyzeResponse)
    assert resp.insight_type == "business"
    assert resp.content
    assert resp.model


@pytest.mark.asyncio
async def test_minimax_analyze_contains_keyword():
    provider = MiniMaxProvider()
    resp = await provider.analyze(keyword="量子计算")
    assert "量子计算" in resp.content


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
