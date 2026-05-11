from __future__ import annotations

import unittest

from bots import Bot
from relay.conversations import Conversation
from relay.users import User


class FakeBot:
    group_id: int = 100

    def get_bot_key(self) -> str:
        return "telebot"


class ConversationTest(unittest.TestCase):

    def test_conversation_tracks_participants_and_callbacks(self):
        bot: FakeBot = FakeBot()
        user: User = User(1, {"telebot": {123}}, 0)
        conversation: Conversation = Conversation(10, "conv", lambda bot_key: bot, lambda: 1, create_message = True)

        party: Conversation.Participant = Conversation.Participant(user, bot, 123)
        conversation.add_party(party, admin_role = False, save = False)
        callback_data: str = conversation.get_callback("close")

        self.assertIs(party, conversation.find_party("telebot", 123))
        self.assertTrue(conversation.check_callback_data(callback_data))
        self.assertEqual(["close"], conversation.parse_callback(callback_data))

    def test_conversation_remove_message_updates_history(self):
        bot: FakeBot = FakeBot()
        conversation: Conversation = Conversation(10, "conv", lambda bot_key: bot, lambda: 1, create_message = False)
        message: Bot.BaseMessage = Bot.BaseMessage(100, "hello")
        message.set_chat_id(123)
        message.set_id(55)
        group: object = type("Group", (), {"bot": bot, "messages": [message]})()
        conversation.messages.append(group)

        conversation.remove_message("missing", "telebot", 55)

        self.assertEqual([], group.messages)


if __name__ == "__main__":
    unittest.main()
