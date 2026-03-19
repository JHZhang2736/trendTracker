"""TikTok mock collector — returns static fixture data for testing."""

from __future__ import annotations

from app.collectors.base import BaseCollector

_MOCK_TRENDS = [
    {
        "keyword": "#fyp",
        "rank": 0,
        "heat_score": 50_000_000_000.0,
        "url": "https://www.tiktok.com/tag/fyp",
    },
    {
        "keyword": "#viral",
        "rank": 1,
        "heat_score": 30_000_000_000.0,
        "url": "https://www.tiktok.com/tag/viral",
    },
    {
        "keyword": "#trending",
        "rank": 2,
        "heat_score": 20_000_000_000.0,
        "url": "https://www.tiktok.com/tag/trending",
    },
    {
        "keyword": "#ai",
        "rank": 3,
        "heat_score": 10_000_000_000.0,
        "url": "https://www.tiktok.com/tag/ai",
    },
    {
        "keyword": "#dance",
        "rank": 4,
        "heat_score": 8_000_000_000.0,
        "url": "https://www.tiktok.com/tag/dance",
    },
]


class TikTokMockCollector(BaseCollector):
    """Mock collector for TikTok — returns fixed test data without network I/O."""

    platform = "tiktok"

    async def collect(self) -> list[dict]:
        """Return static mock trend data for TikTok."""
        now = self._now()
        return [
            {
                "platform": self.platform,
                "keyword": item["keyword"],
                "rank": item["rank"],
                "heat_score": item["heat_score"],
                "url": item["url"],
                "collected_at": now,
            }
            for item in _MOCK_TRENDS
        ]
