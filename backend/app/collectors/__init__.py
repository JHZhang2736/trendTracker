from app.collectors.base import BaseCollector
from app.collectors.registry import CollectorRegistry, registry
from app.collectors.weibo_mock import WeiboMockCollector

# Auto-register bundled collectors
registry.register(WeiboMockCollector)

__all__ = ["BaseCollector", "CollectorRegistry", "WeiboMockCollector", "registry"]
