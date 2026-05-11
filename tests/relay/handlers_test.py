from __future__ import annotations

import unittest
from datetime import datetime
from unittest.mock import MagicMock

from bots import Bot
from bots import Telebot
from relay.app import App
from relay.callback_data import Callback
from relay.handlers import Command
from relay.handlers import Context
from relay.handlers import NoHandlers
from relay.sessions import Session
from relay.users import User


class FakeApp(App):

    def __init__(self):
        pass


class FakeBot(Telebot):

    def initAPI(self):
        return MagicMock()

    def check_callback(self, event: Bot.Event) -> bool:
        return event.DEBUG_CALLBACK


class FakeUser(User):

    def __init__(self):
        super().__init__(1, {"telebot": {123}}, 0)
        self.processed: bool = False

    def process(self, context: Context):
        self.processed = True

    def create_message_id(self) -> int:
        return 1

    def go_session(self, session_class: type, context: Context, data: dict | None = None, message = None):
        return FakeSession(self)


class FakeSession(Session):

    def __init__(self, user: FakeUser):
        self.user: FakeUser = user

    def process(self, context: Context):
        self.user.process(context)


class HandlersTest(unittest.TestCase):
    TOKEN: str = "12345:" + ("A" * 46)

    def test_command_matches_text_and_carries_method(self):
        called: list[str] = []

        def run(context: Context):
            called.append(context.event.get_text())

        command: Command = Command("start", ["start"], 1, 1, 20, run)
        accepted: Command | None = command.check("/start")

        self.assertIsNotNone(accepted)
        self.assertEqual("start", accepted.name)

    def test_context_parses_callback_data(self):
        bot: FakeBot = FakeBot(self.TOKEN, "@portfolio_bot", 12345)
        user: FakeUser = FakeUser()
        event: Bot.Event = Bot.Event(1, 123, Callback(5, "open").stringfy(), datetime.now())
        event.DEBUG_CALLBACK = True
        context: Context = Context(FakeApp(), bot, user, None, event)

        self.assertTrue(context.is_callback())
        self.assertEqual(["open"], context.get_callback_data())
        self.assertEqual("open", context.get_callback_string())

    def test_no_handlers_routes_to_user_process(self):
        bot: FakeBot = FakeBot(self.TOKEN, "@portfolio_bot", 12345)
        user: FakeUser = FakeUser()
        event: Bot.Event = Bot.Event(1, 123, "unknown", datetime.now())
        context: Context = Context(FakeApp(), bot, user, None, event)
        handler: NoHandlers = NoHandlers()

        handler.check(context)
        self.assertIsInstance(context.handler, FakeSession)
        handler.process(context)
        self.assertTrue(user.processed)


if __name__ == "__main__":
    unittest.main()
