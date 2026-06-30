from __future__ import annotations

from wielenbot.store import SeenStore

from .conftest import make_listing


def test_filter_new_excludes_seen(tmp_path):
    store = SeenStore(tmp_path / "seen.sqlite3")
    a, b, c = make_listing("1"), make_listing("2"), make_listing("3")

    assert store.filter_new("s", [a, b]) == [a, b]
    store.mark_seen("s", [a.ad_id, b.ad_id])

    new = store.filter_new("s", [a, b, c])
    assert [lst.ad_id for lst in new] == ["3"]


def test_filter_new_dedups_within_batch(tmp_path):
    store = SeenStore(tmp_path / "seen.sqlite3")
    dup1, dup2 = make_listing("9"), make_listing("9", price=9999)

    new = store.filter_new("s", [dup1, dup2])
    assert len(new) == 1


def test_seen_is_scoped_per_search(tmp_path):
    store = SeenStore(tmp_path / "seen.sqlite3")
    a = make_listing("1")
    store.mark_seen("search-A", [a.ad_id])

    # Same ad is "new" for a different search.
    assert store.filter_new("search-B", [a]) == [a]
    assert store.is_seen("search-A", "1")
    assert not store.is_seen("search-B", "1")


def test_has_any(tmp_path):
    store = SeenStore(tmp_path / "seen.sqlite3")
    assert not store.has_any("s")
    store.mark_seen("s", ["1"])
    assert store.has_any("s")


def test_state_persists_across_reopen(tmp_path):
    db = tmp_path / "seen.sqlite3"
    store = SeenStore(db)
    store.mark_seen("s", ["1"])
    store.close()

    reopened = SeenStore(db)
    assert reopened.is_seen("s", "1")
