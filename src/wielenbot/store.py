"""Persistent record of which listings we've already notified about.

Backed by SQLite so the dedup state survives container restarts. The unique key
is (search_name, ad_id): the same car can legitimately match two different
searches and we want to notify once per search.
"""

from __future__ import annotations

import sqlite3
import threading
from collections.abc import Iterable, Sequence
from pathlib import Path

from .i18n import DEFAULT_LANGUAGE, normalize_language
from .models import Listing


def _ensure_parent(path: Path) -> None:
    if path.parent and str(path.parent) not in {"", "."}:
        path.parent.mkdir(parents=True, exist_ok=True)


class SeenStore:
    def __init__(self, db_path: str | Path) -> None:
        self._path = Path(db_path)
        _ensure_parent(self._path)
        self._conn = sqlite3.connect(str(self._path))
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS seen (
                search_name TEXT NOT NULL,
                ad_id       TEXT NOT NULL,
                first_seen  TEXT NOT NULL DEFAULT (datetime('now')),
                PRIMARY KEY (search_name, ad_id)
            )
            """
        )
        self._conn.commit()

    def has_any(self, search_name: str) -> bool:
        """True if we've ever recorded a listing for this search (i.e. not a cold start)."""
        cur = self._conn.execute(
            "SELECT 1 FROM seen WHERE search_name = ? LIMIT 1", (search_name,)
        )
        return cur.fetchone() is not None

    def is_seen(self, search_name: str, ad_id: str) -> bool:
        cur = self._conn.execute(
            "SELECT 1 FROM seen WHERE search_name = ? AND ad_id = ? LIMIT 1",
            (search_name, ad_id),
        )
        return cur.fetchone() is not None

    def filter_new(self, search_name: str, listings: Iterable[Listing]) -> list[Listing]:
        """Return listings not yet recorded for this search, de-duped within the batch."""
        new: list[Listing] = []
        batch_ids: set[str] = set()
        for listing in listings:
            if listing.ad_id in batch_ids:
                continue
            if not self.is_seen(search_name, listing.ad_id):
                new.append(listing)
                batch_ids.add(listing.ad_id)
        return new

    def mark_seen(self, search_name: str, ad_ids: Sequence[str]) -> None:
        if not ad_ids:
            return
        self._conn.executemany(
            "INSERT OR IGNORE INTO seen (search_name, ad_id) VALUES (?, ?)",
            [(search_name, ad_id) for ad_id in ad_ids],
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()


class SettingsStore:
    """Per-chat preferences (currently language).

    Read by the polling loop and written by the command listener — i.e. from two
    threads — so the connection allows cross-thread use and every access is
    guarded by a lock.
    """

    def __init__(self, db_path: str | Path) -> None:
        self._path = Path(db_path)
        _ensure_parent(self._path)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(str(self._path), check_same_thread=False)
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_settings (
                chat_id  TEXT PRIMARY KEY,
                language TEXT NOT NULL
            )
            """
        )
        self._conn.commit()

    def get_language(self, chat_id: str, default: str = DEFAULT_LANGUAGE) -> str:
        with self._lock:
            cur = self._conn.execute(
                "SELECT language FROM chat_settings WHERE chat_id = ?", (str(chat_id),)
            )
            row = cur.fetchone()
        return normalize_language(row[0]) if row else normalize_language(default)

    def set_language(self, chat_id: str, language: str) -> None:
        lang = normalize_language(language)
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO chat_settings (chat_id, language) VALUES (?, ?)
                ON CONFLICT(chat_id) DO UPDATE SET language = excluded.language
                """,
                (str(chat_id), lang),
            )
            self._conn.commit()

    def close(self) -> None:
        with self._lock:
            self._conn.close()
