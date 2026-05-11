"""
Описывает SQLAlchemy ORM-модели storage-layer.
Модуль относится к архитектурной зоне: слой хранения `db`, который изолирует SQLAlchemy, репозитории и документы состояния от app-layer.

### Публичные классы
- `AppStateORM`: ORM-модель глобального состояния и счётчиков приложения.
- `UserORM`: ORM-модель пользователя приложения.
- `UserChatIdORM`: ORM-модель связи пользователя с chat id транспорта.
- `AdminORM`: ORM-модель администратора и его настроек.
- `ConversationORM`: ORM-модель диалога клиента и администратора.
- `BotConfigORM`: ORM-модель конфигурации подключённого бота.
- `StorageDocumentORM`: ORM-модель JSON-документа хранилища.

### Публичные функции
- Публичные функции отсутствуют.

### Публичные константы и типы
- Ключевые публичные значения: `JSON_DATA`.

### Связи
Используется storage-слоем и runtime-логикой приложения для чтения, сохранения и миграции состояния без прямой зависимости app-layer от деталей SQLAlchemy.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger
from sqlalchemy import Boolean
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import UniqueConstraint
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship
from sqlalchemy.types import JSON

from db.base import Base


JSON_DATA = JSON().with_variant(JSONB, "postgresql")


class AppStateORM(Base):
    """
    Описывает SQLAlchemy-модель `AppStateORM`.
    Модель принадлежит storage-layer и описывает таблицу, которую используют репозитории. App-layer работает с ней через storage API, а не напрямую.

    ### Поля
    - `id`: единственная строка глобального состояния приложения.
    - `message_id`: последний выданный id wrapper-сообщения.
    - `session_id`: последний выданный id пользовательской сессии.
    - `event_id`: последний выданный id входящего transport-события.
    - `user_id`: последний выданный внутренний id пользователя.
    - `conv_id`: последний выданный id сохранённого live-диалога.
    - `client_id`: последний выданный id GPT-клиента.
    - `element_id`: последний выданный id доменного элемента автошколы или GPT-настройки.
    - `message_queue_id`: последний выданный id элемента очереди сообщений.
    - `bot_enabled`: флаги включения transport-ботов по ключам.

    ### Жизненный цикл
    Объект создаётся на время storage-операции или описывает таблицу; внешние слои работают через storage API и не управляют SQLAlchemy-сессией напрямую.

    ### Пример использования
    ```py
    appStateORM: AppStateORM
    ```
    """
    __tablename__: str = "app_state"

    id: Mapped[int] = mapped_column(Integer, primary_key = True, default = 1)
    message_id: Mapped[int] = mapped_column(Integer, nullable = False, default = 0)
    session_id: Mapped[int] = mapped_column(Integer, nullable = False, default = 0)
    event_id: Mapped[int] = mapped_column(Integer, nullable = False, default = 0)
    user_id: Mapped[int] = mapped_column(Integer, nullable = False, default = 0)
    conv_id: Mapped[int] = mapped_column(Integer, nullable = False, default = 0)
    client_id: Mapped[int] = mapped_column(Integer, nullable = False, default = 0)
    element_id: Mapped[int] = mapped_column(Integer, nullable = False, default = 0)
    message_queue_id: Mapped[int] = mapped_column(Integer, nullable = False, default = 0)
    bot_enabled: Mapped[bool] = mapped_column(Boolean, nullable = False, default = True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone = True), server_default = func.now(), nullable = False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone = True), server_default = func.now(), onupdate = func.now(), nullable = False)


class UserORM(Base):
    """
    Описывает SQLAlchemy-модель `UserORM`.
    Модель принадлежит storage-layer и описывает таблицу, которую используют репозитории. App-layer работает с ней через storage API, а не напрямую.

    ### Поля
    - `id`: внутренний id пользователя в app-layer.
    - `access_level`: уровень доступа пользователя или администратора.
    - `payload`: JSON-совместимое состояние, которое сохраняется в storage.
    - `created_at`: время создания записи в storage.
    - `updated_at`: время последнего обновления записи в storage.
    - `chat_ids`: соответствие transport key и chat id пользователя в конкретной платформе.
    - `admin`: связанная запись администратора, если пользователь имеет admin-настройки.

    ### Жизненный цикл
    Объект создаётся на время storage-операции или описывает таблицу; внешние слои работают через storage API и не управляют SQLAlchemy-сессией напрямую.

    ### Пример использования
    ```py
    userORM: UserORM
    ```
    """
    __tablename__: str = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key = True)
    access_level: Mapped[int] = mapped_column(Integer, nullable = False, default = 0)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON_DATA, nullable = False, default = dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone = True), server_default = func.now(), nullable = False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone = True), server_default = func.now(), onupdate = func.now(), nullable = False)

    chat_ids: Mapped[list["UserChatIdORM"]] = relationship(
        back_populates = "user",
        cascade = "all, delete-orphan",
    )
    admin: Mapped["AdminORM | None"] = relationship(
        back_populates = "user",
        cascade = "all, delete-orphan",
    )


class UserChatIdORM(Base):
    """
    Описывает SQLAlchemy-модель `UserChatIdORM`.
    Модель принадлежит storage-layer и описывает таблицу, которую используют репозитории. App-layer работает с ней через storage API, а не напрямую.

    ### Поля
    - `id`: технический id строки связи.
    - `user_id`: внутренний id пользователя, которому принадлежит transport chat id.
    - `bot_key`: ключ транспорта, например `telebot` или `vkbot`.
    - `chat_id`: id чата или пользователя внутри конкретной платформы.
    - `created_at`: время создания записи в storage.
    - `user`: пользователь, связанный с этим chat id.

    ### Жизненный цикл
    Объект создаётся на время storage-операции или описывает таблицу; внешние слои работают через storage API и не управляют SQLAlchemy-сессией напрямую.

    ### Пример использования
    ```py
    userChatIdORM: UserChatIdORM
    ```
    """
    __tablename__: str = "user_chat_ids"
    __table_args__: tuple[UniqueConstraint] = (
        UniqueConstraint("bot_key", "chat_id", name = "uq_user_chat_ids_bot_key_chat_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key = True, autoincrement = True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete = "CASCADE"), nullable = False, index = True)
    bot_key: Mapped[str] = mapped_column(String(32), nullable = False)
    chat_id: Mapped[int] = mapped_column(BigInteger, nullable = False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone = True), server_default = func.now(), nullable = False)

    user: Mapped[UserORM] = relationship(back_populates = "chat_ids")


class AdminORM(Base):
    """
    Описывает SQLAlchemy-модель `AdminORM`.
    Модель принадлежит storage-layer и описывает таблицу, которую используют репозитории. App-layer работает с ней через storage API, а не напрямую.

    ### Поля
    - `user_id`: внутренний id пользователя, для которого включены admin-настройки.
    - `access_level`: уровень доступа пользователя или администратора.
    - `permissions`: права администратора или пользователя.
    - `notifications`: хранит уведомления администраторов для операций этого объекта.
    - `created_at`: время создания записи в storage.
    - `updated_at`: время последнего обновления записи в storage.
    - `user`: базовая запись пользователя администратора.

    ### Жизненный цикл
    Объект создаётся на время storage-операции или описывает таблицу; внешние слои работают через storage API и не управляют SQLAlchemy-сессией напрямую.

    ### Пример использования
    ```py
    adminORM: AdminORM
    ```
    """
    __tablename__: str = "admins"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete = "CASCADE"), primary_key = True)
    access_level: Mapped[int] = mapped_column(Integer, nullable = False, default = 0)
    permissions: Mapped[dict[str, Any]] = mapped_column(JSON_DATA, nullable = False, default = dict)
    notifications: Mapped[dict[str, Any]] = mapped_column(JSON_DATA, nullable = False, default = dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone = True), server_default = func.now(), nullable = False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone = True), server_default = func.now(), onupdate = func.now(), nullable = False)

    user: Mapped[UserORM] = relationship(back_populates = "admin")


class ConversationORM(Base):
    """
    Описывает SQLAlchemy-модель `ConversationORM`.
    Модель принадлежит storage-layer и описывает таблицу, которую используют репозитории. App-layer работает с ней через storage API, а не напрямую.

    ### Поля
    - `id`: id сохранённого live-диалога между клиентом и администраторами.
    - `payload`: JSON-совместимое состояние, которое сохраняется в storage.
    - `created_at`: время создания записи в storage.
    - `updated_at`: время последнего обновления записи в storage.

    ### Жизненный цикл
    Объект создаётся на время storage-операции или описывает таблицу; внешние слои работают через storage API и не управляют SQLAlchemy-сессией напрямую.

    ### Пример использования
    ```py
    conversationORM: ConversationORM
    ```
    """
    __tablename__: str = "conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key = True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON_DATA, nullable = False, default = dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone = True), server_default = func.now(), nullable = False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone = True), server_default = func.now(), onupdate = func.now(), nullable = False)


class BotConfigORM(Base):
    """
    Описывает SQLAlchemy-модель `BotConfigORM`.
    Модель принадлежит storage-layer и описывает таблицу, которую используют репозитории. App-layer работает с ней через storage API, а не напрямую.

    ### Поля
    - `id`: технический id строки конфигурации transport-бота.
    - `position`: порядковый номер записи в списке.
    - `bot_key`: ключ транспорта, например `telebot` или `vkbot`.
    - `token`: секретный token transport-бота. Используется для инициализации Telegram/VK SDK и не должен попадать в логи или публичные примеры.
    - `name`: человекочитаемое имя бота в конфигурации и логах.
    - `group_id`: идентификатор группы или сообщества, от имени которого работает transport-бот.
    - `created_at`: время создания записи в storage.
    - `updated_at`: время последнего обновления записи в storage.

    ### Жизненный цикл
    Объект создаётся на время storage-операции или описывает таблицу; внешние слои работают через storage API и не управляют SQLAlchemy-сессией напрямую.

    ### Пример использования
    ```py
    botConfigORM: BotConfigORM
    ```
    """
    __tablename__: str = "bot_configs"
    __table_args__: tuple[UniqueConstraint] = (
        UniqueConstraint("bot_key", "group_id", name = "uq_bot_configs_bot_key_group_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key = True, autoincrement = True)
    position: Mapped[int] = mapped_column(Integer, nullable = False, default = 0)
    bot_key: Mapped[str] = mapped_column(String(32), nullable = False)
    token: Mapped[str] = mapped_column(String(512), nullable = False)
    name: Mapped[str] = mapped_column(String(255), nullable = False)
    group_id: Mapped[int] = mapped_column(BigInteger, nullable = False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone = True), server_default = func.now(), nullable = False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone = True), server_default = func.now(), onupdate = func.now(), nullable = False)


class StorageDocumentORM(Base):
    """
    Описывает SQLAlchemy-модель `StorageDocumentORM`.
    Модель принадлежит storage-layer и описывает таблицу, которую используют репозитории. App-layer работает с ней через storage API, а не напрямую.

    ### Поля
    - `key`: ключ storage-записи или настройки.
    - `payload`: JSON-совместимое состояние, которое сохраняется в storage.
    - `created_at`: время создания записи в storage.
    - `updated_at`: время последнего обновления записи в storage.

    ### Жизненный цикл
    Объект создаётся на время storage-операции или описывает таблицу; внешние слои работают через storage API и не управляют SQLAlchemy-сессией напрямую.

    ### Пример использования
    ```py
    storageDocumentORM: StorageDocumentORM
    ```
    """
    __tablename__: str = "storage_documents"

    key: Mapped[str] = mapped_column(String(128), primary_key = True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON_DATA, nullable = False, default = dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone = True), server_default = func.now(), nullable = False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone = True), server_default = func.now(), onupdate = func.now(), nullable = False)
