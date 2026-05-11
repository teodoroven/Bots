from __future__ import annotations

import unittest

from relay.sessions import Level
from relay.sessions import Stage
from relay.sessions import Value


class SessionStateTest(unittest.TestCase):

    def test_stage_dumps_loads_and_resets(self):
        stage: Stage = Stage(asked = True, confirming = True, confirmed = False)
        dumped: dict[str, bool] = stage.dumps()
        loaded: Stage = Stage()
        loaded.load(dumped)

        self.assertTrue(loaded.asked)
        self.assertTrue(loaded.confirming)
        loaded.reset()
        self.assertFalse(loaded.asked)

    def test_value_roundtrip_preserves_json_value_and_stage(self):
        value: Value = Value({"answer": 1}, Stage(asked = True))
        loaded: Value = Value.loads(value.dumps())

        self.assertEqual({"answer": 1}, loaded.value)
        self.assertTrue(loaded.stage.asked)

    def test_level_calls_configured_method_and_rejects_missing_load(self):
        calls: list[str] = []

        def method(level: Level, context: object | None):
            calls.append("called")

        level: Level = Level(method)
        with self.assertRaises(RuntimeError):
            level.get_value()

        level.load()
        level.call_method(None)

        self.assertEqual(["called"], calls)
        self.assertIsInstance(level.get_value(), Value)


if __name__ == "__main__":
    unittest.main()
