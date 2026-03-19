"""Trends service — business logic for trends queries."""

from __future__ import annotations

from datetime import UTC, datetime

from app.collectors.registry import registry
from app.collectors.weibo_mock import WeiboMockCollector

# Register built-in collectors if not already registered.
if WeiboMockCollector.platform not in registry.list_platforms():
    registry.register(WeiboMockCollector)

# ---------------------------------------------------------------------------
# Mock trend data used until real DB persistence is implemented.
# ---------------------------------------------------------------------------

_MOCK_TRENDS = [
    {
        "platform": "weibo",
        "keyword": "ChatGPT最新版",
        "rank": 1,
        "heat_score": 9800.0,
        "url": "https://weibo.com/hot/1",
        "collected_at": datetime(2026, 3, 19, 6, 0, 0, tzinfo=UTC),
    },
    {
        "platform": "weibo",
        "keyword": "春节档电影票房",
        "rank": 2,
        "heat_score": 8500.0,
        "url": "https://weibo.com/hot/2",
        "collected_at": datetime(2026, 3, 19, 6, 0, 0, tzinfo=UTC),
    },
    {
        "platform": "weibo",
        "keyword": "A股行情",
        "rank": 3,
        "heat_score": 7200.0,
        "url": "https://weibo.com/hot/3",
        "collected_at": datetime(2026, 3, 19, 6, 0, 0, tzinfo=UTC),
    },
    {
        "platform": "weibo",
        "keyword": "世界杯预选赛",
        "rank": 4,
        "heat_score": 6100.0,
        "url": "https://weibo.com/hot/4",
        "collected_at": datetime(2026, 3, 19, 6, 0, 0, tzinfo=UTC),
    },
    {
        "platform": "weibo",
        "keyword": "国产大模型发布",
        "rank": 5,
        "heat_score": 5500.0,
        "url": "https://weibo.com/hot/5",
        "collected_at": datetime(2026, 3, 19, 6, 0, 0, tzinfo=UTC),
    },
]


def get_trends(page: int = 1, page_size: int = 20) -> dict:
    """Return a paginated slice of mock trend data."""
    total = len(_MOCK_TRENDS)
    start = (page - 1) * page_size
    end = start + page_size
    items = _MOCK_TRENDS[start:end]
    return {"total": total, "page": page, "page_size": page_size, "items": items}


def get_platforms() -> list[str]:
    """Return all registered platform slugs."""
    return registry.list_platforms()
