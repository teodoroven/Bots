"""
Описывает GPT-запросы, ответы и wrapper провайдера.
Модуль относится к архитектурной зоне: прикладной слой `relay`, который связывает пользователей, сессии, доменную модель, GPT, уведомления и runtime-логику приложения.

### Публичные классы
- `GPT`: wrapper GPT-провайдера.
- `Request`: GPT-запрос с контекстом и токенами.
- `Response`: ответ GPT для сохранения в истории.

### Публичные функции
- Публичные функции отсутствуют.

### Связи
Используется app-layer сценариями, обработчиками, сессиями и runtime-миксинами для единого пользовательского потока между ботами, GPT и storage.
"""

from __future__ import annotations




from .common import (
    BotTypes,
    Iterable,
    Model,
    OpenAI,
    Thread,
    requests,
)
from .config import logger_gpt, logger_user_flow
from .domain.base import Element
from .domain.gpt import SystemContext
from .utils import count_tokens
class GPT():
    """
    `GPT` хранит API-ключ ProxyAPI/OpenAI-compatible провайдера и кэш клиентов по `base_url` модели.
    Класс делает внешние GPT-вызовы, применяет timeout/retry настройки OpenAI-клиента и возвращает fallback-ответ при ошибке запроса.

    ### Поля
    - `confirm`: флаг необходимости подтверждать GPT-действие.
    - `show`: флаг показа GPT-элемента в пользовательском интерфейсе.
    - `request_timeout`: timeout HTTP-запроса к GPT API.
    - `request_max_retries`: число retry, передаваемое OpenAI-клиенту.
    - `request_fallback_content`: текст ответа при ошибке GPT API.
    - `apikey`: секрет для внешнего API; используется в OpenAI-compatible клиенте и запросе баланса ProxyAPI.
    - `_clients`: кэш `OpenAI` clients по `model.base_url`.

    ### Методы
    - `__init__`: Сохраняет API-ключ и создаёт пустой кэш клиентов.
    - `get_tokens`: Запрашивает баланс ProxyAPI по HTTP и возвращает баланс или `-1` при ошибке.
    - `send_request`: Вызывает `client.chat.completions.create` и возвращает `Response` или fallback.

    ### Жизненный цикл
    Создаётся runtime-слоем при загрузке GPT-настроек и переиспользует клиентов для запросов к моделям с одинаковым `base_url`.

    ### Пример использования
    ```py
    gpt: GPT
    ```
    """
    confirm: bool = True
    show: bool = True
    request_timeout: float = 30.0
    request_max_retries: int = 2
    request_fallback_content: str = "Извините, GPT временно недоступен. Попробуйте повторить запрос чуть позже."

    def __init__(self, apikey: str):
        """
        Инициализирует описание GPT-провайдера без сетевых вызовов в конструкторе.

        ### Аргументы:
        :param apikey: API-ключ провайдера GPT

        ### Пример использования:
        ```py
        gPT = GPT(apikey = apikey)
        ```
        """
        self.apikey: str = str(apikey)
        self._clients: dict[str, OpenAI] = {}

    def _get_client(self, model: Model) -> OpenAI:
        base_url: object = model.base_url
        client_key: str = str(base_url)
        client: OpenAI | None = self._clients.get(client_key)

        if client is None:
            client = OpenAI(
                api_key = self.apikey,
                base_url = base_url,
                timeout = self.request_timeout,
                max_retries = self.request_max_retries,
            )
            self._clients[client_key] = client

        return client

    def _fallback_response(self, response_id: int, request: Request) -> Response:
        return Response(response_id, request, 0, self.request_fallback_content)

    def _log_send_request_error(self, response_id: int, request: Request, err: Exception):
        try:
            model: Model = request.model
            logger_gpt.warning(
                "send_request failed: response_id=%s request_id=%s model=%s base_url=%s messages=%s error_type=%s status_code=%s",
                response_id,
                getattr(request, "id", None),
                getattr(model, "model", None),
                getattr(model, "base_url", None),
                len(getattr(request, "messages", [])),
                err.__class__.__name__,
                getattr(err, "status_code", None),
            )
        except Exception:
            pass

    def get_tokens(self) -> float:
        """
        Запрашивает баланс ProxyAPI через `https://api.proxyapi.ru/proxyapi/balance`.
        Метод делает внешний HTTP-запрос с bearer token из `self.apikey`; локальное состояние токенов он не читает.

        :return: баланс из ответа ProxyAPI как `float`; `-1`, если запрос, status code или JSON-разбор завершились ошибкой

        ### Пример использования:
        ```py
        gPT.get_tokens()
        ```
        """

        url = "https://api.proxyapi.ru/proxyapi/balance"
        headers = {
            "Authorization": f"Bearer {self.apikey}"
        }

        try:
            response = requests.get(url, headers = headers, timeout = 10)
        except Exception as err:
            # logger.error("get_tokens:",type(err), err)
            return -1

        if response.status_code == 200:
            try:
                balance_info: dict = response.json()
                balance: object = balance_info.get("balance")
                return float(balance)
            except Exception:
                return -1
        else:
            return -1

    def send_request(self, response_id: int, request: Request) -> Response:
        """
        Отправляет GPT-запрос через OpenAI-compatible client для `request.model.base_url`.
        Метод создаёт или переиспользует `OpenAI` client, вызывает `client.chat.completions.create`, читает `choices[0].message.content` и `usage.total_tokens`; при любой ошибке логирует её и возвращает fallback `Response`.

        ### Аргументы:
        :param response_id: id создаваемого ответа GPT
        :param request: GPT-запрос с моделью и списком messages для API

        :return: `Response` с текстом GPT и total tokens или fallback-ответом

        ### Пример использования:
        ```py
        gPT.send_request(response_id = response_id, request = request)
        ```
        """
        model: Model = request.model
        messages: list[dict[str, str]] = request.messages

        try:
            client: OpenAI = self._get_client(model)
            response = client.chat.completions.create(model = model.model, messages = messages)

            choices: object = getattr(response, "choices", None)
            if not choices:
                raise RuntimeError("GPT response has no choices")

            result = choices[0]
            message = getattr(result, "message", None)
            content: str = str(getattr(message, "content", None) or "").strip()
            if not content:
                raise RuntimeError("GPT response has empty content")

            usage = getattr(response, "usage", None)
            total_tokens: int = int(getattr(usage, "total_tokens", 0) or 0)
            return Response(response_id, request, total_tokens, content)
        except Exception as err:
            self._log_send_request_error(response_id, request, err)
            return self._fallback_response(response_id, request)


class Request(Element):

    """
    Описывает GPT-запрос `Request`: выбранную модель, system context, messages для API и рассчитанное число токенов.
    Объект сериализуется в storage вместе с id модели, id контекста, текстом контекста, messages и `tokens`.

    ### Поля
    - `model`: GPT-модель с `model`, `base_url` и token limits.
    - `context_id`: id `SystemContext`, из которого взят системный текст.
    - `context`: содержимое system context на момент создания запроса.
    - `messages`: список словарей `role/content`, отправляемых в GPT API.
    - `chatgpt_prefix_messages`: сообщения, добавляемые перед пользовательским batch.
    - `chatgpt_pending_user_batch`: накопленный пользовательский batch перед отправкой.
    - `chatgpt_suffix_messages`: сообщения, добавляемые после пользовательского batch.
    - `tokens`: локально рассчитанное число токенов или `None`, если подсчёт ещё не выполнен.

    ### Методы
    - `__init__`: Сохраняет модель, system context и messages без обращения к GPT API.
    - `set_chatgpt_batch`: Копирует prefix/pending/suffix messages в поля batch.
    - `get_chatgpt_batch_length`: Считает суммарную длину `content` в pending batch.
    - `dumps`: Возвращает JSON-совместимый снимок запроса.
    - `count_tokens`: Оценивает число токенов для `messages`.
    - `check_tokens`: Проверяет, что `tokens` уже является неотрицательным `int`.
    - `process_tokens`: Запускает подсчёт токенов в отдельном `Thread` и списывает их у пользователя.

    ### Жизненный цикл
    Создаётся перед обращением к GPT, сохраняется у пользователя как pending request и позже связывается с `Response`.

    ### Пример использования
    ```py
    request: Request
    ```
    """
    def __init__(self, request_id: int, model: Model, system_context: SystemContext, messages: list[dict[str, str]]):
        """
        Инициализирует GPT-запрос, сообщения батча и счётчик токенов без обращения к провайдеру.

        ### Аргументы:
        :param request_id: request id
        :param model: GPT-модель
        :param system_context: system context
        :param messages: сообщения или группы сообщений для обработки

        ### Пример использования:
        ```py
        request = Request(request_id = request_id, model = model, system_context = system_context, messages = messages)
        ```
        """
        super().__init__(request_id)
        self.model: Model = model
        self.context_id: int = system_context.id
        self.context: str = system_context.content
        self.messages: list[dict[str, str]] = list(messages)
        self.chatgpt_prefix_messages: list[dict[str, str]] = []
        self.chatgpt_pending_user_batch: list[dict[str, str]] = []
        self.chatgpt_suffix_messages: list[dict[str, str]] = []
        self.tokens: int | None = None

    def set_chatgpt_batch(self, prefix_messages: Iterable[dict[str, str]], pending_user_batch: Iterable[dict[str, str]], suffix_messages: Iterable[dict[str, str]]):
        """
        Копирует части GPT batch в `Request`.
        Метод заменяет текущие `chatgpt_prefix_messages`, `chatgpt_pending_user_batch` и `chatgpt_suffix_messages` новыми словарями.

        ### Аргументы:
        :param prefix_messages: сообщения перед пользовательским batch
        :param pending_user_batch: пользовательские сообщения, ожидающие отправки
        :param suffix_messages: сообщения после пользовательского batch

        ### Пример использования:
        ```py
        request.set_chatgpt_batch(prefix_messages = prefix_messages, pending_user_batch = pending_user_batch, suffix_messages = suffix_messages)
        ```
        """
        self.chatgpt_prefix_messages = [dict(message) for message in prefix_messages]
        self.chatgpt_pending_user_batch = [dict(message) for message in pending_user_batch]
        self.chatgpt_suffix_messages = [dict(message) for message in suffix_messages]

    def get_chatgpt_batch_length(self) -> int:
        """
        Считает суммарную длину поля `content` во всех сообщениях `chatgpt_pending_user_batch`.

        :return: количество символов в pending user batch

        ### Пример использования:
        ```py
        request.get_chatgpt_batch_length()
        ```
        """
        return sum(len(message.get("content", "")) for message in self.chatgpt_pending_user_batch)

    def __repr__(self) -> str:
        id = self.id
        context = self.context_id
        content = len(self.context)
        tokens = self.tokens

        try:
            model = self.model.model
        except Exception as err:
            model = err

        result: str = f"{self.__class__.__name__}({id=} {model=} {context=} length={content} {tokens=})["

        if self.messages:
            for message in self.messages:
                result += f"\n\t{repr(message)}"

            return f"{result}\n]"
        else:
            return f"{result}]"

    def dumps(self) -> BotTypes.REQUEST_TYPE:
        """
        Возвращает JSON-совместимый снимок объекта для storage или callback payload.

        :return: JSON-совместимый словарь для сохранения или передачи между слоями

        ### Пример использования:
        ```py
        request.dumps()
        ```
        """
        result: BotTypes.REQUEST_TYPE = super().dumps()

        result.update({
            "model": str(self.model.model),
            "context_id": int(self.context_id),
            "context": str(self.context),
            "messages": list(self.messages),
            "tokens": None if self.tokens is None else int(self.tokens)
        })

        return result

    def count_tokens(self) -> int:
        """
        Считает примерное число токенов для `self.messages` и выбранной GPT-модели.

        :return: оценка количества токенов запроса

        ### Пример использования:
        ```py
        request.count_tokens()
        ```
        """
        return count_tokens(self.messages, self.model)

    def check_tokens(self) -> bool:
        """
        Проверяет только локальное поле `self.tokens` после подсчёта токенов.
        Метод не сравнивает значение с `model.max_context`, балансом пользователя или другими лимитами; он принимает только неотрицательный `int`.

        :return: `True`, если `self.tokens` является `int` и не меньше нуля; иначе `False`

        ### Пример использования:
        ```py
        request.check_tokens()
        ```
        """
        return isinstance(self.tokens, int) and self.tokens >= 0

    def process_tokens(self, user: User):
        """
        Запускает фоновый подсчёт токенов для запроса.
        Внутренний поток вызывает `count_tokens`, затем при текущей логике, если `check_tokens()` вернул `False`, временно выставляет `self.tokens = -1`, списывает рассчитанные токены у пользователя через `user.debit_tokens(tokens)` и сохраняет число токенов в `self.tokens`.

        ### Аргументы:
        :param user: пользователь, с баланса которого списываются рассчитанные токены

        ### Пример использования:
        ```py
        request.process_tokens(user = user)
        ```
        """
        def process_tokens():
            tokens: int = self.count_tokens()

            if not self.check_tokens():
                self.tokens = -1
                user.debit_tokens(tokens)
                self.tokens = tokens

        id: int = self.id
        Thread(target = process_tokens, name = f"Request({id=}).process_tokens").start()


class Response(Element):

    """
    Описывает сохранённый ответ GPT на конкретный `Request`.
    Ответ хранит ссылку на запрос, текст content и количество токенов, полученное из API usage или fallback-логики.

    ### Поля
    - `request`: GPT-запрос, на который получен ответ.
    - `tokens`: total tokens ответа по данным API или `0` для fallback-ответа.
    - `content`: текст ответа, который будет сохранён в истории пользователя.

    ### Методы
    - `__init__`: Сохраняет id ответа, request, tokens и content.
    - `dumps`: Возвращает JSON-совместимый снимок ответа для storage.

    ### Жизненный цикл
    Создаётся после вызова GPT API или fallback-обработки ошибки и сохраняется в истории ответов пользователя.

    ### Пример использования
    ```py
    response: Response
    ```
    """
    def __init__(self, response_id: int, request: Request, tokens: int, content: str):
        """
        Инициализирует GPT-ответ с текстом, request id и количеством токенов.

        ### Аргументы:
        :param response_id: response id
        :param request: GPT-запрос
        :param tokens: количество токенов
        :param content: содержимое доменного элемента

        ### Пример использования:
        ```py
        response = Response(response_id = response_id, request = request, tokens = tokens, content = content)
        ```
        """
        super().__init__(response_id)
        self.request: Request = request
        self.tokens: int = tokens
        self.content: str = content

    def __repr__(self) -> str:
        id = self.id
        content = len(self.content)
        tokens = self.tokens

        try:
            request = self.request.id
        except Exception as err:
            request = err

        return f"{self.__class__.__name__}({id=} {request=} length={content} {tokens=})"

    def dumps(self) -> BotTypes.RESPONSE_TYPE:
        """
        Возвращает JSON-совместимый снимок объекта для storage или callback payload.

        :return: JSON-совместимый словарь для сохранения или передачи между слоями

        ### Пример использования:
        ```py
        response.dumps()
        ```
        """
        result: BotTypes.RESPONSE_TYPE = super().dumps()

        result.update({
            "request_id": int(self.request.id),
            "content": str(self.content),
            "tokens": int(self.tokens)
        })

        return result
