"""Collector registry — plug-in manager for platform collectors."""

from __future__ import annotations

from typing import Type

from app.collectors.base import BaseCollector


class CollectorRegistry:
    """Central registry that maps platform slugs to collector classes."""

    def __init__(self) -> None:
        self._registry: dict[str, Type[BaseCollector]] = {}

    def register(self, collector_cls: Type[BaseCollector]) -> Type[BaseCollector]:
        """Register a collector class by its ``platform`` attribute.

        Can be used as a decorator::

            @registry.register
            class MyCollector(BaseCollector):
                platform = "my_platform"
        """
        if not collector_cls.platform:
            raise ValueError(
                f"Collector {collector_cls.__name__} must define a non-empty 'platform' attribute."
            )
        self._registry[collector_cls.platform] = collector_cls
        return collector_cls

    def get(self, platform: str) -> Type[BaseCollector]:
        """Return the collector class for *platform*.

        Raises:
            KeyError: If no collector is registered for the given platform slug.
        """
        if platform not in self._registry:
            raise KeyError(f"No collector registered for platform '{platform}'.")
        return self._registry[platform]

    def list_platforms(self) -> list[str]:
        """Return sorted list of registered platform slugs."""
        return sorted(self._registry.keys())

    def all(self) -> dict[str, Type[BaseCollector]]:
        """Return a copy of the full registry mapping."""
        return dict(self._registry)


# Global singleton registry used across the application.
registry = CollectorRegistry()
