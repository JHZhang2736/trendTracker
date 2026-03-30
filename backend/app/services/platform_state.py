"""Runtime platform enable/disable state.

All registered platforms are enabled by default unless disabled via
``PLATFORM_<SLUG>=false`` in ``.env``.  Toggling a platform off excludes it
from scheduled collection, manual collection, and all trend queries
(dashboard, trends list, heatmap, velocity).

The initial disabled set is loaded lazily on first access so that collector
registration (which happens in ``app.collectors.__init__``) is guaranteed to
have completed before we query the registry.
"""

from __future__ import annotations

import logging

from app.collectors.registry import registry
from app.config import settings

logger = logging.getLogger(__name__)

_disabled_platforms: set[str] | None = None  # None = not yet initialised


def _slug_to_config_key(slug: str) -> str:
    """Convert a platform slug like ``qq-news`` to config field ``platform_qq_news``."""
    return f"platform_{slug.replace('-', '_')}"


def _ensure_loaded() -> set[str]:
    """Lazily initialise the disabled-set from PLATFORM_* config on first use."""
    global _disabled_platforms  # noqa: PLW0603
    if _disabled_platforms is not None:
        return _disabled_platforms

    disabled: set[str] = set()
    for slug in registry.list_platforms():
        key = _slug_to_config_key(slug)
        if not getattr(settings, key, True):
            disabled.add(slug)
            logger.info("Platform '%s' disabled by config (%s=false)", slug, key.upper())
    _disabled_platforms = disabled
    return _disabled_platforms


def get_enabled_platforms() -> list[str]:
    """Return the list of currently enabled platform slugs."""
    disabled = _ensure_loaded()
    return [p for p in registry.list_platforms() if p not in disabled]


def get_disabled_platforms() -> set[str]:
    """Return the set of disabled platform slugs."""
    return set(_ensure_loaded())


def is_platform_enabled(slug: str) -> bool:
    """Check whether a specific platform is enabled."""
    return slug not in _ensure_loaded()


def set_platform_enabled(slug: str, enabled: bool) -> None:
    """Enable or disable a platform at runtime."""
    _ensure_loaded()
    assert _disabled_platforms is not None
    if enabled:
        _disabled_platforms.discard(slug)
        logger.info("Platform '%s' enabled", slug)
    else:
        _disabled_platforms.add(slug)
        logger.info("Platform '%s' disabled", slug)


def get_all_platform_states() -> dict[str, bool]:
    """Return {slug: enabled} for all registered platforms."""
    disabled = _ensure_loaded()
    return {p: p not in disabled for p in registry.list_platforms()}
