"""Runtime platform enable/disable state.

All registered platforms are enabled by default. Toggling a platform off
excludes it from scheduled collection, manual collection, and all trend
queries (dashboard, trends list, heatmap, velocity).
"""

from __future__ import annotations

import logging

from app.collectors.registry import registry

logger = logging.getLogger(__name__)

# None means "use default" (all enabled).  Once set, this overrides.
_disabled_platforms: set[str] = set()


def get_enabled_platforms() -> list[str]:
    """Return the list of currently enabled platform slugs."""
    all_platforms = registry.list_platforms()
    return [p for p in all_platforms if p not in _disabled_platforms]


def get_disabled_platforms() -> set[str]:
    """Return the set of disabled platform slugs."""
    return set(_disabled_platforms)


def is_platform_enabled(slug: str) -> bool:
    """Check whether a specific platform is enabled."""
    return slug not in _disabled_platforms


def set_platform_enabled(slug: str, enabled: bool) -> None:
    """Enable or disable a platform at runtime."""
    if enabled:
        _disabled_platforms.discard(slug)
        logger.info("Platform '%s' enabled", slug)
    else:
        _disabled_platforms.add(slug)
        logger.info("Platform '%s' disabled", slug)


def get_all_platform_states() -> dict[str, bool]:
    """Return {slug: enabled} for all registered platforms."""
    return {p: p not in _disabled_platforms for p in registry.list_platforms()}
