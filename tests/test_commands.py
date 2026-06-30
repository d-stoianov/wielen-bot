from __future__ import annotations

from wielenbot.commands import TelegramCommandListener, language_keyboard
from wielenbot.store import SettingsStore, WatchStore

CHAT = "100"
OTHER = "999"


class FakeTelegram:
    def __init__(self) -> None:
        self.messages: list[dict] = []
        self.answered: list[str] = []

    def send_message(self, text, *, chat_id=None, reply_markup=None, disable_preview=False):
        self.messages.append({"text": text, "chat_id": chat_id, "reply_markup": reply_markup})

    def answer_callback_query(self, callback_query_id, text=None):
        self.answered.append(callback_query_id)

    def last(self) -> str:
        return self.messages[-1]["text"]


def _listener(tmp_path):
    settings = SettingsStore(tmp_path / "seen.sqlite3")
    watches = WatchStore(tmp_path / "seen.sqlite3")
    tg = FakeTelegram()
    listener = TelegramCommandListener(tg, settings, watches, CHAT)
    return listener, tg, settings, watches


def _message(text, chat_id=CHAT):
    return {"update_id": 1, "message": {"chat": {"id": chat_id}, "text": text}}


def _callback(data, chat_id=CHAT, cb_id="cb1"):
    return {
        "update_id": 1,
        "callback_query": {"id": cb_id, "data": data, "message": {"chat": {"id": chat_id}}},
    }


def _feed(listener, *texts, chat_id=CHAT):
    for text in texts:
        listener.handle_update(_message(text, chat_id=chat_id))


# --- language / basic ---

def test_start_sends_welcome(tmp_path):
    listener, tg, *_ = _listener(tmp_path)
    listener.handle_update(_message("/start"))
    assert "Welcome" in tg.last()


def test_language_command_shows_keyboard(tmp_path):
    listener, tg, *_ = _listener(tmp_path)
    listener.handle_update(_message("/language"))
    assert tg.messages[-1]["reply_markup"] == language_keyboard()


def test_callback_sets_dutch(tmp_path):
    listener, tg, settings, _ = _listener(tmp_path)
    listener.handle_update(_callback("setlang:nl"))
    assert settings.get_language(CHAT) == "nl"
    assert "Nederlands" in tg.last()


def test_ignores_other_chats(tmp_path):
    listener, tg, _, watches = _listener(tmp_path)
    listener.handle_update(_message("/start", chat_id=OTHER))
    listener.handle_update(_message("/add", chat_id=OTHER))
    assert tg.messages == []


# --- /add wizard ---

def test_add_full_flow_creates_watch(tmp_path):
    listener, tg, _, watches = _listener(tmp_path)
    _feed(
        listener,
        "/add",
        "Audi A4 daily",   # name
        "audi",            # make
        "a4",              # model
        "2016",            # year_min
        "2020",            # year_max
        "15000",           # price_max
        "150000",          # km_max
        "diesel",          # fuel
    )
    w = watches.get(CHAT, "Audi A4 daily")
    assert w is not None
    assert w.make == "audi" and w.model == "a4"
    assert w.year_min == 2016 and w.year_max == 2020
    assert w.price_max == 15000 and w.km_max == 150000
    assert w.fuel == "diesel"
    assert "created" in tg.last().lower() or "✅" in tg.last()


def test_add_flow_with_skips(tmp_path):
    listener, _tg, _, watches = _listener(tmp_path)
    _feed(
        listener,
        "/add",
        "Cheap Golf",
        "volkswagen",
        "/skip",   # model
        "/skip",   # year_min
        "/skip",   # year_max
        "8000",    # price_max
        "/skip",   # km_max
        "/skip",   # fuel
    )
    w = watches.get(CHAT, "Cheap Golf")
    assert w is not None
    assert w.model is None
    assert w.price_max == 8000
    assert w.fuel is None


def test_add_rejects_invalid_number_then_recovers(tmp_path):
    listener, tg, _, watches = _listener(tmp_path)
    _feed(
        listener,
        "/add", "W", "audi", "/skip",
        "not-a-year",   # invalid year_min
    )
    assert any("⚠️" in m["text"] for m in tg.messages)
    # still on year_min; supply a valid value and finish
    _feed(listener, "2018", "/skip", "/skip", "/skip", "/skip")
    w = watches.get(CHAT, "W")
    assert w is not None and w.year_min == 2018


def test_add_duplicate_name_blocked_at_name_step(tmp_path):
    listener, tg, _, watches = _listener(tmp_path)
    watches.add(CHAT, __import__("wielenbot.models", fromlist=["Watch"]).Watch(name="Dup"))
    _feed(listener, "/add", "Dup")
    assert "already" in tg.last().lower() or "al" in tg.last().lower()
    # name not accepted, so still in flow at name step
    _feed(listener, "Fresh", "audi", "/skip", "/skip", "/skip", "/skip", "/skip", "/skip")
    assert watches.get(CHAT, "Fresh") is not None


def test_cancel_aborts_flow(tmp_path):
    listener, tg, _, watches = _listener(tmp_path)
    _feed(listener, "/add", "Temp", "/cancel")
    assert watches.get(CHAT, "Temp") is None
    # after cancel, plain text is ignored again
    _feed(listener, "audi")
    assert watches.count(CHAT) == 0


# --- /list and /remove ---

def test_list_empty_then_populated(tmp_path):
    listener, tg, _, watches = _listener(tmp_path)
    listener.handle_update(_message("/list"))
    assert "no watches" in tg.last().lower()

    _feed(listener, "/add", "A4", "audi", "a4", "/skip", "/skip", "/skip", "/skip", "/skip")
    listener.handle_update(_message("/list"))
    assert "A4" in tg.last()


def test_remove_existing_and_missing(tmp_path):
    listener, tg, _, watches = _listener(tmp_path)
    _feed(listener, "/add", "A4", "audi", "a4", "/skip", "/skip", "/skip", "/skip", "/skip")

    listener.handle_update(_message("/remove A4"))
    assert watches.get(CHAT, "A4") is None
    assert "A4" in tg.last()

    listener.handle_update(_message("/remove Ghost"))
    assert "Ghost" in tg.last()


def test_remove_without_name_shows_usage(tmp_path):
    listener, tg, *_ = _listener(tmp_path)
    listener.handle_update(_message("/remove"))
    assert "/remove" in tg.last()
