from __future__ import annotations

import unittest
from datetime import datetime
from unittest.mock import MagicMock
from unittest.mock import patch

from bots import Bot
from bots import Vkbot


class FakeVkbot(Vkbot):

    def initAPI(self):
        self.bot: MagicMock = MagicMock()
        self.upload: MagicMock = MagicMock()

    def extract_name(self, event: Bot.Event, chat_id: int) -> tuple[str, str]:
        event.set_name("Ivan", "VK")
        return "Ivan", "VK"


class VkTransportTest(unittest.TestCase):

    def build_bot(self) -> FakeVkbot:
        return FakeVkbot("vk" + ("x" * 220), "@portfolio_vk", 123)

    def test_inline_keyboard_serializes_callback_payloads(self):
        keyboard: Vkbot.Keyboard = Vkbot.Keyboard(["One", "Two"], max_width = 2, inline = True)
        payload: str = keyboard.get_keyboard()

        self.assertEqual(2, len(keyboard.buttons))
        self.assertIn("One", payload)
        self.assertEqual([], keyboard.get_unused_buttons())

    def test_split_creates_message_with_keyboard(self):
        bot: FakeVkbot = self.build_bot()

        with patch.object(Vkbot.Message, "set_vkbot", lambda message, vkbot: setattr(message, "vkbot", vkbot)):
            messages: list[Vkbot.Message] = bot.split("hello", ["A"], [], reply = None, forward = [], max_width = 2, inline = True)

        self.assertEqual(1, len(messages))
        self.assertEqual("hello", messages[0].get_text())
        self.assertIsNotNone(messages[0].get_keyboard())

    def test_parse_message_and_payload_without_longpoll(self):
        bot: FakeVkbot = self.build_bot()
        message: dict[str, object] = {
            "from_id": 10,
            "peer_id": 10,
            "text": "hello",
            "date": 1,
            "attachments": [],
            "fwd_messages": [],
        }

        event: Bot.Event = bot.parse_message(message, datetime.now())

        self.assertEqual(10, event.get_chat_id())
        self.assertEqual("hello", event.get_text())
        self.assertEqual(("Ivan", "VK"), event.get_name())


if __name__ == "__main__":
    unittest.main()
