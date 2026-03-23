"""Bing search provider — scrapes bing.com, no API key required."""

from __future__ import annotations

import asyncio
import base64
from urllib.parse import parse_qs, urlparse

import requests
from bs4 import BeautifulSoup

from app.search.base import BaseSearchProvider, SearchResult

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9",
}


class BingProvider(BaseSearchProvider):
    """Bing web search — scrapes bing.com, free, good Chinese coverage."""

    provider_name = "bing"

    async def _do_search(self, query: str, max_results: int) -> list[SearchResult]:
        """Search Bing and return results."""
        return await asyncio.to_thread(self._sync_search, query, max_results)

    @staticmethod
    def _sync_search(query: str, max_results: int) -> list[SearchResult]:
        """Scrape Bing search results page."""
        resp = requests.get(
            "https://www.bing.com/search",
            params={"q": query, "count": max_results, "mkt": "zh-CN", "cc": "CN"},
            headers=_HEADERS,
            timeout=15,
        )
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        items = soup.find_all("li", class_="b_algo")

        results: list[SearchResult] = []
        for item in items[:max_results]:
            h2 = item.find("h2")
            a = h2.find("a") if h2 else None
            if not a:
                continue

            title = a.get_text(strip=True)
            url = _extract_real_url(a.get("href", ""))

            # Snippet: try <p> first, then b_caption div
            p = item.find("p")
            if not p:
                caption = item.find("div", class_="b_caption")
                p = caption.find("p") if caption else None
            snippet = p.get_text(strip=True) if p else ""

            results.append(SearchResult(title=title, snippet=snippet, url=url))

        return results


def _extract_real_url(href: str) -> str:
    """Extract the real URL from a Bing tracking redirect, if present."""
    parsed = urlparse(href)
    if "bing.com" not in parsed.netloc:
        return href

    qs = parse_qs(parsed.query)
    encoded_list = qs.get("u", [])
    if not encoded_list:
        return href

    encoded = encoded_list[0]
    if encoded.startswith("a1"):
        try:
            # Bing encodes real URL as base64 with "a1" prefix
            padded = encoded[2:] + "==="
            return base64.b64decode(padded).decode("utf-8", errors="replace")
        except Exception:
            pass
    return href
