"""
Описывает runtime-обработку GPT-запросов.
Модуль относится к архитектурной зоне: прикладной слой `relay`, который связывает пользователей, сессии, доменную модель, GPT, уведомления и runtime-логику приложения.

### Публичные классы
- `GptRequestsMixin`: runtime-логика GPT-запросов.

### Публичные функции
- Публичные функции отсутствуют.

### Связи
Используется app-layer сценариями, обработчиками, сессиями и runtime-миксинами для единого пользовательского потока между ботами, GPT и storage.
"""

from __future__ import annotations



from relay.common import Model, Thread, datetime, sleep
from relay.config import (
    CHATGPT_DEBOUNCE_POLL_SECONDS,
    CHATGPT_DEBOUNCE_WAIT_SECONDS,
    CHATGPT_MAX_DEBOUNCE_MESSAGES,
    MAX_PRINT_LENGTH,
    MAX_REQUEST_LENGTH,
    get_phrase,
    logger_gpt,
)
from relay.gpt import GPT, Request, Response
from relay.domain import SystemContext
from relay.handlers import Context
from relay.users import User
from relay.utils import is_int
class GptRequestsMixin:
    """
    Добавляет `App` операции gptrequests без привязки к transport-layer.
    Mixin рассчитан на включение в `App` и работает с его registry, storage, пользователями, ботами и очередями.

    ### Методы
    - `prove_request`: Проверяет введённое пользователем значение для шага `request`.
    - `get_chatgpt_request_text_limit`: Возвращает chatgpt request text limit из текущего состояния `GptRequestsMixin`.
    - `get_chatgpt_messages_length`: Возвращает chatgpt messages length из текущего состояния `GptRequestsMixin`.
    - `split_chatgpt_request`: Делит chatgpt request на части, допустимые для transport-layer.
    - `check_chatgpt_wait_required`: Проверяет chatgpt wait required перед использованием.
    - `wait_chatgpt_debounce`: Ждёт debounce-окно перед продолжением GPT-сценария.
    - `process_request`: Обрабатывает GPT-запрос в текущем пользовательском или transport-layer потоке.
    - `process_request_delayed`: Обрабатывает request delayed в текущем пользовательском или transport-layer потоке.
    - `process_request_sync`: Обрабатывает request sync в текущем пользовательском или transport-layer потоке.
    - `debit_tokens`: Списывает tokens с лимитов GPT-клиентов пользователя.

    ### Жизненный цикл
    Создаётся app-layer кодом, участвует в обработке пользовательского события и сохраняет изменённое состояние через существующие runtime/storage механизмы.

    ### Пример использования
    ```py
    app: GptRequestsMixin
    ```
    """
    def prove_request(self, context: Context):
        """
        Проверяет введённое пользователем значение для шага `request`.

        ### Аргументы:
        :param context: контекст обработки события

        :return: значение, которое runtime использует для продолжения обработки события

        ### Пример использования:
        ```py
        gptRequestsMixin.prove_request(context = context)
        ```
        """
        bot_key: BOT_KEY = context.bot.get_bot_key()

        chat_id: int = context.get_chat_id()

        if not context.has_event():


            return

        elif context.is_callback():


            return

        elif context.event.attachments:


            return

        text = cut(context.event.text, MAX_PRINT_LENGTH)


        for s in ("В ОТВЕТЕ", "ИГНОРИРУЙ", "IGNOR"):

            if s.upper() in text.upper():

                return

        # WARNING:

        if len(text) > MAX_REQUEST_LENGTH:

            self.admin_warning("too long request")

            return

        if not self.gpt:

            self.admin_warning("no_token")

            return

        if not self.model:

            self.admin_warning("no_model")

            return

        max_message_length: int = MAX_REQUEST_LENGTH

        model: Model = self.model

        if is_int(model.max_prompt) and model.max_prompt > 0:

            max_message_length = min(max_message_length, model.max_prompt)


        user: User = self.get_user(bot_key, chat_id)


        # if not user.clients:

        #     client: GPT.Client = context.self.get_client(user)

        #     user.clients[client.id] = client

        # Количество оставшихся токеном

        left: float = user.get_tokens()


        if left < self.settings.gpt.get("min_request", 8000):

            logger_gpt.warning("Недостаточно пользовательских токенов: user_id=%s", user.id)

            return

        messages: list[dict[str, str]] = []

        def add_message(role: Literal["system", "assistant", "user"], content: str) -> dict[str, str]:

            message: dict[str, str] = {

                "role": role if role in ("system", "assistant", "user") else 5/0,

                "content": cut(content, max_message_length)

            }

            messages.append(message)

            return message

        # Системный запрос (system)

        system_context: SystemContext | None = self.get_context()

        questions: list[Question] = self.get_questions()

        if system_context is None:

            self.admin_warning("no_context")

            return


        max_tokens: int = min(left, model.max_context) - system_context.get_tokens(model)


        groups: list[Message.MessagesGroup] = user.get_history(bot_key, max_tokens, self.get_bot, CHATGPT_MAX_DEBOUNCE_MESSAGES)


        batch_start_index: int = len(groups)

        for group in reversed(groups):

            if group.owner_id == chat_id:

                batch_start_index -= 1

            else:

                break

        for group in groups:

            text = group.get_text()


            add_message("user" if group.owner_id == chat_id else "assistant", cut(group.get_text(), max_message_length))


        add_message("system" if model.model != "o1-mini" else "user", system_context.get_context(questions))

        request: Request = Request(self.create_id(), model, system_context, messages)

        request.set_chatgpt_batch(messages[:batch_start_index], messages[batch_start_index:len(groups)], messages[len(groups):])

        context.set_handler(request)

    def get_chatgpt_request_text_limit(self, model: Model) -> int:
        """
        Возвращает лимит длины текста для одного GPT-запроса.

        ### Аргументы:
        :param model: GPT-модель

        :return: chatgpt request text limit

        ### Пример использования:
        ```py
        gptRequestsMixin.get_chatgpt_request_text_limit(model = model)
        ```
        """
        max_message_length: int = MAX_REQUEST_LENGTH

        if is_int(model.max_prompt) and model.max_prompt > 0:

            max_message_length = min(max_message_length, model.max_prompt)

        return int(max_message_length)

    def get_chatgpt_messages_length(self, messages: Iterable[dict[str, str]]) -> int:
        """
        Возвращает максимальное число сообщений, хранимых для GPT-контекста.

        ### Аргументы:
        :param messages: сообщения или группы сообщений для обработки

        :return: chatgpt messages length

        ### Пример использования:
        ```py
        gptRequestsMixin.get_chatgpt_messages_length(messages = messages)
        ```
        """
        return sum(len(message.get("content", "")) for message in messages)

    def split_chatgpt_request(self, request: Request) -> list[Request]:
        """
        Делит chatgpt request на части, допустимые для transport-layer.

        ### Аргументы:
        :param request: GPT-запрос, связанный с пользователем

        :return: значение, которое runtime использует для продолжения обработки события

        ### Пример использования:
        ```py
        app.split_chatgpt_request(request = request)
        ```
        """
        pending_user_batch: list[dict[str, str]] = [dict(message) for message in request.chatgpt_pending_user_batch]

        if not pending_user_batch:

            return [request]

        max_length: int = self.get_chatgpt_request_text_limit(request.model)

        if request.get_chatgpt_batch_length() < max_length and len(pending_user_batch) <= CHATGPT_MAX_DEBOUNCE_MESSAGES:

            return [request]

        prefix_messages: list[dict[str, str]] = [dict(message) for message in request.chatgpt_prefix_messages]

        suffix_messages: list[dict[str, str]] = [dict(message) for message in request.chatgpt_suffix_messages]

        stable_length: int = self.get_chatgpt_messages_length(prefix_messages + suffix_messages)

        chunks: list[list[dict[str, str]]] = []

        current_chunk: list[dict[str, str]] = []

        current_length: int = stable_length

        for message in pending_user_batch:

            message_length: int = len(message.get("content", ""))

            next_length: int = current_length + message_length

            if current_chunk and (next_length > max_length or len(current_chunk) >= CHATGPT_MAX_DEBOUNCE_MESSAGES):

                chunks.append(current_chunk)

                current_chunk = []

                current_length = stable_length

            current_chunk.append(dict(message))

            current_length += message_length

        if current_chunk:

            chunks.append(current_chunk)

        requests: list[Request] = []

        for index, chunk in enumerate(chunks):

            request_id: int = request.id if index == 0 else self.create_id()

            system_context: SystemContext = SystemContext(request.context_id, request.context)

            messages: list[dict[str, str]] = [dict(message) for message in prefix_messages + chunk + suffix_messages]

            chunk_request: Request = Request(request_id, request.model, system_context, messages)

            chunk_request.set_chatgpt_batch(prefix_messages, chunk, suffix_messages)

            requests.append(chunk_request)

        return requests

    def check_chatgpt_wait_required(self, request: Request) -> bool:
        """
        Проверяет значение `chatgpt wait required` перед сохранением или использованием.

        ### Аргументы:
        :param request: GPT-запрос

        :return: `True`, если значение `chatgpt wait required` перед сохранением или использованием; иначе `False`

        ### Пример использования:
        ```py
        gptRequestsMixin.check_chatgpt_wait_required(request = request)
        ```
        """
        if len(request.chatgpt_pending_user_batch) >= CHATGPT_MAX_DEBOUNCE_MESSAGES:

            return False

        elif request.get_chatgpt_batch_length() >= self.get_chatgpt_request_text_limit(request.model):

            return False

        else:

            return True

    def wait_chatgpt_debounce(self, bot_key: BOT_KEY, chat_id: int, version: int, request: Request) -> bool:
        """
        Ждёт debounce-окно перед продолжением GPT-сценария.

        ### Аргументы:
        :param bot_key: ключ транспорта
        :param chat_id: идентификатор чата
        :param version: версия GPT-запроса для защиты от устаревших ответов
        :param request: GPT-запрос

        :return: значение, которое runtime использует для продолжения обработки события

        ### Пример использования:
        ```py
        gptRequestsMixin.wait_chatgpt_debounce(bot_key = bot_key, chat_id = chat_id, version = version, request = request)
        ```
        """
        wait_required: bool = self.check_chatgpt_wait_required(request)

        started_at: datetime = datetime.now()

        while self.check_chatgpt_version(bot_key, chat_id, version):

            waited: float = (datetime.now() - started_at).total_seconds()

            if wait_required and waited < CHATGPT_DEBOUNCE_WAIT_SECONDS:

                sleep(CHATGPT_DEBOUNCE_POLL_SECONDS)

                continue

            if self.has_pending_chatgpt_task(bot_key, chat_id):

                sleep(CHATGPT_DEBOUNCE_POLL_SECONDS)

                continue

            return True

        return False

    def process_request(self, context: Context, delayed: bool = False):
        """
        Обрабатывает GPT-запрос в текущем runtime-контексте.

        ### Аргументы:
        :param context: контекст обработки события
        :param delayed: нужно ли отложить обработку ответа

        :return: значение, которое runtime использует для продолжения обработки события

        ### Пример использования:
        ```py
        gptRequestsMixin.process_request(context = context, delayed = delayed)
        ```
        """

        if delayed:

            request: Request = context.handler

            bot_key: BOT_KEY = context.bot.get_bot_key()

            chat_id: int = context.get_chat_id()

            version: int = self.create_chatgpt_version(bot_key, chat_id)

            worker_context: Context = context.copy()

            worker_context.set_handler(request)

            thread: Thread = Thread(

                target = self.process_request_delayed,

                args = (worker_context, bot_key, chat_id, version),

                name = f"ChatGPTRequest({bot_key=}, {chat_id=}, {version=})",

                daemon = True

            )

            thread.start()

            return

        return self.process_request_sync(context, context.handler)

    def process_request_delayed(self, context: Context, bot_key: BOT_KEY, chat_id: int, version: int):
        """
        Обрабатывает request delayed в текущем runtime-контексте.

        ### Аргументы:
        :param context: контекст обработки события
        :param bot_key: ключ транспорта
        :param chat_id: идентификатор чата
        :param version: версия GPT-запроса для защиты от устаревших ответов

        ### Пример использования:
        ```py
        gptRequestsMixin.process_request_delayed(context = context, bot_key = bot_key, chat_id = chat_id, version = version)
        ```
        """
        request: Request = context.handler

        try:

            if not self.wait_chatgpt_debounce(bot_key, chat_id, version, request):

                self.set_chatgpt_request_status(bot_key, chat_id, version, "skipped_before_send")

                return

            requests: list[Request] = self.split_chatgpt_request(request)

            for chunk_request in requests:

                if not self.check_chatgpt_version(bot_key, chat_id, version):

                    self.set_chatgpt_request_status(bot_key, chat_id, version, "skipped_before_send")

                    return

                self.set_chatgpt_request_status(bot_key, chat_id, version, "sent")

                self.process_request_sync(

                    context,

                    chunk_request,

                    bot_key = bot_key,

                    chat_id = chat_id,

                    version = version,

                    suppress_stale_response = True

                )

                if not self.check_chatgpt_version(bot_key, chat_id, version):

                    return

            self.set_chatgpt_request_status(bot_key, chat_id, version, "completed")

        except Exception as err:

            logger_gpt.exception("Ошибка фоновой обработки ChatGPT-запроса: %s", err)

        finally:

            self.cleanup_chatgpt_request_status(bot_key, chat_id, version)

    def process_request_sync(

            self,

            context: Context,

            request: Request,

            bot_key: BOT_KEY | None = None,

            chat_id: int | None = None,

            version: int | None = None,

            suppress_stale_response: bool = False,

            ):
        """
        Обрабатывает request sync в текущем runtime-контексте.

        ### Аргументы:
        :param context: контекст обработки события
        :param request: GPT-запрос
        :param bot_key: ключ транспорта
        :param chat_id: идентификатор чата
        :param version: версия GPT-запроса для защиты от устаревших ответов
        :param suppress_stale_response: нужно ли скрыть устаревший GPT-ответ

        ### Пример использования:
        ```py
        gptRequestsMixin.process_request_sync(context = context, request = request, bot_key = bot_key, chat_id = chat_id, version = version, suppress_stale_response = suppress_stale_response)
        ```
        """
        user: User = context.user

        gpt: GPT = self.gpt

        if suppress_stale_response and bot_key is not None and chat_id is not None and version is not None:

            if not self.check_chatgpt_version(bot_key, chat_id, version):

                return

        request.process_tokens(user)

        user.add_request(request)

        try:

            response: Response = self.catch_bot(

                lambda: gpt.send_request(self.create_id(), request),

                description = "gpt.send_request",

                raise_error = True,

            )

        except Exception as err:

            logger_gpt.exception("Не удалось отправить запрос GPT: %s", err)

            if not suppress_stale_response or bot_key is None or chat_id is None or version is None or self.check_chatgpt_version(bot_key, chat_id, version):

                self.send(context, get_phrase("incorrect"))

            return

        user.add_response(request.id, response)

        sleep(2)

        logger_gpt.info(

            "GPT-запрос обработан: user_id=%s request_id=%s response_tokens=%s",

            getattr(user, "id", 0),

            request.id,

            response.tokens,

        )

        if suppress_stale_response and bot_key is not None and chat_id is not None and version is not None:

            if self.check_chatgpt_version(bot_key, chat_id, version):

                self.send_response(context, response.content)

            else:

                self.set_chatgpt_request_status(bot_key, chat_id, version, "response_suppressed")

        else:

            self.send_response(context, response.content)

        self.debit_tokens(user, request, response.tokens)

    def debit_tokens(self, user: User, request: Request, tokens: float):
        """
        Координирует runtime-состояние приложения между очередями, пользователями и transport-layer.

        ### Аргументы:
        :param user: пользователь приложения
        :param request: GPT-запрос
        :param tokens: количество токенов

        ### Пример использования:
        ```py
        gptRequestsMixin.debit_tokens(user = user, request = request, tokens = tokens)
        ```
        """

        tokens_debited: float = request.tokens if request.check_tokens() else 0

        total_tokens: float = tokens - tokens_debited


        if total_tokens != 0:

            user.debit_tokens(total_tokens)

            request.tokens = int(tokens)
