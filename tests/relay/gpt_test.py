from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock
from unittest.mock import patch

from models import Model
from relay.gpt import GPT
from relay.gpt import Request
from relay.gpt import Response
from relay.domain import SystemContext


class GptTest(unittest.TestCase):

    def create_request(self) -> Request:
        model: Model = Model("https://example.test/v1", "test-model", 1000, 2000)
        context: SystemContext = SystemContext(1, "system")
        return Request(2, model, context, [{"role": "user", "content": "hello"}])

    def test_request_and_response_dump_public_fields(self):
        request: Request = self.create_request()
        response: Response = Response(3, request, 15, "answer")

        self.assertEqual("test-model", request.dumps()["model"])
        self.assertEqual(15, response.dumps()["tokens"])
        self.assertEqual(2, response.dumps()["request_id"])

    def test_send_request_uses_mocked_openai_client(self):
        request: Request = self.create_request()
        completion: SimpleNamespace = SimpleNamespace(
            usage = SimpleNamespace(total_tokens = 12),
            choices = [SimpleNamespace(message = SimpleNamespace(content = " mocked answer "))],
        )
        client: MagicMock = MagicMock()
        client.chat.completions.create.return_value = completion

        with patch("relay.gpt.OpenAI", return_value = client) as openai_class:
            response: Response = GPT("fake-key").send_request(10, request)

        openai_class.assert_called_once_with(
            api_key = "fake-key",
            base_url = "https://example.test/v1",
            timeout = GPT.request_timeout,
            max_retries = GPT.request_max_retries,
        )
        client.chat.completions.create.assert_called_once_with(model = "test-model", messages = request.messages)
        self.assertEqual("mocked answer", response.content)
        self.assertEqual(12, response.tokens)

    def test_get_tokens_uses_http_mock_and_never_requires_real_api(self):
        http_response: MagicMock = MagicMock(status_code = 200)
        http_response.json.return_value = {"balance": "123.45"}

        with patch("relay.gpt.requests.get", return_value = http_response) as get:
            balance: float = GPT("fake-key").get_tokens()

        get.assert_called_once()
        self.assertEqual(123.45, balance)


if __name__ == "__main__":
    unittest.main()
