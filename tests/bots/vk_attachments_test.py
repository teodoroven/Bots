from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import MagicMock

from bots import Vkbot
from test_support import temp_directory


class FakeVkbot(Vkbot):

    def initAPI(self):
        self.bot: MagicMock = MagicMock()
        self.upload: MagicMock = MagicMock()


class VkAttachmentTest(unittest.TestCase):

    def build_bot(self) -> FakeVkbot:
        return FakeVkbot("vk" + ("x" * 220), "@portfolio_vk", 123)

    def test_photo_from_filename_uses_mocked_upload(self):
        bot: FakeVkbot = self.build_bot()
        bot.upload.photo_messages.return_value = [{"owner_id": 1, "id": 2, "access_key": "key"}]

        with temp_directory() as directory:
            filename: Path = Path(directory) / "photo.jpg"
            filename.write_bytes(b"image")
            attachment: Vkbot.Attachment = Vkbot.PhotoAttachment.from_filename(str(filename), bot)

        self.assertEqual("photo1_2_key", str(attachment))
        self.assertEqual(1, attachment.get_owner_id())
        self.assertEqual(2, attachment.get_id())

    def test_vk_attachment_dumps_and_loads_string_format(self):
        attachment: Vkbot.Attachment = Vkbot.Attachment("doc", 10, 20, "access")

        self.assertEqual("doc10_20_access", str(attachment))
        self.assertEqual("doc", attachment.dumps()["type"])
        self.assertEqual(10, attachment.dumps()["owner_id"])
        self.assertEqual("access", attachment.dumps()["access_key"])

    def test_url_attachment_keeps_public_fields_only(self):
        attachment: Vkbot.UrlAttachment = Vkbot.UrlAttachment({"height": 100, "width": 200, "url": "https://example.test/a.jpg", "type": "x"})

        self.assertEqual({
            "height": 100,
            "width": 200,
            "url": "https://example.test/a.jpg",
            "type": "x",
        }, attachment.dumps())

    def test_non_photo_from_filename_is_explicitly_unsupported(self):
        bot: FakeVkbot = self.build_bot()

        with temp_directory() as directory:
            filename: Path = Path(directory) / "doc.txt"
            filename.write_text("data", encoding = "utf-8")

            with self.assertRaises(Exception):
                Vkbot.DocAttachment.from_filename(str(filename), bot)


if __name__ == "__main__":
    unittest.main()
