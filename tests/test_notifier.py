from __future__ import annotations

from wielenbot.models import Listing, Search
from wielenbot.notifier import Notifier
from wielenbot.store import SeenStore

from .conftest import make_listing


class FakeFetcher:
    def __init__(self, batches: list[list[Listing]]):
        self._batches = batches
        self.calls = 0

    def fetch(self, search: Search, max_items: int) -> list[Listing]:
        batch = self._batches[min(self.calls, len(self._batches) - 1)]
        self.calls += 1
        return batch


class RaisingFetcher:
    def fetch(self, search: Search, max_items: int) -> list[Listing]:
        raise RuntimeError("blocked by WAF")


class RecordingTelegram:
    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []

    def send_listing(self, listing: Listing, search_name: str) -> None:
        self.sent.append((listing.ad_id, search_name))

    def send_text(self, text: str, disable_preview: bool = False) -> None:  # pragma: no cover
        pass


SEARCH = Search(name="Audi A4", url="https://www.gaspedaal.nl/audi/a4?srt=df-a")


def _notifier(tmp_path, fetcher, telegram, *, notify_on_first_run=False):
    store = SeenStore(tmp_path / "seen.sqlite3")
    return store, Notifier(
        fetcher, store, telegram, max_items=25, notify_on_first_run=notify_on_first_run
    )


def test_cold_start_seeds_silently(tmp_path):
    fetcher = FakeFetcher([[make_listing("1"), make_listing("2")]])
    telegram = RecordingTelegram()
    _store, notifier = _notifier(tmp_path, fetcher, telegram)

    result = notifier.run_search(SEARCH)

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

    notifier.run_search(SEARCH)
    result = notifier.run_search(SEARCH)

    assert result.new == 1
    assert telegram.sent == [("3", "Audi A4")]


def test_same_listing_not_renotified(tmp_path):
    fetcher = FakeFetcher(
        [
            [make_listing("1")],  # seed
            [make_listing("2")],  # notify 2
            [make_listing("2")],  # 2 again -> nothing
        ]
    )
    telegram = RecordingTelegram()
    _store, notifier = _notifier(tmp_path, fetcher, telegram)

    notifier.run_search(SEARCH)
    notifier.run_search(SEARCH)
    third = notifier.run_search(SEARCH)

    assert third.new == 0
    assert telegram.sent == [("2", "Audi A4")]


def test_notify_on_first_run_sends_everything(tmp_path):
    fetcher = FakeFetcher([[make_listing("1"), make_listing("2")]])
    telegram = RecordingTelegram()
    _store, notifier = _notifier(tmp_path, fetcher, telegram, notify_on_first_run=True)

    result = notifier.run_search(SEARCH)

    assert result.new == 2
    assert {ad for ad, _ in telegram.sent} == {"1", "2"}


def test_fetch_error_is_captured_not_raised(tmp_path):
    telegram = RecordingTelegram()
    _store, notifier = _notifier(tmp_path, RaisingFetcher(), telegram)

    result = notifier.run_search(SEARCH)

    assert result.error is not None
    assert "blocked by WAF" in result.error
    assert telegram.sent == []


def test_error_in_one_search_does_not_stop_others(tmp_path):
    # First search raises, second succeeds within the same run_once.
    class MixedFetcher:
        def fetch(self, search: Search, max_items: int):
            if search.name == "bad":
                raise RuntimeError("boom")
            return [make_listing("1")]

    telegram = RecordingTelegram()
    store = SeenStore(tmp_path / "seen.sqlite3")
    notifier = Notifier(
        MixedFetcher(), store, telegram, max_items=25, notify_on_first_run=True
    )

    results = notifier.run_once(
        (Search("bad", "u1"), Search("good", "u2"))
    )

    assert results[0].error is not None
    assert results[1].new == 1
