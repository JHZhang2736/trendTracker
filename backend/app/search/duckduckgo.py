"""DuckDuckGo search provider using the duckduckgo-search library."""

from __future__ import annotations

import asyncio

from app.search.base import BaseSearchProvider, SearchResult


class DuckDuckGoProvider(BaseSearchProvider):
    """DuckDuckGo web search — free, no API key required."""

    provider_name = "duckduckgo"

    async def _do_search(self, query: str, max_results: int) -> list[SearchResult]:
        """Search DuckDuckGo and return results."""
        return await asyncio.to_thread(self._sync_search, query, max_results)

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
