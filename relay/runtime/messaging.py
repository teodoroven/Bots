"""
Описывает отправку, удаление и регистрацию wrapper-сообщений runtime.
Модуль относится к архитектурной зоне: прикладной слой `relay`, который связывает пользователей, сессии, доменную модель, GPT, уведомления и runtime-логику приложения.

### Публичные классы
- `MessagingMixin`: runtime-логика обработки сообщений.

### Публичные функции
- Публичные функции отсутствуют.

### Связи
Используется app-layer сценариями, обработчиками, сессиями и runtime-миксинами для единого пользовательского потока между ботами, GPT и storage.
"""

from __future__ import annotations



from relay.common import sys, traceback
from relay.config import (
    BOT_KEYS,
    MAX_RESPONSE_LENGTH,
    MAX_USERS,
    get_phrase,
    logger,
    logger_admin,
    logger_gpt,
)
from relay.conversations import Conversation
from relay.handlers import (
    ChatGPTHandler,
    CommonCommands,
    Context,
    GeneralCommands,
    NoHandlers,
    SessionsHandler,
)
from relay.notifications import AdminEvent, AppointmentEvent, CallAdminEvent, Notification
from relay.users import Admin, User
from relay.utils import is_int, log_warn, split_callback
class MessagingMixin:
        """
        Добавляет `App` операции messaging без привязки к transport-layer.
        Mixin рассчитан на включение в `App` и работает с его registry, storage, пользователями, ботами и очередями.

        ### Методы
        - `remove_message`: Удаляет wrapper-сообщение из внутреннего состояния или storage.
        - `process`: Передаёт текущий `Context` выбранному обработчику и обновляет `context.handler` по результату.
        - `vkbot_listener`: Координирует runtime-состояние приложения между очередями, пользователями и transport-layer.
        - `telebot_listener`: Координирует runtime-состояние приложения между очередями, пользователями и transport-layer.
        - `send_response`: Отправляет ответ GPT через доступный transport-layer адаптер.
        - `send`: Отправляет сообщение или вложение через transport-layer.
        - `set_keyboard`: Проверяет и сохраняет клавиатуру сообщения в состоянии `MessagingMixin`.
        - `new_event`: Координирует runtime-состояние приложения между очередями, пользователями и transport-layer.
        - `process_notifications`: Обрабатывает уведомления администраторов в текущем пользовательском или transport-layer потоке.
        - `next_level`: Переходит к следующему уровню пользовательского сценария.

        ### Жизненный цикл
        Создаётся app-layer кодом, участвует в обработке пользовательского события и сохраняет изменённое состояние через существующие runtime/storage механизмы.

        ### Пример использования
        ```py
        app: MessagingMixin
        ```
        """
        def _remove_message(self, bot_key: BOT_KEY, chat_id: int, owner_id: int, message_id: int):

            bot: BOT = self.get_bot(bot_key)

            message: Bot.Message = bot.__class__.Message(bot.bot, bot.group_id, "Sentinel")

            try:

                message.set_owner_id(owner_id)

                message.set_chat_id(chat_id)

                message.set_id(message_id)

                message.delete()

            except Exception as err:

                logger.exception(f"Ошибка при удалении сообщения по запросу {bot_key=} {chat_id=} {message_id=}: {err=}")

        def remove_message(self, context: Context, callback_data: str):
            """
            Удаляет wrapper-сообщение из внутреннего состояния или storage.

            ### Аргументы:
            :param context: контекст обработки события с app, bot, user, handler и message
            :param callback_data: данные callback-кнопки, пришедшие из транспорта

            :raises ValueError: если значение не проходит локальную проверку перед сохранением

            ### Пример использования:
            ```py
            app.remove_message(context = context, callback_data = callback_data)
            ```
            """
            user: User = context.user

            user_bot_key: BOT_KEY = context.bot.get_bot_key()

            user_chat_id: int = context.get_chat_id()

            session: ConvSession | None = user.find_conv_session(user_bot_key)

            conv: Conversation | None = self.find_conv(session.conv_id) if session and session.conv_id else None

            args: list[str] = split_callback(callback_data)

            if len(args) == 5:

                _, message_bot_key, chat_id, owner_id, message_id = args

                if message_bot_key not in BOT_KEYS:

                    raise ValueError(f"Некорректное значение {message_bot_key=} аргумента {callback_data=}")

                if not is_int(owner_id):

                    raise ValueError(f"Некорректное значение {owner_id=} аргумента {callback_data=}")

                else:

                    owner_id: int = int(owner_id)

                if not is_int(chat_id):

                    raise ValueError(f"Некорректное значение {chat_id=} аргумента {callback_data=}")

                else:

                    chat_id: int = int(chat_id)

                if not is_int(message_id):

                    raise ValueError(f"Некорректное значение {message_id=} аргумента {callback_data=}")

                else:

                    message_id: int = int(message_id)

                self._remove_message(message_bot_key, chat_id, owner_id, message_id)

                if conv:

                    conv.remove_message(callback_data, message_bot_key, message_id)

            else:

                log_warn(f"Некорректный запрос: {args=}")

        def _process(self, bot: BOT, event: Bot.Event):
            """
            Получает на вход запрос.

            Перебирает обработчики, чтобы выяснить какие могут обработать запрос.

            Среди отобранных обработчиков перебирает их пока один из них не обработает запрос.

            После обработки запроса в `context.handler` не должно быть `None`.

            Если после обработки `context.handler=None`, то значит предыдущий обработчик не справился с обработкой (или завершил работу) и тогда переходим к следующему.
            """

            text: str = event.get_text()

            # logger.print(event, f"{text=} {event.attachments=}", color = "purple")

            bot_key: BOT_KEY = bot.get_bot_key()

            chat_id: int = int(event.chat_id)

            if not self.is_bot_enabled() and self.get_event_access_level(bot_key, chat_id) < 1:

                return

            username: str = event.get_username()

            # name: str = event.get_name()

            user: User = self.get_user(bot_key, chat_id)

            user.set_username(bot_key, username)

            user.set_name(bot_key, " ".join(event.get_name()).strip())

            user.add_event(bot, event)



            context: Context = Context(self, bot, user, handler = None, event = event)

            if text == "id":

                self.send(context, str(event.chat_id))

                return

            elif text == "log" and user.get_access_level() > 1:

                logger_admin.info("Администратор запросил лог: user_id=%s bot_key=%s chat_id=%s", user.id, bot_key, chat_id)

                return

            elif text.startswith(CALLBACK_REMOVE) and context.is_callback():

                self.remove_message(context, text)

                return

            def process():

                for h in self.process_handlers:

                    general_handler: GeneralCommands | SessionsHandler | CommonCommands | ChatGPTHandler | NoHandlers = h

                    # Этап 1: Проверка предварительных условий

                    general_handler.check(context)  # -> context.handler


                    if context.has_handler():


                        general_handler.process(context)  # -> context.handler

                        # Этап 2: Проверка была ли выполнена команда или пропущена

                        if context.has_handler():

                            # here


                            # del self.users[user.id]

                            # WARNING:

                            if len(self.users) >= MAX_USERS:

                                if user.id in self.users:


                                    del self.users[user.id]

                            return

                # logger.error("no handlers")

            try:

                process()

            except Exception as err:

                # logger.error(f"exception! {err=}")

                exc_type, exc_value, exc_traceback = sys.exc_info()

                formatted_traceback: list[str] = traceback.format_exception(exc_type, exc_value, exc_traceback)

                self.log_process(context, formatted_traceback, err)

        def process(self, bot: BOT, event: Bot.Event):
            """
            Передаёт текущий `Context` выбранному обработчику и обновляет `context.handler` по результату.

            ### Аргументы:
            :param bot: transport-адаптер
            :param event: transport-событие для обработки

            ### Пример использования:
            ```py
            messagingMixin.process(bot = bot, event = event)
            ```
            """
            self.enqueue_process_task(bot, event)

        def vkbot_listener(self, bot: Vkbot, event: Bot.Event):
            """
            Координирует runtime-состояние приложения между очередями, пользователями и transport-layer.

            ### Аргументы:
            :param bot: transport-адаптер
            :param event: transport-событие для обработки

            ### Пример использования:
            ```py
            messagingMixin.vkbot_listener(bot = bot, event = event)
            ```
            """
            self.process(bot, event)

        def telebot_listener(self, bot: Telebot, event: Bot.Event):
            """
            Координирует runtime-состояние приложения между очередями, пользователями и transport-layer.

            ### Аргументы:
            :param bot: transport-адаптер
            :param event: transport-событие для обработки

            ### Пример использования:
            ```py
            messagingMixin.telebot_listener(bot = bot, event = event)
            ```
            """
            self.process(bot, event)

        def send_response(self, context: Context, response: str):
            """
            Отправляет ответ GPT через доступный transport-layer адаптер.

            ### Аргументы:
            :param context: контекст обработки события с app, bot, user, handler и message
            :param response: ответ GPT, привязанный к запросу пользователя

            :return: значение, которое runtime использует для продолжения обработки события

            ### Пример использования:
            ```py
            app.send_response(context = context, response = response)
            ```
            """
            def failed():

                context.remove_handler()

            if len(response) > MAX_RESPONSE_LENGTH:

                logger_gpt.warning("Слишком длинный GPT-ответ: length=%s", len(response))

                return failed()

            for s in ("Запрос:", "Ответ:", "[", "]", "{", "}", "CALL_ADMIN"):

                if s in response:

                    logger_gpt.warning("GPT-ответ отклонён по запрещённому маркеру")

                    return failed()

            return self.send(context, cut(response, MAX_RESPONSE_LENGTH))

        def send(self, context: Context, text: str, buttons: Iterable[str | Bot.Keyboard.Button] = [], inline: bool = True, max_width: int | None = None) -> Message:
            """
            Отправляет сообщение или вложение через transport-layer.

            ### Аргументы:
            :param context: контекст обработки события
            :param text: текст
            :param buttons: кнопки, которые нужно показать пользователю
            :param inline: признак inline-клавиатуры
            :param max_width: максимальная ширина строки кнопок

            :return: значение, которое runtime использует для продолжения обработки события

            ### Пример использования:
            ```py
            messagingMixin.send(context = context, text = text, buttons = buttons, inline = inline, max_width = max_width)
            ```
            """
            user: User = context.user

            bot: BOT = context.bot

            chat_id: int = context.get_chat_id()

            message: Message = user.get_message(bot.get_bot_key())

            message.set_text(text)

            if buttons:

                message.set_keyboard(buttons, inline = inline, max_width = max_width)

            else:

                self.set_keyboard(message, user.get_access_level())

            self.catch_message_send(message, bot, chat_id)

            user.add_message(bot.get_bot_key(), bot.name, message)

            return message

        def set_keyboard(self, message: Message, access_level: int):
            """
            Проверяет и сохраняет клавиатуру сообщения в состоянии `MessagingMixin`.

            ### Аргументы:
            :param message: wrapper-сообщение, которое можно отправить, обновить или сохранить
            :param access_level: уровень доступа пользователя или администратора

            ### Пример использования:
            ```py
            app.set_keyboard(message = message, access_level = access_level)
            ```
            """

            buttons: list[Bot.Keyboard.Button] = []

            for button_data in self.settings.buttons:

                text: str = button_data.get("text", "")

                callback_data: str = button_data.get("callback_data", "")

                color: int = get_int(button_data, Bot.Keyboard.Button.DEFAULT_COLOR, "color")

                access: int = get_int(button_data, 1, "access")

                text = get_phrase(text).strip() if text else ""

                if text and access_level >= access:

                    buttons.append(

                        Bot.Keyboard.Button(text, color = color, callback_data = callback_data)

                    )

            message.set_keyboard(buttons, inline = False, max_width = 2)

        def new_event(self, event_class: type[AdminEvent], context: Context, data: dict | None = {}):
            """
            Координирует runtime-состояние приложения между очередями, пользователями и transport-layer.

            ### Аргументы:
            :param event_class: event class
            :param context: контекст обработки события
            :param data: сериализованный словарь

            ### Пример использования:
            ```py
            messagingMixin.new_event(event_class = event_class, context = context, data = data)
            ```
            """

            self.event_id += 1

            event_id: int = self.event_id

            event: AdminEvent = event_class(event_id, context, data or {})

            self.events.append(event)

            notifications: list[Notification] = event.process()

            self.process_notifications(notifications)

        def process_notifications(self, notifications: list[Notification]):
            """
            Обрабатывает настройки уведомлений в текущем runtime-контексте.

            ### Аргументы:
            :param notifications: настройки уведомлений

            ### Пример использования:
            ```py
            messagingMixin.process_notifications(notifications = notifications)
            ```
            """
            for elem in notifications:

                elem.send(self.get_bot, self.catch_message_send)

        def next_level(self, bot_key: BOT_KEY, chat_id: int, session_class: type[ManageSession], data: dict | None, message: Message | None = None):
            """
            Переходит к следующему уровню пользовательского сценария.

            ### Аргументы:
            :param bot_key: ключ транспорта
            :param chat_id: идентификатор чата
            :param session_class: session class
            :param data: сериализованный словарь
            :param message: сообщение проекта или сообщение конкретного транспорта

            :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

            ### Пример использования:
            ```py
            messagingMixin.next_level(bot_key = bot_key, chat_id = chat_id, session_class = session_class, data = data, message = message)
            ```
            """
            user: User = self.get_user(bot_key, chat_id)

            if session_class is NotImplemented:

                raise NotImplementedError()

            context: Context = Context(self, self.get_bot(bot_key), user, None, None)

            user.go_session(session_class, context, data, )

        def make_appointment(self, context: Context, filial: Filial, date: Date | MonthDate | None, phone: str = "", name: str = "") -> bool:
            """
            Координирует runtime-состояние приложения между очередями, пользователями и transport-layer.

            ### Аргументы:
            :param context: контекст обработки события
            :param filial: филиал автошколы
            :param date: время сообщения или события
            :param phone: телефон пользователя
            :param name: имя

            :return: значение, которое runtime использует для продолжения обработки события

            ### Пример использования:
            ```py
            messagingMixin.make_appointment(context = context, filial = filial, date = date, phone = phone, name = name)
            ```
            """
            self.new_event(AppointmentEvent, context, {

                "filial_id": int(filial.id),

                "date_id": int(date.id) if date or filial.name != "Теория онлайн" else None,

                "phone": str(phone).strip(),

                "name": str(name).strip()

            })

            return True

        def admin_warning(self, phrase_key: str):
            """
            Координирует runtime-состояние приложения между очередями, пользователями и transport-layer.

            ### Аргументы:
            :param phrase_key: ключ локализованной фразы

            ### Пример использования:
            ```py
            messagingMixin.admin_warning(phrase_key = phrase_key)
            ```
            """
            logger_admin.warning(phrase_key)

        def log_process(self, context: Context, formatted_traceback: list[str], exception: Exception):
            """
            Координирует runtime-состояние приложения между очередями, пользователями и transport-layer.

            ### Аргументы:
            :param context: контекст обработки события
            :param formatted_traceback: подготовленный traceback для сообщения администратору
            :param exception: исключение, о котором нужно сообщить

            ### Пример использования:
            ```py
            messagingMixin.log_process(context = context, formatted_traceback = formatted_traceback, exception = exception)
            ```
            """
            log_info: list[str] = ["Возникла ошибка при обработке события пользователя"]

            handler_name: str = context.handler.__class__.__name__ if context.handler else "None"

            bot_key: str = "unknown"

            chat_id: int | str = "unknown"

            user_id: int | str = "unknown"

            try:

                bot_key = context.bot.get_bot_key()

            except Exception as err:

                bot_key = err.__class__.__name__

            try:

                chat_id = context.get_chat_id()

            except Exception as err:

                chat_id = err.__class__.__name__

            try:

                user_id = context.user.id

            except Exception as err:

                user_id = err.__class__.__name__

            log_info.append(f"handler={handler_name}")

            log_info.append(f"bot_key={bot_key}")

            log_info.append(f"chat_id={chat_id}")

            log_info.append(f"user_id={user_id}")

            logger_admin.error(

                "\n".join([

                    "\n".join(log_info),

                    *formatted_traceback,

                    f"exception_type={type(exception).__name__}",

                ])

            )

        def call_admin(self, context: Context):
            """
            Координирует runtime-состояние приложения между очередями, пользователями и transport-layer.

            ### Аргументы:
            :param context: контекст обработки события

            ### Пример использования:
            ```py
            messagingMixin.call_admin(context = context)
            ```
            """
            self.start_conv(context, last_messages = 10)

            self.new_event(CallAdminEvent, context)

        def get_admin_list(self,

                permissions: Iterable[str] = [],

                notifications: Iterable[str] = [],

                ) -> list[Admin]:
            """
            Возвращает список администраторов для уведомления.

            ### Аргументы:
            :param permissions: права администратора
            :param notifications: настройки уведомлений

            :return: admin list

            ### Пример использования:
            ```py
            messagingMixin.get_admin_list(permissions = permissions, notifications = notifications)
            ```
            """
            admin_list: list[Admin] = []

            listed_user_ids: set[int] = set()

            for user_id, admin_data in self.admins_storage.items():

                access_level: int = int(admin_data.get("access_level") or 0)

                if user_id not in self.users:

                    continue

                user: User = self.users[user_id]

                admin: Admin = Admin(user.id, user.chat_ids, access_level)

                admin.permissions.update(dict(admin_data.get("permissions", {})))

                admin.notifications.update(dict(admin_data.get("notifications", {})))

                if admin.access_level <= 0:

                    continue

                if admin.check_permissions(permissions) and admin.check_notifications(notifications):

                    admin_list.append(admin)

                    listed_user_ids.add(user_id)

            return admin_list
