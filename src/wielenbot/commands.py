"""Listens for Telegram commands so the user can change language at runtime.

Runs in its own thread, long-polling getUpdates. It handles:
  /start, /help   -> localized welcome
  /language, /lang -> inline keyboard to pick a language
  callback setlang:<code> -> persist the choice and confirm

Only the configured chat is honoured; updates from other chats are ignored so a
leaked bot username can't flip your language or spam you.
"""

from __future__ import annotations

import logging
import threading
from typing import Any

from .i18n import LANGUAGE_FLAGS, LANGUAGE_NAMES, LANGUAGES, normalize_language, t
from .store import SettingsStore
from .telegram import TelegramNotifier

logger = logging.getLogger(__name__)

_CALLBACK_PREFIX = "setlang:"


def language_keyboard() -> dict[str, Any]:
    return {
        "inline_keyboard": [
            [
                {
                    "text": f"{LANGUAGE_FLAGS[code]} {LANGUAGE_NAMES[code]}",
                    "callback_data": f"{_CALLBACK_PREFIX}{code}",
                }
                for code in LANGUAGES
            ]
        ]
    }


def command_definitions(lang: str) -> list[dict[str, str]]:
    return [
        {"command": "start", "description": t("cmd_start_desc", lang)},
        {"command": "language", "description": t("cmd_language_desc", lang)},
    ]


class TelegramCommandListener:
    def __init__(
        self,
        telegram: TelegramNotifier,
        settings: SettingsStore,
        chat_id: str,
        *,
        stop_event: threading.Event | None = None,
        poll_timeout: int = 30,
    ) -> None:
        self._tg = telegram
        self._settings = settings
        self._chat_id = str(chat_id)
        self._stop = stop_event or threading.Event()
        self._poll_timeout = poll_timeout

    # -- handling (pure-ish, unit-tested) -------------------------------------

    def handle_update(self, update: dict[str, Any]) -> None:
        message = update.get("message")
        if message:
            self._handle_message(message)
            return
        callback = update.get("callback_query")
        if callback:
            self._handle_callback(callback)

    def _handle_message(self, message: dict[str, Any]) -> None:
        chat_id = str((message.get("chat") or {}).get("id", ""))
        if chat_id != self._chat_id:
            return
        text = (message.get("text") or "").strip()
        command = text.split()[0].lstrip("/").split("@")[0].lower() if text else ""
        lang = self._settings.get_language(chat_id)

        if command in {"start", "help"}:
            self._tg.send_message(t("welcome", lang), chat_id=chat_id, disable_preview=True)
        elif command in {"language", "lang"}:
            self._tg.send_message(
                t("choose_language", lang),
                chat_id=chat_id,
                reply_markup=language_keyboard(),
            )

    def _handle_callback(self, callback: dict[str, Any]) -> None:
        data = callback.get("data") or ""
        callback_id = callback.get("id", "")
        chat_id = str(((callback.get("message") or {}).get("chat") or {}).get("id", ""))
        if chat_id != self._chat_id or not data.startswith(_CALLBACK_PREFIX):
            if callback_id:
                self._tg.answer_callback_query(callback_id)
            return

        new_lang = normalize_language(data[len(_CALLBACK_PREFIX) :])
        self._settings.set_language(chat_id, new_lang)
        if callback_id:
            self._tg.answer_callback_query(callback_id)
        self._tg.send_message(t("language_set", new_lang), chat_id=chat_id, disable_preview=True)

    # -- loop -----------------------------------------------------------------

    def run(self) -> None:
        """Blocking long-poll loop; intended to run in a daemon thread."""
        try:
            lang = self._settings.get_language(self._chat_id)
            self._tg.set_my_commands(command_definitions(lang))
        except Exception:  # noqa: BLE001 - non-fatal, keep listening
            logger.exception("Could not register bot commands")

        offset: int | None = None
        while not self._stop.is_set():
            try:
                updates = self._tg.get_updates(offset, timeout=self._poll_timeout)
            except Exception:  # noqa: BLE001 - transient network/API error
                logger.exception("getUpdates failed; retrying")
                self._stop.wait(5)
                continue
            for update in updates:
                offset = update["update_id"] + 1
                try:
                    self.handle_update(update)
                except Exception:  # noqa: BLE001 - one bad update shouldn't kill the loop
                    logger.exception("Failed to handle update %s", update.get("update_id"))
