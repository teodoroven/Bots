import unittest
from threading import Lock
from unittest.mock import patch

import relay.bootstrap as bootstrap
import relay.public as relay


class FakeBot:

    def __init__(self, bot_key: relay.BOT_KEY):
        self.bot_key: relay.BOT_KEY = bot_key
        self.group_id: int = 1

    def get_bot_key(self) -> relay.BOT_KEY:
        return self.bot_key

    def check_chat_id(self, chat_id: int) -> bool:
        return isinstance(chat_id, int) and chat_id > 0


class StartupBot:

    def get_bot_key(self) -> relay.BOT_KEY:
        return "telebot"


class StartupAutocenter:

    def __init__(self, enter_menu: bool = False):
        self.bots: list[StartupBot] = [StartupBot()]
        self.stopped: bool = False

    def has_active_admins(self) -> bool:
        return False

    def stop(self):
        self.stopped = True


class AdminSetupAutocenter(relay.Autocenter):

    def __init__(self):
        self.working: bool = True
        self.users: dict[int, relay.User] = {}
        self.users_ids: dict[int, dict[str, set[int]]] = {}
        self.users_lock: Lock = Lock()
        self.user_id: int = 0
        self.admins_storage: dict[int, dict[str, relay.JSONABLE]] = {}
        self.bots: list[FakeBot] = [FakeBot("telebot")]
        self.saved_ids: bool = False
        self.saved_admins: bool = False

    def save_ids(self):
        self.saved_ids = True

    def save_admins(self):
        self.saved_admins = True

    def create_user(self, bot_key: relay.BOT_KEY, chat_id: int, access_level: int = 0) -> relay.User:
        with self.users_lock:
            user_id: int = self.create_user_id()
            chat_ids: dict[str, set[int]] = self.add_id(user_id, bot_key, chat_id)
            user: relay.User = relay.User(user_id, chat_ids, max(access_level, self.get_access_level(user_id)))
            user.app = self
            self.users[user_id] = user
            return user

    def login_user(self, user_id: int, bot_key: relay.BOT_KEY, chat_id: int) -> relay.User:
        user: relay.User = relay.User(user_id, self.add_id(user_id, bot_key, chat_id), self.resolve_user_access_level(user_id, bot_key, chat_id))
        user.app = self
        self.users[user_id] = user
        return user


class AdminSetupTest(unittest.TestCase):

    def test_check_startup_without_admins_does_not_fail(self):
        with self.assertLogs("bot.main", level = "WARNING") as logs:
            exit_code: int = bootstrap.run_bot(["--check-startup"], app_class = StartupAutocenter)

        self.assertEqual(exit_code, 0)
        self.assertTrue(any("WARNING:bot.main:" in message for message in logs.output))

    def test_has_active_admins(self):
        app: AdminSetupAutocenter = AdminSetupAutocenter()
        self.assertFalse(app.has_active_admins())

        app.admins_storage[1] = {
            "access_level": 0,
            "permissions": {},
            "notifications": {}
        }
        self.assertFalse(app.has_active_admins())

        app.admins_storage[2] = {
            "access_level": 1,
            "permissions": {},
            "notifications": {}
        }
        self.assertTrue(app.has_active_admins())

    def test_create_first_admin_creates_new_user(self):
        app: AdminSetupAutocenter = AdminSetupAutocenter()

        with self.assertLogs("bot.admin", level = "INFO") as logs, patch.object(relay.User, "save", lambda user: None):
            admin: relay.User = app.create_first_admin("telebot", 123)

        self.assertEqual(admin.access_level, relay.SYSTEM_ADMIN_ACCESS_LEVEL)
        self.assertEqual(app.users_ids[admin.id]["telebot"], {123})
        self.assertEqual(app.admins_storage[admin.id]["access_level"], relay.SYSTEM_ADMIN_ACCESS_LEVEL)
        self.assertEqual(app.admins_storage[admin.id]["permissions"], {key: True for key in relay.PERMISSION_KEYS})
        self.assertEqual(app.admins_storage[admin.id]["notifications"], dict(relay.DEFAULT_NOTIFICATIONS))
        self.assertTrue(app.saved_ids)
        self.assertTrue(app.saved_admins)
        self.assertTrue(any("user_id=" in message and "bot_key=telebot" in message and "access_level=3" in message for message in logs.output))

    def test_create_first_admin_updates_existing_user(self):
        app: AdminSetupAutocenter = AdminSetupAutocenter()
        user: relay.User = app.create_user("telebot", 456)
        app.saved_admins = False

        with patch.object(relay.User, "save", lambda current_user: None):
            admin: relay.User = app.create_first_admin("telebot", 456)

        self.assertEqual(admin.id, user.id)
        self.assertEqual(admin.access_level, relay.SYSTEM_ADMIN_ACCESS_LEVEL)
        self.assertEqual(app.admins_storage[user.id]["permissions"], {key: True for key in relay.PERMISSION_KEYS})
        self.assertEqual(app.admins_storage[user.id]["notifications"], dict(relay.DEFAULT_NOTIFICATIONS))
        self.assertTrue(app.saved_admins)

    def test_set_access_level_logs_safe_admin_event(self):
        app: AdminSetupAutocenter = AdminSetupAutocenter()
        user: relay.User = app.create_user("telebot", 789)
        app.saved_admins = False

        with self.assertLogs("bot.admin", level = "INFO") as logs, patch.object(relay.User, "save", lambda current_user: None):
            app.set_access_level(user.id, 1)

        self.assertEqual(app.admins_storage[user.id]["access_level"], 1)
        self.assertTrue(app.saved_admins)
        self.assertTrue(any("actor_id=None" in message and "target_user_id=" in message and "old_level=0" in message and "new_level=1" in message for message in logs.output))

    def test_log_process_does_not_include_sensitive_user_content(self):
        app: AdminSetupAutocenter = AdminSetupAutocenter()

        class SensitiveUser:
            id: int = 42

            def repr_messages(self) -> str:
                return "SECRET_USER_TEXT"

            def repr_requests(self) -> str:
                return "SECRET_GPT_REQUEST"

            def repr_responses(self) -> str:
                return "SECRET_GPT_RESPONSE"

        class SensitiveBot:
            def get_bot_key(self) -> relay.BOT_KEY:
                return "telebot"

        class SensitiveContext:
            handler: object = object()
            bot: SensitiveBot = SensitiveBot()
            user: SensitiveUser = SensitiveUser()

            def get_chat_id(self) -> int:
                return 123

        with self.assertLogs("bot.admin", level = "ERROR") as logs:
            app.log_process(SensitiveContext(), ["Traceback safe"], RuntimeError("SECRET_EXCEPTION_TEXT"))

        output: str = "\n".join(logs.output)
        self.assertIn("user_id=42", output)
        self.assertNotIn("SECRET_USER_TEXT", output)
        self.assertNotIn("SECRET_GPT_REQUEST", output)
        self.assertNotIn("SECRET_GPT_RESPONSE", output)
        self.assertNotIn("SECRET_EXCEPTION_TEXT", output)


if __name__ == "__main__":
    unittest.main()
