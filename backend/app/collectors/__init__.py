from app.collectors.base import BaseCollector
from app.collectors.google import GoogleTrendsCollector
from app.collectors.google_mock import GoogleMockCollector
from app.collectors.registry import CollectorRegistry, registry
from app.collectors.weibo import WeiboCollector
from app.collectors.weibo_mock import WeiboMockCollector

# Auto-register real collectors
registry.register(WeiboCollector)
registry.register(GoogleTrendsCollector)

__all__ = [
    "BaseCollector",
    "CollectorRegistry",
    "GoogleMockCollector",
    "GoogleTrendsCollector",
    "WeiboCollector",
    "WeiboMockCollector",
    "registry",
]
