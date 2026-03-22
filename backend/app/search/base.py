"""Abstract base class for all search providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class SearchResult:
    """A single web search result."""

    title: str
    snippet: str
    url: str


class BaseSearchProvider(ABC):
    """Abstract interface that every search provider must implement."""

    provider_name: str = ""

    @abstractmethod
    async def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        """Search the web and return a list of results.

        Args:
            query: Search query string.
            max_results: Maximum number of results to return.

        Returns:
            A list of :class:`SearchResult` objects.
        """
