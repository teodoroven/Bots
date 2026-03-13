import json
import os
import sys
import tempfile
import types
import unittest

# modules/__init__.py imports requests, but tests below do not use network calls.
if "requests" not in sys.modules:
    sys.modules["requests"] = types.ModuleType("requests")

from modules import (
    get_filenames,
    only_directory,
    readfile,
    loadfiles,
    writefile,
    writefiles,
    savefiles,
)


class TestModulesUtils(unittest.TestCase):
    def test_get_filenames_returns_primary_and_backup(self):
        primary, backup = get_filenames("json", "data.json")
        self.assertEqual(primary, os.path.join("json", "data.json"))
        self.assertEqual(backup, os.path.join("json", "data.json") + ".backup")

    def test_only_directory_normalizes_path(self):
        self.assertEqual(only_directory("a/b/../c/file.txt"), os.path.join("a", "c"))

    def test_readfile_returns_none_for_missing(self):
        self.assertIsNone(readfile("definitely_missing_file_123456.txt"))

    def test_loadfiles_skips_invalid_json_and_reads_next(self):
        with tempfile.TemporaryDirectory() as tmp:
            invalid = os.path.join(tmp, "invalid.json")
            valid = os.path.join(tmp, "valid.json")
            with open(invalid, "w", encoding="utf-8") as f:
                f.write("{broken json")
            with open(valid, "w", encoding="utf-8") as f:
                json.dump({"ok": True}, f)

            result = loadfiles([invalid, valid])
            self.assertEqual(result, {"ok": True})

    def test_writefile_and_writefiles(self):
        with tempfile.TemporaryDirectory() as tmp:
            first = os.path.join(tmp, "a", "one.txt")
            second = os.path.join(tmp, "b", "two.txt")

            self.assertIsNone(writefile(first, "hello"))
            self.assertEqual(readfile(first), "hello")

            errors = writefiles([first, second], "payload")
            self.assertEqual(errors, {})
            self.assertEqual(readfile(second), "payload")

    def test_savefiles_writes_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = os.path.join(tmp, "json", "data.json")
            err = savefiles([target], {"value": 42})
            self.assertIsNone(err)
            with open(target, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            self.assertEqual(loaded, {"value": 42})


if __name__ == "__main__":
    unittest.main()
