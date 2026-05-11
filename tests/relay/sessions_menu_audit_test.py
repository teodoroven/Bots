from __future__ import annotations

import unittest

import relay.public as relay


class SessionsMenuAuditTest(unittest.TestCase):

    def test_public_session_registry_has_core_workflows(self):
        expected_sessions: set[str] = {
            "MainSession",
            "NoHandlersSession",
            "ConvSession",
            "GPTSession",
            "SessionUsers",
            "SessionAdmins",
            "SessionProviders",
            "SessionModels",
            "SessionContexts",
            "SessionQuestions",
            "SessionLimits",
            "SessionFilials",
            "DateSession",
            "SessionDates",
            "ConfigureDateSession",
            "ChangeContentSession",
        }
        registered_sessions: set[str] = set(relay.App.SESSIONS)

        self.assertTrue(expected_sessions.issubset(registered_sessions))

    def test_registered_session_callbacks_are_parseable_and_unique(self):
        seen: set[str] = set()

        for session_name in sorted(relay.App.SESSIONS):
            callback_data: str = relay.Callback(1, session_name, "audit").stringfy()
            parsed: relay.Callback = relay.Callback.loads(callback_data)

            self.assertEqual(1, parsed.session_id)
            self.assertEqual([session_name, "audit"], parsed.args)
            self.assertNotIn(callback_data, seen)
            seen.add(callback_data)

    def test_callback_collision_audit_uses_full_session_name(self):
        users_callback: str = relay.Callback(1, "SessionUsers").stringfy()
        admins_callback: str = relay.Callback(1, "SessionAdmins").stringfy()

        self.assertNotEqual(users_callback, admins_callback)


if __name__ == "__main__":
    unittest.main()
