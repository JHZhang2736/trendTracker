"""MiniMax LLM provider stub — does not call the real API in this version."""

from __future__ import annotations

from typing import Any

from app.ai.base import AnalyzeResponse, BaseLLMProvider, ChatMessage, ChatResponse
from app.config import settings


class MiniMaxProvider(BaseLLMProvider):
    """Stub implementation of the MiniMax LLM provider.

    In the MVP phase this class returns deterministic placeholder responses so
    that the rest of the application can be developed and tested without live
    API credentials.  Replace the method bodies with real ``httpx`` calls once
    you are ready to connect to the MiniMax API.
    """

    provider_name = "minimax"

    def __init__(self) -> None:
        self.api_key = settings.minimax_api_key
        self.group_id = settings.minimax_group_id
        self.model = "abab6.5s-chat"

    async def chat(self, messages: list[ChatMessage], **kwargs: Any) -> ChatResponse:
        """Return a stub chat reply (no real API call)."""
        last_user = next(
            (m.content for m in reversed(messages) if m.role == "user"),
            "",
        )
        stub_content = f"[MiniMax stub] Received: {last_user[:80]}"
        return ChatResponse(
            content=stub_content,
            model=self.model,
            usage={"prompt_tokens": 0, "completion_tokens": 0},
        )

    async def analyze(
        self,
        keyword: str,
        context: str = "",
        insight_type: str = "business",
        **kwargs: Any,
    ) -> AnalyzeResponse:
        """Return a stub analysis (no real API call)."""
        stub_content = (
            f"[MiniMax stub] Analysis for '{keyword}' "
            f"(type={insight_type}): This is a placeholder insight. "
            "Connect to the real MiniMax API to obtain genuine results."
        )
        return AnalyzeResponse(
            insight_type=insight_type,
            content=stub_content,
            model=self.model,
        )
