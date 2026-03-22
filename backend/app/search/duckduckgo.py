"""DuckDuckGo search provider using the duckduckgo-search library."""

from __future__ import annotations

import asyncio
import logging

from app.search.base import BaseSearchProvider, SearchResult

logger = logging.getLogger(__name__)


class DuckDuckGoProvider(BaseSearchProvider):
    """DuckDuckGo web search — free, no API key required."""

    provider_name = "duckduckgo"

    async def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        """Search DuckDuckGo and return results."""
        try:
            results = await asyncio.to_thread(self._sync_search, query, max_results)
            return results
        except Exception:
            logger.exception("DuckDuckGo search failed for query: %s", query)
            return []

    @staticmethod
    def _sync_search(query: str, max_results: int) -> list[SearchResult]:
        """Run the synchronous DuckDuckGo search in a thread."""
        from duckduckgo_search import DDGS

        results: list[SearchResult] = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append(
                    SearchResult(
                        title=r.get("title", ""),
                        snippet=r.get("body", ""),
                        url=r.get("href", ""),
                    )
                )
        return results
