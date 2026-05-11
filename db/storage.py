"""
Описывает storage API и SQLAlchemy-реализацию хранилища приложения.
Модуль относится к архитектурной зоне: слой хранения `db`, который изолирует SQLAlchemy, репозитории и документы состояния от app-layer.

### Публичные классы
- `Storage`: абстрактный контракт хранилища приложения.
- `SqlAlchemyStorage`: SQLAlchemy-реализация хранилища приложения.

### Публичные функции
- Публичные функции отсутствуют.

### Связи
Используется storage-слоем и runtime-логикой приложения для чтения, сохранения и миграции состояния без прямой зависимости app-layer от деталей SQLAlchemy.
"""

from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from typing import Any

from sqlalchemy.orm import Session
from sqlalchemy.orm import sessionmaker

from db.repositories import AdminRepository
from db.repositories import AppStateRepository
from db.repositories import BotConfigRepository
from db.repositories import ConversationRepository
from db.repositories import DocumentRepository
from db.repositories import UserRepository
from db.session import SessionLocal
from db.session import get_db_session


class Storage(ABC):

    """
    Задаёт контракт storage-layer для состояния приложения.
    Абстракция скрывает SQLAlchemy и репозитории от app-layer. Реализации читают и записывают пользователей, ботов, документы, диалоги, счётчики и общее состояние приложения.

    ### Методы
    - `ensure_defaults`: Создаёт обязательные storage-записи с настройками по умолчанию, если их ещё нет.
    - `load_app_state`: Загружает состояние приложения из storage.
    - `save_app_state`: Сохраняет JSON-совместимое состояние приложения в storage.
    - `next_id`: Возвращает следующий числовой идентификатор для именованного счётчика и увеличивает его в storage.
    - `ensure_counters_at_least`: Поднимает сохранённые счётчики до заданных минимальных значений, не уменьшая уже большие значения.
    - `load_user`: Загружает состояние пользователя из storage.
    - `save_user`: Сохраняет сериализованное состояние пользователя в storage.
    - `load_user_ids`: Загружает связи пользователей с chat_id по транспортам из storage.
    - `save_user_ids`: Заменяет сохранённые связи пользователей с chat_id по транспортам.
    - `add_user_chat_id`: Сохраняет связь пользователя с chat_id в конкретном транспорте.

    ### Жизненный цикл
    Объект создаётся на время storage-операции или описывает таблицу; внешние слои работают через storage API и не управляют SQLAlchemy-сессией напрямую.

    ### Пример использования
    ```py
    def load_state(storage: Storage):
        return storage.load_app_state()
    ```
    """
    @abstractmethod
    def ensure_defaults(self):
        """
        Создаёт обязательные storage-записи с настройками по умолчанию, если их ещё нет.

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Примеры вызова:
        ```py
        storage.ensure_defaults()
        ```
        """
        raise NotImplementedError()

    @abstractmethod
    def load_app_state(self) -> dict[str, Any]:
        """
        Загружает состояние приложения из storage.

        :return: сериализованные данные состояния приложения

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Примеры вызова:
        ```py
        storage.load_app_state()
        ```
        """
        raise NotImplementedError()

    @abstractmethod
    def save_app_state(self, data: dict[str, Any]):
        """
        Сохраняет JSON-совместимое состояние приложения в storage.

        ### Аргументы:
        :param data: JSON-совместимые данные для соответствующего repository

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        storage.save_app_state(data = data)
        ```
        """
        raise NotImplementedError()

    @abstractmethod
    def next_id(self, counter_name: str) -> int:
        """
        Возвращает следующий числовой идентификатор для именованного счётчика и увеличивает его в storage.

        ### Аргументы:
        :param counter_name: имя счётчика, для которого нужен следующий идентификатор

        :return: данные, считанные из storage

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        storage.next_id(counter_name = counter_name)
        ```
        """
        raise NotImplementedError()

    @abstractmethod
    def ensure_counters_at_least(self, **counters: int):
        """
        Поднимает сохранённые счётчики до заданных минимальных значений, не уменьшая уже большие значения.

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Примеры вызова:
        ```py
        storage.ensure_counters_at_least(**kwargs)
        ```
        """
        raise NotImplementedError()

    @abstractmethod
    def load_user(self, user_id: int) -> dict[str, Any]:
        """
        Загружает состояние пользователя из storage.

        ### Аргументы:
        :param user_id: внутренний идентификатор пользователя в app-layer

        :return: сериализованные данные состояния пользователя

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        storage.load_user(user_id = user_id)
        ```
        """
        raise NotImplementedError()

    @abstractmethod
    def save_user(self, user_id: int, payload: dict[str, Any], access_level: int = 0):
        """
        Сохраняет сериализованное состояние пользователя в storage.

        ### Аргументы:
        :param user_id: внутренний идентификатор пользователя в app-layer
        :param payload: сериализованный словарь, который хранится в storage
        :param access_level: уровень доступа пользователя или администратора

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        storage.save_user(user_id = user_id, payload = payload, access_level = access_level)
        ```
        """
        raise NotImplementedError()

    @abstractmethod
    def load_user_ids(self) -> dict[int, dict[str, set[int]]]:
        """
        Загружает связи пользователей с chat_id по транспортам из storage.

        :return: сериализованные данные для связи пользователей с chat_id по транспортам

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Примеры вызова:
        ```py
        storage.load_user_ids()
        ```
        """
        raise NotImplementedError()

    @abstractmethod
    def save_user_ids(self, users_ids: dict[int, dict[str, set[int] | list[int]]]):
        """
        Заменяет сохранённые связи пользователей с chat_id по транспортам.

        ### Аргументы:
        :param users_ids: соответствие user_id, transport key и набора chat_id

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        storage.save_user_ids(users_ids = users_ids)
        ```
        """
        raise NotImplementedError()

    @abstractmethod
    def add_user_chat_id(self, user_id: int, bot_key: str, chat_id: int):
        """
        Сохраняет связь пользователя с chat_id в конкретном транспорте.

        ### Аргументы:
        :param user_id: внутренний идентификатор пользователя в app-layer
        :param bot_key: ключ транспорта, например `vkbot` или `telebot`
        :param chat_id: идентификатор чата в конкретной платформе

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        storage.add_user_chat_id(user_id = user_id, bot_key = bot_key, chat_id = chat_id)
        ```
        """
        raise NotImplementedError()

    @abstractmethod
    def find_user_id(self, bot_key: str, chat_id: int) -> int | None:
        """
        Ищет user id по данным, которые пришли из вызывающего слоя.

        ### Аргументы:
        :param bot_key: ключ транспорта, например `vkbot` или `telebot`
        :param chat_id: идентификатор чата в конкретной платформе

        :return: найденное значение для user id или None, если записи нет

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        storage.find_user_id(bot_key = bot_key, chat_id = chat_id)
        ```
        """
        raise NotImplementedError()

    @abstractmethod
    def load_admins(self) -> dict[int, dict[str, Any]]:
        """
        Загружает настройки администраторов из storage.

        :return: сериализованные данные для настройки администраторов

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Примеры вызова:
        ```py
        storage.load_admins()
        ```
        """
        raise NotImplementedError()

    @abstractmethod
    def save_admins(self, admins: dict[int, dict[str, Any]]):
        """
        Сохраняет список администраторов и их права в storage.

        ### Аргументы:
        :param admins: словарь настроек администраторов по user_id

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        storage.save_admins(admins = admins)
        ```
        """
        raise NotImplementedError()

    @abstractmethod
    def list_conversation_ids(self) -> list[int]:
        """
        Возвращает id всех сохранённых live-диалогов.

        :return: список id сохранённых диалогов

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Примеры вызова:
        ```py
        storage.list_conversation_ids()
        ```
        """
        raise NotImplementedError()

    @abstractmethod
    def load_conversation(self, conv_id: int) -> dict[str, Any]:
        """
        Загружает историю диалога из storage.

        ### Аргументы:
        :param conv_id: идентификатор сохранённого диалога

        :return: сериализованный снимок истории диалога

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        storage.load_conversation(conv_id = conv_id)
        ```
        """
        raise NotImplementedError()

    @abstractmethod
    def save_conversation(self, conv_id: int, payload: dict[str, Any]):
        """
        Сохраняет JSON-снимок live-диалога в storage.

        ### Аргументы:
        :param conv_id: идентификатор сохранённого диалога
        :param payload: сериализованный словарь, который хранится в storage

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        storage.save_conversation(conv_id = conv_id, payload = payload)
        ```
        """
        raise NotImplementedError()

    @abstractmethod
    def load_document(self, key: str) -> dict[str, Any]:
        """
        Загружает служебный JSON-документ из storage.

        ### Аргументы:
        :param key: ключ служебного документа или набора команд

        :return: сериализованные данные служебного JSON-документа

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        storage.load_document(key = key)
        ```
        """
        raise NotImplementedError()

    @abstractmethod
    def save_document(self, key: str, payload: dict[str, Any]):
        """
        Сохраняет служебный JSON-документ в storage.

        ### Аргументы:
        :param key: ключ служебного документа или набора команд
        :param payload: сериализованный словарь, который хранится в storage

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        storage.save_document(key = key, payload = payload)
        ```
        """
        raise NotImplementedError()

    @abstractmethod
    def load_bots(self) -> dict[str, list[dict[str, Any]]]:
        """
        Загружает конфигурации транспортных ботов из storage.

        :return: сериализованные данные для конфигурации транспортных ботов

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Примеры вызова:
        ```py
        storage.load_bots()
        ```
        """
        raise NotImplementedError()

    @abstractmethod
    def save_bots(self, data: dict[str, list[dict[str, Any]]]):
        """
        Сохраняет конфигурации transport-ботов в storage.

        ### Аргументы:
        :param data: JSON-совместимые данные для соответствующего repository

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        storage.save_bots(data = data)
        ```
        """
        raise NotImplementedError()

    @abstractmethod
    def load_commands(self, key: str) -> dict[str, dict[str, Any]]:
        """
        Загружает команды интерфейса из storage.

        ### Аргументы:
        :param key: ключ служебного документа или набора команд

        :return: сериализованные команды интерфейса

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        storage.load_commands(key = key)
        ```
        """
        raise NotImplementedError()

    @abstractmethod
    def load_phrases(self) -> dict[str, dict[str, dict[str, list[str]]]]:
        """
        Загружает локализованные фразы из storage.

        :return: сериализованные локализованные фразы

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Примеры вызова:
        ```py
        storage.load_phrases()
        ```
        """
        raise NotImplementedError()


class SqlAlchemyStorage(Storage):

    """
    Реализует storage-layer поверх SQLAlchemy-сессий и репозиториев.
    Каждый публичный метод открывает короткую SQLAlchemy session через `get_db_session`, вызывает соответствующий repository, а commit/rollback выполняет context manager. Из app-layer наружу выходят только JSON-совместимые структуры.

    ### Поля
    - `session_factory`: фабрика SQLAlchemy-сессий для коротких storage-операций.

    ### Методы
    - `__init__`: Сохраняет фабрику SQLAlchemy-сессий.
    - `ensure_defaults`: Через `AppStateRepository` создаёт обязательные storage-записи, если их нет.
    - `load_app_state`: Через `AppStateRepository` читает состояние приложения.
    - `save_app_state`: Через `AppStateRepository` сохраняет состояние приложения.
    - `next_id`: Через `AppStateRepository` увеличивает и возвращает именованный счётчик.
    - `ensure_counters_at_least`: Через `AppStateRepository` поднимает счётчики до заданных минимумов.
    - `load_user`: Через `UserRepository` читает состояние пользователя.
    - `save_user`: Через `UserRepository` сохраняет состояние пользователя.
    - `load_user_ids`: Через `UserRepository` читает связи пользователей с chat_id по транспортам.
    - `save_user_ids`: Через `UserRepository` заменяет связи пользователей с chat_id по транспортам.

    ### Жизненный цикл
    Объект живёт как storage API приложения; SQLAlchemy-сессии создаются только на время отдельных операций.

    ### Пример использования
    ```py
    storage: SqlAlchemyStorage
    ```
    """
    def __init__(self, session_factory: sessionmaker[Session] = SessionLocal):
        """
        Создаёт storage-объект `SqlAlchemyStorage` и сохраняет фабрику SQLAlchemy-сессий для коротких операций с БД.

        ### Аргументы:
        :param session_factory: фабрика коротких SQLAlchemy-сессий

        ### Пример использования:
        ```py
        sqlAlchemyStorage = SqlAlchemyStorage(session_factory = session_factory)
        ```
        """
        self.session_factory: sessionmaker[Session] = session_factory

    def ensure_defaults(self):
        """
        Создаёт обязательные storage-записи с настройками по умолчанию, если их ещё нет.

        ### Примеры вызова:
        ```py
        storage.ensure_defaults()
        ```
        """
        with get_db_session(self.session_factory) as session:
            AppStateRepository(session).get_or_create()

    def load_app_state(self) -> dict[str, Any]:
        """
        Загружает состояние приложения из storage.

        :return: сериализованные данные состояния приложения

        ### Примеры вызова:
        ```py
        storage.load_app_state()
        ```
        """
        with get_db_session(self.session_factory) as session:
            return AppStateRepository(session).load()

    def save_app_state(self, data: dict[str, Any]):
        """
        Сохраняет JSON-совместимое состояние приложения в storage.

        ### Аргументы:
        :param data: JSON-совместимые данные для соответствующего repository

        ### Пример использования:
        ```py
        storage.save_app_state(data = data)
        ```
        """
        with get_db_session(self.session_factory) as session:
            AppStateRepository(session).save(data)

    def next_id(self, counter_name: str) -> int:
        """
        Открывает короткую DB session через `get_db_session` и вызывает `AppStateRepository.next_id`.
        Repository атомарно увеличивает и возвращает значение именованного счётчика в рамках гарантий SQLAlchemy session/context manager.

        ### Аргументы:
        :param counter_name: имя счётчика идентификаторов

        :return: новое значение именованного счётчика

        ### Пример использования:
        ```py
        sqlAlchemyStorage.next_id(counter_name = counter_name)
        ```
        """
        with get_db_session(self.session_factory) as session:
            return AppStateRepository(session).next_id(counter_name)

    def ensure_counters_at_least(self, **counters: int):
        """
        Поднимает сохранённые счётчики до заданных минимальных значений, не уменьшая уже большие значения.

        ### Примеры вызова:
        ```py
        storage.ensure_counters_at_least(**kwargs)
        ```
        """
        with get_db_session(self.session_factory) as session:
            AppStateRepository(session).ensure_at_least(**counters)

    def load_user(self, user_id: int) -> dict[str, Any]:
        """
        Загружает состояние пользователя из storage.

        ### Аргументы:
        :param user_id: внутренний идентификатор пользователя в app-layer

        :return: сериализованные данные состояния пользователя

        ### Пример использования:
        ```py
        storage.load_user(user_id = user_id)
        ```
        """
        with get_db_session(self.session_factory) as session:
            return UserRepository(session).load_payload(user_id)

    def save_user(self, user_id: int, payload: dict[str, Any], access_level: int = 0):
        """
        Сохраняет сериализованное состояние пользователя в storage.

        ### Аргументы:
        :param user_id: внутренний идентификатор пользователя в app-layer
        :param payload: сериализованный словарь, который хранится в storage
        :param access_level: уровень доступа пользователя или администратора

        ### Пример использования:
        ```py
        storage.save_user(user_id = user_id, payload = payload, access_level = access_level)
        ```
        """
        with get_db_session(self.session_factory) as session:
            UserRepository(session).save_payload(user_id, payload, access_level)

    def load_user_ids(self) -> dict[int, dict[str, set[int]]]:
        """
        Загружает связи пользователей с chat_id по транспортам из storage.

        :return: сериализованные данные для связи пользователей с chat_id по транспортам

        ### Примеры вызова:
        ```py
        storage.load_user_ids()
        ```
        """
        with get_db_session(self.session_factory) as session:
            return UserRepository(session).load_chat_ids()

    def save_user_ids(self, users_ids: dict[int, dict[str, set[int] | list[int]]]):
        """
        Заменяет сохранённые связи пользователей с chat_id по транспортам.

        ### Аргументы:
        :param users_ids: соответствие user_id, transport key и набора chat_id

        ### Пример использования:
        ```py
        storage.save_user_ids(users_ids = users_ids)
        ```
        """
        with get_db_session(self.session_factory) as session:
            UserRepository(session).replace_chat_ids(users_ids)

    def add_user_chat_id(self, user_id: int, bot_key: str, chat_id: int):
        """
        Сохраняет связь пользователя с chat_id в конкретном транспорте.

        ### Аргументы:
        :param user_id: внутренний идентификатор пользователя в app-layer
        :param bot_key: ключ транспорта, например `vkbot` или `telebot`
        :param chat_id: идентификатор чата в конкретной платформе

        ### Пример использования:
        ```py
        storage.add_user_chat_id(user_id = user_id, bot_key = bot_key, chat_id = chat_id)
        ```
        """
        with get_db_session(self.session_factory) as session:
            UserRepository(session).add_chat_id(user_id, bot_key, chat_id)

    def find_user_id(self, bot_key: str, chat_id: int) -> int | None:
        """
        Ищет user id по данным, которые пришли из вызывающего слоя.

        ### Аргументы:
        :param bot_key: ключ транспорта, например `vkbot` или `telebot`
        :param chat_id: идентификатор чата в конкретной платформе

        :return: найденное значение для user id или None, если записи нет

        ### Пример использования:
        ```py
        storage.find_user_id(bot_key = bot_key, chat_id = chat_id)
        ```
        """
        with get_db_session(self.session_factory) as session:
            return UserRepository(session).find_user_id(bot_key, chat_id)

    def load_admins(self) -> dict[int, dict[str, Any]]:
        """
        Загружает настройки администраторов из storage.

        :return: сериализованные данные для настройки администраторов

        ### Примеры вызова:
        ```py
        storage.load_admins()
        ```
        """
        with get_db_session(self.session_factory) as session:
            return AdminRepository(session).load_all()

    def save_admins(self, admins: dict[int, dict[str, Any]]):
        """
        Сохраняет список администраторов и их права в storage.

        ### Аргументы:
        :param admins: словарь настроек администраторов по user_id

        ### Пример использования:
        ```py
        storage.save_admins(admins = admins)
        ```
        """
        with get_db_session(self.session_factory) as session:
            AdminRepository(session).replace_all(admins)

    def list_conversation_ids(self) -> list[int]:
        """
        Возвращает id всех сохранённых live-диалогов.

        :return: список id сохранённых диалогов

        ### Примеры вызова:
        ```py
        storage.list_conversation_ids()
        ```
        """
        with get_db_session(self.session_factory) as session:
            return ConversationRepository(session).list_ids()

    def load_conversation(self, conv_id: int) -> dict[str, Any]:
        """
        Загружает историю диалога из storage.

        ### Аргументы:
        :param conv_id: идентификатор сохранённого диалога

        :return: сериализованный снимок истории диалога

        ### Пример использования:
        ```py
        storage.load_conversation(conv_id = conv_id)
        ```
        """
        with get_db_session(self.session_factory) as session:
            return ConversationRepository(session).load_payload(conv_id)

    def save_conversation(self, conv_id: int, payload: dict[str, Any]):
        """
        Сохраняет JSON-снимок live-диалога в storage.

        ### Аргументы:
        :param conv_id: идентификатор сохранённого диалога
        :param payload: сериализованный словарь, который хранится в storage

        ### Пример использования:
        ```py
        storage.save_conversation(conv_id = conv_id, payload = payload)
        ```
        """
        with get_db_session(self.session_factory) as session:
            ConversationRepository(session).save_payload(conv_id, payload)

    def load_document(self, key: str) -> dict[str, Any]:
        """
        Загружает служебный JSON-документ из storage.

        ### Аргументы:
        :param key: ключ служебного документа или набора команд

        :return: сериализованные данные служебного JSON-документа

        ### Пример использования:
        ```py
        storage.load_document(key = key)
        ```
        """
        with get_db_session(self.session_factory) as session:
            return DocumentRepository(session).load(key)

    def save_document(self, key: str, payload: dict[str, Any]):
        """
        Сохраняет служебный JSON-документ в storage.

        ### Аргументы:
        :param key: ключ служебного документа или набора команд
        :param payload: сериализованный словарь, который хранится в storage

        ### Пример использования:
        ```py
        storage.save_document(key = key, payload = payload)
        ```
        """
        with get_db_session(self.session_factory) as session:
            DocumentRepository(session).save(key, payload)

    def load_bots(self) -> dict[str, list[dict[str, Any]]]:
        """
        Загружает конфигурации транспортных ботов из storage.

        :return: сериализованные данные для конфигурации транспортных ботов

        ### Примеры вызова:
        ```py
        storage.load_bots()
        ```
        """
        with get_db_session(self.session_factory) as session:
            return BotConfigRepository(session).load_all()

    def save_bots(self, data: dict[str, list[dict[str, Any]]]):
        """
        Сохраняет конфигурации transport-ботов в storage.

        ### Аргументы:
        :param data: JSON-совместимые данные для соответствующего repository

        ### Пример использования:
        ```py
        storage.save_bots(data = data)
        ```
        """
        with get_db_session(self.session_factory) as session:
            BotConfigRepository(session).replace_all(data)

    def load_commands(self, key: str) -> dict[str, dict[str, Any]]:
        """
        Загружает команды интерфейса из storage.

        ### Аргументы:
        :param key: ключ служебного документа или набора команд

        :return: сериализованные команды интерфейса

        ### Пример использования:
        ```py
        storage.load_commands(key = key)
        ```
        """
        document_key: str = f"commands:{key}"
        with get_db_session(self.session_factory) as session:
            return DocumentRepository(session).load(document_key)

    def load_phrases(self) -> dict[str, dict[str, dict[str, list[str]]]]:
        """
        Загружает локализованные фразы из storage.

        :return: сериализованные локализованные фразы

        ### Примеры вызова:
        ```py
        storage.load_phrases()
        ```
        """
        with get_db_session(self.session_factory) as session:
            return DocumentRepository(session).load("phrases")
