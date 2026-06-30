"""Telegram delivery: format listings and talk to the Bot API."""

from __future__ import annotations

import html
import logging
from typing import Any

import httpx

from .i18n import DEFAULT_LANGUAGE, t
from .models import Listing

logger = logging.getLogger(__name__)

_API_BASE = "https://api.telegram.org"


def format_listing(listing: Listing, search_name: str, lang: str = DEFAULT_LANGUAGE) -> str:
    """Build an HTML-formatted Telegram message for a single listing."""
    title = html.escape(listing.title or "Car listing")
    lines = [f"🚗 <b>{title}</b>"]

    facts: list[str] = []
    if listing.price is not None:
        facts.append(f"€{listing.price:,}".replace(",", "."))
    if listing.year is not None:
        facts.append(str(listing.year))
    if listing.mileage_km is not None:
        facts.append(f"{listing.mileage_km:,} km".replace(",", "."))
    if listing.fuel:
        facts.append(html.escape(listing.fuel))
    if facts:
        lines.append(" · ".join(facts))

    meta: list[str] = []
    if listing.location:
        meta.append(html.escape(listing.location))
    if listing.source:
        meta.append(html.escape(listing.source))
    if meta:
        lines.append("📍 " + " · ".join(meta))

    lines.append(f"🔎 <i>{html.escape(search_name)}</i>")
    if listing.url:
        label = html.escape(t("view_listing", lang))
        lines.append(f'<a href="{html.escape(listing.url, quote=True)}">{label}</a>')
    return "\n".join(lines)


class TelegramNotifier:
    """Thin Bot API client: sends messages and reads updates (long-poll)."""

    def __init__(
        self,
        bot_token: str,
        chat_id: str,
        *,
        client: httpx.Client | None = None,
        api_base: str = _API_BASE,
    ) -> None:
        self._token = bot_token
        self._chat_id = chat_id
        self._client = client or httpx.Client(timeout=30.0)
        self._api_base = api_base

    def _url(self, method: str) -> str:
        return f"{self._api_base}/bot{self._token}/{method}"

    def send_message(
        self,
        text: str,
        *,
        chat_id: str | None = None,
        reply_markup: dict[str, Any] | None = None,
        disable_preview: bool = False,
    ) -> None:
        payload: dict[str, Any] = {
            "chat_id": chat_id or self._chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": disable_preview,
        }
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        resp = self._client.post(self._url("sendMessage"), json=payload)
        resp.raise_for_status()

    def send_text(self, text: str, *, disable_preview: bool = False) -> None:
        self.send_message(text, disable_preview=disable_preview)

    def send_listing(self, listing: Listing, search_name: str, lang: str = DEFAULT_LANGUAGE) -> None:
        self.send_message(format_listing(listing, search_name, lang))

    def answer_callback_query(self, callback_query_id: str, text: str | None = None) -> None:
        payload: dict[str, Any] = {"callback_query_id": callback_query_id}
        if text is not None:
            payload["text"] = text
        resp = self._client.post(self._url("answerCallbackQuery"), json=payload)
        resp.raise_for_status()

    def set_my_commands(self, commands: list[dict[str, str]]) -> None:
        resp = self._client.post(self._url("setMyCommands"), json={"commands": commands})
        resp.raise_for_status()

    def get_updates(self, offset: int | None = None, timeout: int = 30) -> list[dict[str, Any]]:
        payload: dict[str, Any] = {"timeout": timeout}
        if offset is not None:
            payload["offset"] = offset
        # Read timeout must outlast the long-poll timeout.
        resp = self._client.post(
            self._url("getUpdates"), json=payload, timeout=timeout + 15
        )
        resp.raise_for_status()
        return resp.json().get("result", [])

    def close(self) -> None:
        self._client.close()
