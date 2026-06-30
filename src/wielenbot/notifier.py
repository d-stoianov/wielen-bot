"""Orchestration: fetch each search, diff against the store, notify, persist."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass

from .fetchers.base import Fetcher
from .i18n import DEFAULT_LANGUAGE
from .models import Search
from .store import SeenStore
from .telegram import TelegramNotifier

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    search: Search
    fetched: int = 0
    new: int = 0
    seeded: bool = False  # cold-start: recorded silently, did not notify
    error: str | None = None


class Notifier:
    def __init__(
        self,
        fetcher: Fetcher,
        store: SeenStore,
        telegram: TelegramNotifier,
        *,
        max_items: int,
        notify_on_first_run: bool,
        language_provider: Callable[[], str] = lambda: DEFAULT_LANGUAGE,
    ) -> None:
        self._fetcher = fetcher
        self._store = store
        self._telegram = telegram
        self._max_items = max_items
        self._notify_on_first_run = notify_on_first_run
        self._language_provider = language_provider

    def run_search(self, search: Search) -> SearchResult:
        result = SearchResult(search=search)
        try:
            listings = self._fetcher.fetch(search, self._max_items)
        except Exception as exc:  # noqa: BLE001 - report, don't crash the loop
            logger.exception("Fetch failed for %r", search.name)
            result.error = f"{type(exc).__name__}: {exc}"
            return result

        result.fetched = len(listings)
        new = self._store.filter_new(search.name, listings)

        # Cold start: avoid blasting every currently-listed car. Record them as
        # seen so only genuinely new listings notify from here on.
        cold_start = not self._store.has_any(search.name)
        if cold_start and not self._notify_on_first_run:
            self._store.mark_seen(search.name, [lst.ad_id for lst in listings])
            result.seeded = True
            logger.info("Seeded %d existing listings for %r (no notify)", len(listings), search.name)
            return result

        lang = self._language_provider()
        for listing in new:
            self._telegram.send_listing(listing, search.name, lang)
        self._store.mark_seen(search.name, [lst.ad_id for lst in new])
        result.new = len(new)
        if new:
            logger.info("Notified %d new listings for %r", len(new), search.name)
        return result

    def run_once(self, searches: tuple[Search, ...]) -> list[SearchResult]:
        return [self.run_search(s) for s in searches]
