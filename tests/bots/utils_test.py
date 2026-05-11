from __future__ import annotations

import os
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from bots.utils.dates import diff_sec
from bots.utils.dates import get_timestamp
from bots.utils.dates import strftime
from bots.utils.env import get_env_int
from bots.utils.env import get_env_int_set
from bots.utils.files import change_extension
from bots.utils.files import create_filename
from bots.utils.files import only_directory
from bots.utils.files import only_extension
from bots.utils.files import only_filename
from bots.utils.mapping import get_from
from bots.utils.mapping import get_int
from bots.utils.mapping import is_int
from bots.utils.mapping import is_iterable
from bots.utils.text import cut
from bots.utils.text import preceding
from test_support import temp_directory


class TextUtilsTest(unittest.TestCase):

    def test_cut_keeps_short_values_and_slices_iterables(self):
        self.assertEqual("short", cut("short", 10))
        self.assertEqual("12...", cut("1234567890", 5, dots = True))
        self.assertEqual([1, 2], cut([1, 2, 3], 2))
        self.assertEqual((1, 2), cut((1, 2, 3), 2))

    def test_cut_rejects_non_sized_values(self):
        with self.assertRaises(TypeError):
            cut(1, 3)

    def test_preceding_escapes_markdown_symbols(self):
        self.assertEqual("\\[a\\]\\(b\\)\\!", preceding("[a](b)!"))


class FileUtilsTest(unittest.TestCase):

    def test_path_parts_and_extension_change(self):
        filename: str = os.path.join("folder", "file.name.txt")

        self.assertEqual(".name.txt", only_extension(filename))
        self.assertEqual("file", only_filename(filename))
        self.assertTrue(only_directory(filename).endswith("folder"))
        self.assertEqual(os.path.join("folder", "file.name.md"), change_extension(filename, ".md"))

    def test_create_filename_avoids_existing_file(self):
        with temp_directory() as directory:
            path: Path = Path(directory) / "report.txt"
            path.write_text("first", encoding = "utf-8")

            created: str = create_filename(directory, "report.txt")

        self.assertTrue(created.endswith("report (2).txt"))

    def test_change_extension_validates_extension(self):
        with self.assertRaises(ValueError):
            change_extension("file.txt", "md")


class MappingEnvDateUtilsTest(unittest.TestCase):

    def test_mapping_helpers_respect_defaults_and_types(self):
        data: dict[str, object] = {"outer": {"value": "7"}, "items": [1, 2]}

        self.assertEqual("7", get_from(data, "outer", "value", types = (str,)))
        self.assertEqual(0, get_int(data, 0, "outer", "value"))
        self.assertEqual("fallback", get_from(data, "missing", default = "fallback"))
        self.assertTrue(is_iterable(data["items"]))
        self.assertTrue(is_int("42"))
        self.assertFalse(is_int("4.2"))

    def test_env_helpers_use_defaults_and_parse_values(self):
        with patch.dict(os.environ, {"BOT_INT": "12", "BOT_SET": "1, 2, 3"}, clear = False):
            self.assertEqual(12, get_env_int("BOT_INT", default = 0))
            self.assertEqual({1, 2, 3}, get_env_int_set("BOT_SET"))

        with patch.dict(os.environ, {}, clear = True):
            self.assertEqual(9, get_env_int("BOT_INT", default = 9))
            self.assertEqual({5}, get_env_int_set("BOT_SET", default = {5}))

    def test_date_helpers_are_deterministic_for_known_datetime(self):
        date: datetime = datetime(2026, 5, 6, 10, 0, 0)

        self.assertEqual(int(date.timestamp()), get_timestamp(date))
        self.assertEqual(-5, diff_sec(datetime(2026, 5, 6, 10, 0, 5), date))
        self.assertEqual("06.05.2026 10:00:00", strftime(date))


if __name__ == "__main__":
    unittest.main()
