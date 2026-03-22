"""MiniMax LLM provider — real ChatCompletion V2 API calls."""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from app.ai.base import AnalyzeResponse, BaseLLMProvider, ChatMessage, ChatResponse
from app.config import settings

logger = logging.getLogger(__name__)

_API_URL = "https://api.minimax.chat/v1/text/chatcompletion_v2"

_ANALYZE_SYSTEM_PROMPT = (
    "你是一个商业趋势分析专家。分析用户给出的热门关键词，"
    "严格以如下 JSON 格式返回（不要有任何额外文字）：\n"
    "{\n"
    '  "business_insight": "商业建议，100字以内",\n'
    '  "sentiment": "positive 或 negative 或 neutral 三者之一",\n'
    '  "related_keywords": ["词1", "词2", "词3", "词4", "词5"]\n'
    "}"
)


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

    async def analyze(
        self,
        keyword: str,
        context: str = "",
        insight_type: str = "business",
        **kwargs: Any,
    ) -> AnalyzeResponse:
        """Analyze a trend keyword; returns business_insight, sentiment, related_keywords."""
        user_content = f"请分析热门词：{keyword}"
        if context:
            user_content += f"\n背景信息：{context}"

        messages = [
            ChatMessage(role="system", content=_ANALYZE_SYSTEM_PROMPT),
            ChatMessage(role="user", content=user_content),
        ]
        payload = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(_API_URL, headers=self._headers(), json=payload)
            resp.raise_for_status()
            data = resp.json()

        raw_content = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})

        # Parse structured JSON from the model response
        try:
            parsed = json.loads(raw_content)
        except json.JSONDecodeError:
            logger.warning("MiniMax response was not valid JSON, storing raw content")
            parsed = {
                "business_insight": raw_content,
                "sentiment": "neutral",
                "related_keywords": [],
            }

        # Normalise fields
        sentiment = parsed.get("sentiment", "neutral")
        if sentiment not in {"positive", "negative", "neutral"}:
            sentiment = "neutral"
        related = parsed.get("related_keywords", [])
        if not isinstance(related, list):
            related = []

        structured = {
            "business_insight": parsed.get("business_insight", ""),
            "sentiment": sentiment,
            "related_keywords": related[:5],
        }
        return AnalyzeResponse(
            insight_type=insight_type,
            content=json.dumps(structured, ensure_ascii=False),
            model=self.model,
            extra={"usage": usage},
        )
