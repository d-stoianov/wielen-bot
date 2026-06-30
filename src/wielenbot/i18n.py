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
            "watches.\n\n"
            "<b>Commands</b>\n"
            "/add — create a new watch\n"
            "/list — show your watches\n"
            "/remove &lt;name&gt; — delete a watch\n"
            "/language — change language"
        ),
        "nl": (
            "👋 Welkom bij <b>wielen-bot</b>!\n"
            "Ik waarschuw je voor nieuwe auto-advertenties op gaspedaal.nl die bij "
            "je zoekopdrachten passen.\n\n"
            "<b>Commando's</b>\n"
            "/add — nieuwe zoekopdracht maken\n"
            "/list — je zoekopdrachten tonen\n"
            "/remove &lt;naam&gt; — zoekopdracht verwijderen\n"
            "/language — taal wijzigen"
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
    "cmd_add_desc": {
        "en": "Create a new car watch",
        "nl": "Nieuwe zoekopdracht maken",
    },
    "cmd_list_desc": {
        "en": "Show your watches",
        "nl": "Je zoekopdrachten tonen",
    },
    "cmd_remove_desc": {
        "en": "Remove a watch",
        "nl": "Zoekopdracht verwijderen",
    },
    # --- /add wizard ---
    "ask_name": {
        "en": "📝 Give this watch a name (e.g. <i>Audi A4 daily</i>):",
        "nl": "📝 Geef deze zoekopdracht een naam (bijv. <i>Audi A4 dagelijks</i>):",
    },
    "ask_make": {
        "en": "🚗 Which make? (e.g. <i>audi</i>)",
        "nl": "🚗 Welk merk? (bijv. <i>audi</i>)",
    },
    "ask_model": {
        "en": "🔧 Which model? (e.g. <i>a4</i>) — or /skip",
        "nl": "🔧 Welk model? (bijv. <i>a4</i>) — of /skip",
    },
    "ask_year_min": {
        "en": "📅 Earliest build year? (e.g. <i>2016</i>) — or /skip",
        "nl": "📅 Vroegste bouwjaar? (bijv. <i>2016</i>) — of /skip",
    },
    "ask_year_max": {
        "en": "📅 Latest build year? (e.g. <i>2020</i>) — or /skip",
        "nl": "📅 Laatste bouwjaar? (bijv. <i>2020</i>) — of /skip",
    },
    "ask_price_max": {
        "en": "💶 Maximum price in €? (e.g. <i>15000</i>) — or /skip",
        "nl": "💶 Maximale prijs in €? (bijv. <i>15000</i>) — of /skip",
    },
    "ask_km_max": {
        "en": "🛣 Maximum mileage in km? (e.g. <i>150000</i>) — or /skip",
        "nl": "🛣 Maximale kilometerstand in km? (bijv. <i>150000</i>) — of /skip",
    },
    "ask_fuel": {
        "en": "⛽ Fuel type? <i>petrol / diesel / electric / hybrid</i> — or /skip",
        "nl": "⛽ Brandstof? <i>benzine / diesel / elektrisch / hybride</i> — of /skip",
    },
    "invalid_number": {
        "en": "⚠️ Please send a number, or /skip.",
        "nl": "⚠️ Stuur een getal, of /skip.",
    },
    "invalid_fuel": {
        "en": "⚠️ Pick one of: petrol, diesel, electric, hybrid — or /skip.",
        "nl": "⚠️ Kies uit: benzine, diesel, elektrisch, hybride — of /skip.",
    },
    "watch_created": {
        "en": "✅ Watch created:\n<b>{name}</b> — {summary}\nI'll alert you on new matches.",
        "nl": "✅ Zoekopdracht aangemaakt:\n<b>{name}</b> — {summary}\nIk waarschuw je bij nieuwe treffers.",
    },
    "watch_exists": {
        "en": "⚠️ You already have a watch named <b>{name}</b>. Pick another name:",
        "nl": "⚠️ Je hebt al een zoekopdracht met de naam <b>{name}</b>. Kies een andere naam:",
    },
    "add_cancelled": {
        "en": "❌ Cancelled.",
        "nl": "❌ Geannuleerd.",
    },
    "list_empty": {
        "en": "You have no watches yet. Use /add to create one.",
        "nl": "Je hebt nog geen zoekopdrachten. Gebruik /add om er een te maken.",
    },
    "list_header": {
        "en": "🔎 <b>Your watches</b>:",
        "nl": "🔎 <b>Je zoekopdrachten</b>:",
    },
    "remove_usage": {
        "en": "Usage: <code>/remove &lt;name&gt;</code>. See /list for names.",
        "nl": "Gebruik: <code>/remove &lt;naam&gt;</code>. Zie /list voor namen.",
    },
    "watch_removed": {
        "en": "🗑 Removed watch <b>{name}</b>.",
        "nl": "🗑 Zoekopdracht <b>{name}</b> verwijderd.",
    },
    "watch_not_found": {
        "en": "⚠️ No watch named <b>{name}</b>. See /list.",
        "nl": "⚠️ Geen zoekopdracht met de naam <b>{name}</b>. Zie /list.",
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
