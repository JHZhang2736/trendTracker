"""MiniMax LLM provider — real ChatCompletion V2 API calls."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.ai.base import BaseLLMProvider, ChatMessage, ChatResponse
from app.config import settings

logger = logging.getLogger(__name__)

_API_URL = "https://api.minimax.chat/v1/text/chatcompletion_v2"


class MiniMaxProvider(BaseLLMProvider):
    """MiniMax LLM provider using ChatCompletion V2 API."""

    provider_name = "minimax"

    def __init__(self) -> None:
        self.api_key = settings.minimax_api_key
        self.group_id = settings.minimax_group_id
        self.model = "abab6.5s-chat"

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def chat(self, messages: list[ChatMessage], **kwargs: Any) -> ChatResponse:
        """Send messages to MiniMax ChatCompletion V2 and return the reply."""
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "max_tokens": kwargs.get("max_tokens", 2048),
        }
        if "temperature" in kwargs:
            payload["temperature"] = kwargs["temperature"]
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(_API_URL, headers=self._headers(), json=payload)
            resp.raise_for_status()
            data = resp.json()

        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        return ChatResponse(content=content, model=self.model, usage=usage)
