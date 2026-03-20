"""TikTok trending hashtag collector — uses Creative Center unofficial API.

Authentication note
-------------------
TikTok's Creative Center API requires a valid login session.  Set the
``TIKTOK_COOKIE`` environment variable to the full ``Cookie`` header value
copied from an authenticated browser session on ``ads.tiktok.com``.

If ``TIKTOK_COOKIE`` is not configured the collector returns an empty list and
logs a warning — other platforms are unaffected.
"""

from __future__ import annotations

import logging

import httpx

from app.collectors.base import BaseCollector
from app.config import settings

logger = logging.getLogger(__name__)

_API_URL = (
    "https://ads.tiktok.com/creative_radar_api/v1/popular_trend/hashtag/list"
    "?period=7&page=1&limit=20&order_by=popular&country_code={country_code}"
)
_BASE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer": "https://ads.tiktok.com/business/creativecenter/hashtag/pc/en",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Origin": "https://ads.tiktok.com",
}


def _build_headers(cookie: str) -> dict[str, str]:
    """Merge base headers with cookie and extract X-CSRFToken if present."""
    headers = dict(_BASE_HEADERS)
    headers["Cookie"] = cookie
    # TikTok Creative Center requires X-CSRFToken matching the csrftoken cookie
    for part in cookie.split(";"):
        part = part.strip()
        if part.startswith("csrftoken="):
            headers["X-CSRFToken"] = part[len("csrftoken=") :]
            break
    return headers


class TikTokCollector(BaseCollector):
    """Collect trending hashtags from TikTok Creative Center (multiple regions).

    Fetches from multiple countries and merges into a single list, deduplicated
    by hashtag (keeps the entry with the highest view count).

    Requires ``TIKTOK_COOKIE`` in the environment.  Returns ``[]`` and logs a
    warning if the cookie is not configured or if the API rejects the request.
    """

    platform = "tiktok"

    DEFAULT_COUNTRIES = ("US", "GB", "JP", "BR", "ID", "TH")

    def __init__(self, countries: tuple[str, ...] | None = None) -> None:
        self.countries = countries or self.DEFAULT_COUNTRIES

    async def _fetch_country(
        self, client: httpx.AsyncClient, country_code: str, now: object
    ) -> list[dict]:
        """Fetch trending hashtags for a single country."""
        url = _API_URL.format(country_code=country_code)
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()

        if data.get("code") != 0:
            logger.warning(
                "TikTokCollector[%s]: API code=%s msg=%s",
                country_code,
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

    async def collect(self) -> list[dict]:
        """Fetch trending hashtags from all configured countries and merge.

        Deduplicates by hashtag — when the same tag appears in multiple
        countries, the entry with the highest ``heat_score`` is kept.
        Final list is sorted by heat descending and re-ranked 0..N-1.
        """
        import asyncio

        cookie = settings.tiktok_cookie.strip()
        if not cookie:
            logger.warning(
                "TikTokCollector: TIKTOK_COOKIE is not set — skipping collection. "
                "Copy the Cookie header from an authenticated ads.tiktok.com browser "
                "session and set it in your .env file."
            )
            return []

        now = self._now()
        headers = _build_headers(cookie)

        async with httpx.AsyncClient(headers=headers, timeout=15.0) as client:
            country_results = await asyncio.gather(
                *(self._fetch_country(client, cc, now) for cc in self.countries),
                return_exceptions=True,
            )

        # Merge: deduplicate by hashtag, keep highest heat_score
        best: dict[str, dict] = {}
        for result in country_results:
            if isinstance(result, Exception):
                logger.error("TikTokCollector: region failed — %s", result)
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
