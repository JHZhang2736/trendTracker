"""Search provider factory — creates the correct provider from env config."""

from __future__ import annotations

from app.config import settings
from app.search.base import BaseSearchProvider


class SearchFactory:
    """Factory that instantiates the configured search provider.

    The active provider is controlled by the ``SEARCH_PROVIDER`` environment
    variable (mapped to :attr:`~app.config.Settings.search_provider`).
    """

    _PROVIDERS: dict[str, str] = {
        "duckduckgo": "app.search.duckduckgo.DuckDuckGoProvider",
        "google": "app.search.google.GoogleProvider",
        "bing": "app.search.bing.BingProvider",
    }

    @classmethod
    def create(cls, provider_name: str | None = None) -> BaseSearchProvider:
        """Return an instance of the configured search provider."""
        name = (provider_name or settings.search_provider).lower()
        dotted_path = cls._PROVIDERS.get(name)
        if dotted_path is None:
            available = ", ".join(sorted(cls._PROVIDERS.keys()))
            raise ValueError(f"Unknown search provider '{name}'. Available: {available}.")

        module_path, class_name = dotted_path.rsplit(".", 1)
        import importlib

        module = importlib.import_module(module_path)
        provider_cls = getattr(module, class_name)
        return provider_cls()
