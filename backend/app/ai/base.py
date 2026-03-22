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


class BaseLLMProvider(ABC):
    """Abstract interface that every LLM provider must implement.

    Concrete providers should:
    - declare a ``provider_name`` class attribute
    - implement :meth:`chat` for free-form conversation
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
