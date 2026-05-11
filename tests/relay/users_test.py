from __future__ import annotations

import unittest
from datetime import datetime
from unittest.mock import patch

from bots import Message
from relay.domain import Client
from relay.domain import Limit
from relay.users import Admin
from relay.users import Settings
from relay.users import User


class UsersTest(unittest.TestCase):

    def test_user_names_chat_ids_and_access_level(self):
        user: User = User(1, {"telebot": {123}, "vkbot": {456}}, 0)
        with patch.object(User, "save"):
            user.set_username("telebot", "@user")
            user.set_name("telebot", "User Name")
            user.access_level = 2

        self.assertEqual(123, user.get_chat_id("telebot"))
        self.assertEqual("@user", user.get_username("telebot"))
        self.assertEqual("User Name", user.get_name("telebot"))
        self.assertEqual(2, user.get_access_level())

    def test_user_client_limits_debit_tokens(self):
        user: User = User(1, {"telebot": {123}}, 0)
        client: Client = Client(1)
        client.add_limit(Limit(1, 60, 100, datetime.now(), 100, False))
        user.clients = [client]

        with patch.object(User, "save"):
            user.debit_tokens(10)

        self.assertEqual(90, user.get_tokens())

    def test_admin_permissions_and_settings_defaults(self):
        admin: Admin = Admin(1, {"telebot": {123}}, 1)
        settings: Settings = Settings()

        self.assertTrue(admin.check_permissions([]))
        self.assertTrue(admin.check_notifications([]))
        self.assertIn("quantity", settings.call_admin)

    def test_user_messages_can_be_made_last(self):
        user: User = User(1, {"telebot": {123}}, 0)
        message_one: Message = Message(1, "one")
        message_two: Message = Message(2, "two")
        user.messages = {"telebot": [message_one, message_two]}

        user.make_last("telebot", message_one)

        self.assertTrue(user.is_last_message("telebot", message_one))
        self.assertFalse(user.is_last_message("telebot", message_two))


if __name__ == "__main__":
    unittest.main()
