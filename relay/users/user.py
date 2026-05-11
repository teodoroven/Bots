"""
Описывает публичные классы `User`.
Модуль относится к архитектурной зоне: прикладной слой `relay`, который связывает пользователей, сессии, доменную модель, GPT, уведомления и runtime-логику приложения.

### Публичные классы
- `User`: доменная модель пользователя.

### Публичные функции
- Публичные функции отсутствуют.

### Связи
Используется app-layer сценариями, обработчиками, сессиями и runtime-миксинами для единого пользовательского потока между ботами, GPT и storage.
"""

from __future__ import annotations




from relay.common import (
    Any,
    BotTypes,
    Callable,
    Iterable,
    Literal,
    Never,
    abstractmethod,
    datetime,
    json,
)
from bots import Message
from bots import Telebot
from bots import Vkbot
from relay.config import (
    BOT_KEYS,
    BUTTON_LENGTH,
    MAX_ADMIN_SESSIONS,
    MAX_HISTORY,
    MAX_MESSAGES,
    MAX_REQUESTS,
    MAX_RESPONSES,
    MAX_USER_SESSIONS,
    get_phrase,
)
from relay.gpt import Request, Response
from relay.utils import (
    catch_json,
    catch_parsefiles,
    count_group_tokens,
    is_int,
    log_warn,
)
class User():
    """
    Структура для хранения данных о пользователе, включающая:
    ```
    self.id: int  # Уникальный идентификатор пользователя
    self.chat_ids: dict[str, set[int]]  # Идентификаторы пользователя в разных ботах (`chat_id` в `Vkbot` и `Telebot`), ключ это `bot_key`
    self.sessions: self.sessions: dict[Literal["", "Vkbot", "Telebot"], list[Session]]  # Сессии пользователя в порядке запуска, текущая сессия - последняя в списке
    self.messages: dict[BOT_KEY, list[Message]]  # Текущие сообщения в чате с пользователем. Хранятся для редактирования вместо отправки новых сообщений
    self.saved_messages: list[Message]  # Сообщения, отмеченные для предотвращения удаления в конце пользовательской сессии (не путать с `Session`, говорится о сессии в контексте работы программы с пользователем)
    self.usernames: dict[str, str]  # Пользовательское имя в разных ботах (в `Vkbot` и `Telebot`), ключ это `bot_key`
    self.history: list[dict[str, str | int | list[dict[str, str | int | dict | list[dict] | None]]]]  # История сообщений пользователя, ответов бота и администраторов, хранится для передачи администратору в случае его вызова
    self.access_level: int | None  # Уровень доступа пользователя, `1` - администратор, `2` - создатель
    self.storage_key: str  # Ключ записи пользователя в хранилище
    ```
    """
    DEFAULT_SINGLE_KEY: Literal["user_single"] = "user_single"
    USER_TYPE = BotTypes.USER_TYPE

    def load(self, autocenter: App, get_bot: Callable[[BOT_KEY], BOT]):
        """
        Восстанавливает состояние пользователя из storage и связывает его с текущим `App`.

        ### Аргументы:
        :param autocenter: экземпляр `App`, через который пользователь связан с runtime и storage
        :param get_bot: функция поиска транспортного бота по ключу

        :raises TypeError: если входная или сериализованная структура имеет неподдерживаемый формат

        ### Пример использования:
        ```py
        user.load(autocenter = autocenter, get_bot = get_bot)
        ```
        """
        self.create_message_id = autocenter.create_message_id
        self.app = autocenter

        data: "User.USER_TYPE" = autocenter.storage.load_user(self.id)

        self.sessions.clear()
        self.sessions["vkbot"] = []
        self.sessions["telebot"] = []

        self.messages.clear()
        self.messages["vkbot"] = []
        self.messages["telebot"] = []

        # with catch_parsefiles((self.storage_key,), "load_user"):
        #     self.access_level = int(data.get("access_level") or 0)

        # for client_id in data.get("clients", []):
        #     if not is_int(client_id):
        #         raise ValueError(f"Некорректное значение словаря под ключом {clients=}. Некорректный идентификатор {client_id=}")

        #     client: GPT.Client | None = autocenter.find_client(int(client_id))

        #     if not client:
        #         clients = data.get("clients")
        #         raise ValueError(f"Некорректное значение словаря под ключом {clients=}. Не найден клиент с идентификатором {client_id=}")

        #     self.add_client(client)

        # if not self.clients:
        #     client: GPT.Client = autocenter.create_client()
        #     self.add_client(client)

        self.history = self.dumps_history(data.get("history", []))

        self.usernames = self.dumps_names(data.get("usernames", {}))
        self.names = self.dumps_names(data.get("names", {}))

        with catch_parsefiles((self.storage_key,), "load_user_messages"):
            for bot_key, messages in data.get("messages", {}).items():
                for message_data in messages:
                    with catch_parsefiles((self.storage_key,), "load_user_messages"):
                        if message_data:
                            if type(message_data) is dict:
                                message: Message = Message.loads(message_data, get_bot)
                                self.messages[bot_key].append(message)
                            else:
                                raise TypeError(f"Ожидался {message_data=} типа dict, а получен {type(message_data)}")

        with catch_parsefiles((self.storage_key,), "load_saved_messages"):
            for message_id in data.get("saved_messages", []):
                with catch_parsefiles((self.storage_key,), "load_saved_messages"):
                    message: Message | None = self.find_message(message_id)

                    if message:
                        self.saved_messages.append(message)

        # self.print_messages()

        with catch_parsefiles((self.storage_key,), "load_session"):
            for bot_key, sessions in data.get("sessions", {}).items():
                for session_container in sessions:
                    with catch_parsefiles((self.storage_key,), "load_session"):
                        session_id, session_type, session_content, bot_key, message_id = session_container

                        session_data: BotTypes.UNKNOWN_JSON_OBJECT = {}

                        with catch_json((self.storage_key,)):
                            session_data = json.loads(session_content)

                        with catch_parsefiles((self.storage_key,), "load_session"):
                            session_class: type[Session] = autocenter.__class__.SESSIONS[session_type]
                            bot: BOT | None = get_bot(bot_key)

                            mes: Message | None = self.find_message(message_id)
                            message: Message = mes or self.get_message(bot_key)
                            session: Session = autocenter.create_session(int(session_id), session_class, Context(autocenter, bot, self, None, None), session_data or {}, message)

                            if not mes:
                                user = self
                                log_warn(f"Для сессии {session=} было создано новое сообщение {message=} так как сообщение с {message_id=} не найдено у пользователя {user=}")
                            # Сессия добавляется в user.sessions внутри конструктора session.__init__
                            # self.add_session(session)

        client_data: BotTypes.CLIENT_TYPE = data.get("client", {})
        client: Client = autocenter.load_client(client_data)
        client.update_limits(autocenter.user_client, autocenter.create_limit)
        self.clients.clear()
        self.clients.append(autocenter.shared_client)
        self.clients.append(client)

        self.save()

    def __init__(self, user_id: int, chat_ids: dict[str, set[int]], access_level: int):
        """
        Создаёт `User` и сохраняет app-layer ссылки, которые нужны обработчикам.

        ### Аргументы:
        :param user_id: внутренний идентификатор пользователя в app-layer
        :param chat_ids: существующее соответствие transport key и chat id; объект хранит ссылку на этот словарь
        :param access_level: уровень доступа пользователя или администратора

        :raises TypeError: если входная или сериализованная структура имеет неподдерживаемый формат

        ### Пример использования:
        ```py
        user: User = User(user_id = user_id, chat_ids = chat_ids, access_level = access_level)
        ```
        """
        self.id: int = int(user_id)
        self.chat_ids: dict[str, set[int]] = chat_ids  # ссылка
        self.sessions: dict[BotTypes.USER_BOT_KEY, list[Session]] = {
            "vkbot": [],
            "telebot": []
        }
        self.messages: dict[BOT_KEY, list[Message]] = {
            "vkbot": [],
            "telebot": []
        }
        self.usernames: dict[BOT_KEY, str] = {}
        self.names: dict[BOT_KEY, str] = {}
        self.saved_messages: list[Message] = []
        self.history: list["Message.MessagesGroup.GROUP_TYPE"] = []
        self.requests: dict[int, Request] = {}
        self.responses: dict[int, Response] = {}  # WARNING: int - это request.id, не response.id!
        self.clients: list[Client] = []
        self.access_level: int = int(access_level)
        self.app: App | None = None
        self.storage_key: str = f"user:{user_id}"

        if not isinstance(self.chat_ids, dict):
            raise TypeError(f"Некорректное значение аргумента {chat_ids=}")

        if self.chat_ids and not isinstance(self.chat_ids[tuple(self.chat_ids.keys())[0]], set):
            raise TypeError(f"Некорректное значение аргумента {chat_ids=}")

    def __repr__(self) -> str:
        id: int = self.id
        access_level: int = self.get_access_level()
        sessions: int = len(self.sessions)
        messages: int = len(self.messages)

        vkbot: list[int] = self.chat_ids.get(Vkbot.BOT_KEY, [])
        telebot: list[int] = self.chat_ids.get(Telebot.BOT_KEY, [])
        chat_ids: str = f"{vkbot=} {telebot=}"

        vkbot: list[int] = self.usernames.get(Vkbot.BOT_KEY)
        telebot: list[int] = self.usernames.get(Telebot.BOT_KEY)
        usernames: str = f"{vkbot=} {telebot=}"
        return f"User({id=} {access_level=} {sessions=} {messages=})[{chat_ids}]" + "{" + usernames + "}"

    def repr_messages(self) -> str:
        """
        Собирает строку с текущими сообщениями пользователя по transport key для логов.

        :return: результат выполнения операции

        ### Примеры вызова:
        ```py
        user.repr_messages()
        ```
        """
        log_info: list[str] = []

        for bot_key, messages in self.messages.items():
            log_info.append(f"{bot_key=} ({len(messages)}) {messages=}")

        return "\n".join(log_info)

    def repr_sessions(self) -> str:
        """
        Собирает строку с активными сессиями пользователя по transport key для логов.

        :return: результат выполнения операции

        ### Примеры вызова:
        ```py
        user.repr_sessions()
        ```
        """
        log_info: list[str] = []

        for bot_key, sessions in self.sessions.items():
            log_info.append(f"{bot_key=} ({len(sessions)}) {sessions=}")

        return "\n".join(log_info)

    def repr_requests(self) -> str:
        """
        Собирает строку с сохранёнными GPT-запросами пользователя для логов.

        :return: результат выполнения операции

        ### Примеры вызова:
        ```py
        user.repr_requests()
        ```
        """
        log_info: list[str] = []

        for request in self.requests:
            log_info.append(f"{request=}")

        return "\n".join(log_info)

    def repr_responses(self) -> str:
        """
        Собирает строку с сохранёнными GPT-ответами пользователя для логов.

        :return: результат выполнения операции

        ### Примеры вызова:
        ```py
        user.repr_responses()
        ```
        """
        log_info: list[str] = []

        for response in self.responses:
            log_info.append(f"{response=}")

        return "\n".join(log_info)

    def dumps_names(self, names: dict[str, str]) -> BotTypes.USER_NAMES_TYPE:
        """
        Нормализует names к JSON-совместимому виду storage/API.

        ### Аргументы:
        :param names: имена пользователя по transport key из storage или transport-layer

        :return: JSON-совместимое представление для names

        ### Пример использования:
        ```py
        user.dumps_names(names = names)
        ```
        """
        result: BotTypes.USER_NAMES_TYPE = {}

        for bot_key, name in names.items():
            if bot_key in ("vkbot", "telebot"):
                result[bot_key] = str(name)

        return result

    def dumps_history(self, history: Iterable[BotTypes.MESSAGE_GROUP_TYPE]) -> list[BotTypes.MESSAGE_GROUP_TYPE]:
        """
        Фильтрует историю сообщений и оставляет только JSON-совместимые словари, пригодные для storage.

        ### Аргументы:
        :param history: сериализованные группы сообщений пользователя

        :return: история без несериализуемых и пустых элементов

        ### Пример использования:
        ```py
        user.dumps_history(history = history)
        ```
        """
        return [group for group in history if isinstance(group, dict)]

    def dumps(self) -> USER_TYPE:
        """
        Возвращает JSON-совместимый снимок объекта для storage или callback payload.

        :return: JSON-совместимый словарь для сохранения или передачи между слоями

        ### Пример использования:
        ```py
        user.dumps()
        ```
        """
        sessions: BotTypes.SESSION_STORAGE_TYPE = {
            bot_key: [
                [
                    int(session.id),
                    session.__class__.__name__,
                    session.stringify(),
                    session.bot.get_bot_key(),
                    int(session.get_message().id)
                ] for session in sessions
            ] for bot_key, sessions in self.sessions.items()
        }
        messages: BotTypes.USER_MESSAGES_TYPE = {
            bot_key: [
                message.dumps() for message in messages
            ] for bot_key, messages in self.messages.items()
        }

        return {
            "access_level": int(self.access_level or 0),
            "sessions": sessions,
            "messages": messages,
            "usernames": self.dumps_names(self.usernames),
            "names": self.dumps_names(self.names),
            "saved_messages": [int(message.id) for message in self.saved_messages],
            "client": self.get_client().dumps(),
            "history": self.dumps_history(self.history),
            "requests": [request.dumps() for request in self.requests.values()],
            "responses": [response.dumps() for response in self.responses.values()]
        }

    def save(self):
        """
        Записывает текущее JSON-представление через storage API.

        :raises RuntimeError: если объект ещё не связан с необходимым runtime-состоянием

        ### Пример использования:
        ```py
        user.save()
        ```
        """
        if self.app is None:
            raise RuntimeError(f"Сначала вызовите метод load у пользователя {self.id=}")

        self.app.storage.save_user(self.id, self.dumps(), self.access_level)

    def set_username(self, bot_key: BOT_KEY, username: str):
        """
        Проверяет и сохраняет имя пользователя в объекте.

        ### Аргументы:
        :param bot_key: ключ транспорта
        :param username: имя пользователя

        ### Пример использования:
        ```py
        user.set_username(bot_key = bot_key, username = username)
        ```
        """
        self.usernames[bot_key] = username
        self.save()

    def set_name(self, bot_key: BOT_KEY, name: str):
        """
        Проверяет и сохраняет служебное имя в состоянии `User`.

        ### Аргументы:
        :param bot_key: ключ транспорта, например `vkbot` или `telebot`
        :param name: служебное имя бота, элемента, команды или настройки

        ### Пример использования:
        ```py
        user.set_name(bot_key = bot_key, name = name)
        ```
        """
        self.names[bot_key] = name
        self.save()

    @abstractmethod
    def create_message_id(self) -> int:
        """
        Создаёт message id и связывает результат с текущим app-layer состоянием.

        :return: созданный объект для message id

        :raises RuntimeError: если объект ещё не связан с необходимым runtime-состоянием

        ### Примеры вызова:
        ```py
        user.create_message_id()
        ```
        """
        raise RuntimeError(f"Сначала вызовите метод load у пользователя {self.id=}")

    def get_access_level(self) -> int:
        """
        Возвращает сохранённый уровень доступа.

        :return: уровень доступа пользователя

        :raises RuntimeError: если объект ещё не связан с необходимым runtime-состоянием

        ### Пример использования:
        ```py
        user.get_access_level()
        ```
        """
        if self.app is None:
            if self.access_level is None:
                raise RuntimeError(f"Сначала вызовите метод load у пользователя {self.id=}")
            return int(self.access_level)

        access_level: int = self.app.get_access_level(self.id)
        self.access_level = access_level
        return access_level

    def set_access_level(self, access_level: int):
        """
        Проверяет и сохраняет значение `access level` в `User`.

        ### Аргументы:
        :param access_level: уровень доступа пользователя или администратора

        :raises RuntimeError: если объект ещё не связан с необходимым runtime-состоянием

        ### Пример использования:
        ```py
        user.set_access_level(access_level = access_level)
        ```
        """
        if self.app is None:
            raise RuntimeError(f"Сначала вызовите метод load у пользователя {self.id=}")

        self.app.set_access_level(self.id, access_level, actor_id = self.id)

    def check_access_level(self, access_level: int) -> bool:
        """
        Проверяет, достаточен ли уровень доступа пользователя.

        ### Аргументы:
        :param access_level: уровень доступа

        :return: `True`, если уровень пользователя не ниже `access_level`; иначе `False`

        ### Пример использования:
        ```py
        user.check_access_level(access_level = access_level)
        ```
        """
        return self.get_access_level() >= int(access_level)

    def get_bot_keys(self) -> list[BOT_KEY]:
        """
        Возвращает transport keys, которые лучше подходят для ответа пользователю.
        Выбор повторяет старую логику приоритета: если активная сессия есть
        только в одном транспорте, берётся он; иначе используется транспорт
        последнего сообщения; если сообщений нет, возвращаются транспорты, где
        у пользователя сохранены `chat_id`.

        :return: список transport keys пользователя

        ### Пример использования:
        ```py
        user.get_bot_keys()
        ```
        """
        last_sessions: dict[BOT_KEY, list[Session]] = {}

        for bot_key, sessions in self.sessions.items():
            if sessions:
                last_sessions[bot_key] = sessions[-1]

        if len(last_sessions) == 1:
            return [tuple(last_sessions.keys())[0]]

        last_messages: dict[BOT_KEY, list[Message]] = {}

        for bot_key, messages in self.messages.items():
            if messages:
                last_messages[bot_key] = messages[-1]

        if len(last_messages) == 1:
            return [tuple(last_messages.keys())[0]]
        elif last_messages:
            result: list[BOT_KEY] = []

            for bot_key, messages in last_messages.items():
                result.append(bot_key)

            if result:
                return result

        return list(self.chat_ids.keys())

    def has_answer_identity(self, bot_key: BOT_KEY) -> bool:
        """
        Проверяет, есть ли отображаемое имя для ответа через выбранный транспорт.
        Имя считается найденным, если сохранён `name` или `username`.

        ### Аргументы:
        :param bot_key: ключ транспорта

        :return: `True`, если у пользователя есть `name` или `username` в транспорте; иначе `False`

        ### Пример использования:
        ```py
        user.has_answer_identity(bot_key = bot_key)
        ```
        """
        return bool(self.get_name(bot_key) or self.get_username(bot_key))

    def get_answer_bot_key(self, bot_key: BOT_KEY | None = None) -> BOT_KEY:
        """
        Выбирает transport key, через который лучше показывать пользователя в ответе.
        Явно переданный `bot_key` используется как стартовый вариант. Если у
        пользователя несколько транспортов и выбранный транспорт не содержит
        имени, но `telebot` содержит `name` или `username`, метод переключается
        на `telebot`. Если данных о транспортах нет, fallback остаётся `telebot`.

        ### Аргументы:
        :param bot_key: предпочтительный ключ транспорта

        :return: transport key для ответа пользователю

        ### Пример использования:
        ```py
        user.get_answer_bot_key(bot_key = bot_key)
        ```
        """
        bot_keys: list[BOT_KEY] = self.get_bot_keys()
        answer_bot_key: BOT_KEY = bot_key if bot_key else bot_keys[0] if bot_keys else "telebot"

        if len(bot_keys) > 1 and answer_bot_key != "telebot" and "telebot" in bot_keys:
            if not self.has_answer_identity(answer_bot_key) and self.has_answer_identity("telebot"):
                answer_bot_key = "telebot"

        return answer_bot_key

    def get_display_answer(self, bot_key: BOT_KEY | None = None, cut_string: bool = True) -> str:
        """
        Возвращает строку для отображения пользователя в меню.
        Если передан `bot_key`, добавляет chat id этого транспорта; при `cut_string=True` сокращает строку до длины кнопки.

        ### Аргументы:
        :param bot_key: transport key, chat id которого нужно добавить в подпись
        :param cut_string: нужно ли сокращать строку до длины кнопки

        :return: отображаемое имя пользователя с id и, при наличии, chat id

        ### Пример использования:
        ```py
        user.get_display_answer(bot_key = bot_key, cut_string = cut_string)
        ```
        """
        answer_bot_key: BOT_KEY = self.get_answer_bot_key(bot_key)
        return self.get_answer(answer_bot_key, cut_string = cut_string)


    def get_chat_id(self, bot_key: BOT_KEY) -> int:
        """
        Возвращает сохранённый chat id.

        ### Аргументы:
        :param bot_key: ключ транспорта

        :return: идентификатор чата

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        :raises Exception: если нижележащий слой сообщает об ошибке операции

        ### Пример использования:
        ```py
        user.get_chat_id(bot_key = bot_key)
        ```
        """
        chat_ids: set[int] = self.chat_ids.get(bot_key, tuple())

        if chat_ids:
            return tuple(chat_ids)[0]
        elif bot_key not in BOT_KEYS:
            raise ValueError(f"Некорректное значение аргумента {bot_key=}")
        else:
            raise Exception(f"{self} не имеет chat_id в боте {bot_key=}")

    def find_chat_id(self, bot_key: BOT_KEY) -> int | None:
        """
        Ищет chat id по данным, которые пришли из вызывающего слоя.

        ### Аргументы:
        :param bot_key: ключ транспорта, например `vkbot` или `telebot`

        :return: найденное значение для chat id или None, если записи нет

        :raises ValueError: если значение не проходит локальную проверку перед сохранением

        ### Пример использования:
        ```py
        user.find_chat_id(bot_key = bot_key)
        ```
        """
        chat_ids: set[int] = self.chat_ids.get(bot_key, -1)

        if is_int(chat_ids):
            return int(chat_ids)
        elif chat_ids:
            return tuple(chat_ids)[0]
        elif bot_key not in BOT_KEYS:
            raise ValueError(f"Некорректное значение аргумента {bot_key=}")
        else:
            return None

    def get_username(self, bot_key: BOT_KEY | Any) -> str | Literal[""]:
        """
        Возвращает сохранённое имя пользователя.

        ### Аргументы:
        :param bot_key: ключ транспорта

        :return: имя пользователя в транспорте

        ### Пример использования:
        ```py
        user.get_username(bot_key = bot_key)
        ```
        """
        if bot_key is Any:
            for bot_key, username in self.usernames.items():
                if username:
                    return username

            return ""
        else:
            return self.usernames.get(bot_key, "")

    def get_name(self, bot_key: BOT_KEY | Any) -> str | Literal[""]:
        """
        Возвращает сохранённое имя.

        ### Аргументы:
        :param bot_key: ключ транспорта

        :return: служебное имя

        ### Пример использования:
        ```py
        user.get_name(bot_key = bot_key)
        ```
        """
        if bot_key is Any:
            for bot_key, name in self.names.items():
                if name:
                    return name

            return ""
        else:
            return self.names.get(bot_key, "")


    def stop(self, delete_messages: bool = True):
        """
        Завершает все активные сессии пользователя и при необходимости удаляет несохранённые сообщения.
        Метод меняет user state: очищает списки сессий и может удалить wrapper-сообщения через transport API.

        ### Аргументы:
        :param delete_messages: нужно ли удалять несохранённые сообщения активных сессий

        ### Пример использования:
        ```py
        user.stop(delete_messages = delete_messages)
        ```
        """
        for bot_key, sessions in self.sessions.items():
            for session in sessions:
                session.finish()
                self.finish_session(bot_key, session)

        if delete_messages:
            for bot_key, messages in self.messages.items():
                for message in messages:
                    if not self.check_saved(message):
                        message.delete()

    def is_last_message(self, bot_key: BOT_KEY, message: Message) -> bool:
        """
        Проверяет, стоит ли wrapper-сообщение последним в списке сообщений транспорта.
        Метод не меняет состояние пользователя; если сообщение отсутствует в
        списке `self.messages[bot_key]`, ошибка не скрывается и вызывается
        `RuntimeError`.

        ### Аргументы:
        :param bot_key: ключ транспорта
        :param message: сообщение проекта или сообщение конкретного транспорта

        :return: `True`, если сообщение найдено последним; иначе `False`

        :raises RuntimeError: если объект ещё не связан с необходимым runtime-состоянием

        ### Пример использования:
        ```py
        user.is_last_message(bot_key = bot_key, message = message)
        ```
        """
        messages: list[Message] = self.messages[bot_key]

        if message in messages:
            return messages.index(message) + 1 == len(messages)
        else:
            raise RuntimeError(f"Проверяемое сообщение отсутствует в списке {bot_key=} {self.messages[bot_key]}\n{message=}")

    def make_last(self, bot_key: BOT_KEY, message: Message):
        """
        Переносит wrapper-сообщение в конец списка сообщений пользователя и инициирует обновление или переотправку UI.

        ### Аргументы:
        :param bot_key: transport key, в списке которого находится сообщение
        :param message: wrapper-сообщение, которое нужно сделать последним

        ### Пример использования:
        ```py
        user.make_last(bot_key = bot_key, message = message)
        ```
        """
        self.messages[bot_key].remove(message)
        self.messages[bot_key].append(message)
        message.edit(force_resend = True)

    def index_session(self, bot_key: BOT_KEY, session: Session) -> int | None:
        """
        Ищет индекс сессии по `session.id` в списке сессий указанного транспорта.

        ### Аргументы:
        :param bot_key: transport key, в котором нужно искать сессию
        :param session: сессия с искомым идентификатором

        :return: индекс сессии или `None`, если сессия не найдена

        ### Пример использования:
        ```py
        user.index_session(bot_key = bot_key, session = session)
        ```
        """
        for i, elem in enumerate(self.sessions[bot_key]):
            if elem.id == session.id:
                return i
        return None

    def index_message(self, bot_key: BOT_KEY, message: Message) -> int | None:
        """
        Ищет индекс wrapper-сообщения по `message.id` в списке сообщений указанного транспорта.

        ### Аргументы:
        :param bot_key: transport key, в котором нужно искать сообщение
        :param message: wrapper-сообщение с искомым идентификатором

        :return: индекс сообщения или `None`, если сообщение не найдено

        ### Пример использования:
        ```py
        user.index_message(bot_key = bot_key, message = message)
        ```
        """
        for i, elem in enumerate(self.messages[bot_key]):
            if elem.id == message.id:
                return i
        return None

    def make_current(self, bot_key: BOT_KEY, session_class: type[Session]):
        """
        Перемещает сообщение выбранной сессии в конец истории сообщений пользователя.

        ### Аргументы:
        :param bot_key: ключ транспорта
        :param session_class: класс сессии, сообщение которой нужно сделать текущим

        :raises RuntimeError: если объект ещё не связан с необходимым runtime-состоянием

        ### Пример использования:
        ```py
        user.make_current(bot_key = bot_key, session_class = session_class)
        ```
        """
        sessions_list: list[Session] = self.sessions[bot_key]
        messages_list: list[Message] = self.messages[bot_key]

        session: Session | None = self.find_session(bot_key, session_class)

        if session is None:
            user = self
            raise RuntimeError(f"{user=} {session=} {bot_key=} {session_class=} {sessions_list=}")

        message: Message = session.get_message()

        session_index: int | None = self.index_session(bot_key, session)
        message_index: int | None = self.index_message(bot_key, message)

        if session_index is None:
            user = self
            raise RuntimeError(f"{user=} {session=} {bot_key=} {session_index=} {sessions_list=}")

        if message_index is None:
            user = self
            raise RuntimeError(f"{user=} {session=} {bot_key=} {message_index=} {messages_list=}")

        if session_index != len(sessions_list) - 1:
            sessions_list.append(sessions_list.pop(session_index))

        if message_index != len(messages_list) - 1:
            messages_list.append(messages_list.pop(message_index))


    def create_message(self, bot_key: BOT_KEY) -> Message:
        """
        Создаёт wrapper-сообщение и связывает результат с текущим app-layer состоянием.

        ### Аргументы:
        :param bot_key: ключ транспорта, например `vkbot` или `telebot`

        :return: созданный объект для wrapper-сообщение

        ### Пример использования:
        ```py
        user.create_message(bot_key = bot_key)
        ```
        """
        message_id: int = self.create_message_id()
        message: Message = Message(message_id)
        self.messages[bot_key].append(message)

        # WARNING:
        while len(self.messages[bot_key]) > MAX_MESSAGES:
            self.messages[bot_key].pop(0)
            # logger.error("User.create_message pop!")

        return message

    def delete_message(self, bot_key: BOT_KEY, message: Message):
        """
        Удаляет wrapper-сообщение из внутреннего состояния или storage.

        ### Аргументы:
        :param bot_key: ключ транспорта, например `vkbot` или `telebot`
        :param message: wrapper-сообщение, которое можно отправить, обновить или сохранить

        ### Пример использования:
        ```py
        user.delete_message(bot_key = bot_key, message = message)
        ```
        """
        if message in self.messages[bot_key]:
            self.messages[bot_key].remove(message)

            if not self.check_saved(message):
                message.delete()

    def set_saved(self, message: Message, save: bool):
        """
        Проверяет и сохраняет значение `saved` в `User`.

        ### Аргументы:
        :param message: wrapper-сообщение, которое можно отправить, обновить или сохранить
        :param save: нужно ли сразу сохранить состояние пользователя после изменения

        ### Пример использования:
        ```py
        user.set_saved(message = message, save = save)
        ```
        """
        if save:
            if message not in self.saved_messages:
                self.saved_messages.append(message)

            # WARNING:
            while len(self.saved_messages) > MAX_MESSAGES:
                self.saved_messages.pop(0)
                # logger.error("User.set_saved pop!")
        else:
            if message in self.saved_messages:
                self.saved_messages.remove(message)

    def check_saved(self, message: Message) -> bool:
        """
        Проверяет значение `saved` перед сохранением или использованием.

        ### Аргументы:
        :param message: сообщение проекта или сообщение конкретного транспорта

        :return: `True`, если значение `saved` перед сохранением или использованием; иначе `False`

        ### Пример использования:
        ```py
        user.check_saved(message = message)
        ```
        """
        return message in self.saved_messages

    def find_message(self, message_id: int) -> Message | None:
        """
        Ищет message в текущих данных объекта или storage.

        ### Аргументы:
        :param message_id: идентификатор сообщения

        :return: message или None, если подходящей записи нет

        ### Пример использования:
        ```py
        user.find_message(message_id = message_id)
        ```
        """
        for bot_key, messages in self.messages.items():
            for message in messages:
                if message.id == message_id:
                    return message

        return None

    def find_group(self, get_bot: Callable, message_id: int, event: Bot.Event | None = None, text: str = "", date: datetime | None = None) -> Message.MessagesGroup | None:
        """
        Ищет group в текущих данных объекта или storage.

        ### Аргументы:
        :param get_bot: get bot
        :param message_id: идентификатор сообщения
        :param event: transport-событие для обработки
        :param text: текст
        :param date: время сообщения или события

        :return: group или None, если подходящей записи нет

        ### Пример использования:
        ```py
        user.find_group(get_bot = get_bot, message_id = message_id, event = event, text = text, date = date)
        ```
        """
        results: dict[Bot.Message, Message.MessagesGroup] = {}

        for group in self.get_last_messages(get_bot):
            for message in group.messages:
                if event is not None and event in message.events[message.__class__.CREATE_KEY]:
                    return group
                elif message.get_id() == message_id:
                    if message_id is None or message_id < 0:
                        results[message] = group
                    else:
                        return group

        for message, group in results.items():
            if message.get_text() == text:
                if date is None or date == message.get_date(message.__class__.CREATE_KEY) or not message.get_date(message.__class__.CREATE_KEY):
                    return group

        return None

    def find_session(self, bot_key: BOT_KEY, session_class: type[Session]) -> Session | None:
        """
        Ищет пользовательскую сессию по данным, которые пришли из вызывающего слоя.

        ### Аргументы:
        :param bot_key: ключ транспорта, например `vkbot` или `telebot`
        :param session_class: класс сессии, который нужно найти, создать или обновить

        :return: найденное значение для пользовательскую сессию или None, если записи нет

        ### Пример использования:
        ```py
        user.find_session(bot_key = bot_key, session_class = session_class)
        ```
        """
        for session in reversed(self.sessions[bot_key]):
            if isinstance(session, session_class):
                return session
        return None

    def find_conv_session(self, bot_key: BOT_KEY, conv_id: int | Any = Any) -> ConvSession | None:
        """
        Ищет conv session по данным, которые пришли из вызывающего слоя.

        ### Аргументы:
        :param bot_key: ключ транспорта, например `vkbot` или `telebot`
        :param conv_id: идентификатор сохранённого диалога

        :return: найденное значение для conv session или None, если записи нет

        ### Пример использования:
        ```py
        user.find_conv_session(bot_key = bot_key, conv_id = conv_id)
        ```
        """
        for session in reversed(self.sessions[bot_key]):
            if isinstance(session, ConvSession):
                if conv_id is Any or session.conv_id == conv_id:
                    return session
        return None

    def get_conv_list(self, bot_key: BOT_KEY) -> list[int]:
        """
        Возвращает список активных conversation-сессий пользователя.

        ### Аргументы:
        :param bot_key: ключ транспорта

        :return: conv list

        ### Пример использования:
        ```py
        user.get_conv_list(bot_key = bot_key)
        ```
        """
        conv_list: list[int] = []

        for session in reversed(self.sessions[bot_key]):
            if isinstance(session, ConvSession):
                conv_list.append(session.conv_id)

        return conv_list

    def check_joined(self, bot_key: BOT_KEY, conv_id: int):
        """
        Проверяет значение `joined` перед сохранением или использованием.

        ### Аргументы:
        :param bot_key: ключ транспорта
        :param conv_id: conv id

        :return: `True`, если значение `joined` перед сохранением или использованием; иначе `False`

        ### Пример использования:
        ```py
        user.check_joined(bot_key = bot_key, conv_id = conv_id)
        ```
        """
        return conv_id in self.get_conv_list(bot_key)

    def add_history(self, data: "Message.MessagesGroup.GROUP_TYPE"):
        """
        Добавляет сериализованные сообщения в историю пользователя.

        ### Аргументы:
        :param data: JSON-совместимые данные для соответствующего repository

        :raises ValueError: если значение не проходит локальную проверку перед сохранением

        ### Пример использования:
        ```py
        user.add_history(data = data)
        ```
        """
        if isinstance(data, dict):
            self.history.append(data)

            # WARNING:
            while len(self.history) > MAX_HISTORY:
                self.history.pop(0)
                # logger.error("User.add_history pop!")
        else:
            raise ValueError(f"Некорректное значение аргумента {data=}")

    def add_message(self, bot_key: BOT_KEY, bot_name: str, message: Message):
        """
        Добавляет wrapper-сообщение в список сообщений пользователя.

        ### Аргументы:
        :param bot_key: ключ транспорта
        :param bot_name: имя transport-бота из конфигурации
        :param message: сообщение проекта или сообщение конкретного транспорта

        ### Пример использования:
        ```py
        user.add_message(bot_key = bot_key, bot_name = bot_name, message = message)
        ```
        """
        chat_id: int = self.get_chat_id(bot_key)
        group: Message.MessagesGroup = message.get_last_group(bot_key, chat_id)
        group.username = bot_name
        data: "Message.MessagesGroup.GROUP_TYPE" = group.dumps()
        self.add_history(data)

    def add_event(self, bot: BOT, event: Bot.Event):
        """
        Добавляет transport-событие в историю пользователя.

        ### Аргументы:
        :param bot: transport-адаптер
        :param event: transport-событие для обработки

        ### Пример использования:
        ```py
        user.add_event(bot = bot, event = event)
        ```
        """
        bot_key: BOT_KEY = bot.get_bot_key()
        chat_id: int = self.get_chat_id(bot_key)
        owner_id: int = chat_id
        messages: list[Bot.Message] = [bot.__class__.Message.from_event(event, bot.bot)]

        message_id: int | None = messages[0].get_id()
        if message_id is not None:
            messages[0].add_event(event, event.get_date(), Bot.Message.SENT_KEY)

        group: Message.MessagesGroup = Message.MessagesGroup(bot, chat_id, owner_id, messages, event.get_username(), datetime.now())
        data: "Message.MessagesGroup.GROUP_TYPE" = group.dumps()
        self.add_history(data)


    def check_back(self, bot_key: BOT_KEY) -> Callable | None:
        """
        Проверяет значение `back` перед сохранением или использованием.

        ### Аргументы:
        :param bot_key: ключ транспорта

        :return: `True`, если значение `back` перед сохранением или использованием; иначе `False`

        ### Пример использования:
        ```py
        user.check_back(bot_key = bot_key)
        ```
        """
        return len(self.sessions[bot_key]) > 1

    def get_back(self, session_id: int) -> bool:
        """
        Проверяет, можно ли показать кнопку возврата для указанной сессии.

        ### Аргументы:
        :param session_id: идентификатор сессии

        :return: `True`, если у bot-стека сессии есть предыдущий экран

        ### Пример использования:
        ```py
        user.get_back(session_id = session_id)
        ```
        """
        bot_keys: list[BOT_KEY] = []

        for bot_key, sessions in self.sessions.items():
            for session in sessions:
                if session.id == session_id:
                    bot_keys.append(bot_key)

        if len(bot_keys) > 0:
            return any(self.check_back(bot_key) for bot_key in bot_keys)
        else:
            user = self
            log_warn(f"Указанный аргумент {session_id=} не соответствует ни одной сессии пользователя {user=}")
            return False

    def get_last_messages(self, get_bot: Callable, bot_key_filter: Iterable[str] | tuple[Never] = (Vkbot.BOT_KEY, Telebot.BOT_KEY), quantity: int = None) -> list[Message.MessagesGroup]:
        """
        Возвращает последние элементы из истории сообщений с ботом.
        - Сообщения в историю добавляются через методы `User.add_event` и `User.add_message`.
        - Сообщения возвращаются в порядке от старых к новым.

        :param get_bot: Функция `App.get_bot`, которая принимает `bot_key: str` и возвращает `BOT`.
        :param bot_key_filter: Если пуст, то вернёт сообщения с любым ботом, иначе только те, `bot_key` которых содержится в переданном аргументе (по умолчанию - все).
        :return: Список из групп сообщений, каждая из которых содержит сообщение в виде на момент отправки.
        """
        if quantity is None:
            quantity = len(self.history)

        quantity = min(quantity, len(self.history))
        quantity = max(quantity, 0)
        result: list[Message.MessagesGroup] = []

        for i in range(len(self.history) - 1, len(self.history) - quantity - 1, -1):
            data: "Message.MessagesGroup.GROUP_TYPE" = self.history[i]
            bot_key: BOT_KEY = data["bot_key"]

            if bot_key in bot_key_filter or not bot_key_filter:
                bot: BOT = get_bot(bot_key)
                group: Message.MessagesGroup = Message.MessagesGroup.loads(data, bot)
                result.append(group)

        return result[::-1]

    def get_last_conversation(self,  get_bot: Callable, bot_key: BOT_KEY, max_from_one: int = 5) -> list[Message.MessagesGroup]:
        """
        Возвращает последний диалог пользователя с ботом, стремясь включить сообщения от обеих сторон.
        - Функция будет включать последние сообщения в результат пока не найдёт сообщения от второго отправителя или пока количество сообщений от одного не достигнет `max_from_one`.
        - Сообщения возвращаются в порядке от старых к новым.

        :param get_bot: Функция `App.get_bot`, которая принимает `bot_key: str` и возвращает `BOT`.
        :param bot_key_filter: Если пуст, то вернёт сообщения с любым ботом, иначе только те, `bot_key` которых содержится в переданном аргументе (по умолчанию - все).
        :param max_from_one: Максимальное количество сообщений от одного отправителя подряд (по умолчанию - `5`).
        :return: Список из групп сообщений, каждая из которых содержит сообщение в виде на момент отправки.
        """
        history: list[Message.MessagesGroup] = self.get_last_messages(get_bot, (bot_key,))
        groups: list[Message.MessagesGroup] = []
        groups_changes: int = 0

        if history:
            for i in range(len(history) - 1, max(len(history) - max_from_one - 1, -1), -1):
                group: Message.MessagesGroup = history[i]

                if groups:
                    if group.owner_id != groups[-1].owner_id:
                        groups_changes += 1
                    elif len(groups) >= max_from_one:
                        return groups[::-1]

                if groups_changes > 3:
                    return (groups + [group])[::-1]
                else:
                    groups.append(group)

        return groups[::-1]


    def get_message(self, bot_key: BOT_KEY) -> Message:
        """
        Возвращает последнее сообщение от бота из истории сообщений с пользователем (сообщение, где `owner_id` это бот).
        - Если сообщений нет, то создаёт пустое.
        - Метод используется для редактирования предыдущих сообщений вместо отправки новых.

        :return: Сообщение из чата с пользователем.
        """
        if bot_key in self.messages:
            if self.messages[bot_key]:
                return self.messages[bot_key][-1]
        elif bot_key not in BOT_KEYS:
            raise ValueError(f"Некорректное значение аргумента {bot_key=}")
        else:
            KeyError(f"Некорректное значение атрибута {self.messages=}. Ключ {bot_key=} отсутствует в словаре")

        return self.create_message(bot_key)

    def session_message(self, bot_key: BOT_KEY) -> Message:
        """
        Создаёт wrapper-сообщение для новой сессии выбранного транспорта.

        ### Аргументы:
        :param bot_key: ключ транспорта

        :return: новое wrapper-сообщение для сессии

        ### Пример использования:
        ```py
        user.session_message(bot_key = bot_key)
        ```
        """
        return self.create_message(bot_key)
        match bot_key:
            case "vkbot":
                return self.create_message(bot_key)
            case "telebot":
                return self.get_message(bot_key)

    def start_session(self, session_class: type[Session], context: Context, data: dict | None = None, process_context: bool = True, message: Message | None = None) -> Session:
        """
        Запускает сценарий обработки и подготавливает первое сообщение или задачу.

        ### Аргументы:
        :param session_class: session class
        :param context: контекст обработки события
        :param data: сериализованный словарь
        :param process_context: context, который нужно передать в обработку сессии
        :param message: сообщение проекта или сообщение конкретного транспорта

        :return: результат выполнения операции

        ### Пример использования:
        ```py
        user.start_session(session_class = session_class, context = context, data = data, process_context = process_context, message = message)
        ```
        """
        if data is None:
            data = {}

        bot_key: BOT_KEY = context.bot.get_bot_key()
        self.validate_sessions(bot_key, session_class)

        if self.find_session(bot_key, session_class):
            user = self
            log_warn(f"{user=} start_session {bot_key=} {session_class=} уже имеет сессию: {user.sessions=}")

        if not message:
            message = self.session_message(bot_key)

        session: Session = context.autocenter.new_session(session_class, context, data, message)

        # process
        if process_context:
            session.process(context)

        if session.check_finished():
            self.finish_session(bot_key, session)
        # else:
            # Сессия добавляется в user.sessions внутри конструктора session.__init__
            # self.add_session(session)

        self.save()
        return session

    def go_session(self, session_class: type[Session], context: Context, data: dict | None = None, message: Message | None = None) -> Session:
        """
        Завершает текущую активную сессию пользователя и запускает новую.

        ### Аргументы:
        :param session_class: класс сессии, которую нужно запустить
        :param context: контекст обработки события
        :param data: сериализованный словарь
        :param message: сообщение проекта или сообщение конкретного транспорта

        :return: созданная сессия

        ### Пример использования:
        ```py
        user.go_session(session_class = session_class, context = context, data = data, message = message)
        ```
        """
        user: User = context.user
        bot_key: BOT_KEY = context.bot.get_bot_key()
        session: Session | None = self.find_session(bot_key, session_class)

        if session:
            session.update_data(data or {})
            session.reset()
            session.update()
        else:
            session = self.start_session(session_class, context, data or {}, process_context = False, message = message)
            session.update()

        user.save()
        return session

    def validate_sessions(self, bot_key: BOT_KEY, session_class: type[Session] | None = None) -> Session | None:
        """
        Проверяет значение перед переходом к следующему шагу сценария.

        ### Аргументы:
        :param bot_key: ключ транспорта
        :param session_class: session class

        :return: результат выполнения операции

        ### Пример использования:
        ```py
        user.validate_sessions(bot_key = bot_key, session_class = session_class)
        ```
        """
        max_sessions: int = MAX_ADMIN_SESSIONS if self.get_access_level() > 0 else MAX_USER_SESSIONS

        def finish_sessions(session_class: type[Session]):
            session: Session | None = self.find_session(bot_key, session_class)

            while session:
                # logger.warning(f"finish session {session_class} {session=}")
                session.finish()
                self.finish_session(bot_key, session)
                session = self.find_session(bot_key, session_class)

        if session_class is not NoHandlersSession:
            finish_sessions(NoHandlersSession)

        if session_class is ConvSession:
            finish_sessions(ConvSession)

        # WARNING:
        if len(self.sessions[bot_key]) >= max_sessions:
            session: Session = self.sessions[bot_key].pop(0)
            session.finish()
            self.finish_session(bot_key, session)
            return session

    def finish_session(self, bot_key: BOT_KEY, session: Session):
        """
        Завершает пользовательскую сессию и очищает связанные runtime-данные.

        ### Аргументы:
        :param bot_key: ключ транспорта, например `vkbot` или `telebot`
        :param session: активная пользовательская или административная сессия

        ### Пример использования:
        ```py
        user.finish_session(bot_key = bot_key, session = session)
        ```
        """
        if session in self.sessions[bot_key]:
            self.sessions[bot_key].remove(session)
            session.stop()

            message: Message = session.get_message()

            if message in self.messages[bot_key]:
                self.messages[bot_key].remove(message)
        # else:

    def add_session(self, bot_key: BOT_KEY, session: Session, save: bool = True):
        """
        Добавляет сессию в стек активных пользовательских сессий.

        ### Аргументы:
        :param bot_key: ключ транспорта, например `vkbot` или `telebot`
        :param session: активная пользовательская или административная сессия
        :param save: нужно ли сразу сохранить состояние пользователя после изменения

        ### Пример использования:
        ```py
        user.add_session(bot_key = bot_key, session = session, save = save)
        ```
        """
        # for bot_key, sessions in self.sessions.items():
        #     for session in sessions:
        #         if isinstance(session, ChatSession):
        #             raise Exception("Попытка повторного создания ChatSession")

        self.sessions[bot_key].append(session)

        if save:
            self.save()

    def process(self, context: Context):
        """
        Передаёт текущий `Context` выбранному обработчику и обновляет `context.handler` по результату.

        ### Аргументы:
        :param context: контекст обработки события

        ### Пример использования:
        ```py
        user.process(context = context)
        ```
        """
        bot_key: BOT_KEY = context.bot.get_bot_key()
        sessions: list[Session] = self.sessions[bot_key]
        session: Session = context.handler
        session.process(context)

        if session.check_finished():
            self.finish_session(bot_key, session)
            self.update_session(context)

        self.save()

    def update_session(self, context: Context):
        """
        Обновляет пользовательскую сессию с учётом текущего состояния объекта.

        ### Аргументы:
        :param context: контекст обработки события с app, bot, user, handler и message

        ### Пример использования:
        ```py
        user.update_session(context = context)
        ```
        """
        bot_key: BOT_KEY = context.bot.get_bot_key()

        for session in reversed(self.sessions[bot_key]):
            if not session.check_finished():
                message: Message = session.get_message()

                if message not in self.messages[bot_key]:
                    self.messages[bot_key].append(message)

                session.update()
                return

    def update_sessions(self, session_class: type[Session]):
        """
        Обновляет пользовательские сессии с учётом текущего состояния объекта.

        ### Аргументы:
        :param session_class: класс сессии, который нужно найти, создать или обновить

        ### Пример использования:
        ```py
        user.update_sessions(session_class = session_class)
        ```
        """
        for bot_key, sessions in self.sessions.items():
            for session in sessions:
                if isinstance(session, session_class):
                    session.update(prevent_resend = True)


    def get_client(self) -> Client:
        """
        Возвращает GPT-клиента пользователя из настроек приложения.

        :return: активный GPT-клиент пользователя

        :raises RuntimeError: если объект ещё не связан с необходимым runtime-состоянием

        ### Пример использования:
        ```py
        user.get_client()
        ```
        """
        if len(self.clients) == 2:
            return self.clients[1]
        else:
            raise RuntimeError(f"Сначала вызовите метод load у пользователя {self}")

    def get_tokens(self) -> float:
        """
        Возвращает сохранённое количество GPT-токенов.

        :return: оставшийся лимит токенов

        ### Пример использования:
        ```py
        user.get_tokens()
        ```
        """
        limits: list[Limit] = []

        for client in self.clients:
            limits += client.limits

        return float(min(limit.left for limit in limits)) if limits else float("inf")

    def debit_tokens(self, tokens: int):
        """
        Списывает tokens с лимитов GPT-клиентов пользователя.

        ### Аргументы:
        :param tokens: количество токенов, списываемое с лимитов клиента

        ### Пример использования:
        ```py
        user.debit_tokens(tokens = tokens)
        ```
        """
        for client in self.clients:
            client.debit_tokens(tokens)

        self.save()

    def get_history(self, bot_key: BOT_KEY, max_tokens: int, get_bot: Callable, max_from_one: int = 5) -> list[Message.MessagesGroup]:
        """
        Возвращает историю сообщений пользователя для указанного bot/chat.

        ### Аргументы:
        :param bot_key: ключ транспорта
        :param max_tokens: max tokens
        :param get_bot: get bot
        :param max_from_one: max from one

        :return: история переписки в пределах лимита токенов

        ### Пример использования:
        ```py
        user.get_history(bot_key = bot_key, max_tokens = max_tokens, get_bot = get_bot, max_from_one = max_from_one)
        ```
        """
        groups: list[Message.MessagesGroup] = self.get_last_conversation(get_bot, bot_key, max_from_one)
        result: list[Message.MessagesGroup] = []
        left_tokens: int = int(max_tokens)

        for group in reversed(groups):
            group_tokens: int = count_group_tokens(group)

            if left_tokens >= group_tokens:
                left_tokens -= group_tokens
                result.append(group)
            else:
                return result[::-1]

        return result[::-1]

    def add_request(self, request: Request):
        """
        Добавляет GPT-запрос в список ожидающих пользовательских запросов.

        ### Аргументы:
        :param request: GPT-запрос, связанный с пользователем

        ### Пример использования:
        ```py
        user.add_request(request = request)
        ```
        """
        self.requests[int(request.id)] = request

        while len(self.requests) > MAX_REQUESTS:
            self.requests.pop(0)
            # logger.error("User.add_request pop!")

    def add_response(self, request_id: int, response: Response):
        """
        Добавляет GPT-ответ в историю ответов пользователя.

        ### Аргументы:
        :param request_id: идентификатор GPT-запроса, к которому относится ответ
        :param response: ответ GPT, привязанный к запросу пользователя

        ### Пример использования:
        ```py
        user.add_response(request_id = request_id, response = response)
        ```
        """
        self.responses[int(request_id)] = response

        while len(self.responses) > MAX_RESPONSES:
            self.responses.pop(0)
            # logger.error("User.add_response pop!")


    def get_answer(self, bot_key: BOT_KEY, cut_string: bool = True) -> str:
        """
        Возвращает строку, показываемую пользователю как вариант ответа.

        ### Аргументы:
        :param bot_key: ключ транспорта
        :param cut_string: нужно ли сокращать строку до длины кнопки

        :return: ответ пользователя

        ### Пример использования:
        ```py
        user.get_answer(bot_key = bot_key, cut_string = cut_string)
        ```
        """
        username: str = self.get_name(bot_key) or self.get_username(bot_key) or get_phrase(self.__class__.DEFAULT_SINGLE_KEY).format(str(self.id))

        bot_keys: dict[BOT_KEY, str] = {
            "vkbot": "🟦",
            "telebot": "✈️"
        }

        default: str = "🚫"
        result: str = f"{bot_keys.get(bot_key, default)} {username}"

        if cut_string and len(result) > BUTTON_LENGTH:
            return cut(result, BUTTON_LENGTH)
        else:
            return result
