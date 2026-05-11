from __future__ import annotations

import unittest
from threading import Event
from threading import Lock
from unittest.mock import MagicMock

from bots import Message
from bots import Telebot
from relay.app import App
from relay.handlers import Context
from relay.notifications import AdminEvent
from relay.notifications import BotkeyMessage
from relay.notifications import Notification
from relay.users import Admin
from relay.users import User


class FakeBot(Telebot):

    def initAPI(self):
        return MagicMock()


class FakeApp(App):

    def __init__(self):
        self.event_lock: Lock = Lock()

    def get_admin_list(self, permissions = [], notifications = []) -> list[Admin]:
        return [Admin(1, {"telebot": {100}}, 1), Admin(2, {"telebot": {200}}, 1)]

    def create_message_id(self) -> int:
        return 99


class FakeAdminEvent(AdminEvent):

    def run(self) -> list[Notification]:
        return []


class NotificationsTest(unittest.TestCase):
    TOKEN: str = "12345:" + ("A" * 46)

    def test_botkey_message_returns_specific_or_default_message(self):
        default: Message = Message(1, "default", ["A"])
        specific: Message = Message(2, "telegram")
        botkey: BotkeyMessage = BotkeyMessage(default)
        botkey.set("telebot", specific)

        self.assertIs(specific, botkey.get("telebot"))
        self.assertIs(default, botkey.get("vkbot"))
        self.assertEqual([], botkey.copy(no_buttons = True).get("vkbot").buttons)

    def test_notification_send_uses_catch_send_stub(self):
        user: User = User(1, {"telebot": {123}}, 0)
        botkey: BotkeyMessage = BotkeyMessage(Message(1, "notify"))
        sent: list[tuple[str, int]] = []
        sent_event: Event = Event()

        def get_bot(bot_key: str) -> FakeBot:
            return FakeBot(self.TOKEN, "@portfolio_bot", 12345)

        def catch_send(message: Message, bot: FakeBot, chat_id: int, compression: bool):
            sent.append((bot.get_bot_key(), chat_id))
            sent_event.set()

        notification: Notification = Notification(user, botkey)
        notification.send(get_bot, catch_send = catch_send)

        self.assertTrue(sent_event.wait(1))
        self.assertEqual([("telebot", 123)], sent)

    def test_admin_event_get_next_admin_is_stable(self):
        context: Context = Context(FakeApp(), FakeBot(self.TOKEN, "@portfolio_bot", 12345), User(9, {"telebot": {9}}, 0), None, None)
        event: FakeAdminEvent = FakeAdminEvent(1, context, {})

        self.assertEqual(1, event.get_next_admin().id)
        self.assertEqual(2, event.get_next_admin().id)
        self.assertIsNone(event.get_next_admin())


if __name__ == "__main__":
    unittest.main()
