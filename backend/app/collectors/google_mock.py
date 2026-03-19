"""Google Trends mock collector — returns static fixture data for testing."""

from __future__ import annotations

from app.collectors.base import BaseCollector

_MOCK_TRENDS = [
    {
        "keyword": "Artificial Intelligence",
        "rank": 0,
        "heat_score": 2_000_000.0,
        "url": "https://trends.google.com/trends/explore?q=Artificial+Intelligence",
    },
    {
        "keyword": "World Cup 2026",
        "rank": 1,
        "heat_score": 1_500_000.0,
        "url": "https://trends.google.com/trends/explore?q=World+Cup+2026",
    },
    {
        "keyword": "Stock Market",
        "rank": 2,
        "heat_score": 1_200_000.0,
        "url": "https://trends.google.com/trends/explore?q=Stock+Market",
    },
    {
        "keyword": "Electric Vehicle",
        "rank": 3,
        "heat_score": 900_000.0,
        "url": "https://trends.google.com/trends/explore?q=Electric+Vehicle",
    },
    {
        "keyword": "Cryptocurrency",
        "rank": 4,
        "heat_score": 750_000.0,
        "url": "https://trends.google.com/trends/explore?q=Cryptocurrency",
    },
]


class GoogleMockCollector(BaseCollector):
    """Mock collector for Google Trends — returns fixed test data without network I/O."""

    platform = "google"

    async def collect(self) -> list[dict]:
        """Return static mock trend data for Google Trends."""
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
