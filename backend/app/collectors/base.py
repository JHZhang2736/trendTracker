"""Abstract base class for all data collectors."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import UTC, datetime


class BaseCollector(ABC):
    """Abstract base for platform trend collectors.

    Each concrete collector must implement :meth:`collect` and declare a
    ``platform`` class attribute that identifies it in the registry.
    """

    platform: str = ""

    @abstractmethod
    async def collect(self) -> list[dict]:
        """Fetch trend data from the platform.

        Returns:
            A list of dicts, each containing at minimum:
            - platform (str)
            - keyword (str)
            - rank (int | None)
            - heat_score (float | None)
            - url (str | None)
            - collected_at (datetime)
        """

    @staticmethod
    def _now() -> datetime:
        return datetime.now(UTC)
