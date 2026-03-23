"""Tests for the search layer."""

from __future__ import annotations

import pytest

from app.search.base import BaseSearchProvider, SearchResult
from app.search.factory import SearchFactory


class MockSearchProvider(BaseSearchProvider):
    """Mock search provider for testing."""

    provider_name = "mock"

    async def _do_search(self, query: str, max_results: int) -> list[SearchResult]:
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


def test_search_factory_creates_bing(monkeypatch):
    """Factory should create BingProvider when configured."""
    monkeypatch.setattr("app.search.factory.settings.search_provider", "bing")
    provider = SearchFactory.create()
    assert provider.provider_name == "bing"


@pytest.mark.asyncio
async def test_bing_provider_with_mock(monkeypatch):
    """BingProvider should parse results from mocked HTML."""
    from app.search.bing import BingProvider

    html = """<html><body>
    <ol id="b_results">
      <li class="b_algo">
        <h2><a href="https://example.com/1">测试标题</a></h2>
        <p>测试摘要内容</p>
      </li>
    </ol>
    </body></html>"""

    class FakeResp:
        text = html
        status_code = 200

        def raise_for_status(self):
            pass

    import app.search.bing as bing_mod

    monkeypatch.setattr(bing_mod.requests, "get", lambda *a, **kw: FakeResp())
    provider = BingProvider()
    results = await provider.search("测试")
    assert len(results) == 1
    assert results[0].title == "测试标题"
    assert results[0].snippet == "测试摘要内容"
    assert results[0].url == "https://example.com/1"


@pytest.mark.asyncio
async def test_bing_provider_failure(monkeypatch):
    """BingProvider should return empty list after retries on failure."""
    from app.search.bing import BingProvider

    def raise_err(*a, **kw):
        raise ConnectionError("network down")

    import app.search.base as base_mod
    import app.search.bing as bing_mod

    monkeypatch.setattr(bing_mod.requests, "get", raise_err)
    # Speed up retries for testing
    monkeypatch.setattr(base_mod, "MAX_RETRIES", 1)
    monkeypatch.setattr(base_mod, "BASE_DELAY", 0.01)
    provider = BingProvider()
    results = await provider.search("测试")
    assert results == []


def test_bing_extract_real_url():
    """Bing tracking URLs should be decoded to real URLs."""
    from app.search.bing import _extract_real_url

    # Direct URL — no change
    assert _extract_real_url("https://example.com") == "https://example.com"

    # Non-bing URL — no change
    assert _extract_real_url("https://zhihu.com/q/123") == "https://zhihu.com/q/123"


@pytest.mark.asyncio
async def test_mock_search_provider():
    provider = MockSearchProvider()
    results = await provider.search("AI芯片")
    assert len(results) == 1
    assert "AI芯片" in results[0].title
