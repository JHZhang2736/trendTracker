"""Weibo mock collector — returns static fixture data for testing."""

from __future__ import annotations

from app.collectors.base import BaseCollector

_MOCK_TRENDS = [
    {"keyword": "ChatGPT最新版", "rank": 1, "heat_score": 9800.0, "url": "https://weibo.com/hot/1"},
    {
        "keyword": "春节档电影票房",
        "rank": 2,
        "heat_score": 8500.0,
        "url": "https://weibo.com/hot/2",
    },
    {"keyword": "A股行情", "rank": 3, "heat_score": 7200.0, "url": "https://weibo.com/hot/3"},
    {"keyword": "世界杯预选赛", "rank": 4, "heat_score": 6100.0, "url": "https://weibo.com/hot/4"},
    {
        "keyword": "国产大模型发布",
        "rank": 5,
        "heat_score": 5500.0,
        "url": "https://weibo.com/hot/5",
    },
]


class WeiboMockCollector(BaseCollector):
    """Mock collector for Weibo — returns fixed test data without network I/O."""

    platform = "weibo"

    async def collect(self) -> list[dict]:
        """Return static mock trend data for Weibo."""
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
