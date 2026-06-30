from __future__ import annotations

from wielenbot.models import Listing, Search, Watch
from wielenbot.notifier import Notifier
from wielenbot.store import SeenStore

from .conftest import make_listing


class FakeFetcher:
    def __init__(self, batches: list[list[Listing]]):
        self._batches = batches
        self.calls = 0
        self.urls: list[str] = []

    def fetch(self, search: Search, max_items: int) -> list[Listing]:
        self.urls.append(search.url)
        batch = self._batches[min(self.calls, len(self._batches) - 1)]
        self.calls += 1
        return batch


class RaisingFetcher:
    def fetch(self, search: Search, max_items: int) -> list[Listing]:
        raise RuntimeError("blocked by WAF")


class RecordingTelegram:
    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []

    def send_listing(self, listing: Listing, search_name: str, lang: str = "en") -> None:
        self.sent.append((listing.ad_id, search_name))

    def send_text(self, text: str, disable_preview: bool = False) -> None:  # pragma: no cover
        pass


WATCH = Watch(name="Audi A4", make="audi", model="a4")


def _notifier(tmp_path, fetcher, telegram, *, notify_on_first_run=False):
    store = SeenStore(tmp_path / "seen.sqlite3")
    return store, Notifier(
        fetcher, store, telegram, max_items=25, notify_on_first_run=notify_on_first_run
    )


def test_cold_start_seeds_silently(tmp_path):
    fetcher = FakeFetcher([[make_listing("1"), make_listing("2")]])
    telegram = RecordingTelegram()
    _store, notifier = _notifier(tmp_path, fetcher, telegram)

    result = notifier.run_watch(WATCH)

    assert result.seeded is True
    assert result.new == 0
    assert telegram.sent == []  # no spam on first run


def test_only_new_listings_notify_after_seed(tmp_path):
    fetcher = FakeFetcher(
        [
            [make_listing("1"), make_listing("2")],  # cycle 1: seed
            [make_listing("3"), make_listing("1")],  # cycle 2: only 3 is new
        ]
    )
    telegram = RecordingTelegram()
    _store, notifier = _notifier(tmp_path, fetcher, telegram)

    notifier.run_watch(WATCH)
    result = notifier.run_watch(WATCH)

    assert result.new == 1
    assert telegram.sent == [("3", "Audi A4")]


def test_notify_on_first_run_sends_everything(tmp_path):
    fetcher = FakeFetcher([[make_listing("1"), make_listing("2")]])
    telegram = RecordingTelegram()
    _store, notifier = _notifier(tmp_path, fetcher, telegram, notify_on_first_run=True)

    result = notifier.run_watch(WATCH)

    assert result.new == 2
    assert {ad for ad, _ in telegram.sent} == {"1", "2"}


def test_client_side_filters_applied(tmp_path):
    # Watch wants <= €15k; only the cheap one should be seeded/counted.
    fetcher = FakeFetcher(
        [[make_listing("cheap", price=10000), make_listing("pricey", price=99000)]]
    )
    telegram = RecordingTelegram()
    store, notifier = _notifier(tmp_path, fetcher, telegram, notify_on_first_run=True)
    watch = Watch(name="budget", make="audi", price_max=15000)

    result = notifier.run_watch(watch)

    assert result.fetched == 1
    assert telegram.sent == [("cheap", "budget")]


def test_builds_url_from_make_model(tmp_path):
    fetcher = FakeFetcher([[]])
    telegram = RecordingTelegram()
    _store, notifier = _notifier(tmp_path, fetcher, telegram)

    notifier.run_watch(Watch(name="w", make="Volkswagen", model="Golf"))

    assert fetcher.urls == ["https://www.gaspedaal.nl/volkswagen/golf?srt=df-a"]


def test_fetch_error_is_captured_not_raised(tmp_path):
    telegram = RecordingTelegram()
    _store, notifier = _notifier(tmp_path, RaisingFetcher(), telegram)

    result = notifier.run_watch(WATCH)

    assert result.error is not None
    assert "blocked by WAF" in result.error
    assert telegram.sent == []


def test_error_in_one_watch_does_not_stop_others(tmp_path):
    class MixedFetcher:
        def fetch(self, search: Search, max_items: int):
            if "bad" in search.url:
                raise RuntimeError("boom")
            return [make_listing("1")]

    telegram = RecordingTelegram()
    store = SeenStore(tmp_path / "seen.sqlite3")
    notifier = Notifier(
        MixedFetcher(), store, telegram, max_items=25, notify_on_first_run=True
    )

    results = notifier.run_once(
        [Watch(name="bad", url="https://x/bad"), Watch(name="good", url="https://x/good")]
    )

    assert results[0].error is not None
    assert results[1].new == 1
