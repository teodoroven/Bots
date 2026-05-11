"""
Описывает repository-классы, которые инкапсулируют SQLAlchemy-запросы storage-layer.
Модуль относится к архитектурной зоне: слой хранения `db`, который изолирует SQLAlchemy, репозитории и документы состояния от app-layer.

### Публичные классы
- `AppStateRepository`: репозиторий глобального состояния и счётчиков.
- `UserRepository`: репозиторий пользователей и chat id.
- `AdminRepository`: репозиторий администраторов.
- `ConversationRepository`: репозиторий диалогов.
- `BotConfigRepository`: репозиторий конфигураций ботов.
- `DocumentRepository`: репозиторий документов хранилища.

### Публичные функции
- Публичные функции отсутствуют.

### Связи
Используется storage-слоем и runtime-логикой приложения для чтения, сохранения и миграции состояния без прямой зависимости app-layer от деталей SQLAlchemy.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from sqlalchemy import delete
from sqlalchemy import select
from sqlalchemy.orm import Session

from db.models import AdminORM
from db.models import AppStateORM
from db.models import BotConfigORM
from db.models import ConversationORM
from db.models import StorageDocumentORM
from db.models import UserChatIdORM
from db.models import UserORM


class AppStateRepository:
    """
    Инкапсулирует SQL-операции для appstate.
    Репозиторий принимает готовую SQLAlchemy-сессию и выполняет одну группу запросов. Commit/rollback контролируется вызывающим storage-контекстом.

    ### Поля
    - `STATE_ID`: фиксированный ключ единственной строки состояния приложения.
    - `COUNTER_COLUMNS`: соответствие имён счётчиков колонкам таблицы состояния.
    - `session`: SQLAlchemy-сессия или app-layer сессия, с которой работает объект.

    ### Методы
    - `__init__`: Создаёт объект и сохраняет SQLAlchemy-сессию или фабрику сессий для операций repository-layer.
    - `get_or_create`: Возвращает or create из текущего состояния `AppStateRepository`.
    - `load`: Загружает JSON-представление и восстанавливает поля объекта.
    - `save`: Записывает текущее JSON-представление через storage API.
    - `ensure_at_least`: Гарантирует наличие или минимальное значение для сущности: at least.
    - `next_id`: Выполняет storage-операцию через репозиторий или SQLAlchemy-сессию.

    ### Жизненный цикл
    Объект создаётся на время storage-операции или описывает таблицу; внешние слои работают через storage API и не управляют SQLAlchemy-сессией напрямую.

    ### Пример использования
    ```py
    repository: AppStateRepository
    ```
    """
    STATE_ID: int = 1
    COUNTER_COLUMNS: dict[str, str] = {
        "message": "message_id",
        "session": "session_id",
        "event": "event_id",
        "user": "user_id",
        "conv": "conv_id",
        "conversation": "conv_id",
        "client": "client_id",
        "element": "element_id",
        "message_queue": "message_queue_id",
    }

    def __init__(self, session: Session):
        """
        Создаёт `AppStateRepository` и сохраняет SQLAlchemy-сессию или фабрику сессий для операций repository-layer.

        ### Аргументы:
        :param session: активная пользовательская или административная сессия

        ### Пример использования:
        ```py
        repository: AppStateRepository = AppStateRepository(session = session)
        ```
        """
        self.session: Session = session

    def get_or_create(self) -> AppStateORM:
        """
        Возвращает существующую storage-запись или создаёт её.

        :return: or create

        ### Пример использования:
        ```py
        repository.get_or_create()
        ```
        """
        state: AppStateORM | None = self.session.get(AppStateORM, self.STATE_ID)

        if state is None:
            state = AppStateORM(id = self.STATE_ID)
            self.session.add(state)
            self.session.flush()

        return state

    def load(self) -> dict[str, int | bool | list[int]]:
        """
        Загружает JSON-представление и восстанавливает поля объекта.

        :return: восстановленный объект или загруженное состояние

        ### Пример использования:
        ```py
        repository.load()
        ```
        """
        state: AppStateORM = self.get_or_create()
        return {
            "message_id": int(state.message_id),
            "session_id": int(state.session_id),
            "event_id": int(state.event_id),
            "user_id": int(state.user_id),
            "conv_id": int(state.conv_id),
            "client_id": int(state.client_id),
            "element_id": int(state.element_id),
            "message_queue_id": int(state.message_queue_id),
            "bot_enabled": bool(state.bot_enabled),
            "admins": [],
        }

    def save(self, data: dict[str, Any]):
        """
        Записывает текущее JSON-представление через storage API.

        ### Аргументы:
        :param data: сериализованный словарь

        ### Пример использования:
        ```py
        repository.save(data = data)
        ```
        """
        state: AppStateORM = self.get_or_create()
        key: str

        for key in (
                "message_id",
                "session_id",
                "event_id",
                "user_id",
                "conv_id",
                "client_id",
                "element_id",
                "message_queue_id",
                ):
            if key in data and data[key] is not None:
                setattr(state, key, int(data[key]))

        if "bot_enabled" in data:
            state.bot_enabled = bool(data["bot_enabled"])

        self.session.flush()

    def ensure_at_least(self, **counters: int):
        """
        Гарантирует наличие или минимальное значение для сущности: at least.

        ### Примеры вызова:
        ```py
        repository.ensure_at_least(**kwargs)
        ```
        """
        state: AppStateORM = self.get_or_create()
        name: str
        value: int

        for name, value in counters.items():
            column: str = self.COUNTER_COLUMNS.get(name, name)

            if hasattr(state, column):
                setattr(state, column, max(int(getattr(state, column)), int(value)))

        self.session.flush()

    def next_id(self, counter_name: str) -> int:
        """
        Выполняет storage-операцию через репозиторий или SQLAlchemy-сессию.

        ### Аргументы:
        :param counter_name: имя счётчика идентификаторов

        :return: данные, считанные из storage

        ### Пример использования:
        ```py
        repository.next_id(counter_name = counter_name)
        ```
        """
        state: AppStateORM = self.get_or_create()
        column: str = self.COUNTER_COLUMNS[counter_name]
        value: int = int(getattr(state, column)) + 1
        setattr(state, column, value)
        self.session.flush()
        return value


class UserRepository:

    """
    Инкапсулирует SQL-операции для состояние пользователя.
    Репозиторий принимает готовую SQLAlchemy-сессию и выполняет одну группу запросов. Commit/rollback контролируется вызывающим storage-контекстом.

    ### Поля
    - `session`: SQLAlchemy-сессия или app-layer сессия, с которой работает объект.

    ### Методы
    - `__init__`: Создаёт объект и сохраняет SQLAlchemy-сессию или фабрику сессий для операций repository-layer.
    - `get_or_create`: Возвращает or create из текущего состояния `UserRepository`.
    - `load_payload`: Загружает payload из storage.
    - `save_payload`: Сохраняет JSON payload в таблицу, которой управляет этот repository.
    - `add_chat_id`: Сохраняет связь пользователя с chat id конкретного транспорта.
    - `find_user_id`: Ищет user id по данным, которые пришли из вызывающего слоя.
    - `load_chat_ids`: Загружает chat ids из storage.
    - `replace_chat_ids`: Полностью заменяет сохранённые данные для сущности: chat ids.
    - `list_user_ids`: Возвращает внутренние id пользователей, для которых есть storage-записи.

    ### Жизненный цикл
    Объект создаётся на время storage-операции или описывает таблицу; внешние слои работают через storage API и не управляют SQLAlchemy-сессией напрямую.

    ### Пример использования
    ```py
    repository: UserRepository
    ```
    """
    def __init__(self, session: Session):
        """
        Создаёт `UserRepository` и сохраняет SQLAlchemy-сессию или фабрику сессий для операций repository-layer.

        ### Аргументы:
        :param session: активная пользовательская или административная сессия

        ### Пример использования:
        ```py
        repository: UserRepository = UserRepository(session = session)
        ```
        """
        self.session: Session = session

    def get_or_create(self, user_id: int, access_level: int = 0) -> UserORM:
        """
        Возвращает существующую storage-запись или создаёт её.

        ### Аргументы:
        :param user_id: user id
        :param access_level: уровень доступа

        :return: or create

        ### Пример использования:
        ```py
        repository.get_or_create(user_id = user_id, access_level = access_level)
        ```
        """
        user: UserORM | None = self.session.get(UserORM, int(user_id))

        if user is None:
            user = UserORM(id = int(user_id), access_level = int(access_level), payload = {})
            self.session.add(user)
            self.session.flush()

        return user

    def load_payload(self, user_id: int) -> dict[str, Any]:
        """
        Загружает payload из storage.

        ### Аргументы:
        :param user_id: внутренний идентификатор пользователя в app-layer

        :return: сериализованные данные для payload

        ### Пример использования:
        ```py
        repository.load_payload(user_id = user_id)
        ```
        """
        user: UserORM | None = self.session.get(UserORM, int(user_id))
        return dict(user.payload) if user is not None and user.payload else {}

    def save_payload(self, user_id: int, payload: dict[str, Any], access_level: int = 0):
        """
        Сохраняет JSON payload в таблицу, которой управляет этот repository.

        ### Аргументы:
        :param user_id: внутренний идентификатор пользователя в app-layer
        :param payload: сериализованный словарь, который хранится в storage
        :param access_level: уровень доступа пользователя или администратора

        ### Пример использования:
        ```py
        repository.save_payload(user_id = user_id, payload = payload, access_level = access_level)
        ```
        """
        user: UserORM = self.get_or_create(int(user_id), int(access_level))
        user.payload = dict(payload)
        user.access_level = int(payload.get("access_level", access_level) or 0)
        self.session.flush()

    def add_chat_id(self, user_id: int, bot_key: str, chat_id: int):
        """
        Сохраняет связь пользователя с chat id конкретного транспорта.

        ### Аргументы:
        :param user_id: внутренний идентификатор пользователя в app-layer
        :param bot_key: ключ транспорта, например `vkbot` или `telebot`
        :param chat_id: идентификатор чата в конкретной платформе

        ### Пример использования:
        ```py
        repository.add_chat_id(user_id = user_id, bot_key = bot_key, chat_id = chat_id)
        ```
        """
        self.get_or_create(int(user_id))
        statement = select(UserChatIdORM).where(
            UserChatIdORM.bot_key == str(bot_key),
            UserChatIdORM.chat_id == int(chat_id),
        )
        row: UserChatIdORM | None = self.session.scalar(statement)

        if row is None:
            self.session.add(UserChatIdORM(user_id = int(user_id), bot_key = str(bot_key), chat_id = int(chat_id)))
        elif row.user_id != int(user_id):
            row.user_id = int(user_id)

        self.session.flush()

    def find_user_id(self, bot_key: str, chat_id: int) -> int | None:
        """
        Ищет user id по данным, которые пришли из вызывающего слоя.

        ### Аргументы:
        :param bot_key: ключ транспорта, например `vkbot` или `telebot`
        :param chat_id: идентификатор чата в конкретной платформе

        :return: найденное значение для user id или None, если записи нет

        ### Пример использования:
        ```py
        repository.find_user_id(bot_key = bot_key, chat_id = chat_id)
        ```
        """
        statement = select(UserChatIdORM.user_id).where(
            UserChatIdORM.bot_key == str(bot_key),
            UserChatIdORM.chat_id == int(chat_id),
        )
        user_id: int | None = self.session.scalar(statement)
        return int(user_id) if user_id is not None else None

    def load_chat_ids(self) -> dict[int, dict[str, set[int]]]:
        """
        Загружает chat ids из storage.

        :return: сериализованные данные для chat ids

        ### Примеры вызова:
        ```py
        repository.load_chat_ids()
        ```
        """
        result: dict[int, dict[str, set[int]]] = {}
        rows: Iterable[UserChatIdORM] = self.session.scalars(select(UserChatIdORM))
        row: UserChatIdORM

        for row in rows:
            user_ids: dict[str, set[int]] = result.setdefault(int(row.user_id), {})
            chat_ids: set[int] = user_ids.setdefault(str(row.bot_key), set())
            chat_ids.add(int(row.chat_id))

        return result

    def replace_chat_ids(self, users_ids: dict[int, dict[str, set[int] | list[int]]]):
        """
        Полностью заменяет сохранённые данные для сущности: chat ids.

        ### Аргументы:
        :param users_ids: соответствие user_id, transport key и набора chat_id

        ### Пример использования:
        ```py
        repository.replace_chat_ids(users_ids = users_ids)
        ```
        """
        self.session.execute(delete(UserChatIdORM))
        user_id: int
        bot_key: str
        id_set: set[int] | list[int]

        for user_id, chat_ids in users_ids.items():
            self.get_or_create(int(user_id))

            for bot_key, id_set in chat_ids.items():
                chat_id: int

                for chat_id in id_set:
                    self.session.add(UserChatIdORM(user_id = int(user_id), bot_key = str(bot_key), chat_id = int(chat_id)))

        self.session.flush()

    def list_user_ids(self) -> list[int]:
        """
        Возвращает внутренние id пользователей, для которых есть storage-записи.

        :return: список внутренних id пользователей

        ### Примеры вызова:
        ```py
        repository.list_user_ids()
        ```
        """
        return [int(user_id) for user_id in self.session.scalars(select(UserORM.id))]


class AdminRepository:

    """
    Инкапсулирует SQL-операции для администратора.
    Репозиторий принимает готовую SQLAlchemy-сессию и выполняет одну группу запросов. Commit/rollback контролируется вызывающим storage-контекстом.

    ### Поля
    - `session`: SQLAlchemy-сессия или app-layer сессия, с которой работает объект.

    ### Методы
    - `__init__`: Создаёт объект и сохраняет SQLAlchemy-сессию или фабрику сессий для операций repository-layer.
    - `load_all`: Загружает all из storage.
    - `replace_all`: Полностью заменяет сохранённые данные для сущности: all.

    ### Жизненный цикл
    Объект создаётся на время storage-операции или описывает таблицу; внешние слои работают через storage API и не управляют SQLAlchemy-сессией напрямую.

    ### Пример использования
    ```py
    repository: AdminRepository
    ```
    """
    def __init__(self, session: Session):
        """
        Создаёт `AdminRepository` и сохраняет SQLAlchemy-сессию или фабрику сессий для операций repository-layer.

        ### Аргументы:
        :param session: активная пользовательская или административная сессия

        ### Пример использования:
        ```py
        repository: AdminRepository = AdminRepository(session = session)
        ```
        """
        self.session: Session = session

    def load_all(self) -> dict[int, dict[str, Any]]:
        """
        Загружает all из storage.

        :return: сериализованные данные для all

        ### Примеры вызова:
        ```py
        repository.load_all()
        ```
        """
        result: dict[int, dict[str, Any]] = {}
        rows: Iterable[AdminORM] = self.session.scalars(select(AdminORM))
        row: AdminORM

        for row in rows:
            result[int(row.user_id)] = {
                "access_level": int(row.access_level),
                "permissions": dict(row.permissions or {}),
                "notifications": dict(row.notifications or {}),
            }

        return result

    def replace_all(self, admins: dict[int, dict[str, Any]]):
        """
        Полностью заменяет сохранённые данные для сущности: all.

        ### Аргументы:
        :param admins: словарь настроек администраторов по user_id

        ### Пример использования:
        ```py
        repository.replace_all(admins = admins)
        ```
        """
        self.session.execute(delete(AdminORM))
        user_repository: UserRepository = UserRepository(self.session)
        user_id: int
        data: dict[str, Any]

        for user_id, data in admins.items():
            user_repository.get_or_create(int(user_id), int(data.get("access_level") or 0))
            self.session.add(
                AdminORM(
                    user_id = int(user_id),
                    access_level = int(data.get("access_level") or 0),
                    permissions = dict(data.get("permissions") or {}),
                    notifications = dict(data.get("notifications") or {}),
                )
            )

        self.session.flush()


class ConversationRepository:

    """
    Инкапсулирует SQL-операции для историю диалога.
    Репозиторий принимает готовую SQLAlchemy-сессию и выполняет одну группу запросов. Commit/rollback контролируется вызывающим storage-контекстом.

    ### Поля
    - `session`: SQLAlchemy-сессия или app-layer сессия, с которой работает объект.

    ### Методы
    - `__init__`: Создаёт объект и сохраняет SQLAlchemy-сессию или фабрику сессий для операций repository-layer.
    - `load_payload`: Загружает payload из storage.
    - `save_payload`: Сохраняет JSON payload в таблицу, которой управляет этот repository.
    - `list_ids`: Возвращает id сохранённых live-диалогов.

    ### Жизненный цикл
    Объект создаётся на время storage-операции или описывает таблицу; внешние слои работают через storage API и не управляют SQLAlchemy-сессией напрямую.

    ### Пример использования
    ```py
    repository: ConversationRepository
    ```
    """
    def __init__(self, session: Session):
        """
        Создаёт `ConversationRepository` и сохраняет SQLAlchemy-сессию или фабрику сессий для операций repository-layer.

        ### Аргументы:
        :param session: активная пользовательская или административная сессия

        ### Пример использования:
        ```py
        repository: ConversationRepository = ConversationRepository(session = session)
        ```
        """
        self.session: Session = session

    def load_payload(self, conv_id: int) -> dict[str, Any]:
        """
        Загружает payload из storage.

        ### Аргументы:
        :param conv_id: идентификатор сохранённого диалога

        :return: сериализованные данные для payload

        ### Пример использования:
        ```py
        repository.load_payload(conv_id = conv_id)
        ```
        """
        conversation: ConversationORM | None = self.session.get(ConversationORM, int(conv_id))
        return dict(conversation.payload) if conversation is not None and conversation.payload else {}

    def save_payload(self, conv_id: int, payload: dict[str, Any]):
        """
        Сохраняет JSON payload в таблицу, которой управляет этот repository.

        ### Аргументы:
        :param conv_id: идентификатор сохранённого диалога
        :param payload: сериализованный словарь, который хранится в storage

        ### Пример использования:
        ```py
        repository.save_payload(conv_id = conv_id, payload = payload)
        ```
        """
        conversation: ConversationORM | None = self.session.get(ConversationORM, int(conv_id))

        if conversation is None:
            conversation = ConversationORM(id = int(conv_id), payload = dict(payload))
            self.session.add(conversation)
        else:
            conversation.payload = dict(payload)

        self.session.flush()

    def list_ids(self) -> list[int]:
        """
        Возвращает id сохранённых live-диалогов.

        :return: список id сохранённых диалогов

        ### Примеры вызова:
        ```py
        repository.list_ids()
        ```
        """
        statement = select(ConversationORM.id).order_by(ConversationORM.id)
        return [int(conv_id) for conv_id in self.session.scalars(statement)]


class BotConfigRepository:

    """
    Инкапсулирует SQL-операции для botconfig.
    Репозиторий принимает готовую SQLAlchemy-сессию и выполняет одну группу запросов. Commit/rollback контролируется вызывающим storage-контекстом.

    ### Поля
    - `session`: SQLAlchemy-сессия или app-layer сессия, с которой работает объект.

    ### Методы
    - `__init__`: Создаёт объект и сохраняет SQLAlchemy-сессию или фабрику сессий для операций repository-layer.
    - `load_all`: Загружает all из storage.
    - `replace_all`: Полностью заменяет сохранённые данные для сущности: all.

    ### Жизненный цикл
    Объект создаётся на время storage-операции или описывает таблицу; внешние слои работают через storage API и не управляют SQLAlchemy-сессией напрямую.

    ### Пример использования
    ```py
    repository: BotConfigRepository
    ```
    """
    def __init__(self, session: Session):
        """
        Создаёт `BotConfigRepository` и сохраняет SQLAlchemy-сессию или фабрику сессий для операций repository-layer.

        ### Аргументы:
        :param session: активная пользовательская или административная сессия

        ### Пример использования:
        ```py
        repository: BotConfigRepository = BotConfigRepository(session = session)
        ```
        """
        self.session: Session = session

    def load_all(self) -> dict[str, list[dict[str, Any]]]:
        """
        Загружает all из storage.

        :return: сериализованные данные для all

        ### Примеры вызова:
        ```py
        repository.load_all()
        ```
        """
        statement = select(BotConfigORM).order_by(BotConfigORM.position, BotConfigORM.id)
        bots: list[dict[str, Any]] = []
        row: BotConfigORM

        for row in self.session.scalars(statement):
            bots.append({
                "bot_key": str(row.bot_key),
                "token": str(row.token),
                "name": str(row.name),
                "group_id": int(row.group_id),
            })

        return {"bots": bots}

    def replace_all(self, data: dict[str, list[dict[str, Any]]]):
        """
        Полностью заменяет сохранённые данные для сущности: all.

        ### Аргументы:
        :param data: JSON-совместимые данные для соответствующего repository

        ### Пример использования:
        ```py
        repository.replace_all(data = data)
        ```
        """
        self.session.execute(delete(BotConfigORM))
        position: int
        bot_data: dict[str, Any]

        for position, bot_data in enumerate(data.get("bots", [])):
            self.session.add(
                BotConfigORM(
                    position = int(position),
                    bot_key = str(bot_data["bot_key"]),
                    token = str(bot_data["token"]),
                    name = str(bot_data["name"]),
                    group_id = int(bot_data["group_id"]),
                )
            )

        self.session.flush()


class DocumentRepository:

    """
    Инкапсулирует SQL-операции для служебных JSON-документов.
    Репозиторий принимает готовую SQLAlchemy-сессию и выполняет одну группу запросов. Commit/rollback контролируется вызывающим storage-контекстом.

    ### Поля
    - `session`: SQLAlchemy-сессия или app-layer сессия, с которой работает объект.

    ### Методы
    - `__init__`: Создаёт объект и сохраняет SQLAlchemy-сессию или фабрику сессий для операций repository-layer.
    - `load`: Загружает JSON-представление и восстанавливает поля объекта.
    - `save`: Записывает текущее JSON-представление через storage API.
    - `ensure_defaults`: Создаёт обязательные storage-записи с настройками по умолчанию, если их ещё нет.

    ### Жизненный цикл
    Объект создаётся на время storage-операции или описывает таблицу; внешние слои работают через storage API и не управляют SQLAlchemy-сессией напрямую.

    ### Пример использования
    ```py
    repository: DocumentRepository
    ```
    """
    def __init__(self, session: Session):
        """
        Создаёт `DocumentRepository` и сохраняет SQLAlchemy-сессию или фабрику сессий для операций repository-layer.

        ### Аргументы:
        :param session: активная пользовательская или административная сессия

        ### Пример использования:
        ```py
        repository: DocumentRepository = DocumentRepository(session = session)
        ```
        """
        self.session: Session = session

    def load(self, key: str) -> dict[str, Any]:
        """
        Загружает JSON-представление и восстанавливает поля объекта.

        ### Аргументы:
        :param key: ключ записи или настройки

        :return: восстановленный объект или загруженное состояние

        ### Пример использования:
        ```py
        repository.load(key = key)
        ```
        """
        document: StorageDocumentORM | None = self.session.get(StorageDocumentORM, str(key))
        return dict(document.payload) if document is not None and document.payload else {}

    def save(self, key: str, payload: dict[str, Any]):
        """
        Записывает текущее JSON-представление через storage API.

        ### Аргументы:
        :param key: ключ записи или настройки
        :param payload: JSON-совместимое состояние

        ### Пример использования:
        ```py
        repository.save(key = key, payload = payload)
        ```
        """
        document: StorageDocumentORM | None = self.session.get(StorageDocumentORM, str(key))

        if document is None:
            document = StorageDocumentORM(key = str(key), payload = dict(payload))
            self.session.add(document)
        else:
            document.payload = dict(payload)

        self.session.flush()

    def ensure_defaults(self, defaults: dict[str, dict[str, Any]]):
        """
        Гарантирует корректное состояние для defaults.

        ### Аргументы:
        :param defaults: значения по умолчанию для создаваемой записи

        ### Пример использования:
        ```py
        repository.ensure_defaults(defaults = defaults)
        ```
        """
        key: str
        payload: dict[str, Any]

        for key, payload in defaults.items():
            if self.session.get(StorageDocumentORM, str(key)) is None:
                self.session.add(StorageDocumentORM(key = str(key), payload = dict(payload)))

        self.session.flush()
