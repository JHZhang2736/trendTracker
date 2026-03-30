"""DailyHot collectors — fetch trending data from self-hosted DailyHotApi.

Each supported sub-platform is registered as its own collector so it can be
scheduled and filtered independently.  The API is expected at the URL
configured via ``DAILYHOT_API_URL`` (default ``http://localhost:6688``).

Reference: https://github.com/imsyy/DailyHotApi
"""

from __future__ import annotations

import logging

import httpx

from app.collectors.base import BaseCollector
from app.config import settings

logger = logging.getLogger(__name__)

_TIMEOUT = 15.0


def _api_url(route: str) -> str:
    base = settings.dailyhot_api_url.rstrip("/")
    return f"{base}/{route}"


def _parse_hot(value: object) -> float:
    """Convert DailyHot ``hot`` field to a float.

    Handles comma-formatted strings like ``'24,129'``, plain numbers, and
    fallback to 0.0 on any conversion failure.
    """
    if value is None:
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        pass
    try:
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return 0.0


class _DailyHotBase(BaseCollector):
    """Shared logic for all DailyHot sub-platform collectors."""

    # Subclasses set these
    platform: str = ""
    _route: str = ""  # API path segment, e.g. "zhihu", "bilibili"

    async def collect(self) -> list[dict]:
        now = self._now()
        url = _api_url(self._route)
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            payload = resp.json()

        if payload.get("code") != 200:
            logger.warning("DailyHot %s returned code %s", self._route, payload.get("code"))
            return []

        items = payload.get("data", [])
        results = []
        for i, item in enumerate(items[:50]):
            title = item.get("title", "").strip()
            if not title:
                continue
            results.append(
                {
                    "platform": self.platform,
                    "keyword": title,
                    "rank": i + 1,
                    "heat_score": _parse_hot(item.get("hot", 0)),
                    "url": item.get("url") or item.get("mobileUrl") or "",
                    "collected_at": now,
                }
            )
        return results


# --- 综合热搜/新闻 ---


class DouyinCollector(_DailyHotBase):
    platform = "douyin"
    _route = "douyin"


class ToutiaoCollector(_DailyHotBase):
    platform = "toutiao"
    _route = "toutiao"


class QQNewsCollector(_DailyHotBase):
    platform = "qq-news"
    _route = "qq-news"


class NeteaseNewsCollector(_DailyHotBase):
    platform = "netease-news"
    _route = "netease-news"


class SinaNewsCollector(_DailyHotBase):
    platform = "sina-news"
    _route = "sina-news"


class NYTimesCollector(_DailyHotBase):
    platform = "nytimes"
    _route = "nytimes"


# --- 社区/讨论 ---


class ZhihuCollector(_DailyHotBase):
    platform = "zhihu"
    _route = "zhihu"


class ZhihuDailyCollector(_DailyHotBase):
    platform = "zhihu-daily"
    _route = "zhihu-daily"


class TiebaCollector(_DailyHotBase):
    platform = "tieba"
    _route = "tieba"


class HupuCollector(_DailyHotBase):
    platform = "hupu"
    _route = "hupu"


class DoubanGroupCollector(_DailyHotBase):
    platform = "douban-group"
    _route = "douban-group"


# --- 科技/互联网 ---


class Kr36Collector(_DailyHotBase):
    platform = "36kr"
    _route = "36kr"


class ProductHuntCollector(_DailyHotBase):
    platform = "producthunt"
    _route = "producthunt"


# --- 开发者 ---


class GitHubCollector(_DailyHotBase):
    platform = "github"
    _route = "github"


class HackerNewsCollector(_DailyHotBase):
    platform = "hackernews"
    _route = "hackernews"


# --- 视频/娱乐 ---


class BilibiliCollector(_DailyHotBase):
    platform = "bilibili"
    _route = "bilibili"


class KuaishouCollector(_DailyHotBase):
    platform = "kuaishou"
    _route = "kuaishou"


# --- 购物/消费 ---


class SmzdmCollector(_DailyHotBase):
    platform = "smzdm"
    _route = "smzdm"


class CoolapkCollector(_DailyHotBase):
    platform = "coolapk"
    _route = "coolapk"


# --- 游戏 ---


class YystvCollector(_DailyHotBase):
    platform = "yystv"
    _route = "yystv"
