"""Abstract base class for all LLM providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ChatMessage:
    """A single message in a chat conversation."""

    role: str  # "system" | "user" | "assistant"
    content: str


@dataclass
class ChatResponse:
    """Normalised response from a chat completion."""

    content: str
    model: str
    usage: dict[str, Any] = field(default_factory=dict)


@dataclass
class AnalyzeResponse:
    """Normalised response from an analysis request."""

    insight_type: str
    content: str
    model: str
    extra: dict[str, Any] = field(default_factory=dict)


class BaseLLMProvider(ABC):
    """Abstract interface that every LLM provider must implement.

    Concrete providers should:
    - declare a ``provider_name`` class attribute
    - implement :meth:`chat` for free-form conversation
    - implement :meth:`analyze` for structured trend analysis
    """

    provider_name: str = ""

    @abstractmethod
    async def chat(self, messages: list[ChatMessage], **kwargs: Any) -> ChatResponse:
        """Send a list of messages and return the assistant reply.

        Args:
            messages: Ordered conversation history.
            **kwargs: Provider-specific parameters (temperature, max_tokens, …).

        Returns:
            A :class:`ChatResponse` with the assistant content.
        """

    @abstractmethod
    async def analyze(
        self,
        keyword: str,
        context: str = "",
        insight_type: str = "business",
        **kwargs: Any,
    ) -> AnalyzeResponse:
        """Analyse a trend keyword and return structured insights.

        Args:
            keyword: The trend keyword to analyse.
            context: Optional surrounding context (e.g. related keywords).
            insight_type: Type of insight requested (e.g. "business", "sentiment").
            **kwargs: Provider-specific parameters.

        Returns:
            An :class:`AnalyzeResponse` with the analysis content.
        """
