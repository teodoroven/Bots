from __future__ import annotations

import ast
import unittest
from pathlib import Path

import bots
import main
import relay
import relay.public as relay_public


PROJECT_ROOT = Path(__file__).resolve().parents[1]
IMPORT_SCAN_TARGETS = (
    PROJECT_ROOT / "main.py",
    PROJECT_ROOT / "relay",
    PROJECT_ROOT / "bots",
    PROJECT_ROOT / "modules",
    PROJECT_ROOT / "callbacks.py",
    PROJECT_ROOT / "tests",
)


class ImportsTest(unittest.TestCase):

    def test_project_does_not_use_wildcard_imports(self):
        offenders: list[str] = []

        for target in IMPORT_SCAN_TARGETS:
            paths: list[Path] = [target] if target.is_file() else list(target.rglob("*.py"))

            for path in paths:
                tree = ast.parse(path.read_text(encoding = "utf-8"), filename = str(path))

                for node in ast.walk(tree):
                    if isinstance(node, ast.ImportFrom) and any(alias.name == "*" for alias in node.names):
                        offenders.append(f"{path.relative_to(PROJECT_ROOT)}:{node.lineno}")

        self.assertEqual([], offenders)

    def test_public_api_exports_project_symbols_only(self):
        expected_relay_symbols: set[str] = {
            "App",
            "Autocenter",
            "BOT_KEY",
            "Callback",
            "ProcessTask",
            "Request",
            "Response",
            "SystemContext",
            "User",
            "run_bot",
        }
        expected_bots_symbols: set[str] = {
            "BOT_KEY",
            "Bot",
            "BotTypes",
            "JSONABLE",
            "Message",
            "Telebot",
            "Vkbot",
        }
        forbidden_symbols: set[str] = {"Any", "TeleBot", "logging", "requests"}

        self.assertLessEqual(expected_relay_symbols, set(relay_public.__all__))
        self.assertLessEqual(expected_relay_symbols, set(relay.__all__))
        self.assertLessEqual(expected_bots_symbols, set(bots.__all__))
        self.assertIn("run_bot", main.__all__)

        self.assertTrue(forbidden_symbols.isdisjoint(relay_public.__all__))
        self.assertTrue(forbidden_symbols.isdisjoint(relay.__all__))
        self.assertTrue(forbidden_symbols.isdisjoint(bots.__all__))
        self.assertTrue(forbidden_symbols.isdisjoint(main.__all__))


if __name__ == "__main__":
    unittest.main()
