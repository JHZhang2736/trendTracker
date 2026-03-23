"""Abstract base class for all search providers."""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Retry defaults
MAX_RETRIES = 3
BASE_DELAY = 1.0  # seconds — delays: 1s, 2s, 4s


@dataclass
class SearchResult:
    """A single web search result."""

    title: str
    snippet: str
    url: str


class BaseSearchProvider(ABC):
    """Abstract interface that every search provider must implement."""

    provider_name: str = ""

    async def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        """Search with exponential backoff retry.

        Subclasses implement :meth:`_do_search` instead of overriding this.
        """
        last_exc: Exception | None = None
        for attempt in range(MAX_RETRIES):
            try:
                results = await self._do_search(query, max_results)
                if attempt > 0:
                    logger.info(
                        "%s search succeeded on attempt %d for '%s'",
                        self.provider_name, attempt + 1, query,
                    )
                return results
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                delay = BASE_DELAY * (2 ** attempt)
                logger.warning(
                    "%s search attempt %d/%d failed for '%s': %s — retrying in %.1fs",
                    self.provider_name, attempt + 1, MAX_RETRIES, query, exc, delay,
                )
                await asyncio.sleep(delay)

        logger.error(
            "%s search failed after %d attempts for '%s': %s",
            self.provider_name, MAX_RETRIES, query, last_exc,
        )
        return []

    @abstractmethod
    async def _do_search(self, query: str, max_results: int) -> list[SearchResult]:
        """Execute the actual search — implemented by each provider.

        Should raise on failure (not return empty) so retry logic can kick in.
        """
