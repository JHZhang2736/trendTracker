from app.collectors.base import BaseCollector
from app.collectors.google import GoogleTrendsCollector
from app.collectors.google_mock import GoogleMockCollector
from app.collectors.registry import CollectorRegistry, registry
from app.collectors.tiktok import TikTokCollector
from app.collectors.tiktok_mock import TikTokMockCollector
from app.collectors.weibo import WeiboCollector
from app.collectors.weibo_mock import WeiboMockCollector

# Auto-register real collectors
registry.register(WeiboCollector)
registry.register(GoogleTrendsCollector)
registry.register(TikTokCollector)

__all__ = [
    "BaseCollector",
    "CollectorRegistry",
    "GoogleMockCollector",
    "GoogleTrendsCollector",
    "TikTokCollector",
    "TikTokMockCollector",
    "WeiboCollector",
    "WeiboMockCollector",
    "registry",
]
