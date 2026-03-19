"""Collector service — business logic for manual collection runs."""

from __future__ import annotations

from app.collectors.registry import registry
from app.collectors.weibo_mock import WeiboMockCollector

# Register built-in collectors if not already registered.
if WeiboMockCollector.platform not in registry.list_platforms():
    registry.register(WeiboMockCollector)


async def run_all_collectors() -> dict:
    """Run all registered collectors and return aggregated result.

    Returns a dict with ``status`` and ``records_count``.
    Business logic only; no DB writes in MVP (mock data).
    """
    platforms = registry.list_platforms()
    total_records = 0

    for platform in platforms:
        collector_cls = registry.get(platform)
        collector = collector_cls()
        try:
            records = await collector.collect()
            total_records += len(records)
        except Exception:  # noqa: BLE001
            pass

    return {"status": "ok", "records_count": total_records}
