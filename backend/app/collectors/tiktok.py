"""TikTok trending hashtag collector — uses Creative Center unofficial API."""

from __future__ import annotations

import logging

import httpx

from app.collectors.base import BaseCollector

logger = logging.getLogger(__name__)

# TikTok Creative Center trending hashtags endpoint (unofficial, no auth required
# for basic requests, but subject to rate limiting and geo-restrictions).
_API_URL = (
    "https://ads.tiktok.com/creative_radar_api/v1/popular_trend/hashtag/list"
    "?period=7&page=1&limit=20&order_by=popular&country_code={country_code}"
)
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer": "https://ads.tiktok.com/business/creativecenter/hashtag/pc/en",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
}


class TikTokCollector(BaseCollector):
    """Collect Top-20 trending hashtags from TikTok Creative Center.

    Args:
        country_code: ISO 3166-1 alpha-2 country code, e.g. ``"US"``, ``"JP"``.
    """

    platform = "tiktok"

    def __init__(self, country_code: str = "US") -> None:
        self.country_code = country_code

    async def collect(self) -> list[dict]:
        """Fetch Top-20 trending hashtags from TikTok Creative Center API.

        Returns:
            List of trend dicts with standard BaseCollector fields.
            Returns an empty list if the API is unavailable or rate-limited.
        """
        now = self._now()
        url = _API_URL.format(country_code=self.country_code)

        async with httpx.AsyncClient(headers=_HEADERS, timeout=15.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()

        if data.get("code") != 0:
            logger.warning(
                "TikTokCollector: API returned code=%s msg=%s",
                data.get("code"),
                data.get("msg"),
            )
            return []

        items = data.get("data", {}).get("list", [])
        results = []
        for rank, item in enumerate(items[:20]):
            tag = item.get("hashtag_name", "").lstrip("#")
            if not tag:
                continue
            # video_views is the best proxy for heat; fall back to publish_cnt
            heat = float(item.get("video_views") or item.get("publish_cnt") or 0)
            results.append(
                {
                    "platform": self.platform,
                    "keyword": f"#{tag}",
                    "rank": rank,
                    "heat_score": heat,
                    "url": f"https://www.tiktok.com/tag/{tag}",
                    "collected_at": now,
                }
            )
        return results
