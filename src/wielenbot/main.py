"""Entry point: build everything from config and poll on an interval."""

from __future__ import annotations

import logging
import os
import random
import signal
import sys
import threading
import time

from .commands import TelegramCommandListener
from .config import Config
from .fetchers import build_fetcher
from .i18n import t
from .notifier import Notifier, SearchResult
from .store import SeenStore, SettingsStore
from .telegram import TelegramNotifier

logger = logging.getLogger("wielenbot")


def _summarize(results: list[SearchResult]) -> str:
    lines: list[str] = []
    for r in results:
        if r.error:
            lines.append(f"⚠️ {r.search.name}: {r.error}")
        elif r.seeded:
            lines.append(f"🌱 {r.search.name}: seeded {r.fetched} existing")
        elif r.new:
            lines.append(f"✅ {r.search.name}: {r.new} new")
        else:
            lines.append(f"· {r.search.name}: 0 new ({r.fetched} checked)")
    return "\n".join(lines)


def run() -> int:
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    config = Config.load()
    store = SeenStore(config.db_path)
    settings = SettingsStore(config.db_path)
    telegram = TelegramNotifier(config.telegram_bot_token, config.telegram_chat_id)
    fetcher = build_fetcher(config)

    def current_language() -> str:
        return settings.get_language(config.telegram_chat_id)

    notifier = Notifier(
        fetcher,
        store,
        telegram,
        max_items=config.max_items_per_search,
        notify_on_first_run=config.notify_on_first_run,
        language_provider=current_language,
    )

    stop = threading.Event()

    def _handle_signal(signum: int, _frame: object) -> None:
        logger.info("Received signal %s, shutting down after current cycle", signum)
        stop.set()

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    # Listen for /language and other commands in the background.
    listener = TelegramCommandListener(telegram, settings, config.telegram_chat_id, stop_event=stop)
    listener_thread = threading.Thread(target=listener.run, name="tg-listener", daemon=True)
    listener_thread.start()

    logger.info(
        "wielen-bot started: %d searches, fetcher=%s, every %ds (+/-%ds)",
        len(config.searches),
        config.fetcher,
        config.poll_interval_seconds,
        config.poll_jitter_seconds,
    )
    if config.send_status_messages:
        try:
            telegram.send_text(
                t(
                    "started",
                    current_language(),
                    count=len(config.searches),
                    fetcher=config.fetcher,
                ),
                disable_preview=True,
            )
        except Exception:  # noqa: BLE001
            logger.exception("Could not send startup message")

    while not stop.is_set():
        results = notifier.run_once(config.searches)
        summary = _summarize(results)
        logger.info("Cycle done:\n%s", summary)
        if config.send_status_messages and any(r.error for r in results):
            try:
                telegram.send_text(summary, disable_preview=True)
            except Exception:  # noqa: BLE001
                logger.exception("Could not send error summary")

        jitter = random.uniform(0, config.poll_jitter_seconds)
        wait = config.poll_interval_seconds + jitter
        logger.info("Sleeping %.0fs", wait)
        stop.wait(wait)

    telegram.close()
    store.close()
    settings.close()
    logger.info("wielen-bot stopped")
    return 0


if __name__ == "__main__":
    sys.exit(run())
