"""Google Trends real collector — daily trending searches via RSS feed."""

from __future__ import annotations

import xml.etree.ElementTree as ET

import httpx

from app.collectors.base import BaseCollector

_RSS_URL = "https://trends.google.com/trends/trendingsearches/daily/rss"
_NS = {"ht": "https://trends.google.com/trends/trendingsearches/daily"}
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
    """Collect Top-20 daily trending searches from Google Trends RSS feed.

    Args:
        geo: ISO 3166-1 alpha-2 country code, e.g. ``"US"``, ``"TW"``.
    """

    platform = "google"

    def __init__(self, geo: str = "US") -> None:
        self.geo = geo

    async def collect(self) -> list[dict]:
        """Fetch Top-20 trending searches for *geo* from Google Trends RSS.

        Returns:
            List of trend dicts with standard BaseCollector fields.
        Raises:
            httpx.HTTPError on network / HTTP failures.
        """
        now = self._now()
        url = f"{_RSS_URL}?geo={self.geo}"

        async with httpx.AsyncClient(headers=_HEADERS, timeout=15.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            xml_text = resp.text

        root = ET.fromstring(xml_text)
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
