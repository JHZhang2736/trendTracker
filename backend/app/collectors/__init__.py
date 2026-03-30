from app.collectors.base import BaseCollector
from app.collectors.dailyhot import (
    BilibiliCollector,
    CoolapkCollector,
    DoubanGroupCollector,
    DouyinCollector,
    GitHubCollector,
    HackerNewsCollector,
    HupuCollector,
    Kr36Collector,
    KuaishouCollector,
    NeteaseNewsCollector,
    NYTimesCollector,
    ProductHuntCollector,
    QQNewsCollector,
    SinaNewsCollector,
    SmzdmCollector,
    TiebaCollector,
    ToutiaoCollector,
    YystvCollector,
    ZhihuCollector,
    ZhihuDailyCollector,
)
from app.collectors.registry import CollectorRegistry, registry
from app.collectors.weibo import WeiboCollector
from app.collectors.weibo_mock import WeiboMockCollector

# Auto-register all collectors
registry.register(WeiboCollector)
registry.register(DouyinCollector)
registry.register(ToutiaoCollector)
registry.register(QQNewsCollector)
registry.register(NeteaseNewsCollector)
registry.register(SinaNewsCollector)
registry.register(NYTimesCollector)
registry.register(ZhihuCollector)
registry.register(ZhihuDailyCollector)
registry.register(TiebaCollector)
registry.register(HupuCollector)
registry.register(DoubanGroupCollector)
registry.register(Kr36Collector)
registry.register(ProductHuntCollector)
registry.register(GitHubCollector)
registry.register(HackerNewsCollector)
registry.register(BilibiliCollector)
registry.register(KuaishouCollector)
registry.register(SmzdmCollector)
registry.register(CoolapkCollector)
registry.register(YystvCollector)

__all__ = [
    "BaseCollector",
    "BilibiliCollector",
    "CollectorRegistry",
    "CoolapkCollector",
    "DoubanGroupCollector",
    "DouyinCollector",
    "GitHubCollector",
    "HackerNewsCollector",
    "HupuCollector",
    "Kr36Collector",
    "KuaishouCollector",
    "NeteaseNewsCollector",
    "NYTimesCollector",
    "ProductHuntCollector",
    "QQNewsCollector",
    "SinaNewsCollector",
    "SmzdmCollector",
    "TiebaCollector",
    "ToutiaoCollector",
    "WeiboCollector",
    "WeiboMockCollector",
    "YystvCollector",
    "ZhihuCollector",
    "ZhihuDailyCollector",
    "registry",
]
