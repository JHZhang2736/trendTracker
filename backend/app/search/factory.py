"""Search provider factory — creates the correct provider from env config."""

from __future__ import annotations

import logging

from app.config import settings
from app.search.base import BaseSearchProvider, SearchResult

logger = logging.getLogger(__name__)


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

    # Fallback order — primary provider is tried first, then these in order.
    _FALLBACK_ORDER: list[str] = ["bing", "duckduckgo", "google"]

    @classmethod
    def create(cls, provider_name: str | None = None) -> BaseSearchProvider:
        """Return an instance of the configured search provider."""
        name = (provider_name or settings.search_provider).lower()
        return cls._instantiate(name)

    @classmethod
    def _instantiate(cls, name: str) -> BaseSearchProvider:
        dotted_path = cls._PROVIDERS.get(name)
        if dotted_path is None:
            available = ", ".join(sorted(cls._PROVIDERS.keys()))
            raise ValueError(f"Unknown search provider '{name}'. Available: {available}.")

        import importlib

        module_path, class_name = dotted_path.rsplit(".", 1)
        module = importlib.import_module(module_path)
        provider_cls = getattr(module, class_name)
        return provider_cls()

    @classmethod
    def get_fallback_chain(cls) -> list[str]:
        """Return ordered fallback list: primary provider first, then others."""
        primary = settings.search_provider.lower()
        chain = [primary]
        for name in cls._FALLBACK_ORDER:
            if name != primary:
                chain.append(name)
        return chain

    @classmethod
    async def search_with_fallback(cls, query: str, max_results: int = 5) -> list[SearchResult]:
        """Try each provider in fallback chain until one returns results.

        Each provider's own retry logic (3 attempts with backoff) is exhausted
        before moving to the next provider.
        """
        chain = cls.get_fallback_chain()
        for i, name in enumerate(chain):
            try:
                provider = cls._instantiate(name)
                results = await provider.search(query, max_results)
                if results:
                    if i > 0:
                        logger.info(
                            "Fallback search succeeded with %s for '%s' (%d results)",
                            name,
                            query,
                            len(results),
                        )
                    return results
                logger.warning(
                    "Provider %s returned 0 results for '%s', trying next fallback",
                    name,
                    query,
                )
            except Exception:  # noqa: BLE001
                logger.warning(
                    "Provider %s crashed for '%s', trying next fallback",
                    name,
                    query,
                )
        logger.error(
            "All search providers failed for '%s' (chain: %s)",
            query,
            " → ".join(chain),
        )
        return []
