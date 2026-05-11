from __future__ import annotations

import unittest
from datetime import datetime
from pathlib import Path

from bots import Bot
from test_support import temp_directory


class ConcreteAttachment(Bot.Attachment):

    def set_id(self, attachment_id: int | str):
        self.id = attachment_id

    def get_type(self) -> str:
        return "doc"

    def check(self) -> bool:
        return bool(self.id) or bool(self.filename)


class ButtonTest(unittest.TestCase):

    def test_button_defaults_to_callback_payload_and_dumps(self):
        button: Bot.Keyboard.Button = Bot.Keyboard.Button("Open")

        self.assertEqual("Open", button.get_text())
        self.assertEqual("Open", button.get_callback_data())
        self.assertEqual("callback_data", button.get_type())
        self.assertEqual("Open", button.dumps()["callback_data"])

    def test_button_rejects_empty_text_and_conflicting_url(self):
        with self.assertRaises(ValueError):
            Bot.Keyboard.Button("")

        with self.assertRaises(ValueError):
            Bot.Keyboard.Button("Open", callback_data = "callback", url = "https://example.test")

    def test_url_button_has_url_type(self):
        button: Bot.Keyboard.Button = Bot.Keyboard.Button("Site", callback_data = None, url = "https://example.test")

        self.assertEqual("url", button.get_type())
        self.assertEqual("https://example.test", button.get_url())


class KeyboardEventAttachmentTest(unittest.TestCase):

    def test_keyboard_stores_inline_flag_and_dumps_buttons(self):
        keyboard: Bot.Keyboard = Bot.Keyboard(["One", Bot.Keyboard.Button("Two")], max_width = 2, inline = True)

        self.assertTrue(keyboard.check_inline())
        self.assertTrue(keyboard.check_editable())
        self.assertEqual([], keyboard.get_unused_buttons())
        self.assertEqual(2, keyboard.dumps()["max_width"])

    def test_keyboard_rejects_non_bool_inline(self):
        with self.assertRaises(ValueError):
            Bot.Keyboard([], max_width = 2, inline = "yes")

    def test_event_dumps_core_fields_and_rejects_bad_forward(self):
        date: datetime = datetime(2026, 5, 6, 10, 0, 0)
        event: Bot.Event = Bot.Event(1, 2, "hello", date)
        event.set_name("Ivan", "Ivanov")

        self.assertEqual(2, event.dumps()["chat_id"])
        self.assertEqual("hello", event.dumps()["text"])
        self.assertEqual(("Ivan", "Ivanov"), event.get_name())

        with self.assertRaises(ValueError):
            Bot.Event(1, 2, "hello", date, forward = [object()])

    def test_base_attachment_filename_validation(self):
        attachment: ConcreteAttachment = ConcreteAttachment(attachment_id = "remote-id")

        with temp_directory() as directory:
            filename: Path = Path(directory) / "file.txt"
            filename.write_text("content", encoding = "utf-8")
            attachment.set_filename(str(filename))

            self.assertEqual(str(filename.resolve()), attachment.get_filename())
            self.assertEqual("remote-id", attachment.dumps()["id"])

        with self.assertRaises(FileNotFoundError):
            ConcreteAttachment("").set_filename("missing.txt")


class BaseMessageTest(unittest.TestCase):

    def test_base_message_tracks_sent_and_deleted_events(self):
        message: Bot.BaseMessage = Bot.BaseMessage(10, "hello")
        message.set_chat_id(20)
        message.set_id(30)

        self.assertFalse(message.was_sent())
        message.add_event(30, datetime.now(), message.SENT_KEY)

        self.assertTrue(message.was_sent())
        self.assertTrue(message.check_editable())
        self.assertEqual(30, message.get_id())

        message.add_event(30, datetime.now(), message.DELETE_KEY)
        self.assertFalse(message.check_editable())

    def test_base_message_rejects_empty_text_and_negative_ids(self):
        with self.assertRaises(ValueError):
            Bot.BaseMessage(1, "")

        message: Bot.BaseMessage = Bot.BaseMessage(1, "hello")
        with self.assertRaises(ValueError):
            message.set_chat_id(-1)


if __name__ == "__main__":
    unittest.main()
