from __future__ import annotations

import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock
from unittest.mock import patch

from bots import Bot
from bots import Telebot


class FakeTelebot(Telebot):

    def initAPI(self):
        return MagicMock()


class TelegramTransportTest(unittest.TestCase):
    TOKEN: str = "12345:" + ("A" * 46)

    def build_bot(self) -> FakeTelebot:
        return FakeTelebot(self.TOKEN, "@portfolio_bot", 12345)

    def test_button_and_keyboard_build_inline_payloads(self):
        button: Telebot.Keyboard.Button = Telebot.Keyboard.Button("Start", callback_data = "start")
        keyboard: Telebot.Keyboard = Telebot.Keyboard([button, "Help"], max_width = 2, inline = True)

        self.assertEqual("start", button.get_kwarg()["callback_data"])
        self.assertEqual(2, len(keyboard.buttons))
        self.assertEqual([], keyboard.get_unused_buttons())

    def test_split_places_keyboard_on_last_text_message(self):
        bot: FakeTelebot = self.build_bot()

        with patch.object(Telebot.Message, "set_telebot", lambda message, telebot: setattr(message, "telebot", telebot)):
            messages: list[Telebot.Message] = bot.split("hello", ["A", "B"], [], reply = None, forward = [], max_width = 2, inline = True)

        self.assertEqual(1, len(messages))
        self.assertEqual("hello", messages[0].get_text())
        self.assertIsNotNone(messages[0].get_keyboard())

    def test_parse_message_and_callback_without_network(self):
        bot: FakeTelebot = self.build_bot()
        user: SimpleNamespace = SimpleNamespace(id = 777, first_name = "Ivan", last_name = "Test", username = "ivan")
        chat: SimpleNamespace = SimpleNamespace(id = 777)
        message: SimpleNamespace = SimpleNamespace(from_user = user, chat = chat, text = "hello", date = 1, message_id = 55)
        callback_message: SimpleNamespace = SimpleNamespace(chat = chat, message_id = 56)
        callback: SimpleNamespace = SimpleNamespace(from_user = user, message = callback_message, data = "session;1;ok")

        with patch.object(Telebot, "check_event", return_value = True):
            event: Bot.Event = bot.parse_message(message, datetime.now())
            callback_event: Bot.Event = bot.parse_callback(callback, datetime.now())

        self.assertEqual(777, event.get_chat_id())
        self.assertEqual("hello", event.get_text())
        self.assertEqual("session;1;ok", callback_event.get_text())


if __name__ == "__main__":
    unittest.main()
