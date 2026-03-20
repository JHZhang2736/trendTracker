"""Google Trends real collector — daily trending searches via RSS feed."""

from __future__ import annotations

import xml.etree.ElementTree as ET

import httpx

from app.collectors.base import BaseCollector

_RSS_URL = "https://trends.google.com/trending/rss"
_NS = {"ht": "https://trends.google.com/trending/rss"}
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
}


def _parse_traffic(traffic_str: str) -> float:
    """Convert '1,000,000+' or '500K+' style strings to a float."""
    s = traffic_str.strip().rstrip("+").replace(",", "").replace(" ", "")
    if s.upper().endswith("K"):
        try:
            return float(s[:-1]) * 1_000
        except ValueError:
            return 0.0
    if s.upper().endswith("M"):
        try:
            return float(s[:-1]) * 1_000_000
        except ValueError:
            return 0.0
    try:
        return float(s)
    except ValueError:
        return 0.0


class GoogleTrendsCollector(BaseCollector):
    """Collect daily trending searches from Google Trends RSS feed.

    Fetches from multiple regions and merges into a single list, deduplicated
    by keyword (keeps the entry with the highest traffic).

    Args:
        geos: Region codes (ISO 3166-1 alpha-2).  Defaults to US, TW, JP.
    """

    platform = "google"

    # Default regions — configurable via constructor
    DEFAULT_GEOS = ("US", "TW", "JP")

    def __init__(self, geos: tuple[str, ...] | None = None) -> None:
        self.geos = geos or self.DEFAULT_GEOS

    async def _fetch_geo(self, client: httpx.AsyncClient, geo: str, now: object) -> list[dict]:
        """Fetch trending searches for a single region."""
        url = f"{_RSS_URL}?geo={geo}"
        resp = await client.get(url)
        resp.raise_for_status()

        root = ET.fromstring(resp.text)
        items = root.findall(".//item")[:20]

        results = []
        for rank, item in enumerate(items):
            title = item.findtext("title", "").strip()
            if not title:
                continue
            traffic_str = item.findtext("ht:approx_traffic", "0", _NS)
            heat = _parse_traffic(traffic_str)
            link = item.findtext("link", "") or ""
            results.append(
                {
                    "platform": self.platform,
                    "keyword": title,
                    "rank": rank,
                    "heat_score": heat,
                    "url": link,
                    "collected_at": now,
                }
            )
        return results

    async def collect(self) -> list[dict]:
        """Fetch trending searches from all configured regions and merge.

        Deduplicates by keyword — when the same keyword appears in multiple
        regions, the entry with the highest ``heat_score`` is kept.
        Final list is sorted by heat descending and re-ranked 0..N-1.
        """
        import asyncio

        now = self._now()

        async with httpx.AsyncClient(headers=_HEADERS, timeout=15.0) as client:
            geo_results = await asyncio.gather(
                *(self._fetch_geo(client, geo, now) for geo in self.geos),
                return_exceptions=True,
            )

        # Merge: deduplicate by keyword, keep highest heat_score
        best: dict[str, dict] = {}
        for result in geo_results:
            if isinstance(result, Exception):
                continue
            for item in result:
                kw = item["keyword"]
                if kw not in best or item["heat_score"] > best[kw]["heat_score"]:
                    best[kw] = item

        # Sort by heat descending and re-rank
        merged = sorted(best.values(), key=lambda x: x["heat_score"], reverse=True)
        for rank, item in enumerate(merged):
            item["rank"] = rank

        return merged
