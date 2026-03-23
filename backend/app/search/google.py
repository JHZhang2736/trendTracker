"""Google search provider using googlesearch-python (scrapes Google)."""

from __future__ import annotations

import asyncio

from app.search.base import BaseSearchProvider, SearchResult


class GoogleProvider(BaseSearchProvider):
    """Google web search — scrapes Google, no API key required."""

    provider_name = "google"

    async def _do_search(self, query: str, max_results: int) -> list[SearchResult]:
        """Search Google and return results."""
        return await asyncio.to_thread(self._sync_search, query, max_results)

    @staticmethod
    def _sync_search(query: str, max_results: int) -> list[SearchResult]:
        """Run the synchronous Google search in a thread."""
        from googlesearch import search

        results: list[SearchResult] = []
        for r in search(query, num_results=max_results, lang="zh", advanced=True):
            results.append(
                SearchResult(
                    title=r.title or "",
                    snippet=r.description or "",
                    url=r.url or "",
                )
            )
        return results
