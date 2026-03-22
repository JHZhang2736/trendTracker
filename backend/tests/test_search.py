"""Tests for the search layer."""

from __future__ import annotations

import pytest

from app.search.base import BaseSearchProvider, SearchResult
from app.search.factory import SearchFactory


class MockSearchProvider(BaseSearchProvider):
    """Mock search provider for testing."""

    provider_name = "mock"

    async def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        return [
            SearchResult(
                title=f"Result for {query}",
                snippet=f"This is about {query}",
                url=f"https://example.com/{query}",
            )
        ]


def test_search_result_dataclass():
    r = SearchResult(title="T", snippet="S", url="https://example.com")
    assert r.title == "T"
    assert r.snippet == "S"
    assert r.url == "https://example.com"


def test_search_factory_unknown_provider():
    with pytest.raises(ValueError, match="Unknown search provider"):
        SearchFactory.create("nonexistent")


def test_search_factory_creates_duckduckgo(monkeypatch):
    """Factory should create DuckDuckGoProvider when configured."""
    monkeypatch.setattr("app.search.factory.settings.search_provider", "duckduckgo")
    provider = SearchFactory.create()
    assert provider.provider_name == "duckduckgo"


@pytest.mark.asyncio
async def test_mock_search_provider():
    provider = MockSearchProvider()
    results = await provider.search("AI芯片")
    assert len(results) == 1
    assert "AI芯片" in results[0].title
