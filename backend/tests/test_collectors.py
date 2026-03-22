"""Unit tests for BaseCollector, CollectorRegistry, and WeiboMockCollector."""
from __future__ import annotations

import pytest

from app.collectors.base import BaseCollector
from app.collectors.registry import CollectorRegistry
from app.collectors.weibo_mock import WeiboMockCollector

# ---------------------------------------------------------------------------
# BaseCollector — abstract interface
# ---------------------------------------------------------------------------


def test_base_collector_is_abstract():
    """Cannot instantiate BaseCollector directly."""
    with pytest.raises(TypeError):
        BaseCollector()  # type: ignore[abstract]


def test_concrete_collector_must_implement_collect():
    """A subclass that doesn't implement collect() is still abstract."""

    class IncompleteCollector(BaseCollector):
        platform = "test"

    with pytest.raises(TypeError):
        IncompleteCollector()  # type: ignore[abstract]


# ---------------------------------------------------------------------------
# CollectorRegistry
# ---------------------------------------------------------------------------


def test_registry_register_and_get():
    reg = CollectorRegistry()

    class DummyCollector(BaseCollector):
        platform = "dummy"

        async def collect(self) -> list[dict]:
            return []

    reg.register(DummyCollector)
    assert reg.get("dummy") is DummyCollector


def test_registry_list_platforms():
    reg = CollectorRegistry()

    class AlphaCollector(BaseCollector):
        platform = "alpha"

        async def collect(self) -> list[dict]:
            return []

    class BetaCollector(BaseCollector):
        platform = "beta"

        async def collect(self) -> list[dict]:
            return []

    reg.register(AlphaCollector)
    reg.register(BetaCollector)
    assert reg.list_platforms() == ["alpha", "beta"]


def test_registry_get_unknown_raises_key_error():
    reg = CollectorRegistry()
    with pytest.raises(KeyError):
        reg.get("nonexistent")


def test_registry_register_without_platform_raises():
    reg = CollectorRegistry()

    class NoPlatformCollector(BaseCollector):
        platform = ""

        async def collect(self) -> list[dict]:
            return []

    with pytest.raises(ValueError):
        reg.register(NoPlatformCollector)


def test_registry_decorator_usage():
    """register() can be used as a decorator."""
    reg = CollectorRegistry()

    @reg.register
    class DecoratedCollector(BaseCollector):
        platform = "decorated"

        async def collect(self) -> list[dict]:
            return []

    assert "decorated" in reg.list_platforms()


def test_registry_all_returns_copy():
    reg = CollectorRegistry()

    class C(BaseCollector):
        platform = "c"

        async def collect(self) -> list[dict]:
            return []

    reg.register(C)
    snap = reg.all()
    snap["injected"] = C  # mutating the copy should not affect registry
    assert "injected" not in reg.list_platforms()


# ---------------------------------------------------------------------------
# WeiboMockCollector
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_weibo_mock_collector_platform():
    assert WeiboMockCollector.platform == "weibo"


@pytest.mark.asyncio
async def test_weibo_mock_collector_returns_list():
    collector = WeiboMockCollector()
    results = await collector.collect()
    assert isinstance(results, list)
    assert len(results) > 0


@pytest.mark.asyncio
async def test_weibo_mock_collector_record_schema():
    collector = WeiboMockCollector()
    results = await collector.collect()
    required_keys = {"platform", "keyword", "rank", "heat_score", "url", "collected_at"}
    for item in results:
        assert required_keys <= set(item.keys()), f"Missing keys in record: {item}"


@pytest.mark.asyncio
async def test_weibo_mock_collector_platform_field():
    collector = WeiboMockCollector()
    results = await collector.collect()
    for item in results:
        assert item["platform"] == "weibo"


@pytest.mark.asyncio
async def test_weibo_mock_collector_rank_order():
    collector = WeiboMockCollector()
    results = await collector.collect()
    ranks = [r["rank"] for r in results if r["rank"] is not None]
    assert ranks == sorted(ranks), "Ranks should be in ascending order"


# ---------------------------------------------------------------------------
# _collect_one — error handling
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_collect_one_returns_error_on_failure():
    """_collect_one must return (slug, [], error_str) when the collector raises."""
    from unittest.mock import AsyncMock, patch

    from app.services.collector import _collect_one

    with patch(
        "app.collectors.registry.registry.get",
        return_value=type(
            "FailCollector",
            (),
            {
                "__init__": lambda self: None,
                "collect": AsyncMock(side_effect=RuntimeError("network unreachable")),
            },
        ),
    ):
        slug, records, error = await _collect_one("google")

    assert slug == "google"
    assert records == []
    assert error is not None
    assert "network unreachable" in error


@pytest.mark.asyncio
async def test_collect_one_returns_none_error_on_success():
    """_collect_one must return (slug, records, None) when the collector succeeds."""
    from unittest.mock import AsyncMock, patch

    from app.services.collector import _collect_one

    fake_records = [
        {
            "platform": "google",
            "keyword": "test",
            "rank": 0,
            "heat_score": 1000.0,
            "url": "",
            "collected_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).replace(tzinfo=None),
        }
    ]

    with patch(
        "app.collectors.registry.registry.get",
        return_value=type(
            "OkCollector",
            (),
            {
                "__init__": lambda self: None,
                "collect": AsyncMock(return_value=fake_records),
            },
        ),
    ):
        slug, records, error = await _collect_one("google")

    assert slug == "google"
    assert len(records) == 1
    assert error is None
