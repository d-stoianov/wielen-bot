from __future__ import annotations

from wielenbot.store import SettingsStore


def test_default_language_is_english(tmp_path):
    settings = SettingsStore(tmp_path / "seen.sqlite3")
    assert settings.get_language("123") == "en"


def test_set_and_get_language(tmp_path):
    settings = SettingsStore(tmp_path / "seen.sqlite3")
    settings.set_language("123", "nl")
    assert settings.get_language("123") == "nl"


def test_set_language_upserts(tmp_path):
    settings = SettingsStore(tmp_path / "seen.sqlite3")
    settings.set_language("123", "nl")
    settings.set_language("123", "en")
    assert settings.get_language("123") == "en"


def test_language_scoped_per_chat(tmp_path):
    settings = SettingsStore(tmp_path / "seen.sqlite3")
    settings.set_language("123", "nl")
    assert settings.get_language("999") == "en"


def test_invalid_language_normalized_on_write(tmp_path):
    settings = SettingsStore(tmp_path / "seen.sqlite3")
    settings.set_language("123", "klingon")
    assert settings.get_language("123") == "en"


def test_persists_across_reopen(tmp_path):
    db = tmp_path / "seen.sqlite3"
    settings = SettingsStore(db)
    settings.set_language("123", "nl")
    settings.close()

    reopened = SettingsStore(db)
    assert reopened.get_language("123") == "nl"
