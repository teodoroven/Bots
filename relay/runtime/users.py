"""
Описывает runtime-логику или модели пользователей.
Модуль относится к архитектурной зоне: прикладной слой `relay`, который связывает пользователей, сессии, доменную модель, GPT, уведомления и runtime-логику приложения.

### Публичные классы
- `UsersMixin`: runtime-логика пользователей.

### Публичные функции
- Публичные функции отсутствуют.

### Связи
Используется app-layer сценариями, обработчиками, сессиями и runtime-миксинами для единого пользовательского потока между ботами, GPT и storage.
"""

from __future__ import annotations



from relay.common import BotTypes
from relay.config import get_phrase
from relay.conversations import Conversation
from relay.handlers import Context
from relay.users import Admin, User
from relay.utils import log_warn
class UsersMixin:
        """
        Добавляет `App` операции пользователей без привязки к transport-layer.
        Mixin рассчитан на включение в `App` и работает с его registry, storage, пользователями, ботами и очередями.

        ### Методы
        - `create_message_id`: Создаёт message id и связывает результат с текущим app-layer состоянием.
        - `create_session_id`: Создаёт session id и связывает результат с текущим app-layer состоянием.
        - `create_session`: Создаёт пользовательскую сессию и связывает результат с текущим app-layer состоянием.
        - `new_session`: Координирует runtime-состояние приложения между очередями, пользователями и transport-layer.
        - `add_message_to_session`: Привязывает wrapper-сообщение к активной пользовательской сессии.
        - `load_ids`: Загружает ids из storage.
        - `save_ids`: Сохраняет ids в storage или во внутреннем состоянии объекта.
        - `add_id`: Добавляет user id в индекс пользователей runtime.
        - `find_user`: Ищет состояние пользователя по данным, которые пришли из вызывающего слоя.
        - `create_user_id`: Создаёт user id и связывает результат с текущим app-layer состоянием.

        ### Жизненный цикл
        Создаётся app-layer кодом, участвует в обработке пользовательского события и сохраняет изменённое состояние через существующие runtime/storage механизмы.

        ### Пример использования
        ```py
        app: UsersMixin
        ```
        """
        def create_message_id(self) -> int:
            """
            Создаёт message id и связывает результат с текущим app-layer состоянием.

            :return: созданный объект для message id

            ### Примеры вызова:
            ```py
            app.create_message_id()
            ```
            """
            if hasattr(self, "storage") and getattr(self, "persist_ids", True):

                self.message_id = self.storage.next_id("message")

            else:

                self.message_id += 1

            return self.message_id

        def create_session_id(self) -> int:
            """
            Создаёт session id и связывает результат с текущим app-layer состоянием.

            :return: созданный объект для session id

            ### Примеры вызова:
            ```py
            app.create_session_id()
            ```
            """
            if hasattr(self, "storage") and getattr(self, "persist_ids", True):

                self.session_id = self.storage.next_id("session")

            else:

                self.session_id += 1

            return self.session_id

        def create_session(self, session_id: int, session_class: type[Session], context: Context, data: dict, message: Message) -> Session:
            """
            Создаёт сессия и связывает результат с текущим объектом.

            ### Аргументы:
            :param session_id: идентификатор сессии
            :param session_class: session class
            :param context: контекст обработки события
            :param data: сериализованный словарь
            :param message: сообщение проекта или сообщение конкретного транспорта

            :return: созданный объект: сессия

            ### Пример использования:
            ```py
            usersMixin.create_session(session_id = session_id, session_class = session_class, context = context, data = data, message = message)
            ```
            """

            return session_class(session_id, context, data, message)

        def new_session(self, session_class: type[Session], context: Context, data: dict, message: Message) -> Session:
            """
            Координирует runtime-состояние приложения между очередями, пользователями и transport-layer.

            ### Аргументы:
            :param session_class: session class
            :param context: контекст обработки события
            :param data: сериализованный словарь
            :param message: сообщение проекта или сообщение конкретного транспорта

            :return: значение, которое runtime использует для продолжения обработки события

            ### Пример использования:
            ```py
            usersMixin.new_session(session_class = session_class, context = context, data = data, message = message)
            ```
            """

            return self.create_session(self.create_session_id(), session_class, context, data, message)

        def add_message_to_session(self, message: Message, bot_key: BOT_KEY, chat_id: int):
            """
            Привязывает wrapper-сообщение к активной пользовательской сессии.

            ### Аргументы:
            :param message: wrapper-сообщение, которое можно отправить, обновить или сохранить
            :param bot_key: ключ транспорта, например `vkbot` или `telebot`
            :param chat_id: идентификатор чата в конкретной платформе

            ### Пример использования:
            ```py
            app.add_message_to_session(message = message, bot_key = bot_key, chat_id = chat_id)
            ```
            """

            user: User = self.get_user(bot_key, chat_id)

            # WARNING: Если чат не найден, то он будет создан!

            session: ConvSession | None = user.find_conv_session(bot_key)


            if session:

                session.add_message(message)

                user.save()

            else:

                log_warn(f"Не нашлась ConvSession у пользователя {bot_key=} {chat_id=}")

        def load_ids(self) -> int:
            """
            Загружает ids из storage.

            :return: сериализованные данные для ids

            ### Примеры вызова:
            ```py
            app.load_ids()
            ```
            """
            users_ids: BotTypes.USERS_IDS_TYPE = self.storage.load_user_ids()

            self.users_ids.clear()

            max_id: int = 0


            for user_id, chat_ids in users_ids.items():

                user_id: int = int(user_id)

                self.users_ids[user_id] = {}

                for bot_key, id_set in chat_ids.items():

                    self.users_ids[user_id][bot_key] = set()

                    for chat_id in id_set:

                        self.users_ids[user_id][bot_key].add(int(chat_id))

                if user_id > max_id:

                    max_id = user_id


            max_id = max(max_id, int(self.user_id))

            self.storage.ensure_counters_at_least(user = max_id)

            max_id = max(max_id, int(self.conv_id))

            self.storage.ensure_counters_at_least(conv = max_id)

            return max_id

        def save_ids(self):
            """
            Сохраняет ids в storage или во внутреннем состоянии объекта.

            ### Примеры вызова:
            ```py
            app.save_ids()
            ```
            """
            users_ids: BotTypes.USERS_IDS_TYPE = {}


            for user_id, chat_ids in self.users_ids.items():

                ids:  dict[str, list[int]] = {}

                for bot_key, id_set in chat_ids.items():

                    ids[bot_key] = [int(chat_id) for chat_id in id_set]

                users_ids[user_id] = ids


            self.storage.save_user_ids(users_ids)

            self.storage.ensure_counters_at_least(user = max((int(user_id) for user_id in users_ids), default = 0))

        def add_id(self, user_id: int, bot_key: BOT_KEY, chat_id: int) -> dict[str, set[int]]:
            """
            Добавляет user id в индекс пользователей runtime.

            ### Аргументы:
            :param user_id: внутренний идентификатор пользователя в app-layer
            :param bot_key: ключ транспорта, например `vkbot` или `telebot`
            :param chat_id: идентификатор чата в конкретной платформе

            :return: значение, которое runtime использует для продолжения обработки события

            ### Пример использования:
            ```py
            app.add_id(user_id = user_id, bot_key = bot_key, chat_id = chat_id)
            ```
            """
            needs_save: bool = True

            if user_id not in self.users_ids:

                self.users_ids[user_id] = {

                    bot_key: set([int(chat_id)])

                }

            elif bot_key in self.users_ids[user_id]:

                if chat_id in self.users_ids[user_id][bot_key]:

                    needs_save = False

                self.users_ids[user_id][bot_key].add(int(chat_id))

            else:

                self.users_ids[user_id][bot_key] = set([int(chat_id)])

            if needs_save:

                if hasattr(self, "storage"):

                    self.storage.add_user_chat_id(user_id, bot_key, chat_id)

                    self.storage.ensure_counters_at_least(user = int(user_id))

                else:

                    self.save_ids()

            return self.users_ids[user_id]

        def find_user(self, bot_key: BOT_KEY, chat_id: int) -> int | None:
            """
            Ищет состояние пользователя по данным, которые пришли из вызывающего слоя.

            ### Аргументы:
            :param bot_key: ключ транспорта, например `vkbot` или `telebot`
            :param chat_id: идентификатор чата в конкретной платформе

            :return: найденное значение для состояние пользователя или None, если записи нет

            ### Пример использования:
            ```py
            app.find_user(bot_key = bot_key, chat_id = chat_id)
            ```
            """
            if hasattr(self, "storage"):

                user_id: int | None = self.storage.find_user_id(bot_key, chat_id)

                if user_id is not None:

                    return user_id

            with self.users_lock:

                for user_id, chat_ids in self.users_ids.items():

                    if bot_key in chat_ids:

                        if chat_id in chat_ids[bot_key]:

                            return user_id

            return None

        def create_user_id(self) -> int:
            """
            Создаёт user id и связывает результат с текущим app-layer состоянием.

            :return: созданный объект для user id

            ### Примеры вызова:
            ```py
            app.create_user_id()
            ```
            """
            if hasattr(self, "storage") and getattr(self, "persist_ids", True):

                self.user_id = self.storage.next_id("user")

            else:

                self.user_id += 1

            user_id: int = int(self.user_id)

            self.users_ids[user_id] = {}

            return user_id

        def create_user(self, bot_key: BOT_KEY, chat_id: int, access_level: int = 0):
            """
            Создаёт состояние пользователя и связывает результат с текущим app-layer состоянием.

            ### Аргументы:
            :param bot_key: ключ транспорта, например `vkbot` или `telebot`
            :param chat_id: идентификатор чата в конкретной платформе
            :param access_level: уровень доступа пользователя или администратора

            :return: созданный объект для состояние пользователя

            ### Пример использования:
            ```py
            app.create_user(bot_key = bot_key, chat_id = chat_id, access_level = access_level)
            ```
            """

            with self.users_lock:

                user_id: int = self.create_user_id()

                user: User = User(user_id, self.add_id(user_id, bot_key, chat_id), max(access_level, self.get_access_level(user_id)))

                self.users[user_id] = user

                user.load(self, self.get_bot)

                user.save()

            return user

        def get_access_level(self, user: int | User | BOT_KEY, chat_id: int | None = None) -> int:
            """
            Возвращает сохранённый уровень доступа.

            ### Аргументы:
            :param user: пользователь приложения
            :param chat_id: идентификатор чата

            :return: уровень доступа пользователя

            ### Пример использования:
            ```py
            usersMixin.get_access_level(user = user, chat_id = chat_id)
            ```
            """
            if isinstance(user, User):

                user_id: int = user.id

            elif chat_id is not None and isinstance(user, str):

                user_id: int | None = self.find_user(user, int(chat_id))

                return self.get_access_level(user_id or -1)

            else:

                user_id = int(user)

            if user_id in self.admins_storage:

                return int(self.admins_storage[user_id].get("access_level") or 0)

            return 0

        def get_user_level(self, user: User) -> int:
            """
            Возвращает уровень доступа пользователя.

            ### Аргументы:
            :param user: пользователь приложения

            :return: user level

            ### Пример использования:
            ```py
            usersMixin.get_user_level(user = user)
            ```
            """
            return self.get_access_level(user.id)

        def login_user(self, user_id: int, bot_key: BOT_KEY, chat_id: int):
            """
            Координирует runtime-состояние приложения между очередями, пользователями и transport-layer.

            ### Аргументы:
            :param user_id: user id
            :param bot_key: ключ транспорта
            :param chat_id: идентификатор чата

            :return: значение, которое runtime использует для продолжения обработки события

            ### Пример использования:
            ```py
            usersMixin.login_user(user_id = user_id, bot_key = bot_key, chat_id = chat_id)
            ```
            """
            user: User = User(user_id, self.add_id(user_id, bot_key, chat_id), self.resolve_user_access_level(user_id, bot_key, chat_id))

            user.load(self, self.get_bot)

            self.users[user_id] = user

            return user

        def resolve_user_access_level(self, user_id: int, bot_key: BOT_KEY, chat_id: int) -> int:
            """
            Координирует runtime-состояние приложения между очередями, пользователями и transport-layer.

            ### Аргументы:
            :param user_id: user id
            :param bot_key: ключ транспорта
            :param chat_id: идентификатор чата

            :return: значение, которое runtime использует для продолжения обработки события

            ### Пример использования:
            ```py
            usersMixin.resolve_user_access_level(user_id = user_id, bot_key = bot_key, chat_id = chat_id)
            ```
            """
            return self.get_access_level(user_id)

        def get_user(self, bot_key: BOT_KEY, chat_id: int) -> User:
            """
            Возвращает привязанного пользователя приложения.

            ### Аргументы:
            :param bot_key: ключ транспорта
            :param chat_id: идентификатор чата

            :return: пользователь приложения

            ### Пример использования:
            ```py
            usersMixin.get_user(bot_key = bot_key, chat_id = chat_id)
            ```
            """
            user_id: int | None = self.find_user(bot_key, chat_id)

            if user_id is None:

                user: User = self.create_user(bot_key, chat_id)

            elif user_id in self.users:

                user: User = self.users[user_id]

            else:

                user: User = self.login_user(user_id, bot_key, chat_id)

            user.access_level = self.resolve_user_access_level(user.id, bot_key, chat_id)

            return user

        def get_users_list(self, max_users: int = 20) -> list[User]:
            """
            Возвращает пользователей, доступных текущему runtime-фильтру.

            ### Аргументы:
            :param max_users: максимальное число пользователей в выдаче

            :return: users list

            ### Пример использования:
            ```py
            usersMixin.get_users_list(max_users = max_users)
            ```
            """
            return list(self.users.values())[:max_users][::-1]

        def ignore_user(self, bot_key: BOT_KEY, chat_id: int):
            """
            Координирует runtime-состояние приложения между очередями, пользователями и transport-layer.

            ### Аргументы:
            :param bot_key: ключ транспорта
            :param chat_id: идентификатор чата

            ### Пример использования:
            ```py
            usersMixin.ignore_user(bot_key = bot_key, chat_id = chat_id)
            ```
            """
            user: User = self.get_user(bot_key, chat_id)

            context: Context = Context(self, self.get_bot(bot_key), user, None, None)

            session: NoHandlersSession = user.start_session(NoHandlersSession, context)

        def finish_dialog(self, bot_key: BOT_KEY, chat_id: int):
            """
            Завершает dialog и очищает связанные runtime-данные.

            ### Аргументы:
            :param bot_key: ключ транспорта, например `vkbot` или `telebot`
            :param chat_id: идентификатор чата в конкретной платформе

            ### Пример использования:
            ```py
            app.finish_dialog(bot_key = bot_key, chat_id = chat_id)
            ```
            """
            user: User = self.get_user(bot_key, chat_id)

            session: ConvSession | None = user.find_conv_session(bot_key)

            if session:

                conv: Conversation | None = self.find_conv(session.conv_id)

                if conv:

                    self.finish_conv(conv)

            session: NoHandlersSession | None = user.find_session(bot_key, NoHandlersSession)

            while session:

                if not session.check_finished():

                    session.finish()

                    user.finish_session(bot_key, session)

                session = user.find_session(bot_key, NoHandlersSession)

            user.save()

        def add_admin(self, user: User, permissions: dict[str, bool] = {}, notifications: dict[str, bool] = {}):
            """
            Добавляет администратора в runtime-индекс пользователей.

            ### Аргументы:
            :param user: пользователь приложения
            :param permissions: права администратора
            :param notifications: настройки уведомлений

            ### Пример использования:
            ```py
            usersMixin.add_admin(user = user, permissions = permissions, notifications = notifications)
            ```
            """
            access_level: int = max(self.get_user_level(user), self.get_access_level(user.id), 1)

            user_data: dict[str, JSONABLE] = self.admins_storage.setdefault(user.id, {

                "access_level": access_level,

                "permissions": dict(Admin(user.id, {}).permissions),

                "notifications": dict(Admin(user.id, {}).notifications)

            })

            user_data["access_level"] = max(int(user_data.get("access_level") or 0), access_level)

            user_permissions: dict[str, bool] = dict(user_data.get("permissions", {}))

            user_notifications: dict[str, bool] = dict(user_data.get("notifications", {}))

            for key, value in permissions.items():

                if key not in user_permissions:

                    user_permissions[key] = value

            for key, value in notifications.items():

                if key not in user_notifications:

                    user_notifications[key] = value

            user_data["permissions"] = user_permissions

            user_data["notifications"] = user_notifications

            self.admins_storage[user.id] = user_data

            user.access_level = int(user_data["access_level"])

            self.save_admins()

        def act_deleted(self, bot_key: BOT_KEY, from_bot_key: BOT_KEY, chat_id: int, message_id: int):
            """
            Координирует runtime-состояние приложения между очередями, пользователями и transport-layer.

            ### Аргументы:
            :param bot_key: ключ транспорта
            :param from_bot_key: ключ исходного транспорта
            :param chat_id: идентификатор чата
            :param message_id: идентификатор сообщения

            ### Пример использования:
            ```py
            usersMixin.act_deleted(bot_key = bot_key, from_bot_key = from_bot_key, chat_id = chat_id, message_id = message_id)
            ```
            """
            bot: BOT = self.get_bot(bot_key)

            text: str = get_phrase("deleted")

            key: tuple[BOT_KEY, int, int] = (bot_key, from_bot_key, chat_id, message_id)

            if key in self.removable_messages:

                message: Bot.Message = self.removable_messages[key]

                message.set_text(text)

                message.set_keyboard(None)

                message.edit()
