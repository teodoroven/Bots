import unittest
from queue import PriorityQueue
from threading import Lock
from unittest.mock import patch

import relay.public as relay
import relay.runtime.gpt_runtime.requests as gpt_requests
from models import Model


class FakeBot:

    def __init__(self, bot_key: str):
        self.bot_key: str = bot_key
        self.name: str = "@fake"

    def get_bot_key(self) -> str:
        return self.bot_key


class FakeEvent:

    def __init__(self, chat_id: int):
        self.chat_id: int = int(chat_id)


class FakeUser:

    def __init__(self):
        self.requests: dict[int, main.Request] = {}
        self.responses: dict[int, main.Response] = {}
        self.debited_tokens: float = 0

    def add_request(self, request: relay.Request):
        self.requests[int(request.id)] = request

    def add_response(self, request_id: int, response: relay.Response):
        self.responses[int(request_id)] = response

    def debit_tokens(self, tokens: float):
        self.debited_tokens += float(tokens)


class FakeContext:

    def __init__(self, app: "TestAutocenter", bot_key: str, chat_id: int, request: relay.Request, user: FakeUser):
        self.autocenter: TestAutocenter = app
        self.bot: FakeBot = FakeBot(bot_key)
        self.chat_id: int = int(chat_id)
        self.handler: relay.Request = request
        self.user: FakeUser = user
        self.event: FakeEvent = FakeEvent(chat_id)

    def copy(self) -> "FakeContext":
        return FakeContext(self.autocenter, self.bot.get_bot_key(), self.chat_id, self.handler, self.user)

    def set_handler(self, handler: relay.Request):
        self.handler = handler

    def get_chat_id(self) -> int:
        return int(self.chat_id)


class FakeGPT:

    def __init__(self, app: "TestAutocenter | None" = None, bot_key: str = "telebot", chat_id: int = 1, obsolete_on_send: bool = False):
        self.app: TestAutocenter | None = app
        self.bot_key: str = bot_key
        self.chat_id: int = int(chat_id)
        self.obsolete_on_send: bool = bool(obsolete_on_send)
        self.requests: list[relay.Request] = []

    def get_tokens(self) -> float:
        return 1000.0

    def send_request(self, response_id: int, request: relay.Request) -> relay.Response:
        self.requests.append(request)

        if self.obsolete_on_send and self.app is not None:
            self.app.create_chatgpt_version(self.bot_key, self.chat_id)

        return relay.Response(response_id, request, 7, f"response {len(self.requests)}")


class TestAutocenter(relay.Autocenter):

    def __init__(self):
        self.element_id: int = 100
        self.process_task_lock: Lock = Lock()
        self.process_task_active_keys: dict[tuple[str, int], int] = {}
        self.process_task_queue: PriorityQueue[tuple[int, int, relay.ProcessTask]] = PriorityQueue()
        self.chatgpt_state_lock: Lock = Lock()
        self.chatgpt_versions: dict[tuple[str, int], int] = {}
        self.chatgpt_request_statuses: dict[tuple[str, int], dict[int, str]] = {}
        self.gpt: FakeGPT = FakeGPT()
        self.sent_responses: list[str] = []
        self.sent_messages: list[str] = []

    def send_response(self, context: FakeContext, response: str):
        self.sent_responses.append(str(response))

    def send(self, context: FakeContext, text: str, buttons: list[str] = [], inline: bool = True, max_width: int | None = None):
        self.sent_messages.append(str(text))


class ChatGPTWaitTest(unittest.TestCase):

    def create_request(self, app: TestAutocenter, batch: list[str], max_prompt: int = 100) -> relay.Request:
        model: Model = Model("https://example.test", "test-model", max_prompt, 1000)
        system_context: relay.SystemContext = relay.SystemContext(1, "system")
        prefix_messages: list[dict[str, str]] = [{"role": "assistant", "content": "old"}]
        batch_messages: list[dict[str, str]] = [{"role": "user", "content": text} for text in batch]
        suffix_messages: list[dict[str, str]] = [{"role": "system", "content": "system"}]
        request: relay.Request = relay.Request(app.create_id(), model, system_context, prefix_messages + batch_messages + suffix_messages)
        request.set_chatgpt_batch(prefix_messages, batch_messages, suffix_messages)
        return request

    def test_split_combines_messages_greedily(self):
        app: TestAutocenter = TestAutocenter()
        request: relay.Request = self.create_request(app, ["a" * 10, "b" * 10, "c" * 10], max_prompt = 30)

        chunks: list[relay.Request] = app.split_chatgpt_request(request)

        self.assertEqual(2, len(chunks))
        self.assertEqual(["a" * 10, "b" * 10], [message["content"] for message in chunks[0].chatgpt_pending_user_batch])
        self.assertEqual(["c" * 10], [message["content"] for message in chunks[1].chatgpt_pending_user_batch])
        self.assertEqual("system", chunks[0].messages[-1]["content"])
        self.assertEqual("system", chunks[1].messages[-1]["content"])

    def test_pending_queue_uses_only_same_bot_key_and_chat_id(self):
        app: TestAutocenter = TestAutocenter()
        same_task: relay.ProcessTask = relay.ProcessTask(1, FakeBot("telebot"), FakeEvent(1), False)
        other_chat_task: relay.ProcessTask = relay.ProcessTask(2, FakeBot("telebot"), FakeEvent(2), False)
        other_bot_task: relay.ProcessTask = relay.ProcessTask(3, FakeBot("vkbot"), FakeEvent(1), False)
        app.process_task_queue.put(same_task.get_queue_item())
        app.process_task_queue.put(other_chat_task.get_queue_item())
        app.process_task_queue.put(other_bot_task.get_queue_item())

        self.assertTrue(app.has_pending_chatgpt_task("telebot", 1))
        self.assertFalse(app.has_pending_chatgpt_task("telebot", 3))

    def test_obsolete_before_gpt_call_does_not_send_or_debit(self):
        app: TestAutocenter = TestAutocenter()
        user: FakeUser = FakeUser()
        request: relay.Request = self.create_request(app, ["hello"])
        context: FakeContext = FakeContext(app, "telebot", 1, request, user)
        version: int = app.create_chatgpt_version("telebot", 1)
        app.create_chatgpt_version("telebot", 1)
        app.gpt = FakeGPT(app)

        with patch.object(relay.Request, "process_tokens", lambda self, user: None), patch.object(gpt_requests, "sleep", lambda seconds: None):
            app.process_request_delayed(context, "telebot", 1, version)

        self.assertEqual(0, len(app.gpt.requests))
        self.assertEqual({}, user.requests)
        self.assertEqual(0, user.debited_tokens)
        self.assertEqual([], app.sent_responses)

    def test_obsolete_after_gpt_call_saves_response_and_suppresses_send(self):
        app: TestAutocenter = TestAutocenter()
        user: FakeUser = FakeUser()
        request: relay.Request = self.create_request(app, ["hello"])
        context: FakeContext = FakeContext(app, "telebot", 1, request, user)
        version: int = app.create_chatgpt_version("telebot", 1)
        app.gpt = FakeGPT(app, "telebot", 1, obsolete_on_send = True)

        with patch.object(relay.Request, "process_tokens", lambda self, user: None), patch.object(gpt_requests, "sleep", lambda seconds: None):
            app.process_request_sync(context, request, bot_key = "telebot", chat_id = 1, version = version, suppress_stale_response = True)

        self.assertEqual(1, len(app.gpt.requests))
        self.assertIn(request.id, user.requests)
        self.assertIn(request.id, user.responses)
        self.assertEqual(7, user.debited_tokens)
        self.assertEqual([], app.sent_responses)

    def test_delayed_false_is_synchronous_without_debounce(self):
        app: TestAutocenter = TestAutocenter()
        user: FakeUser = FakeUser()
        request: relay.Request = self.create_request(app, ["hello"])
        context: FakeContext = FakeContext(app, "telebot", 1, request, user)
        app.gpt = FakeGPT(app)

        with patch.object(relay.Request, "process_tokens", lambda self, user: None), patch.object(gpt_requests, "sleep", lambda seconds: None), patch.object(app, "wait_chatgpt_debounce", side_effect = AssertionError("debounce should not run")):
            app.process_request(context, delayed = False)

        self.assertEqual(1, len(app.gpt.requests))
        self.assertEqual(["response 1"], app.sent_responses)


if __name__ == "__main__":
    unittest.main()
