from __future__ import annotations

from wielenbot.commands import TelegramCommandListener, language_keyboard
from wielenbot.store import SettingsStore

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


def _listener(tmp_path):
    settings = SettingsStore(tmp_path / "seen.sqlite3")
    tg = FakeTelegram()
    listener = TelegramCommandListener(tg, settings, CHAT)
    return listener, tg, settings


def _message(text, chat_id=CHAT):
    return {"update_id": 1, "message": {"chat": {"id": chat_id}, "text": text}}


def _callback(data, chat_id=CHAT, cb_id="cb1"):
    return {
        "update_id": 1,
        "callback_query": {"id": cb_id, "data": data, "message": {"chat": {"id": chat_id}}},
    }


def test_start_sends_welcome(tmp_path):
    listener, tg, _ = _listener(tmp_path)
    listener.handle_update(_message("/start"))
    assert len(tg.messages) == 1
    assert "Welcome" in tg.messages[0]["text"]


def test_language_command_shows_keyboard(tmp_path):
    listener, tg, _ = _listener(tmp_path)
    listener.handle_update(_message("/language"))
    assert tg.messages[0]["reply_markup"] == language_keyboard()


def test_callback_sets_dutch_and_confirms(tmp_path):
    listener, tg, settings = _listener(tmp_path)
    listener.handle_update(_callback("setlang:nl"))

    assert settings.get_language(CHAT) == "nl"
    assert tg.answered == ["cb1"]
    assert "Nederlands" in tg.messages[0]["text"]


def test_callback_back_to_english(tmp_path):
    listener, tg, settings = _listener(tmp_path)
    settings.set_language(CHAT, "nl")
    listener.handle_update(_callback("setlang:en"))
    assert settings.get_language(CHAT) == "en"
    assert "English" in tg.messages[0]["text"]


def test_ignores_other_chats(tmp_path):
    listener, tg, settings = _listener(tmp_path)
    listener.handle_update(_message("/start", chat_id=OTHER))
    listener.handle_update(_callback("setlang:nl", chat_id=OTHER))

    assert tg.messages == []
    assert settings.get_language(CHAT) == "en"  # unchanged


def test_command_with_botname_suffix(tmp_path):
    listener, tg, _ = _listener(tmp_path)
    listener.handle_update(_message("/language@wielen_bot"))
    assert tg.messages[0]["reply_markup"] == language_keyboard()


def test_unrelated_text_does_nothing(tmp_path):
    listener, tg, _ = _listener(tmp_path)
    listener.handle_update(_message("hello there"))
    assert tg.messages == []
