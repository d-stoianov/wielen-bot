"""Configuration loaded from environment variables and the YAML search file."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml

from .models import Search


def _get_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _get_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    return int(raw)


@dataclass(frozen=True)
class Config:
    telegram_bot_token: str
    telegram_chat_id: str

    fetcher: str  # "apify" | "playwright"

    apify_token: str
    apify_actor_id: str
    apify_use_proxy: bool

    playwright_proxy: str | None
    playwright_headless: bool

    poll_interval_seconds: int
    poll_jitter_seconds: int
    max_items_per_search: int
    notify_on_first_run: bool
    send_status_messages: bool

    db_path: str
    searches: tuple[Search, ...]

    @staticmethod
    def load(config_path: str | None = None) -> "Config":
        path = config_path or os.environ.get("CONFIG_PATH", "config.yaml")
        searches = load_searches(path)

        fetcher = os.environ.get("FETCHER", "apify").strip().lower()
        if fetcher not in {"apify", "playwright"}:
            raise ValueError(f"FETCHER must be 'apify' or 'playwright', got {fetcher!r}")

        token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
        chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
        if not token or not chat_id:
            raise ValueError("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are required")

        proxy = os.environ.get("PLAYWRIGHT_PROXY", "").strip() or None

        return Config(
            telegram_bot_token=token,
            telegram_chat_id=chat_id,
            fetcher=fetcher,
            apify_token=os.environ.get("APIFY_TOKEN", "").strip(),
            apify_actor_id=os.environ.get(
                "APIFY_ACTOR_ID", "stealth_mode/gaspedaal-cars-search-scraper"
            ).strip(),
            apify_use_proxy=_get_bool("APIFY_USE_PROXY", True),
            playwright_proxy=proxy,
            playwright_headless=_get_bool("PLAYWRIGHT_HEADLESS", True),
            poll_interval_seconds=_get_int("POLL_INTERVAL_SECONDS", 300),
            poll_jitter_seconds=_get_int("POLL_JITTER_SECONDS", 60),
            max_items_per_search=_get_int("MAX_ITEMS_PER_SEARCH", 25),
            notify_on_first_run=_get_bool("NOTIFY_ON_FIRST_RUN", False),
            send_status_messages=_get_bool("SEND_STATUS_MESSAGES", True),
            db_path=os.environ.get("DB_PATH", "data/seen.sqlite3").strip(),
            searches=searches,
        )


def load_searches(path: str | os.PathLike[str]) -> tuple[Search, ...]:
    """Parse the YAML search file into Search objects.

    Raises ValueError with an actionable message on malformed input so a typo in
    config.yaml fails loudly at startup instead of silently watching nothing.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(
            f"Search config not found at {p}. Copy config.example.yaml to {p} and edit it."
        )

    data = yaml.safe_load(p.read_text()) or {}
    raw_searches = data.get("searches")
    if not raw_searches:
        raise ValueError(f"{p} has no 'searches:' entries.")

    searches: list[Search] = []
    for i, entry in enumerate(raw_searches):
        if not isinstance(entry, dict):
            raise ValueError(f"searches[{i}] must be a mapping with 'name' and 'url'.")
        name = str(entry.get("name", "")).strip()
        url = str(entry.get("url", "")).strip()
        if not name or not url:
            raise ValueError(f"searches[{i}] needs both 'name' and 'url'.")
        searches.append(Search(name=name, url=url))
    return tuple(searches)
