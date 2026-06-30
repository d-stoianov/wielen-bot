"""Telegram delivery: format listings and push them via the Bot API."""

from __future__ import annotations

import html
import logging

import httpx

from .models import Listing

logger = logging.getLogger(__name__)

_API_BASE = "https://api.telegram.org"


def format_listing(listing: Listing, search_name: str) -> str:
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

    lines.append(f'🔎 <i>{html.escape(search_name)}</i>')
    if listing.url:
        lines.append(f'<a href="{html.escape(listing.url, quote=True)}">Bekijk advertentie</a>')
    return "\n".join(lines)


class TelegramNotifier:
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

    def send_text(self, text: str, *, disable_preview: bool = False) -> None:
        resp = self._client.post(
            self._url("sendMessage"),
            json={
                "chat_id": self._chat_id,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": disable_preview,
            },
        )
        resp.raise_for_status()

    def send_listing(self, listing: Listing, search_name: str) -> None:
        self.send_text(format_listing(listing, search_name))

    def close(self) -> None:
        self._client.close()
