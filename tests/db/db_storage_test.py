from __future__ import annotations

import json
import shutil
import unittest
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.orm import sessionmaker

from db.base import Base
from db.models import AdminORM
from db.models import ConversationORM
from db.models import UserChatIdORM
from db.models import UserORM
from db.storage import SqlAlchemyStorage
from test_support import temp_directory


class StorageTestCase(unittest.TestCase):

    def setUp(self):
        self.temp_dir_context = temp_directory()
        self.temp_dir: Path = Path(self.temp_dir_context.__enter__())
        database_path: Path = self.temp_dir / "test.db"
        self.engine = create_engine(f"sqlite:///{database_path.as_posix()}", future = True)
        Base.metadata.create_all(self.engine)
        self.session_factory: sessionmaker[Session] = sessionmaker(
            bind = self.engine,
            autoflush = False,
            autocommit = False,
            expire_on_commit = False,
        )
        self.storage: SqlAlchemyStorage = SqlAlchemyStorage(self.session_factory)
        self.storage.ensure_defaults()

    def tearDown(self):
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()
        shutil.rmtree(self.temp_dir, ignore_errors = True)
        self.temp_dir_context.__exit__(None, None, None)

    def count_rows(self, model: type[Base]) -> int:
        with self.session_factory() as session:
            return int(session.query(model).count())


class SqlAlchemyStorageTest(StorageTestCase):

    def test_create_user(self):
        self.storage.save_user(1, {"access_level": 0, "payload": "ok"}, 0)

        self.assertEqual(self.count_rows(UserORM), 1)
        self.assertEqual(self.storage.load_user(1)["payload"], "ok")

    def test_find_user_by_bot_key_chat_id(self):
        self.storage.save_user(1, {"access_level": 0}, 0)
        self.storage.add_user_chat_id(1, "telebot", 123)

        self.assertEqual(self.storage.find_user_id("telebot", 123), 1)

    def test_save_and_load_payload(self):
        payload: dict[str, object] = {
            "access_level": 2,
            "sessions": {"telebot": []},
            "messages": {"telebot": []},
        }
        self.storage.save_user(5, payload, 2)

        self.assertEqual(self.storage.load_user(5), payload)

    def test_upsert_without_duplicates(self):
        self.storage.save_user(1, {"access_level": 0}, 0)
        self.storage.add_user_chat_id(1, "telebot", 123)
        self.storage.save_user(1, {"access_level": 1}, 1)
        self.storage.add_user_chat_id(1, "telebot", 123)

        self.assertEqual(self.count_rows(UserORM), 1)
        self.assertEqual(self.count_rows(UserChatIdORM), 1)


if __name__ == "__main__":
    unittest.main()
