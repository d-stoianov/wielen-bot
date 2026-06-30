"""Tiny i18n layer. English is the default; Dutch is the second language."""

from __future__ import annotations

DEFAULT_LANGUAGE = "en"
LANGUAGES: tuple[str, ...] = ("en", "nl")
LANGUAGE_NAMES = {"en": "English", "nl": "Nederlands"}
LANGUAGE_FLAGS = {"en": "🇬🇧", "nl": "🇳🇱"}

_TRANSLATIONS: dict[str, dict[str, str]] = {
    "view_listing": {
        "en": "View listing",
        "nl": "Bekijk advertentie",
    },
    "welcome": {
        "en": (
            "👋 Welcome to <b>wielen-bot</b>!\n"
            "I notify you about new car listings on gaspedaal.nl that match your "
            "searches.\n\nUse /language to change the language."
        ),
        "nl": (
            "👋 Welkom bij <b>wielen-bot</b>!\n"
            "Ik waarschuw je voor nieuwe auto-advertenties op gaspedaal.nl die bij "
            "je zoekopdrachten passen.\n\nGebruik /language om de taal te wijzigen."
        ),
    },
    "connected": {
        "en": (
            "🤖 <b>wielen-bot</b> is connected! ✅\n"
            "You'll get new car listings here as soon as they appear."
        ),
        "nl": (
            "🤖 <b>wielen-bot</b> is verbonden! ✅\n"
            "Je ontvangt hier nieuwe auto-advertenties zodra ze verschijnen."
        ),
    },
    "started": {
        "en": "🤖 wielen-bot started — watching {count} search(es) via {fetcher}.",
        "nl": "🤖 wielen-bot gestart — {count} zoekopdracht(en) actief via {fetcher}.",
    },
    "choose_language": {
        "en": "🌐 Choose your language:",
        "nl": "🌐 Kies je taal:",
    },
    "language_set": {
        "en": "✅ Language set to English.",
        "nl": "✅ Taal ingesteld op Nederlands.",
    },
    "cmd_start_desc": {
        "en": "Show the welcome message",
        "nl": "Toon het welkomstbericht",
    },
    "cmd_language_desc": {
        "en": "Change language",
        "nl": "Taal wijzigen",
    },
}


def normalize_language(lang: str | None) -> str:
    """Return a supported language code, falling back to the default."""
    if lang:
        code = lang.strip().lower()
        if code in LANGUAGES:
            return code
    return DEFAULT_LANGUAGE


def t(key: str, lang: str = DEFAULT_LANGUAGE, **kwargs: object) -> str:
    """Translate `key` into `lang`, formatting with kwargs. Unknown keys echo back."""
    lang = normalize_language(lang)
    entry = _TRANSLATIONS.get(key)
    if entry is None:
        return key
    text = entry.get(lang) or entry.get(DEFAULT_LANGUAGE) or key
    return text.format(**kwargs) if kwargs else text
