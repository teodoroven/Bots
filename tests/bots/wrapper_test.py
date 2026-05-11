from __future__ import annotations

import unittest
from datetime import datetime

from unittest.mock import MagicMock

from bots import Bot
from bots import Message
from bots import Telebot


class FakeBot(Telebot):

    def __init__(self):
        super().__init__("12345:" + ("A" * 46), "@portfolio_bot", 100)

    def initAPI(self):
        return MagicMock()


class WrapperTest(unittest.TestCase):

    def create_transport_message(self, message_id: int, sent: bool = True) -> Bot.BaseMessage:
        message: Bot.BaseMessage = Bot.BaseMessage(100, "transport")
        message.set_chat_id(200)
        message.set_id(message_id)

        if sent:
            message.add_event(message_id, datetime.now(), message.SENT_KEY)

        return message

    def test_wrapper_message_stores_public_fields(self):
        wrapper: Message = Message(1, "hello", ["A"], max_width = 2, inline = True)

        self.assertEqual(1, wrapper.get_id())
        self.assertEqual("hello", wrapper.dumps()["text"])
        self.assertEqual(1, len(wrapper.buttons))
        self.assertFalse(wrapper.was_sent("telebot", 200))

    def test_add_messages_group_tracks_sent_state(self):
        wrapper: Message = Message(1, "hello")
        bot: FakeBot = FakeBot()
        sent_message: Bot.BaseMessage = self.create_transport_message(10)

        wrapper.add_messages(bot, 200, 100, [sent_message], compression = True, username = "@bot", date = datetime.now())

        self.assertTrue(wrapper.has_groups("telebot", 200))
        self.assertTrue(wrapper.check_sent("telebot", 200))
        self.assertEqual(200, wrapper.get_last_group("telebot", 200).get_chat_id())

    def test_delete_only_removes_editable_messages(self):
        wrapper: Message = Message(1, "hello")
        bot: FakeBot = FakeBot()
        editable: Bot.BaseMessage = self.create_transport_message(10)
        editable.delete = lambda: editable.add_event(10, datetime.now(), editable.DELETE_KEY)
        wrapper.add_messages(bot, 200, 100, [editable], compression = True, username = "@bot", date = datetime.now())

        wrapper.delete("telebot", 200)

        self.assertFalse(wrapper.has_groups("telebot", 200))

    def test_invalid_filename_is_rejected(self):
        with self.assertRaises(FileNotFoundError):
            Message(1, "hello", filenames = ["missing.txt"])


if __name__ == "__main__":
    unittest.main()
