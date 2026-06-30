"""Fetcher interface. A fetcher turns a Search into a list of normalized Listings."""

from __future__ import annotations

from typing import Protocol

from ..models import Listing, Search


class Fetcher(Protocol):
    def fetch(self, search: Search, max_items: int) -> list[Listing]:
        """Return current listings for `search`, newest first, capped at `max_items`.

        Implementations should raise on hard failures (auth, blocked, network) so
        the notifier can report the error rather than silently watching nothing.
        """
        ...
