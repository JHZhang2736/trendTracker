from app.collectors.base import BaseCollector
from app.collectors.registry import CollectorRegistry, registry
from app.collectors.weibo import WeiboCollector
from app.collectors.weibo_mock import WeiboMockCollector

# Auto-register real collectors (WeiboCollector overwrites the mock)
registry.register(WeiboCollector)

__all__ = ["BaseCollector", "CollectorRegistry", "WeiboCollector", "WeiboMockCollector", "registry"]
