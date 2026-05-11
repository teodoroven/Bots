from __future__ import annotations

import unittest

from relay.callback_data import Callback


class CallbackDataTest(unittest.TestCase):

    def test_callback_roundtrip_preserves_session_and_args(self):
        callback: Callback = Callback(12, "open", 34, "value")
        serialized: str = callback.stringfy()
        loaded: Callback = Callback.loads(serialized)

        self.assertEqual(12, loaded.session_id)
        self.assertEqual(["open", "34", "value"], loaded.args)
        self.assertEqual(serialized, loaded.stringfy())

    def test_callback_supports_none_session_for_inline_system_actions(self):
        callback: Callback = Callback(None, "conversation", 5, "close")
        loaded: Callback = Callback.loads(callback.stringfy())

        self.assertIsNone(loaded.session_id)
        self.assertEqual(["conversation", "5", "close"], loaded.args)

    def test_invalid_callback_data_is_rejected(self):
        with self.assertRaises(ValueError):
            Callback.loads("")

        with self.assertRaises(ValueError):
            Callback.loads("not-session;1")


if __name__ == "__main__":
    unittest.main()
