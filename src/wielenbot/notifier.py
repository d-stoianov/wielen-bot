"""Orchestration: for each watch, fetch, filter, diff against the store, notify."""

from __future__ import annotations

import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from .fetchers.base import Fetcher
from .i18n import DEFAULT_LANGUAGE
from .models import Search, Watch
from .store import SeenStore
from .telegram import TelegramNotifier
from .watches import build_search_url, watch_matches

logger = logging.getLogger(__name__)


@dataclass
class WatchResult:
    name: str
    fetched: int = 0  # listings that passed the watch's filters
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

    def run_watch(self, watch: Watch) -> WatchResult:
        result = WatchResult(name=watch.name)
        search = Search(name=watch.name, url=build_search_url(watch))
        try:
            listings = self._fetcher.fetch(search, self._max_items)
        except Exception as exc:  # noqa: BLE001 - report, don't crash the loop
            logger.exception("Fetch failed for %r", watch.name)
            result.error = f"{type(exc).__name__}: {exc}"
            return result

        listings = [lst for lst in listings if watch_matches(watch, lst)]
        result.fetched = len(listings)
        new = self._store.filter_new(watch.name, listings)

        # Cold start: avoid blasting every currently-listed car. Record them as
        # seen so only genuinely new listings notify from here on.
        cold_start = not self._store.has_any(watch.name)
        if cold_start and not self._notify_on_first_run:
            self._store.mark_seen(watch.name, [lst.ad_id for lst in listings])
            result.seeded = True
            logger.info("Seeded %d existing listings for %r (no notify)", len(listings), watch.name)
            return result

        lang = self._language_provider()
        for listing in new:
            self._telegram.send_listing(listing, watch.name, lang)
        self._store.mark_seen(watch.name, [lst.ad_id for lst in new])
        result.new = len(new)
        if new:
            logger.info("Notified %d new listings for %r", len(new), watch.name)
        return result

    def run_once(self, watches: Sequence[Watch]) -> list[WatchResult]:
        return [self.run_watch(w) for w in watches]
