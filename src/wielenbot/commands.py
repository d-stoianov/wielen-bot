"""Listens for Telegram commands so the user can manage watches and language.

Runs in its own thread, long-polling getUpdates. It handles:
  /start, /help          -> localized welcome
  /language, /lang        -> inline keyboard to pick a language
  /add                    -> step-by-step wizard to create a watch
  /list                   -> show the user's watches
  /remove <name>          -> delete a watch
  /cancel                 -> abort the /add wizard
  callback setlang:<code> -> persist language and confirm

Only the configured chat is honoured; updates from other chats are ignored so a
leaked bot username can't manage your watches or spam you.
"""

from __future__ import annotations

import html
import logging
import re
import threading
from typing import Any

from .i18n import LANGUAGE_FLAGS, LANGUAGE_NAMES, LANGUAGES, normalize_language, t
from .models import Watch
from .store import SettingsStore, WatchStore
from .telegram import TelegramNotifier
from .watches import normalize_fuel, watch_summary

logger = logging.getLogger(__name__)

_CALLBACK_PREFIX = "setlang:"
_SKIP_TOKENS = {"skip", "/skip", "-", "none"}

# Ordered wizard steps and the prompt shown when entering each.
_ADD_STEPS = ("name", "make", "model", "year_min", "year_max", "price_max", "km_max", "fuel")
_NUMERIC_STEPS = {"year_min", "year_max", "price_max", "km_max"}
_PROMPT_KEY = {step: f"ask_{step}" for step in _ADD_STEPS}


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
        {"command": "add", "description": t("cmd_add_desc", lang)},
        {"command": "list", "description": t("cmd_list_desc", lang)},
        {"command": "remove", "description": t("cmd_remove_desc", lang)},
        {"command": "language", "description": t("cmd_language_desc", lang)},
        {"command": "start", "description": t("cmd_start_desc", lang)},
    ]


def _is_skip(text: str) -> bool:
    return text.strip().lower() in _SKIP_TOKENS


def _parse_int(text: str) -> int | None:
    digits = re.sub(r"[^\d]", "", text)
    return int(digits) if digits else None


class TelegramCommandListener:
    def __init__(
        self,
        telegram: TelegramNotifier,
        settings: SettingsStore,
        watches: WatchStore,
        chat_id: str,
        *,
        stop_event: threading.Event | None = None,
        poll_timeout: int = 30,
    ) -> None:
        self._tg = telegram
        self._settings = settings
        self._watches = watches
        self._chat_id = str(chat_id)
        self._stop = stop_event or threading.Event()
        self._poll_timeout = poll_timeout
        # chat_id -> {"step": str, "data": dict}
        self._add_flows: dict[str, dict[str, Any]] = {}

    # -- small helpers --------------------------------------------------------

    def _send(self, chat_id: str, text: str, **kwargs: Any) -> None:
        self._tg.send_message(text, chat_id=chat_id, **kwargs)

    def _lang(self, chat_id: str) -> str:
        return self._settings.get_language(chat_id)

    def _prompt_step(self, chat_id: str, step: str, lang: str) -> None:
        self._add_flows[chat_id]["step"] = step
        self._send(chat_id, t(_PROMPT_KEY[step], lang))

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
        lang = self._lang(chat_id)

        # An active /add wizard captures everything except /cancel.
        if chat_id in self._add_flows:
            if text.lower() in {"/cancel", "cancel"}:
                del self._add_flows[chat_id]
                self._send(chat_id, t("add_cancelled", lang))
            else:
                self._advance_add_flow(chat_id, text, lang)
            return

        if not text.startswith("/"):
            return
        command = text[1:].split()[0].split("@")[0].lower() if len(text) > 1 else ""
        arg = text.split(maxsplit=1)[1].strip() if " " in text else ""

        if command in {"start", "help"}:
            self._send(chat_id, t("welcome", lang), disable_preview=True)
        elif command in {"language", "lang"}:
            self._send(chat_id, t("choose_language", lang), reply_markup=language_keyboard())
        elif command == "add":
            self._add_flows[chat_id] = {"step": "name", "data": {}}
            self._send(chat_id, t("ask_name", lang))
        elif command == "list":
            self._list_watches(chat_id, lang)
        elif command == "remove":
            self._remove_watch(chat_id, arg, lang)
        elif command == "cancel":
            self._send(chat_id, t("add_cancelled", lang))

    def _advance_add_flow(self, chat_id: str, text: str, lang: str) -> None:
        flow = self._add_flows[chat_id]
        step = flow["step"]
        data = flow["data"]
        value = text.strip()

        if step == "name":
            if not value or _is_skip(value):
                self._send(chat_id, t("ask_name", lang))
                return
            if self._watches.get(chat_id, value):
                self._send(chat_id, t("watch_exists", lang, name=html.escape(value)))
                return
            data["name"] = value
            self._prompt_step(chat_id, "make", lang)
            return

        if step == "make":
            if not value or _is_skip(value):
                self._send(chat_id, t("ask_make", lang))
                return
            data["make"] = value
            self._prompt_step(chat_id, "model", lang)
            return

        if step == "model":
            data["model"] = None if _is_skip(value) else value
            self._prompt_step(chat_id, "year_min", lang)
            return

        if step in _NUMERIC_STEPS:
            if _is_skip(value):
                data[step] = None
            else:
                parsed = _parse_int(value)
                if parsed is None:
                    self._send(chat_id, t("invalid_number", lang))
                    self._send(chat_id, t(_PROMPT_KEY[step], lang))
                    return
                data[step] = parsed
            self._prompt_step(chat_id, _ADD_STEPS[_ADD_STEPS.index(step) + 1], lang)
            return

        if step == "fuel":
            if _is_skip(value):
                data["fuel"] = None
            else:
                canonical = normalize_fuel(value)
                if canonical is None:
                    self._send(chat_id, t("invalid_fuel", lang))
                    self._send(chat_id, t("ask_fuel", lang))
                    return
                data["fuel"] = canonical
            self._finalize_add(chat_id, lang)

    def _finalize_add(self, chat_id: str, lang: str) -> None:
        data = self._add_flows.pop(chat_id)["data"]
        watch = Watch(
            name=data["name"],
            make=data.get("make"),
            model=data.get("model"),
            year_min=data.get("year_min"),
            year_max=data.get("year_max"),
            price_max=data.get("price_max"),
            km_max=data.get("km_max"),
            fuel=data.get("fuel"),
        )
        if not self._watches.add(chat_id, watch):
            self._send(chat_id, t("watch_exists", lang, name=html.escape(watch.name)))
            return
        self._send(
            chat_id,
            t(
                "watch_created",
                lang,
                name=html.escape(watch.name),
                summary=html.escape(watch_summary(watch)),
            ),
            disable_preview=True,
        )

    def _list_watches(self, chat_id: str, lang: str) -> None:
        watches = self._watches.list(chat_id)
        if not watches:
            self._send(chat_id, t("list_empty", lang))
            return
        lines = [t("list_header", lang)]
        for w in watches:
            lines.append(f"• <b>{html.escape(w.name)}</b> — {html.escape(watch_summary(w))}")
        self._send(chat_id, "\n".join(lines), disable_preview=True)

    def _remove_watch(self, chat_id: str, name: str, lang: str) -> None:
        if not name:
            self._send(chat_id, t("remove_usage", lang))
            return
        if self._watches.remove(chat_id, name):
            self._send(chat_id, t("watch_removed", lang, name=html.escape(name)))
        else:
            self._send(chat_id, t("watch_not_found", lang, name=html.escape(name)))

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
        self._send(chat_id, t("language_set", new_lang), disable_preview=True)

    # -- loop -----------------------------------------------------------------

    def run(self) -> None:
        """Blocking long-poll loop; intended to run in a daemon thread."""
        try:
            self._tg.set_my_commands(command_definitions(self._lang(self._chat_id)))
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
