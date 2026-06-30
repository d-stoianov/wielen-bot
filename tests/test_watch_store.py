from __future__ import annotations

from wielenbot.models import Watch
from wielenbot.store import WatchStore

CHAT = "100"


def test_add_and_list(tmp_path):
    store = WatchStore(tmp_path / "seen.sqlite3")
    assert store.add(CHAT, Watch(name="A4", make="audi", model="a4", year_min=2016))
    watches = store.list(CHAT)
    assert len(watches) == 1
    assert watches[0].name == "A4"
    assert watches[0].make == "audi"
    assert watches[0].year_min == 2016


def test_duplicate_name_rejected(tmp_path):
    store = WatchStore(tmp_path / "seen.sqlite3")
    assert store.add(CHAT, Watch(name="A4", make="audi"))
    assert not store.add(CHAT, Watch(name="A4", make="bmw"))
    assert store.count(CHAT) == 1


def test_get_and_remove(tmp_path):
    store = WatchStore(tmp_path / "seen.sqlite3")
    store.add(CHAT, Watch(name="A4", make="audi"))
    assert store.get(CHAT, "A4") is not None
    assert store.remove(CHAT, "A4") is True
    assert store.get(CHAT, "A4") is None
    assert store.remove(CHAT, "A4") is False  # already gone


def test_scoped_per_chat(tmp_path):
    store = WatchStore(tmp_path / "seen.sqlite3")
    store.add(CHAT, Watch(name="A4", make="audi"))
    assert store.list("999") == []
    assert store.count(CHAT) == 1


def test_persists_across_reopen(tmp_path):
    db = tmp_path / "seen.sqlite3"
    store = WatchStore(db)
    store.add(CHAT, Watch(name="A4", make="audi", fuel="diesel"))
    store.close()

    reopened = WatchStore(db)
    got = reopened.get(CHAT, "A4")
    assert got is not None and got.fuel == "diesel"
