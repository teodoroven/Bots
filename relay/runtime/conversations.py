"""
Описывает диалоги клиента и администратора через бота.
Модуль относится к архитектурной зоне: прикладной слой `relay`, который связывает пользователей, сессии, доменную модель, GPT, уведомления и runtime-логику приложения.

### Публичные классы
- `ConversationsMixin`: runtime-логика диалогов.

### Публичные функции
- Публичные функции отсутствуют.

### Связи
Используется app-layer сценариями, обработчиками, сессиями и runtime-миксинами для единого пользовательского потока между ботами, GPT и storage.
"""

from __future__ import annotations



from relay.conversations import Conversation
from relay.handlers import Context
from relay.users import Admin, User
from relay.utils import catch_parsefiles, log_warn
class ConversationsMixin:
        """
        Добавляет `App` операции conversations без привязки к transport-layer.
        Mixin рассчитан на включение в `App` и работает с его registry, storage, пользователями, ботами и очередями.

        ### Методы
        - `create_conv_id`: Создаёт conv id и связывает результат с текущим app-layer состоянием.
        - `get_conv_storage_key`: Возвращает conv storage key из текущего состояния `ConversationsMixin`.
        - `load_conv`: Загружает conv из storage.
        - `find_conv`: Ищет conv по данным, которые пришли из вызывающего слоя.
        - `create_conv`: Создаёт conv и связывает результат с текущим app-layer состоянием.
        - `get_conv`: Возвращает conv из текущего состояния `ConversationsMixin`.
        - `start_dialog`: Запускает dialog в runtime-потоке приложения.
        - `start_conv`: Запускает conv в runtime-потоке приложения.
        - `finish_conv`: Завершает conv и очищает связанные runtime-данные.

        ### Жизненный цикл
        Создаётся app-layer кодом, участвует в обработке пользовательского события и сохраняет изменённое состояние через существующие runtime/storage механизмы.

        ### Пример использования
        ```py
        app: ConversationsMixin
        ```
        """
        def create_conv_id(self) -> int:
            """
            Создаёт conv id и связывает результат с текущим app-layer состоянием.

            :return: созданный объект для conv id

            ### Примеры вызова:
            ```py
            app.create_conv_id()
            ```
            """
            if hasattr(self, "storage") and getattr(self, "persist_ids", True):

                self.conv_id = self.storage.next_id("conv")

            else:

                self.conv_id += 1

            return self.conv_id

        def get_conv_storage_key(self, conv_id: int) -> str:
            """
            Возвращает storage key live-диалога.

            ### Аргументы:
            :param conv_id: conv id

            :return: conv storage key

            ### Пример использования:
            ```py
            conversationsMixin.get_conv_storage_key(conv_id = conv_id)
            ```
            """
            return f"conversation:{int(conv_id)}"

        def load_conv(self) -> int:
            """
            Загружает conv из storage.

            :return: сериализованные данные для conv

            ### Примеры вызова:
            ```py
            app.load_conv()
            ```
            """
            max_id: int = 0

            for conv_id in self.storage.list_conversation_ids():

                storage_key: str = self.get_conv_storage_key(conv_id)

                with catch_parsefiles((storage_key,), "load_conversation"):

                    conv: Conversation = Conversation(int(conv_id), storage_key, self.get_bot, self.create_message_id, storage = self.storage, create_message = False)

                    conv.load(self.get_bot, self.get_user)

                    if str(conv.id) != str(conv_id):

                        log_warn(f"Некорректный {conv.id=} не соответствует {conv_id=}")


                    # for group in conv.messages:


                    if int(conv.id) > max_id:

                        max_id = int(conv.id)

                    self.chats[conv.id] = conv

            return max_id

        def find_conv(self, conv_id: int) -> Conversation | None:
            """
            Ищет conv по данным, которые пришли из вызывающего слоя.

            ### Аргументы:
            :param conv_id: идентификатор сохранённого диалога

            :return: найденное значение для conv или None, если записи нет

            ### Пример использования:
            ```py
            app.find_conv(conv_id = conv_id)
            ```
            """
            return self.chats.get(conv_id)

        def create_conv(self, username: str | None) -> Conversation:
            """
            Создаёт conv и связывает результат с текущим объектом.

            ### Аргументы:
            :param username: имя пользователя

            :return: созданный объект: conv

            ### Пример использования:
            ```py
            conversationsMixin.create_conv(username = username)
            ```
            """
            with self.conv_lock:

                conv_id: int = self.create_conv_id()

                storage_key: str = self.get_conv_storage_key(conv_id)

                conv: Conversation = Conversation(conv_id, storage_key, self.get_bot, self.create_message_id, storage = self.storage, username = username)

                self.chats[conv_id] = conv

                conv.save()


            return conv

        def get_conv(self, client: User, bot_key: BOT_KEY) -> Conversation:
            """
            Возвращает live-диалог по storage key.

            ### Аргументы:
            :param client: клиент или пользователь GPT-сценария
            :param bot_key: ключ транспорта

            :return: conv

            ### Пример использования:
            ```py
            conversationsMixin.get_conv(client = client, bot_key = bot_key)
            ```
            """

            conv_list: list[int] = client.get_conv_list(bot_key)

            for conv_id in conv_list:

                conv: Conversation | None = self.find_conv(conv_id)

                if isinstance(conv, Conversation):

                    return conv

            return self.create_conv(client.get_username(bot_key))

        def start_dialog(self, user_bot_key: BOT_KEY, user_chat_id: int, admin_bot_key: BOT_KEY, admin_chat_id: int):
            """
            Запускает сценарий обработки и подготавливает первое сообщение или задачу.

            ### Аргументы:
            :param user_bot_key: user bot key
            :param user_chat_id: user chat id
            :param admin_bot_key: admin bot key
            :param admin_chat_id: admin chat id

            ### Пример использования:
            ```py
            conversationsMixin.start_dialog(user_bot_key = user_bot_key, user_chat_id = user_chat_id, admin_bot_key = admin_bot_key, admin_chat_id = admin_chat_id)
            ```
            """
            user: User = self.get_user(user_bot_key, user_chat_id)

            context: Context = Context(self, self.get_bot(user_bot_key), user, None, None)

            conv: Conversation = self.start_conv(context, last_messages = 10)

            admin: Admin = self.get_user(admin_bot_key, admin_chat_id)

            session: ConvSession | None = admin.find_conv_session(admin_bot_key)

            prev_conv: Conversation | None = self.find_conv(session.conv_id) if session and session.conv_id else None

            if prev_conv:

                prev_conv.leave_admin(admin_bot_key, admin_chat_id)

            admin_context: Context = Context(self, self.get_bot(admin_bot_key), admin, None, None)

            admin.start_session(ConvSession, admin_context, {

                "conv_id": conv.id,

                "admin_role": True

            }, process_context = False)

            conv.join_admin(admin_context, user.get_username(user_bot_key), user_bot_key)

        def start_conv(self, context: Context, last_messages: int = 0) -> Conversation:
            """
            Запускает сценарий обработки и подготавливает первое сообщение или задачу.

            ### Аргументы:
            :param context: контекст обработки события
            :param last_messages: last messages

            :return: значение, которое runtime использует для продолжения обработки события

            ### Пример использования:
            ```py
            conversationsMixin.start_conv(context = context, last_messages = last_messages)
            ```
            """
            user: User = context.user

            bot_key: BOT_KEY = context.bot.get_bot_key()

            conv_ids = user.get_conv_list(bot_key)

            conv = self.find_conv(conv_ids[0]) if conv_ids else None

            conv: Conversation = self.get_conv(user, bot_key)

            if not user.check_joined(bot_key, conv.id):

                user.start_session(ConvSession, context, {

                    "conv_id": conv.id,

                    "admin_role": False

                }, process_context = False)

                conv.join(user, context.bot, context.get_chat_id(), admin_role = False, last_messages = int(last_messages))

            else:

                user.make_current(bot_key, ConvSession)

            return conv

        def finish_conv(self, conv: Conversation):
            """
            Координирует runtime-состояние приложения между очередями, пользователями и transport-layer.

            ### Аргументы:
            :param conv: диалог, который нужно обработать

            ### Пример использования:
            ```py
            conversationsMixin.finish_conv(conv = conv)
            ```
            """


            users_list: list[tuple[str, int, Conversation.Participant]] = []

            for bot_key, chat_users in conv.users.items():

                for chat_id, chat_user in chat_users.items():

                    users_list.append((bot_key, chat_id, chat_user))

            for bot_key, chat_id, chat_user in users_list:

                user: User = self.get_user(bot_key, chat_id)



                session: ConvSession | None = user.find_conv_session(bot_key, conv.id)


                if (not session) or session.check_finished():

                    continue

                if session.admin_role:

                    conv.leave_admin(bot_key, chat_id)

                else:

                    conv.leave(bot_key, chat_id)

                session.finish()

                user.finish_session(bot_key, session)

                user.save()
