from __future__ import annotations

import unittest
from pathlib import Path

from bots import Telebot
from test_support import TEMP_ROOT
from test_support import temp_directory


class TelegramAttachmentFromFilenameTest(unittest.TestCase):

    def create_file(self, directory: str, filename: str) -> Path:
        path: Path = Path(directory) / filename
        path.write_bytes(b"payload")
        return path

    def assert_attachment_from_filename(self, attachment_class: type, filename: str):
        attachment: Telebot.Attachment = attachment_class.from_filename(filename)

        self.assertIsInstance(attachment, attachment_class)
        self.assertEqual(str(Path(filename).resolve()), attachment.get_filename())

    def test_photo_video_audio_and_doc_from_relative_filename(self):
        with temp_directory() as directory:
            paths: dict[type, Path] = {
                Telebot.PhotoAttachment: self.create_file(directory, "photo.jpg"),
                Telebot.VideoAttachment: self.create_file(directory, "video.mp4"),
                Telebot.AudioAttachment: self.create_file(directory, "audio.mp3"),
                Telebot.DocAttachment: self.create_file(directory, "doc.txt"),
            }

            for attachment_class, path in paths.items():
                with self.subTest(attachment_class = attachment_class.__name__):
                    self.assert_attachment_from_filename(attachment_class, str(path))

    def test_from_filename_rejects_missing_file(self):
        missing_filename: str = str(TEMP_ROOT / "missing_public_attachment.bin")

        with self.assertRaises(FileNotFoundError):
            Telebot.DocAttachment.from_filename(missing_filename)


if __name__ == "__main__":
    unittest.main()
