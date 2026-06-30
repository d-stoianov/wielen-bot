from __future__ import annotations

from wielenbot.i18n import normalize_language, t


def test_default_is_english():
    assert t("view_listing") == "View listing"


def test_dutch_translation():
    assert t("view_listing", "nl") == "Bekijk advertentie"


def test_unknown_language_falls_back_to_english():
    assert t("view_listing", "fr") == "View listing"


def test_unknown_key_echoes_back():
    assert t("nonexistent_key", "nl") == "nonexistent_key"


def test_formatting_kwargs():
    msg = t("started", "en", count=3, fetcher="apify")
    assert "3" in msg and "apify" in msg


def test_normalize_language():
    assert normalize_language("NL") == "nl"
    assert normalize_language("en") == "en"
    assert normalize_language(None) == "en"
    assert normalize_language("zz") == "en"
