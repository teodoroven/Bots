"""
Описывает административные модели или сессии.
Модуль относится к архитектурной зоне: прикладной слой `relay`, который связывает пользователей, сессии, доменную модель, GPT, уведомления и runtime-логику приложения.

### Публичные классы
- `NoHandlersSession`: сессия для событий без обработчика.
- `BotControlSession`: сессия управления ботами.
- `SessionUsers`: сессия списка пользователей.
- `UserSession`: сессия управления пользователем.
- `SessionAdmins`: сессия списка администраторов.
- `AdminSession`: сессия управления администратором.

### Публичные функции
- Публичные функции отсутствуют.

### Связи
Используется app-layer сценариями, обработчиками, сессиями и runtime-миксинами для единого пользовательского потока между ботами, GPT и storage.
"""

from __future__ import annotations


from relay.common import BotTypes, abstractmethod
from relay.config import BUTTON_LENGTH, get_phrase, logger_user_flow
from relay.conversations import Conversation
from .base import MenuSession
from .manage import ManageSession, Mode, ModeSession
from relay.users import Admin, User
from relay.utils import is_int, join_callback, split_callback
from relay.callback_data import Callback


class NoHandlersSession(MenuSession):

    """
    Описывает пользовательскую или административную сессию `NoHandlersSession`.
    Сессия хранит состояние текущего пользовательского сценария, обновляет сообщения и завершает себя через общий session lifecycle.

    ### Поля
    - `call_admin`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `admin_called`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `user_tokens`: runtime-зависимость или поле, используемое текущим session-сценарием.

    ### Методы
    - `__init__`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `check`: Проверяет значение по правилам текущего класса и не изменяет состояние.
    - `call_admin`: Выполняет следующий шаг текущей сессии.
    - `dumps`: Возвращает JSON-совместимый снимок объекта для storage или callback payload.
    - `input_default`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `process`: Передаёт текущий `Context` выбранному обработчику и обновляет `context.handler` по результату.
    - `update`: Синхронизирует данные сценария с уже отправленными UI-сообщениями.
    - `update_data`: Обновляет data с учётом текущего состояния объекта.

    ### Жизненный цикл
    Создаётся app-layer кодом, участвует в обработке пользовательского события и сохраняет изменённое состояние через существующие runtime/storage механизмы.

    ### Пример использования
    ```py
    session: NoHandlersSession
    ```
    """
    def __init__(self, session_id: int, context: Context, data: dict, message: Message):
        """
        Создаёт session-объект `NoHandlersSession` и сохраняет состояние пользовательского сценария между входящими событиями.

        ### Аргументы:
        :param session_id: идентификатор сессии
        :param context: контекст обработки события
        :param data: сериализованный словарь
        :param message: сообщение проекта или сообщение конкретного транспорта

        ### Пример использования:
        ```py
        session = NoHandlersSession(session_id = session_id, context = context, data = data, message = message)
        ```
        """
        super().__init__(session_id, context, data, message)
        self.call_admin = context.autocenter.call_admin
        self.admin_called: bool = get_from(data, "admin_called", types = (bool,), default = False)
        self.user_tokens: int = context.user.get_tokens()

    def check(self, context: Context) -> bool:
        """
        Проверяет значение по правилам текущего класса и не изменяет состояние.

        ### Аргументы:
        :param context: контекст обработки события

        :return: результат шага сессии

        ### Пример использования:
        ```py
        session.check(context = context)
        ```
        """
        user_tokens: int = context.user.get_tokens()

        if user_tokens == self.user_tokens:
            return True
        else:
            self.finish()
            return False

    @abstractmethod
    def call_admin(self):
        """
        Выполняет следующий шаг текущей сессии.

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        session.call_admin()
        ```
        """
        raise NotImplementedError()

    def dumps(self) -> BotTypes.SESSION_TYPE:
        """
        Возвращает JSON-совместимый снимок объекта для storage или callback payload.

        :return: JSON-совместимый словарь для сохранения или передачи между слоями

        ### Пример использования:
        ```py
        session.dumps()
        ```
        """
        result: BotTypes.SESSION_TYPE = super().dumps()

        result.update({
            "tokens": int(self.user_tokens) if is_int(self.user_tokens) else 0,
            "admin_called": bool(self.admin_called)
        })

        return result

    def input_default(self, make_last: Never = True):
        """
        Показывает меню обращения к администратору, когда других обработчиков нет.

        ### Аргументы:
        :param make_last: нужно ли переместить меню в конец истории сообщений

        ### Пример использования:
        ```py
        session.input_default(make_last = make_last)
        ```
        """
        self.input.update(get_phrase("no_handlers"), answers = {}, actions = {
            "call_admin": CALLBACK_CALL_ADMIN
        }, choosen = [], confirm = False, cancel = False, back = False, skip = False,
        make_last = True)

    def process(self, context: Context):
        """
        Передаёт текущий `Context` выбранному обработчику и обновляет `context.handler` по результату.

        ### Аргументы:
        :param context: контекст обработки события

        ### Пример использования:
        ```py
        session.process(context = context)
        ```
        """
        if context.has_handler() and context.is_callback():
            callback_data: str = context.get_callback_string(1)

            user: User = context.user
            bot_key: BOT_KEY = context.bot.get_bot_key()
            if user.find_conv_session(bot_key):
                return

            if callback_data == CALLBACK_CALL_ADMIN:
                self.call_admin(context)
                self.show_phrase("admin_called")
                self.admin_called = True
                return

        # self.input_default()

    def update(self):
        """
        Синхронизирует данные сценария с уже отправленными UI-сообщениями.

        ### Пример использования:
        ```py
        session.update()
        ```
        """
        self.input_default()

    def update_data(self, data: dict[str, int]):
        """
        Обновляет data с учётом текущего состояния объекта.

        ### Аргументы:
        :param data: JSON-совместимые данные для соответствующего repository

        ### Пример использования:
        ```py
        session.update_data(data = data)
        ```
        """
        self.user_tokens = get_int(data, -1, "tokens")
        self.admin_called = get_from(data, "admin_called", types = (bool,), default = False)


class BotControlSession(MenuSession):

    """
    Описывает пользовательскую или административную сессию `BotControlSession`.
    Сессия хранит состояние текущего пользовательского сценария, обновляет сообщения и завершает себя через общий session lifecycle.

    ### Поля
    - `is_bot_enabled`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `set_bot_enabled`: runtime-зависимость или поле, используемое текущим session-сценарием.

    ### Методы
    - `__init__`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `is_bot_enabled`: Проверяет, включён ли transport-бот в runtime-настройках.
    - `set_bot_enabled`: Проверяет и сохраняет значение `bot enabled` в `BotControlSession`.
    - `update`: Синхронизирует данные сценария с уже отправленными UI-сообщениями.
    - `update_data`: Обновляет data с учётом текущего состояния объекта.
    - `get_back`: Возвращает back из текущего состояния `BotControlSession`.
    - `get_answers`: Возвращает варианты ответа из текущего состояния `BotControlSession`.
    - `get_actions`: Возвращает действия меню из текущего состояния `BotControlSession`.
    - `get_question`: Возвращает вопрос анкеты или GPT-контекста из текущего состояния `BotControlSession`.
    - `process`: Передаёт текущий `Context` выбранному обработчику и обновляет `context.handler` по результату.

    ### Жизненный цикл
    Создаётся app-layer кодом, участвует в обработке пользовательского события и сохраняет изменённое состояние через существующие runtime/storage механизмы.

    ### Пример использования
    ```py
    session: BotControlSession
    ```
    """
    def __init__(self, session_id: int, context: Context, data: dict, message: Message):
        """
        Создаёт session-объект `BotControlSession` и сохраняет состояние пользовательского сценария между входящими событиями.

        ### Аргументы:
        :param session_id: идентификатор сессии
        :param context: контекст обработки события
        :param data: сериализованный словарь
        :param message: сообщение проекта или сообщение конкретного транспорта

        ### Пример использования:
        ```py
        session = BotControlSession(session_id = session_id, context = context, data = data, message = message)
        ```
        """
        super().__init__(session_id, context, data, message)
        self.is_bot_enabled = context.autocenter.is_bot_enabled
        self.set_bot_enabled = context.autocenter.set_bot_enabled
        self.input.lang_actions = True

    @abstractmethod
    def is_bot_enabled(self) -> bool:
        """
        Проверяет, включён ли transport-бот в runtime-настройках.

        :return: `True`, если включён ли transport-бот в runtime-настройках; иначе `False`

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        session.is_bot_enabled()
        ```
        """
        raise NotImplementedError()

    @abstractmethod
    def set_bot_enabled(self, enabled: bool) -> bool:
        """
        Проверяет и сохраняет значение `bot enabled`.

        ### Аргументы:
        :param enabled: нужное состояние включения элемента

        :return: результат шага сессии

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        session.set_bot_enabled(enabled = enabled)
        ```
        """
        raise NotImplementedError()

    def update(self):
        """
        Синхронизирует данные сценария с уже отправленными UI-сообщениями.

        ### Пример использования:
        ```py
        session.update()
        ```
        """
        self.input_default()

    def update_data(self, data: dict):
        """
        Обновляет data с учётом текущего состояния объекта.

        ### Аргументы:
        :param data: JSON-совместимые данные для соответствующего repository

        ### Пример использования:
        ```py
        session.update_data(data = data)
        ```
        """
        self.input.set_choosen([])

    def get_back(self) -> Callback | None:
        """
        Возвращает callback для выхода из текущей admin-сессии.

        :return: callback кнопки «назад» или `None`

        ### Пример использования:
        ```py
        session.get_back()
        ```
        """
        if self.user.get_back(self.id):
            return self.finish
        else:
            return None

    def get_answers(self) -> dict[str, JSONABLE]:
        """
        Возвращает варианты ответа для текущего меню.

        :return: варианты ответа

        ### Пример использования:
        ```py
        session.get_answers()
        ```
        """
        return {}

    def get_actions(self, answers: dict[str, JSONABLE] = {}) -> dict[str, str]:
        """
        Возвращает действия управления bot config.

        ### Аргументы:
        :param answers: варианты ответа

        :return: actions

        ### Пример использования:
        ```py
        session.get_actions(answers = answers)
        ```
        """
        if self.is_bot_enabled():
            return {
                "bot_disable": DISABLE_CALLBACK
            }
        else:
            return {
                "bot_enable": ENABLE_CALLBACK
            }

    def get_question(self, answers: dict[str, JSONABLE] = {}) -> str:
        """
        Возвращает краткое описание элемента для вывода в чат.

        ### Аргументы:
        :param answers: варианты ответа

        :return: строка вида `Филиал «Название»` или `Элемент «id»`

        ### Пример использования:
        ```py
        session.get_question(answers = answers)
        ```
        """
        phrase_key: str = "bot_enabled_status" if self.is_bot_enabled() else "bot_disabled_status"
        return get_phrase(phrase_key)

    def process(self, context: Context):
        """
        Передаёт текущий `Context` выбранному обработчику и обновляет `context.handler` по результату.

        ### Аргументы:
        :param context: контекст обработки события

        ### Пример использования:
        ```py
        session.process(context = context)
        ```
        """
        if isinstance(context.handler, self.__class__):
            self.input_process(context)
        else:
            self.input_default()

    def process_answer(self, bot_key: BOT_KEY, chat_id: int, answer: str) -> bool:
        """
        Обрабатывает ответ пользователя в текущем runtime-контексте.

        ### Аргументы:
        :param bot_key: ключ транспорта
        :param chat_id: идентификатор чата
        :param answer: ответ пользователя

        :return: результат шага сессии

        ### Пример использования:
        ```py
        session.process_answer(bot_key = bot_key, chat_id = chat_id, answer = answer)
        ```
        """
        return False

    def process_action(self, bot_key: BOT_KEY, chat_id: int, action: str) -> bool:
        """
        Обрабатывает действие меню в текущем runtime-контексте.

        ### Аргументы:
        :param bot_key: ключ транспорта
        :param chat_id: идентификатор чата
        :param action: действие меню

        :return: результат шага сессии

        ### Пример использования:
        ```py
        session.process_action(bot_key = bot_key, chat_id = chat_id, action = action)
        ```
        """
        if action == ENABLE_CALLBACK:
            self.set_bot_enabled(True)
        elif action == DISABLE_CALLBACK:
            self.set_bot_enabled(False)
        else:
            return False

        self.input_default()
        return True


class SessionUsers(ModeSession):
    """
    Описывает пользовательскую или административную сессию `SessionUsers`.
    Сессия хранит состояние текущего пользовательского сценария, обновляет сообщения и завершает себя через общий session lifecycle.

    ### Поля
    - `DESCRIPTION_KEY`: ключ сериализации или transport-события, по которому объект отличает один вариант данных от другого.
    - `ALREADY_EXISTS_KEY`: ключ сериализации или transport-события, по которому объект отличает один вариант данных от другого.
    - `get_users_list`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `element_class`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `next_session`: runtime-зависимость или поле, используемое текущим session-сценарием.

    ### Методы
    - `__init__`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `get_users_list`: Возвращает users list из текущего состояния `SessionUsers`.
    - `get_question`: Возвращает вопрос анкеты или GPT-контекста из текущего состояния `SessionUsers`.
    - `get_container`: Возвращает container из текущего состояния `SessionUsers`.
    - `get_answers`: Возвращает варианты ответа из текущего состояния `SessionUsers`.
    - `get_next_level`: Возвращает next level из текущего состояния `SessionUsers`.
    - `mode_admins`: runtime-зависимость или поле, используемое текущим session-сценарием.

    ### Жизненный цикл
    Создаётся app-layer кодом, участвует в обработке пользовательского события и сохраняет изменённое состояние через существующие runtime/storage механизмы.

    ### Пример использования
    ```py
    session: SessionUsers
    ```
    """
    DESCRIPTION_KEY: str = "users_description"
    ALREADY_EXISTS_KEY: str = "repeated_user"

    def __init__(self, session_id: int, context: Context, data: dict, message: Message):
        """
        Создаёт session-объект `SessionUsers` и сохраняет состояние пользовательского сценария между входящими событиями.

        ### Аргументы:
        :param session_id: идентификатор сессии
        :param context: контекст обработки события
        :param data: сериализованный словарь
        :param message: сообщение проекта или сообщение конкретного транспорта

        ### Пример использования:
        ```py
        sessionUsers = SessionUsers(session_id = session_id, context = context, data = data, message = message)
        ```
        """
        super().__init__(session_id, context, data, message)
        self.get_users_list = context.autocenter.get_users_list

        self.element_class = User
        self.next_session = UserSession

        self.always_actions.clear()
        # self.choosing_actions.clear()
        self.removed_actions.clear()

        self.modes.clear()
        self.modes.append(
            Mode("admins", self.mode_admins)
        )

        self.set_mode(data.get("mode", ""))

    @abstractmethod
    def get_users_list(self, max_users: int = 20) -> list[User]:
        """
        Возвращает пользователей, доступных для административного выбора.

        ### Аргументы:
        :param max_users: максимальное число пользователей в выдаче

        :return: users list

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        sessionUsers.get_users_list(max_users = max_users)
        ```
        """
        raise NotImplementedError()

    def get_question(self, answers: dict[str, JSONABLE] = {}) -> str:
        """
        Возвращает краткое описание элемента для вывода в чат.

        ### Аргументы:
        :param answers: варианты ответа

        :return: строка вида `Филиал «Название»` или `Элемент «id»`

        ### Пример использования:
        ```py
        sessionUsers.get_question(answers = answers)
        ```
        """
        return get_phrase("users")

    def get_container(self) -> list[User]:
        """
        Возвращает контейнер пользователей для текущей admin-сессии.

        :return: container

        ### Пример использования:
        ```py
        sessionUsers.get_container()
        ```
        """
        return self.get_users_list()

    def get_answers(self) -> dict[str, str]:
        """
        Возвращает варианты ответа для текущего меню.

        :return: варианты ответа

        ### Пример использования:
        ```py
        sessionUsers.get_answers()
        ```
        """
        answers: dict[str, str] = {}

        for user in self.get_container():
            for bot_key in user.get_bot_keys():
                chat_id: int = user.get_chat_id(bot_key)
                answer: str = user.get_display_answer(bot_key, cut_string = True)
                answer_key: str = answer
                i: int = 1

                while answer_key in answers and i < 100:
                    i += 1
                    answer_key = cut(f"{answer} ({i})", BUTTON_LENGTH)

                if i >= 100:
                    continue

                answers[answer_key] = join_callback(user.id, bot_key, chat_id)

        return answers

    def get_next_level(self, answer: str) -> dict[str, int]:
        """
        Возвращает следующий шаг выбора пользователя.

        ### Аргументы:
        :param answer: ответ пользователя

        :return: next level

        ### Пример использования:
        ```py
        sessionUsers.get_next_level(answer = answer)
        ```
        """
        args: list[str] = split_callback(answer)
        user_id, bot_key, chat_id = args

        return {
            "element_id": int(user_id),
            "bot_key": bot_key,
            "chat_id": int (chat_id)
        }

    def mode_admins(self, context: Context | None):
        """
        Переводит session-меню в режим `admins`.

        ### Аргументы:
        :param context: контекст обработки события

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        sessionUsers.mode_admins(context = context)
        ```
        """
        raise NotImplementedError()


class UserSession(ManageSession):
    """
    Описывает пользовательскую или административную сессию `UserSession`.
    Сессия хранит состояние текущего пользовательского сценария, обновляет сообщения и завершает себя через общий session lifecycle.

    ### Поля
    - `DESCRIPTION_KEY`: ключ сериализации или transport-события, по которому объект отличает один вариант данных от другого.
    - `get_user`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `ignore_user`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `finish_dialog`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `start_dialog`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `bot_key`: хранит ключ транспорта для операций этого объекта.
    - `chat_id`: идентификатор объекта или связанной сущности, по которому runtime восстанавливает связь между слоями.

    ### Методы
    - `__init__`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `get_user`: Возвращает состояние пользователя из текущего состояния `UserSession`.
    - `ignore_user`: Выполняет следующий шаг текущей сессии.
    - `finish_dialog`: Завершает dialog и очищает связанные runtime-данные.
    - `start_dialog`: Запускает dialog в runtime-потоке приложения.
    - `dumps`: Возвращает JSON-совместимый снимок объекта для storage или callback payload.
    - `update_data`: Обновляет data с учётом текущего состояния объекта.
    - `get_element`: Возвращает элемент доменной модели из текущего состояния `UserSession`.
    - `get_description`: Возвращает description из текущего состояния `UserSession`.
    - `get_question`: Возвращает вопрос анкеты или GPT-контекста из текущего состояния `UserSession`.

    ### Жизненный цикл
    Создаётся app-layer кодом, участвует в обработке пользовательского события и сохраняет изменённое состояние через существующие runtime/storage механизмы.

    ### Пример использования
    ```py
    session: UserSession
    ```
    """
    DESCRIPTION_KEY: str = "user_description"

    def __init__(self, session_id: int, context: Context, data: dict, message: Message):
        """
        Создаёт session-объект `UserSession` и сохраняет состояние пользовательского сценария между входящими событиями.

        ### Аргументы:
        :param session_id: идентификатор сессии
        :param context: контекст обработки события
        :param data: сериализованный словарь
        :param message: сообщение проекта или сообщение конкретного транспорта

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        session = UserSession(session_id = session_id, context = context, data = data, message = message)
        ```
        """
        super().__init__(session_id, context, data, message)
        self.get_user = context.autocenter.get_user
        self.ignore_user = context.autocenter.ignore_user
        self.finish_dialog = context.autocenter.finish_dialog
        self.start_dialog = context.autocenter.start_dialog

        self.bot_key: BOT_KEY = data["bot_key"]
        self.chat_id: int = get_int(data, -1, "chat_id")

        if self.chat_id < 0:
            chat_id = data.get("chat_id")
            raise ValueError(f"Некорректное значение под ключом {chat_id=} аргумента {data=}")


    @abstractmethod
    def get_user(self, bot_key: BOT_KEY, chat_id: int) -> User:
        """
        Возвращает привязанного пользователя приложения.

        ### Аргументы:
        :param bot_key: ключ транспорта
        :param chat_id: идентификатор чата

        :return: пользователь приложения

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        session.get_user(bot_key = bot_key, chat_id = chat_id)
        ```
        """
        raise NotImplementedError

    @abstractmethod
    def ignore_user(self, bot_key: BOT_KEY, chat_id: int):
        """
        Выполняет следующий шаг текущей сессии.

        ### Аргументы:
        :param bot_key: ключ транспорта
        :param chat_id: идентификатор чата

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        session.ignore_user(bot_key = bot_key, chat_id = chat_id)
        ```
        """
        raise NotImplementedError

    @abstractmethod
    def finish_dialog(self, bot_key: BOT_KEY, chat_id: int):
        """
        Завершает dialog и очищает связанные runtime-данные.

        ### Аргументы:
        :param bot_key: ключ транспорта, например `vkbot` или `telebot`
        :param chat_id: идентификатор чата в конкретной платформе

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        session.finish_dialog(bot_key = bot_key, chat_id = chat_id)
        ```
        """
        raise NotImplementedError

    @abstractmethod
    def start_dialog(self, user_bot_key: BOT_KEY, user_chat_id: int, admin_bot_key: BOT_KEY, admin_chat_id: int):
        """
        Запускает сценарий обработки и подготавливает первое сообщение или задачу.

        ### Аргументы:
        :param user_bot_key: user bot key
        :param user_chat_id: user chat id
        :param admin_bot_key: admin bot key
        :param admin_chat_id: admin chat id

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        session.start_dialog(user_bot_key = user_bot_key, user_chat_id = user_chat_id, admin_bot_key = admin_bot_key, admin_chat_id = admin_chat_id)
        ```
        """
        raise NotImplementedError


    def dumps(self) -> BotTypes.SESSION_TYPE:
        """
        Возвращает JSON-совместимый снимок объекта для storage или callback payload.

        :return: JSON-совместимый словарь для сохранения или передачи между слоями

        ### Пример использования:
        ```py
        session.dumps()
        ```
        """
        result: BotTypes.SESSION_TYPE = super().dumps()

        result.update({
            "bot_key": self.bot_key,
            "chat_id": self.chat_id
        })

        return result

    def update_data(self, data: dict):
        """
        Обновляет data с учётом текущего состояния объекта.

        ### Аргументы:
        :param data: JSON-совместимые данные для соответствующего repository

        :raises ValueError: если значение не проходит локальную проверку перед сохранением

        ### Пример использования:
        ```py
        session.update_data(data = data)
        ```
        """
        bot_key: BOT_KEY = data["bot_key"]
        chat_id: int = get_int(data, -1, "chat_id")

        self.element_class = User
        if self.chat_id < 0:
            chat_id = data.get("chat_id")
            raise ValueError(f"Некорректное значение под ключом {chat_id=} аргумента {data=}")

        self.bot_key = bot_key
        self.chat_id = chat_id

        # self.always_actions.clear()
        self.removed_actions.clear()
        self.enabled_actions.clear()

    def get_element(self) -> Model:
        """
        Возвращает привязанный доменный элемент.

        :return: доменный элемент

        ### Пример использования:
        ```py
        session.get_element()
        ```
        """
        return self.get_user(self.bot_key, self.chat_id)

    def get_description(self) -> str:
        """
        Возвращает описание пользователя и его прав.

        :return: description

        ### Пример использования:
        ```py
        session.get_description()
        ```
        """
        return ""

    def get_question(self, answers: Never = {}) -> str:
        """
        Возвращает краткое описание элемента для вывода в чат.

        ### Аргументы:
        :param answers: варианты ответа

        :return: строка вида `Филиал «Название»` или `Элемент «id»`

        ### Пример использования:
        ```py
        session.get_question(answers = answers)
        ```
        """
        user: User | None = self.get_element()

        if user:
            return user.get_display_answer(self.bot_key, cut_string = False)
        else:
            self.validate_element()
            return get_phrase("element_removed").format(str(self.element_id))

    def get_actions(self, answers: Never = {}) -> dict[str, str]:
        """
        Возвращает admin-действия для выбранного пользователя.

        ### Аргументы:
        :param answers: варианты ответа

        :return: actions

        ### Пример использования:
        ```py
        session.get_actions(answers = answers)
        ```
        """
        user: User | None = self.get_element()

        if not user:
            self.validate_element()
            return {}

        result: dict[str, str] = {}

        for bot_key in user.sessions:
            session: NoHandlersSession | None = user.find_session(bot_key, NoHandlersSession)

            if session:
                return {
                    "start_dialog": DIALOG_CALLBACK,
                    "continue": FINISH_CALLBACK
                }

        return {
            "start_dialog": DIALOG_CALLBACK,
            "ignore": IGNORE_CALLBACK
        }

    def process_action(self, bot_key: BOT_KEY, chat_id: int, action: str) -> bool:
        """
        Обрабатывает действие меню в текущем runtime-контексте.

        ### Аргументы:
        :param bot_key: ключ транспорта
        :param chat_id: идентификатор чата
        :param action: действие меню

        :return: результат шага сессии

        ### Пример использования:
        ```py
        session.process_action(bot_key = bot_key, chat_id = chat_id, action = action)
        ```
        """


        if action == IGNORE_CALLBACK:
            if self.bot_key != bot_key and self.chat_id != chat_id:
                self.ignore_user(self.bot_key, self.chat_id)
                self.show_phrase("user_ignored", buttons = [
                    Bot.Keyboard.Button(get_phrase("finish_dialog"), callback_data = join_callback(CALLBACK_FINISHDIALOG, self.bot_key, self.chat_id))
                ])
            else:
                self.show_phrase("cant_user")
                self.update()
            self.update()
            return True
        elif action == FINISH_CALLBACK:
            self.finish_dialog(self.bot_key, self.chat_id)
            self.update()
            return True
        elif action == DIALOG_CALLBACK:
            if self.bot_key != bot_key and self.chat_id != chat_id:
                conv: Conversation = self.start_dialog(self.bot_key, self.chat_id, bot_key, chat_id)
            else:
                self.show_phrase("cant_user")
                self.update()
            return True
        else:
            return super().process_action(bot_key, chat_id, action)


class SessionAdmins(ModeSession):
    """
    Описывает пользовательскую или административную сессию `SessionAdmins`.
    Сессия хранит состояние текущего пользовательского сценария, обновляет сообщения и завершает себя через общий session lifecycle.

    ### Поля
    - `DESCRIPTION_KEY`: ключ сериализации или transport-события, по которому объект отличает один вариант данных от другого.
    - `get_users_list`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `get_access_level`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `promote_admin`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `demote_admin`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `promote_admin_by_chat`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `can_promote`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `can_promote_by_chat`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `can_demote`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `element_class`: runtime-зависимость или поле, используемое текущим session-сценарием.

    ### Методы
    - `__init__`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `get_users_list`: Возвращает users list из текущего состояния `SessionAdmins`.
    - `get_access_level`: Возвращает access level из текущего состояния `SessionAdmins`.
    - `promote_admin`: Меняет уровень прав администратора и сохраняет обновлённое состояние пользователя.
    - `demote_admin`: Меняет уровень прав администратора и сохраняет обновлённое состояние пользователя.
    - `promote_admin_by_chat`: Меняет уровень прав администратора и сохраняет обновлённое состояние пользователя.
    - `can_promote`: Сравнивает состояние объектов и возвращает флаг, который нужен перед отправкой или редактированием.
    - `can_demote`: Сравнивает состояние объектов и возвращает флаг, который нужен перед отправкой или редактированием.
    - `can_promote_by_chat`: Сравнивает состояние объектов и возвращает флаг, который нужен перед отправкой или редактированием.
    - `get_question`: Возвращает вопрос анкеты или GPT-контекста из текущего состояния `SessionAdmins`.

    ### Жизненный цикл
    Создаётся app-layer кодом, участвует в обработке пользовательского события и сохраняет изменённое состояние через существующие runtime/storage механизмы.

    ### Пример использования
    ```py
    session: SessionAdmins
    ```
    """
    DESCRIPTION_KEY: str = "admins_description"

    def __init__(self, session_id: int, context: Context, data: dict, message: Message):
        """
        Создаёт session-объект `SessionAdmins` и сохраняет состояние пользовательского сценария между входящими событиями.

        ### Аргументы:
        :param session_id: идентификатор сессии
        :param context: контекст обработки события
        :param data: сериализованный словарь
        :param message: сообщение проекта или сообщение конкретного транспорта

        ### Пример использования:
        ```py
        sessionAdmins = SessionAdmins(session_id = session_id, context = context, data = data, message = message)
        ```
        """
        super().__init__(session_id, context, data, message)
        self.get_users_list = context.autocenter.get_users_list
        self.get_access_level = context.autocenter.get_access_level
        self.promote_admin = context.autocenter.promote_admin
        self.demote_admin = context.autocenter.demote_admin
        self.promote_admin_by_chat = context.autocenter.promote_admin_by_chat
        self.can_promote = context.autocenter.can_promote_admin
        self.can_promote_by_chat = context.autocenter.can_promote_admin_by_chat
        self.can_demote = context.autocenter.can_demote_admin

        self.element_class = User
        self.next_session = AdminSession

        self.always_actions = {}
        self.choosing_actions.clear()
        self.removed_actions.clear()
        self.enabled_actions.clear()

        self.modes.clear()
        self.modes.extend([
            Mode("create", self.mode_create),
            Mode("promote", self.mode_promote),
            Mode("demote", self.mode_demote)
        ])

        self.input.lang_actions = True

        mode: str = data.get("mode", "")
        self.set_mode("" if mode == "admins" else mode)
        self.pending_chat_id: int | None = None
        self.pending_bot_key: BOT_KEY | None = None

    @abstractmethod
    def get_users_list(self, max_users: int = 20) -> list[User]:
        """
        Возвращает список пользователей, которых можно назначить администраторами.

        ### Аргументы:
        :param max_users: максимальное число пользователей в выдаче

        :return: users list

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        sessionAdmins.get_users_list(max_users = max_users)
        ```
        """
        raise NotImplementedError()

    @abstractmethod
    def get_access_level(self, user_id: int) -> int:
        """
        Возвращает сохранённый уровень доступа.

        ### Аргументы:
        :param user_id: user id

        :return: уровень доступа пользователя

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        sessionAdmins.get_access_level(user_id = user_id)
        ```
        """
        raise NotImplementedError()

    @abstractmethod
    def promote_admin(self, actor_id: int, user_id: int) -> bool:
        """
        Меняет уровень прав администратора и сохраняет обновлённое состояние пользователя.

        ### Аргументы:
        :param actor_id: actor id
        :param user_id: user id

        :return: результат шага сессии

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        sessionAdmins.promote_admin(actor_id = actor_id, user_id = user_id)
        ```
        """
        raise NotImplementedError()

    @abstractmethod
    def demote_admin(self, actor_id: int, user_id: int) -> bool:
        """
        Меняет уровень прав администратора и сохраняет обновлённое состояние пользователя.

        ### Аргументы:
        :param actor_id: actor id
        :param user_id: user id

        :return: результат шага сессии

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        sessionAdmins.demote_admin(actor_id = actor_id, user_id = user_id)
        ```
        """
        raise NotImplementedError()

    @abstractmethod
    def promote_admin_by_chat(self, actor_id: int, bot_key: BOT_KEY, chat_id: int) -> bool:
        """
        Меняет уровень прав администратора и сохраняет обновлённое состояние пользователя.

        ### Аргументы:
        :param actor_id: actor id
        :param bot_key: ключ транспорта
        :param chat_id: идентификатор чата

        :return: результат шага сессии

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        sessionAdmins.promote_admin_by_chat(actor_id = actor_id, bot_key = bot_key, chat_id = chat_id)
        ```
        """
        raise NotImplementedError()

    @abstractmethod
    def can_promote(self, actor_id: int, target_id: int) -> bool:
        """
        Сравнивает состояние объектов и возвращает флаг, который нужен перед отправкой или редактированием.

        ### Аргументы:
        :param actor_id: actor id
        :param target_id: target id

        :return: результат шага сессии

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        sessionAdmins.can_promote(actor_id = actor_id, target_id = target_id)
        ```
        """
        raise NotImplementedError()

    @abstractmethod
    def can_demote(self, actor_id: int, target_id: int) -> bool:
        """
        Сравнивает состояние объектов и возвращает флаг, который нужен перед отправкой или редактированием.

        ### Аргументы:
        :param actor_id: actor id
        :param target_id: target id

        :return: результат шага сессии

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        sessionAdmins.can_demote(actor_id = actor_id, target_id = target_id)
        ```
        """
        raise NotImplementedError()

    @abstractmethod
    def can_promote_by_chat(self, actor_id: int, bot_key: BOT_KEY, chat_id: int) -> bool:
        """
        Сравнивает состояние объектов и возвращает флаг, который нужен перед отправкой или редактированием.

        ### Аргументы:
        :param actor_id: actor id
        :param bot_key: ключ транспорта
        :param chat_id: идентификатор чата

        :return: результат шага сессии

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        sessionAdmins.can_promote_by_chat(actor_id = actor_id, bot_key = bot_key, chat_id = chat_id)
        ```
        """
        raise NotImplementedError()

    def get_question(self, answers: dict[str, JSONABLE] = {}) -> str:
        """
        Возвращает краткое описание элемента для вывода в чат.

        ### Аргументы:
        :param answers: варианты ответа

        :return: строка вида `Филиал «Название»` или `Элемент «id»`

        ### Пример использования:
        ```py
        sessionAdmins.get_question(answers = answers)
        ```
        """
        return get_phrase("admins")

    def get_answer(self, user: User, cut_string: bool = True) -> str:
        """
        Возвращает строку, показываемую пользователю как вариант ответа.

        ### Аргументы:
        :param user: пользователь приложения
        :param cut_string: нужно ли сокращать строку до длины кнопки

        :return: ответ пользователя

        ### Пример использования:
        ```py
        sessionAdmins.get_answer(user = user, cut_string = cut_string)
        ```
        """
        return user.get_display_answer(cut_string = cut_string)

    def can_promote_user(self, user: User) -> bool:
        """
        Сравнивает состояние объектов и возвращает флаг, который нужен перед отправкой или редактированием.

        ### Аргументы:
        :param user: пользователь приложения

        :return: результат шага сессии

        ### Пример использования:
        ```py
        sessionAdmins.can_promote_user(user = user)
        ```
        """
        return self.can_promote(self.user.id, user.id)

    def can_demote_user(self, user: User) -> bool:
        """
        Сравнивает состояние объектов и возвращает флаг, который нужен перед отправкой или редактированием.

        ### Аргументы:
        :param user: пользователь приложения

        :return: результат шага сессии

        ### Пример использования:
        ```py
        sessionAdmins.can_demote_user(user = user)
        ```
        """
        return self.can_demote(self.user.id, user.id)

    def reset(self, message: str = ""):
        """
        Возвращает сценарий к начальному шагу и обновляет UI при необходимости.

        ### Аргументы:
        :param message: сообщение проекта или сообщение конкретного транспорта

        ### Пример использования:
        ```py
        sessionAdmins.reset(message = message)
        ```
        """
        self.pending_chat_id = None
        self.pending_bot_key = None
        super().reset(message)

    def get_creator_candidates(self) -> list[User]:
        """
        Возвращает кандидатов на роль создателя bot config.

        :return: creator candidates

        ### Пример использования:
        ```py
        sessionAdmins.get_creator_candidates()
        ```
        """
        return [user for user in self.get_users_list(max_users = 1000) if self.get_access_level(user.id) >= 3]

    def get_container(self) -> list[User]:
        """
        Возвращает контейнер администраторов текущего приложения.

        :return: container

        ### Пример использования:
        ```py
        sessionAdmins.get_container()
        ```
        """
        users: list[User] = self.get_users_list(max_users = 1000)

        if self.check_mode():
            match self.mode.name:
                case "create":
                    return [user for user in users if self.can_promote_user(user)]
                case "promote":
                    return [user for user in users if self.can_promote_user(user)]
                case "demote":
                    return [user for user in users if self.can_demote_user(user)]

        return [user for user in users if self.get_access_level(user.id) >= 1]

    def get_answers(self) -> dict[str, int]:
        """
        Возвращает варианты ответа для текущего меню.

        :return: варианты ответа

        ### Пример использования:
        ```py
        sessionAdmins.get_answers()
        ```
        """
        answers: dict[str, int] = {}

        if not self.check_mode():
            self.input.set_choosen([])

        for user in self.get_container():
            answer: str = self.get_answer(user, cut_string = True)
            answer_key: str = answer
            i: int = 1

            while answer_key in answers and i < 100:
                i += 1
                answer_key = cut(f"{answer} ({i})", BUTTON_LENGTH)

            if i >= 100:
                continue

            answers[answer_key] = user.id

        return answers

    def get_actions(self, answers: dict[str, JSONABLE] = {}) -> dict[str, str]:
        """
        Возвращает действия управления администраторами.

        ### Аргументы:
        :param answers: варианты ответа

        :return: actions

        ### Пример использования:
        ```py
        sessionAdmins.get_actions(answers = answers)
        ```
        """
        if self.check_mode():
            return {}

        result: dict[str, str] = self.always_actions.copy()
        users: list[User] = self.get_users_list(max_users = 1000)

        if self.get_access_level(self.user.id) >= 2:
            result["promote"] = ENABLE_CALLBACK

        if any(self.can_demote_user(user) for user in users):
            result["demote"] = DISABLE_CALLBACK

        return result

    def get_promote_bot_actions(self) -> dict[str, str]:
        """
        Возвращает действия повышения прав для bot-администраторов.

        :return: promote bot actions

        ### Пример использования:
        ```py
        sessionAdmins.get_promote_bot_actions()
        ```
        """
        return {
            "ВКонтакте": PROMOTE_VKBOT_CALLBACK,
            "Telegram": PROMOTE_TELEBOT_CALLBACK
        }

    def process_promote_bot_action(self, action: str) -> bool:
        """
        Обрабатывает promote bot action в текущем runtime-контексте.

        ### Аргументы:
        :param action: действие меню

        :return: результат шага сессии

        ### Пример использования:
        ```py
        sessionAdmins.process_promote_bot_action(action = action)
        ```
        """
        bot_key_by_callback: dict[str, BOT_KEY] = {
            PROMOTE_VKBOT_CALLBACK: "vkbot",
            PROMOTE_TELEBOT_CALLBACK: "telebot"
        }

        if action not in bot_key_by_callback:
            return False

        self.pending_bot_key = bot_key_by_callback[action]
        return True

    def process_answer(self, bot_key: BOT_KEY, chat_id: int, answer: str) -> bool:
        """
        Обрабатывает ответ пользователя в текущем runtime-контексте.

        ### Аргументы:
        :param bot_key: ключ транспорта
        :param chat_id: идентификатор чата
        :param answer: ответ пользователя

        :return: результат шага сессии

        ### Пример использования:
        ```py
        sessionAdmins.process_answer(bot_key = bot_key, chat_id = chat_id, answer = answer)
        ```
        """
        if self.check_mode():
            return super().process_answer(bot_key, chat_id, answer)
        return super().process_answer(bot_key, chat_id, answer)

    def process_action(self, bot_key: BOT_KEY, chat_id: int, action: str) -> bool:
        """
        Обрабатывает действие меню в текущем runtime-контексте.

        ### Аргументы:
        :param bot_key: ключ транспорта
        :param chat_id: идентификатор чата
        :param action: действие меню

        :return: результат шага сессии

        ### Пример использования:
        ```py
        sessionAdmins.process_action(bot_key = bot_key, chat_id = chat_id, action = action)
        ```
        """
        if self.check_mode() and self.mode.name in ("create", "promote"):
            if self.process_promote_bot_action(action):
                return True

        if action == ENABLE_CALLBACK:
            self.start_mode("promote")
            return True
        elif action == DISABLE_CALLBACK:
            self.start_mode("demote")
            return True
        return super().process_action(bot_key, chat_id, action)

    def mode_create(self, context: Context | None):
        """
        Переводит session-меню в режим `create`.

        ### Аргументы:
        :param context: контекст обработки события

        ### Пример использования:
        ```py
        sessionAdmins.mode_create(context = context)
        ```
        """
        self.mode_promote(context)

    def mode_demote(self, context: Context | None):
        """
        Переводит session-меню в режим `demote`.

        ### Аргументы:
        :param context: контекст обработки события

        ### Пример использования:
        ```py
        sessionAdmins.mode_demote(context = context)
        ```
        """
        self.mode_change_level(context, "demote_question", -1)

    def mode_change_level(self, context: Context | None, question_key: str, delta: int, allow_empty: bool = False):
        """
        Переводит session-меню в режим `change_level`.

        ### Аргументы:
        :param context: контекст обработки события
        :param question_key: question key
        :param delta: изменение числового значения
        :param allow_empty: allow empty

        ### Пример использования:
        ```py
        sessionAdmins.mode_change_level(context = context, question_key = question_key, delta = delta, allow_empty = allow_empty)
        ```
        """
        if not allow_empty and self.process_empty():
            return

        if not context:
            answers: dict[str, int] = self.get_answers()
            self.input.update(get_phrase(question_key), answers = answers, actions = [], choosen = [], cancel = True, back = True, max = max(2, len(answers)))
            return
        elif context.is_callback() and context.get_callback_string() == CONFIRM_CALLBACK:
            ids: list[int] = []

            for answer in self.input.choosen:
                user_id = self.input.get_answer(answer)

                if is_int(user_id):
                    ids.append(int(user_id))

            changed: int = 0

            for user_id in ids:
                try:
                    if delta > 0:
                        changed += int(self.promote_admin(self.user.id, user_id))
                    else:
                        changed += int(self.demote_admin(self.user.id, user_id))
                except PermissionError:
                    self.show_phrase("access_denied")
                    self.reset()
                    return
                except Exception:
                    continue

            message_key: str = "changed" if changed else "removed_none"
            self.reset(get_phrase(message_key))
            return

        context.remove_handler()

    def mode_promote(self, context: Context | None):
        """
        Переводит session-меню в режим `promote`.

        ### Аргументы:
        :param context: контекст обработки события

        ### Пример использования:
        ```py
        sessionAdmins.mode_promote(context = context)
        ```
        """
        content, is_callback = self.get_command(context)
        bot_actions: dict[str, str] = self.get_promote_bot_actions()

        logger_user_flow.info(
            "mode_promote state: has_context=%s is_callback=%s pending_bot_key=%s pending_chat_id=%s",
            context is not None,
            is_callback,
            self.pending_bot_key,
            self.pending_chat_id,
        )

        if context and context.has_event():
            if is_callback:
                callback_type: str = context.get_callback_string()
                callback_data: str = context.get_callback_string(1)

                if callback_type == ACTION_CALLBACK:
                    if not self.process_action(context.bot.get_bot_key(), context.get_chat_id(), callback_data):
                        context.remove_handler()
                        return

                if self.pending_bot_key and not self.pending_chat_id:
                    self.input.update(
                        "Введите chat_id пользователя для повышения",
                        answers = {},
                        actions = {},
                        choosen = [],
                        cancel = True,
                        back = True,
                        confirm = False,
                        max = 1
                    )
                    return
            elif content:
                if is_int(content):
                    chat_id: int = int(content)

                    if chat_id > 0:
                        self.pending_chat_id = chat_id
                    else:
                        self.incorrect()
                        return
                else:
                    self.incorrect()
                    return

        logger_user_flow.info(
            "mode_promote pending: pending_bot_key=%s pending_chat_id=%s",
            self.pending_bot_key,
            self.pending_chat_id,
        )
        if self.pending_bot_key is not None and self.pending_chat_id is not None:
            if not self.can_promote_by_chat(self.user.id, self.pending_bot_key, self.pending_chat_id):
                self.show_phrase("access_denied")
                self.reset()
                return

            try:
                changed: bool = self.promote_admin_by_chat(self.user.id, self.pending_bot_key, self.pending_chat_id)
            except PermissionError:
                self.show_phrase("access_denied")
                self.reset()
                return
            except ValueError:
                self.incorrect()
                return

            self.reset(get_phrase("changed") if changed else get_phrase("removed_none"))
            return

        if self.pending_bot_key is not None:
            self.input.update(
                f"Введите chat_id пользователя для бота {self.pending_bot_key}",
                answers = {},
                actions = {},
                choosen = [],
                cancel = True,
                back = True,
                confirm = False,
                max = 1
            )
            return

        if self.pending_chat_id is not None:
            question: str = f"Выберите бота для пользователя с идентификатором {self.pending_chat_id}"
            self.input.update(question, answers = {}, actions = bot_actions, choosen = [], cancel = True, back = True, max = 1, confirm = False)
            return

        if context is None or not context.is_callback():
            answers: dict[str, int] = self.get_answers()
            self.input.update(
                get_phrase("promote_question"),
                answers = answers,
                actions = {},
                choosen = [],
                cancel = True,
                back = True,
                max = max(2, len(answers))
            )
            return

        self.mode_change_level(context, "promote_question", 1, allow_empty = True)


class AdminSession(ModeSession):

    """
    Описывает пользовательскую или административную сессию `AdminSession`.
    Сессия хранит состояние текущего пользовательского сценария, обновляет сообщения и завершает себя через общий session lifecycle.

    ### Поля
    - `get_admin`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `get_user`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `toggle_admin_option`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `admin_id`: идентификатор объекта или связанной сущности, по которому runtime восстанавливает связь между слоями.
    - `element_class`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `next_session`: runtime-зависимость или поле, используемое текущим session-сценарием.

    ### Методы
    - `__init__`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `get_admin`: Возвращает администратора из текущего состояния `AdminSession`.
    - `get_user`: Возвращает состояние пользователя из текущего состояния `AdminSession`.
    - `toggle_admin_option`: Меняет флаг доступности или настройку объекта и оставляет остальное состояние без изменений.
    - `get_question`: Возвращает вопрос анкеты или GPT-контекста из текущего состояния `AdminSession`.
    - `get_answers`: Возвращает варианты ответа из текущего состояния `AdminSession`.
    - `get_actions`: Возвращает действия меню из текущего состояния `AdminSession`.
    - `process_action`: Обрабатывает действие меню в текущем пользовательском или transport-layer потоке.
    - `mode_notifications`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `mode_permissions`: runtime-зависимость или поле, используемое текущим session-сценарием.

    ### Жизненный цикл
    Создаётся app-layer кодом, участвует в обработке пользовательского события и сохраняет изменённое состояние через существующие runtime/storage механизмы.

    ### Пример использования
    ```py
    session: AdminSession
    ```
    """
    def __init__(self, session_id: int, context: Context, data: dict, message: Message):
        """
        Создаёт session-объект `AdminSession` и сохраняет состояние пользовательского сценария между входящими событиями.

        ### Аргументы:
        :param session_id: идентификатор сессии
        :param context: контекст обработки события
        :param data: сериализованный словарь
        :param message: сообщение проекта или сообщение конкретного транспорта

        ### Пример использования:
        ```py
        session = AdminSession(session_id = session_id, context = context, data = data, message = message)
        ```
        """
        super().__init__(session_id, context, data, message)
        self.get_admin = context.autocenter.get_admin
        self.get_user = context.autocenter.get_user
        self.toggle_admin_option = context.autocenter.toggle_admin_option

        self.admin_id: int = get_int(data, -1, "element_id")
        self.element_class = None
        self.next_session = None

        self.always_actions.clear()
        self.choosing_actions.clear()
        self.removed_actions.clear()
        self.enabled_actions.clear()

        self.modes.clear()
        self.modes.extend([
            Mode("notifications", self.mode_notifications),
            Mode("permissions", self.mode_permissions)
        ])

        self.input.lang_answers = True

        self.set_mode(data.get("mode", ""))

    @abstractmethod
    def get_admin(self, user_id: int) -> Admin:
        """
        Возвращает администратора по user id.

        ### Аргументы:
        :param user_id: user id

        :return: admin

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        session.get_admin(user_id = user_id)
        ```
        """
        raise NotImplementedError()

    @abstractmethod
    def get_user(self, bot_key: BOT_KEY, chat_id: int) -> User:
        """
        Возвращает привязанного пользователя приложения.

        ### Аргументы:
        :param bot_key: ключ транспорта
        :param chat_id: идентификатор чата

        :return: пользователь приложения

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        session.get_user(bot_key = bot_key, chat_id = chat_id)
        ```
        """
        raise NotImplementedError()

    @abstractmethod
    def toggle_admin_option(self, actor_id: int, user_id: int, category: Literal["notifications", "permissions"], key: str) -> bool:
        """
        Меняет флаг доступности или настройку объекта и оставляет остальное состояние без изменений.

        ### Аргументы:
        :param actor_id: actor id
        :param user_id: user id
        :param category: категория административной настройки
        :param key: ключ записи или настройки

        :return: результат шага сессии

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        session.toggle_admin_option(actor_id = actor_id, user_id = user_id, category = category, key = key)
        ```
        """
        raise NotImplementedError()

    def get_question(self, answers: dict[str, JSONABLE] = {}) -> str:
        """
        Возвращает краткое описание элемента для вывода в чат.

        ### Аргументы:
        :param answers: варианты ответа

        :return: строка вида `Филиал «Название»` или `Элемент «id»`

        ### Пример использования:
        ```py
        session.get_question(answers = answers)
        ```
        """
        admin_id: int = self.admin_id
        admin: Admin = self.get_admin(admin_id)
        name: str = admin.get_display_answer(cut_string = False)

        if self.check_mode():
            return get_phrase(f"{self.mode.name}_admin_single").format(name)
        else:
            return get_phrase("admin_settings").format(name)

    def get_answers(self):
        """
        Возвращает варианты ответа для текущего меню.

        :return: варианты ответа

        ### Пример использования:
        ```py
        session.get_answers()
        ```
        """
        return []

    def get_actions(self, answers: dict[str, JSONABLE] = {}) -> dict[str, str]:
        """
        Возвращает действия для выбранного администратора.

        ### Аргументы:
        :param answers: варианты ответа

        :return: actions

        ### Пример использования:
        ```py
        session.get_actions(answers = answers)
        ```
        """
        callback_by_option: dict[str, str]
        source: dict[str, bool]

        if self.mode and self.mode.name == "notifications":
            admin: Admin = self.get_admin(self.admin_id)
            source = admin.notifications
            callback_by_option = {
                "call_admin": CALL_ADMIN_NOTIFICATION_CALLBACK,
                "new_appointment": NEW_APPOINTMENT_NOTIFICATION_CALLBACK,
            }
        elif self.mode and self.mode.name == "permissions":
            admin: Admin = self.get_admin(self.admin_id)
            source = admin.permissions
            callback_by_option = {
                "answer_users": ANSWER_USERS_CALLBACK,
                "start_dialog": DIALOG_CALLBACK,
            }
        else:
            return {
                get_phrase("notifications"): NOTIFICATIONS_CALLBACK,
                get_phrase("permissions"): PERMISSIONS_CALLBACK,
            }

        actions: dict[str, str] = {}

        for key, value in source.items():
            callback_data: str = callback_by_option.get(key, key)
            flag: str = "✅" if value else "❌"
            text: str = f"{flag} {get_phrase(key)}"
            actions[text] = callback_data

        return actions

    def process_action(self, bot_key: BOT_KEY, chat_id: int, action: str) -> bool:
        """
        Обрабатывает действие меню в текущем runtime-контексте.

        ### Аргументы:
        :param bot_key: ключ транспорта
        :param chat_id: идентификатор чата
        :param action: действие меню

        :return: результат шага сессии

        ### Пример использования:
        ```py
        session.process_action(bot_key = bot_key, chat_id = chat_id, action = action)
        ```
        """
        if not self.check_mode():
            if action in (NOTIFICATIONS_CALLBACK, PERMISSIONS_CALLBACK):
                self.start_mode(action)
                self.input_default()
                return True
            return False

        option_by_callback: dict[str, str] = {
            ANSWER_USERS_CALLBACK: "answer_users",
            DIALOG_CALLBACK: "start_dialog",
            CALL_ADMIN_NOTIFICATION_CALLBACK: "call_admin",
            NEW_APPOINTMENT_NOTIFICATION_CALLBACK: "new_appointment"
        }

        if action not in option_by_callback:
            return False

        option_key: str = option_by_callback.get(action)
        changed: bool = self.toggle_admin_option(self.user.id, self.admin_id, self.mode.name, option_key)

        if not changed:
            self.show_phrase("access_denied")
            return True

        admin: Admin = self.get_admin(self.admin_id)
        option_enabled: bool = bool(getattr(admin, self.mode.name).get(option_key))
        phrase_key: str

        if self.mode.name == "permissions":
            phrase_key = "admin_permission_enabled" if option_enabled else "admin_permission_disabled"
        else:
            phrase_key = "admin_notification_enabled" if option_enabled else "admin_notification_disabled"

        message: str = get_phrase(phrase_key).format(admin.get_display_answer(cut_string = False), get_phrase(option_key))
        self.show_message(message)

        return True

    def mode_notifications(self, context: Context | None):
        """
        Переводит session-меню в режим `notifications`.

        ### Аргументы:
        :param context: контекст обработки события

        ### Пример использования:
        ```py
        session.mode_notifications(context = context)
        ```
        """
        content, is_callback = self.get_command(context)

        if is_callback:
            callback_data: str = context.get_callback_string(1)
            self.process_action(context.bot.get_bot_key(), context.get_chat_id(), callback_data)

        self.input_default()

    def mode_permissions(self, context: Context | None):
        """
        Переводит session-меню в режим `permissions`.

        ### Аргументы:
        :param context: контекст обработки события

        ### Пример использования:
        ```py
        session.mode_permissions(context = context)
        ```
        """
        content, is_callback = self.get_command(context)

        if is_callback:
            callback_data: str = context.get_callback_string(1)
            self.process_action(context.bot.get_bot_key(), context.get_chat_id(), callback_data)

        self.input_default()
