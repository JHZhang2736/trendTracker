"""Weibo hot search real collector — uses the public side/hotSearch API."""

from __future__ import annotations

import httpx

from app.collectors.base import BaseCollector

_WEIBO_HOT_SEARCH_URL = "https://weibo.com/ajax/side/hotSearch"
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer": "https://weibo.com/",
    "Accept": "application/json, text/plain, */*",
}


class WeiboCollector(BaseCollector):
    """Real Weibo hot search collector using the public API (no login required)."""

    platform = "weibo"

    async def collect(self) -> list[dict]:
        """Fetch Top-50 hot search entries from Weibo public API.

        Returns a list of dicts with standard BaseCollector fields.
        Raises httpx.HTTPError on network / HTTP failures.
        """
        now = self._now()
        async with httpx.AsyncClient(headers=_HEADERS, timeout=15.0) as client:
            resp = await client.get(_WEIBO_HOT_SEARCH_URL)
            resp.raise_for_status()
            data = resp.json()

        items = data.get("data", {}).get("realtime", [])
        results = []
        for item in items[:50]:
            word = item.get("word", "")
            results.append(
                {
                    "platform": self.platform,
                    "keyword": word,
                    "rank": item.get("rank"),
                    "heat_score": float(item.get("num", 0)),
                    "url": f"https://s.weibo.com/weibo?q=%23{word}%23",
                    "collected_at": now,
                }
            )
        return results
