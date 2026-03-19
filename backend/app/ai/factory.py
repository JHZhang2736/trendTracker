"""LLM provider factory — creates the correct provider from env config."""

from __future__ import annotations

from app.ai.base import BaseLLMProvider
from app.config import settings


class LLMFactory:
    """Factory that instantiates the configured LLM provider.

    The active provider is controlled by the ``LLM_PROVIDER`` environment
    variable (mapped to :attr:`~app.config.Settings.llm_provider`).
    Adding a new provider requires only:
    1. Creating a subclass of :class:`~app.ai.base.BaseLLMProvider`.
    2. Registering it in :attr:`_PROVIDERS` below.
    """

    _PROVIDERS: dict[str, str] = {
        "minimax": "app.ai.minimax_provider.MiniMaxProvider",
    }

    @classmethod
    def create(cls, provider_name: str | None = None) -> BaseLLMProvider:
        """Return an instance of the configured LLM provider.

        Args:
            provider_name: Override the provider name from settings.
                           Defaults to ``settings.llm_provider``.

        Raises:
            ValueError: If the requested provider is not registered.
        """
        name = (provider_name or settings.llm_provider).lower()
        dotted_path = cls._PROVIDERS.get(name)
        if dotted_path is None:
            available = ", ".join(sorted(cls._PROVIDERS.keys()))
            raise ValueError(f"Unknown LLM provider '{name}'. Available providers: {available}.")

        module_path, class_name = dotted_path.rsplit(".", 1)
        import importlib

        module = importlib.import_module(module_path)
        provider_cls = getattr(module, class_name)
        return provider_cls()
