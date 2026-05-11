"""
Описывает уведомления и административные события.
Модуль относится к архитектурной зоне: прикладной слой `relay`, который связывает пользователей, сессии, доменную модель, GPT, уведомления и runtime-логику приложения.

### Публичные классы
- `BotkeyMessage`: сообщение, сгруппированное по ключу бота.
- `Notification`: базовое уведомление приложения.
- `AdminEvent`: административное событие уведомления.
- `CallAdminEvent`: уведомление о запросе администратора.
- `AppointmentEvent`: уведомление о записи на занятие.

### Публичные функции
- Публичные функции отсутствуют.

### Связи
Используется app-layer сценариями, обработчиками, сессиями и runtime-миксинами для единого пользовательского потока между ботами, GPT и storage.
"""

from __future__ import annotations




from .common import (
    Callable,
    Literal,
    Lock,
    Thread,
    abstractmethod,
    datetime,
)
from .config import INPUT_LENGTH, get_phrase
from .users import Admin, User
from .utils import is_int, join_callback
class BotkeyMessage():
    """
    Описывает wrapper-сообщение transport-layer `BotkeyMessage`.

    ### Поля
    - `messages`: сообщения, которые приложение хранит для обновления интерфейса пользователя.

    ### Методы
    - `__init__`: Создаёт объект и сохраняет app-layer ссылки, которые нужны обработчикам.
    - `copy`: Создаёт независимую копию объекта без изменения исходного состояния.
    - `set`: Сохраняет wrapper-сообщение для выбранного транспорта.
    - `get`: Возвращает transport-представление вложения.
    - `send`: Отправляет сообщение или вложение через transport-layer.

    ### Жизненный цикл
    Создаётся app-layer кодом, участвует в обработке пользовательского события и сохраняет изменённое состояние через существующие runtime/storage механизмы.

    ### Пример использования
    ```py
    botkeyMessage: BotkeyMessage
    ```
    """
    def __init__(self, message: Message | None = None):
        """
        Создаёт `BotkeyMessage` и сохраняет app-layer ссылки, которые нужны обработчикам.

        ### Аргументы:
        :param message: wrapper-сообщение, которое можно отправить, обновить или сохранить

        ### Пример использования:
        ```py
        botkeyMessage: BotkeyMessage = BotkeyMessage(message = message)
        ```
        """
        self.messages: dict[Literal["", "vkbot", "telebot"], Message] = {}

        if message is not None:
            self.messages[""] = message

    def copy(self, no_buttons: bool = False) -> BotkeyMessage:
        """
        Создаёт независимую копию объекта без изменения исходного состояния.

        ### Аргументы:
        :param no_buttons: no buttons

        :return: результат выполнения операции

        ### Пример использования:
        ```py
        botkeyMessage.copy(no_buttons = no_buttons)
        ```
        """
        result: BotkeyMessage = BotkeyMessage()
        result.messages = self.messages.copy()

        if no_buttons:
            for bot_key, message in result.messages.items():
                message.set_keyboard([])

        return result

    def set(self, bot_key: BOT_KEY, message: Message):
        """
        Сохраняет wrapper-сообщение для выбранного транспорта.

        ### Аргументы:
        :param bot_key: ключ транспорта
        :param message: сообщение проекта или сообщение конкретного транспорта

        ### Пример использования:
        ```py
        botkeyMessage.set(bot_key = bot_key, message = message)
        ```
        """
        self.messages[bot_key] = message

    def get(self, bot_key: BOT_KEY) -> Message:
        """
        Возвращает transport-представление вложения.

        ### Аргументы:
        :param bot_key: ключ транспорта

        :return: результат выполнения операции

        :raises KeyError: если обязательный ключ отсутствует в registry или payload

        ### Пример использования:
        ```py
        botkeyMessage.get(bot_key = bot_key)
        ```
        """
        if bot_key in self.messages:
            return self.messages[bot_key]
        elif "" in self.messages:
            return self.messages[""]
        else:
            raise KeyError(f"Message для {bot_key} не установлено")

    def send(self, bot: BOT, chat_id: int, compression: bool = True) -> Message:
        """
        Отправляет сообщение или вложение через transport-layer.

        ### Аргументы:
        :param bot: transport-адаптер
        :param chat_id: идентификатор чата
        :param compression: признак сжатия вложения

        :return: результат выполнения операции

        :raises KeyError: если обязательный ключ отсутствует в registry или payload

        ### Пример использования:
        ```py
        botkeyMessage.send(bot = bot, chat_id = chat_id, compression = compression)
        ```
        """
        bot_key: BOT_KEY = bot.get_bot_key()

        if bot_key in self.messages:
            message = self.messages[bot_key]
        elif "" in self.messages:
            message = self.messages[""]
        else:
            raise KeyError(f"Message для {bot_key} не установлено")

        message.send(bot, chat_id, compression)
        return message


class Notification():

    """
    Описывает уведомление администратора `Notification`.

    ### Поля
    - `user`: хранит состояние пользователя для операций этого объекта.
    - `message`: хранит wrapper-сообщение для операций этого объекта.
    - `compression`: флаг сжатия групп сообщений перед отправкой.
    - `process_message`: callable для отправки или обработки wrapper-сообщения.

    ### Методы
    - `__init__`: Создаёт объект и сохраняет app-layer ссылки, которые нужны обработчикам.
    - `process_message`: Обрабатывает wrapper-сообщение в текущем пользовательском или transport-layer потоке.
    - `process`: Передаёт текущий `Context` выбранному обработчику и обновляет `context.handler` по результату.
    - `send`: Отправляет сообщение или вложение через transport-layer.

    ### Жизненный цикл
    Создаётся app-layer кодом, участвует в обработке пользовательского события и сохраняет изменённое состояние через существующие runtime/storage механизмы.

    ### Пример использования
    ```py
    notification: Notification
    ```
    """
    def __init__(self, user: User, message: BotkeyMessage, process_message: Callable | None = None, compression: bool = True):
        """
        Создаёт уведомление `Notification` и сохраняет данные, которые позже используются при отправке сообщения пользователю или администратору.

        ### Аргументы:
        :param user: пользователь приложения
        :param message: сообщение проекта или сообщение конкретного транспорта
        :param process_message: process message
        :param compression: признак сжатия вложения

        ### Пример использования:
        ```py
        notification = Notification(user = user, message = message, process_message = process_message, compression = compression)
        ```
        """
        self.user: User = user
        self.message: BotkeyMessage = message
        self.compression: bool = compression
        self.process_message: Callable | None = process_message

    @abstractmethod
    def process_message(self, message: Message):
        """
        Обрабатывает wrapper-сообщение в текущем пользовательском или transport-layer потоке.

        ### Аргументы:
        :param message: wrapper-сообщение, которое можно отправить, обновить или сохранить

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        notification.process_message(message = message)
        ```
        """
        raise NotImplementedError()

    def process(self, message: Message):
        """
        Передаёт текущий `Context` выбранному обработчику и обновляет `context.handler` по результату.

        ### Аргументы:
        :param message: сообщение проекта или сообщение конкретного транспорта

        ### Пример использования:
        ```py
        notification.process(message = message)
        ```
        """
        if self.process_message is not None:
            self.process_message(message)

    def send(self, get_bot: Callable, catch_send: Callable | None = None):
        """
        Отправляет сообщение или вложение через transport-layer.

        ### Аргументы:
        :param get_bot: get bot
        :param catch_send: catch send

        ### Пример использования:
        ```py
        notification.send(get_bot = get_bot, catch_send = catch_send)
        ```
        """
        for bot_key, chat_ids in self.user.chat_ids.items():
            for chat_id in chat_ids:
                bk = bot_key
                ci = chat_id

                def send(bot_key = bk, chat_id = ci):
                    bot: BOT = get_bot(bot_key)
                    message: Message = self.message.get(bot.get_bot_key())

                    if catch_send is None:
                        message.send(bot, chat_id, compression = self.compression)
                    else:
                        catch_send(message, bot, chat_id, self.compression)

                    self.process(message)

                Thread(target = send).start()


class AdminEvent():
    """
    Описывает входящее событие transport-layer `AdminEvent`.

    ### Поля
    - `get_admin_list`: callback для получения списка активных администраторов.
    - `create_message_id`: идентификатор объекта или связанной сущности, по которому runtime восстанавливает связь между слоями.
    - `lock`: threading lock, защищающий обработку уведомления.
    - `id`: внутренний идентификатор записи или доменного объекта.
    - `next_process`: время следующей разрешённой обработки события.
    - `interval`: минимальная пауза между обработками события.
    - `bot`: transport-адаптер, с которым работает объект.
    - `event`: хранит событие транспорта для операций этого объекта.
    - `started`: флаг запуска фонового обработчика.
    - `processing`: флаг выполнения текущей фоновой обработки.

    ### Методы
    - `__init__`: Создаёт объект и сохраняет app-layer ссылки, которые нужны обработчикам.
    - `get_admin_list`: Возвращает admin list из текущего состояния `AdminEvent`.
    - `create_message_id`: Создаёт message id и связывает результат с текущим app-layer состоянием.
    - `dumps`: Возвращает JSON-совместимый снимок объекта для storage или callback payload.
    - `load`: Загружает JSON-представление и восстанавливает поля объекта.
    - `run`: Формирует уведомления администраторам для текущего события.
    - `process`: Передаёт текущий `Context` выбранному обработчику и обновляет `context.handler` по результату.
    - `get_next_admin`: Возвращает next admin из текущего состояния `AdminEvent`.
    - `get_message`: Возвращает wrapper-сообщение из текущего состояния `AdminEvent`.

    ### Жизненный цикл
    Создаётся app-layer кодом, участвует в обработке пользовательского события и сохраняет изменённое состояние через существующие runtime/storage механизмы.

    ### Пример использования
    ```py
    adminEvent: AdminEvent
    ```
    """
    def __init__(self, event_id: int, context: Context, data: BotTypes.UNKNOWN_JSON_OBJECT):
        """
        Создаёт уведомление `AdminEvent` и сохраняет данные, которые позже используются при отправке сообщения пользователю или администратору.

        ### Аргументы:
        :param event_id: id события или чата в очереди транспорта
        :param context: контекст обработки события
        :param data: сериализованный словарь

        ### Пример использования:
        ```py
        adminEvent = AdminEvent(event_id = event_id, context = context, data = data)
        ```
        """
        self.get_admin_list: Callable = context.autocenter.get_admin_list
        self.create_message_id = context.autocenter.create_message_id
        self.lock: Lock = context.autocenter.event_lock

        self.id: int = int(event_id)
        self.next_process: datetime | None = None
        self.interval: int = 0

        self.bot: BOT = context.bot
        self.event: Bot.Event = context.event

        self.started: bool = False
        self.processing: bool = False
        self.finished: bool = False

        self.permissions: tuple[str] = tuple()
        self.notifications: tuple[str] = tuple()
        self.admin_list: list[int] = []

    @abstractmethod
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

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        adminEvent.get_admin_list(permissions = permissions, notifications = notifications)
        ```
        """
        raise NotImplementedError()

    @abstractmethod
    def create_message_id(self) -> int:
        """
        Создаёт message id и связывает результат с текущим app-layer состоянием.

        :return: созданный объект для message id

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Примеры вызова:
        ```py
        adminEvent.create_message_id()
        ```
        """
        raise NotImplementedError()


    def dumps(self) -> BotTypes.ADMIN_EVENT_TYPE:
        """
        Возвращает JSON-совместимый снимок объекта для storage или callback payload.

        :return: JSON-совместимый словарь для сохранения или передачи между слоями

        ### Пример использования:
        ```py
        adminEvent.dumps()
        ```
        """
        return {
            "id": int(self.id),
            "next_process": self.next_process.isoformat() if self.next_process else None,
            "started": bool(self.started),
            "finished": bool(self.finished),
            "admin_list": list(map(int, self.admin_list))
        }

    def load(self, data: BotTypes.ADMIN_EVENT_TYPE):
        """
        Загружает JSON-представление и восстанавливает поля объекта.

        ### Аргументы:
        :param data: сериализованный словарь

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        adminEvent.load(data = data)
        ```
        """
        if data.get("id") is None or not is_int(data.get("id")):
            raise ValueError("id not in data for Event")

        self.id = int(data.get("id"))
        self.next_process = datetime.fromisoformat(data.get("next_process")) if data.get("next_process") else None
        self.started = bool(data.get("started", False))
        self.finished = bool(data.get("finished", False))

    @abstractmethod
    def run(self) -> list[Notification]:
        """
        Формирует уведомления администраторам для текущего события.

        :return: список уведомлений, которые нужно отправить администраторам

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        adminEvent.run()
        ```
        """
        raise NotImplementedError()

    def process(self) -> list[Notification]:
        """
        Передаёт текущий `Context` выбранному обработчику и обновляет `context.handler` по результату.

        :return: результат выполнения операции

        ### Пример использования:
        ```py
        adminEvent.process()
        ```
        """
        with self.lock:
            result: list[Notification] = self.run()
            return result


    def get_next_admin(self) -> Admin | None:
        """
        Возвращает следующего администратора для round-robin уведомления.

        :return: next admin

        ### Пример использования:
        ```py
        adminEvent.get_next_admin()
        ```
        """
        admin_list: list[Admin] = self.get_admin_list(permissions = self.permissions, notifications = self.notifications)

        for admin in admin_list:
            if admin.id not in self.admin_list:
                self.admin_list.append(admin.id)
                return admin

        return None

    def get_message(self, text: str, update_messages: bool = False) -> BotkeyMessage:
        """
        Возвращает сообщение, которое имеет разное содержимое в зависимости от того, через какой бот его отправляют.
        - Текст сообщения будет скорректирован таким образом, чтобы имя пользователя в нём было кликабельно в чате пользователя.
        - Кнопки сообщения позволят начать чат с пользователем.

        :param text: Текст сообщения, обязательно должен содержать пустые фигурные скобки для вставки username.
        :param update_messages: Добавлять ли кнопку обновления текста сообщения.
        """
        botkey_mes: BotkeyMessage = BotkeyMessage()

        # Через который вёлся диалог пользователя с ботом
        bot_key: BOT_KEY = self.bot.get_bot_key()
        username: str = self.event.get_username()
        chat_id: int = self.event.chat_id

        # Пользователь написал в Vk
        if bot_key == Vkbot.BOT_KEY:
            group_id: int = self.bot.group_id
            url: str = f"https://vk.com/gim{group_id}?sel={chat_id}"

            vk_buttons: list[Vkbot.Keyboard.Button] = [
                Vkbot.Keyboard.Button(get_phrase("open_dialog"), url = url),
                Vkbot.Keyboard.Button(get_phrase("start_dialog"), callback_data = join_callback(CALLBACK_CALLADMIN, Vkbot.BOT_KEY, chat_id)),
                Vkbot.Keyboard.Button(get_phrase("finish_dialog"), callback_data = join_callback(CALLBACK_FINISHDIALOG, Vkbot.BOT_KEY, chat_id))
            ]

            if update_messages:
                vk_buttons.append(
                    Vkbot.Keyboard.Button(get_phrase("show_dialog"), callback_data = join_callback(CALLBACK_SHOWDIALOG, Vkbot.BOT_KEY, chat_id))
                )

            botkey_mes.set(Vkbot.BOT_KEY, Message(self.create_message_id(), text.format(username or f"@id{chat_id}"), vk_buttons))

            tg_buttons: list[Telebot.Keyboard.Button] = [
                Telebot.Keyboard.Button(get_phrase("open_dialog"), url = url),
                Telebot.Keyboard.Button(get_phrase("start_dialog"), callback_data = join_callback(CALLBACK_CALLADMIN, Vkbot.BOT_KEY, chat_id)),
                Telebot.Keyboard.Button(get_phrase("finish_dialog"), callback_data = join_callback(CALLBACK_FINISHDIALOG, Vkbot.BOT_KEY, chat_id))
            ]

            if update_messages:
                tg_buttons.append(
                    Telebot.Keyboard.Button(get_phrase("show_dialog"), callback_data = join_callback(CALLBACK_SHOWDIALOG, Vkbot.BOT_KEY, chat_id)),
                )

            botkey_mes.set(Telebot.BOT_KEY, Message(self.create_message_id(), text.format(f"https://vk.com/id{chat_id}"), tg_buttons))
        # Пользователь написал в Telegram
        elif bot_key == Telebot.BOT_KEY:
            vk_buttons: list[Vkbot.Keyboard.Button] = [
                Vkbot.Keyboard.Button(get_phrase("start_dialog"), callback_data = join_callback(CALLBACK_CALLADMIN, Telebot.BOT_KEY, chat_id)),
                Vkbot.Keyboard.Button(get_phrase("finish_dialog"), callback_data = join_callback(CALLBACK_FINISHDIALOG, Telebot.BOT_KEY, chat_id)),
            ]

            if update_messages:
                vk_buttons.append(
                    Vkbot.Keyboard.Button(get_phrase("show_dialog"), callback_data = join_callback(CALLBACK_SHOWDIALOG, Telebot.BOT_KEY, chat_id))
                )

            botkey_mes.set(Vkbot.BOT_KEY, Message(self.create_message_id(), text.format(f"https://t.me/{username[1:]}"), vk_buttons))

            tg_buttons: list[Telebot.Keyboard.Button] = [
                Telebot.Keyboard.Button(get_phrase("start_dialog"), callback_data = join_callback(CALLBACK_CALLADMIN, Telebot.BOT_KEY, chat_id)),
                Telebot.Keyboard.Button(get_phrase("finish_dialog"), callback_data = join_callback(CALLBACK_FINISHDIALOG, Telebot.BOT_KEY, chat_id)),
            ]

            if update_messages:
                tg_buttons.append(
                    Telebot.Keyboard.Button(get_phrase("show_dialog"), callback_data = join_callback(CALLBACK_SHOWDIALOG, Telebot.BOT_KEY, chat_id))
                )

            botkey_mes.set(Telebot.BOT_KEY, Message(self.create_message_id(), text.format(username), tg_buttons))

        return botkey_mes


class CallAdminEvent(AdminEvent):

    """
    Описывает входящее событие transport-layer `CallAdminEvent`.

    ### Поля
    - `get_bot`: callback для получения transport-адаптера по ключу.
    - `get_user`: callback для поиска пользователя по transport-событию.
    - `add_message_to_session`: callback для привязки сообщения к пользовательской сессии.
    - `settings`: хранит настройки пользователя или GPT для операций этого объекта.
    - `permissions`: права администратора или пользователя.
    - `notifications`: хранит уведомления администраторов для операций этого объекта.
    - `bot_key`: хранит ключ транспорта для операций этого объекта.
    - `chat_id`: идентификатор объекта или связанной сущности, по которому runtime восстанавливает связь между слоями.

    ### Методы
    - `__init__`: Создаёт объект и сохраняет app-layer ссылки, которые нужны обработчикам.
    - `get_bot`: Возвращает bot из текущего состояния `CallAdminEvent`.
    - `get_user`: Возвращает состояние пользователя из текущего состояния `CallAdminEvent`.
    - `add_message_to_session`: Привязывает wrapper-сообщение к активной пользовательской сессии.
    - `run`: Формирует уведомления администраторам о запросе связи с клиентом.

    ### Жизненный цикл
    Создаётся app-layer кодом, участвует в обработке пользовательского события и сохраняет изменённое состояние через существующие runtime/storage механизмы.

    ### Пример использования
    ```py
    callAdminEvent: CallAdminEvent
    ```
    """
    def __init__(self, event_id: int, context: Context, data: dict):
        """
        Создаёт уведомление `CallAdminEvent` и сохраняет данные, которые позже используются при отправке сообщения пользователю или администратору.

        ### Аргументы:
        :param event_id: id события или чата в очереди транспорта
        :param context: контекст обработки события
        :param data: сериализованный словарь

        ### Пример использования:
        ```py
        callAdminEvent = CallAdminEvent(event_id = event_id, context = context, data = data)
        ```
        """
        super().__init__(event_id, context, data)
        self.get_bot = context.autocenter.get_bot
        self.get_user = context.autocenter.get_user
        self.add_message_to_session = context.autocenter.add_message_to_session

        self.settings: dict = context.autocenter.settings.call_admin
        self.permissions: tuple[str] = ("answer_users",)
        self.notifications: tuple[str] = ("call_admin",)

        # Информация о пользователе, который вызвал администратора
        self.bot_key: BOT_KEY = context.bot.get_bot_key()
        self.chat_id: int = context.get_chat_id()


    @abstractmethod
    def get_bot(self, bot_key: BOT_KEY) -> BOT:
        """
        Возвращает привязанный transport-адаптер.

        ### Аргументы:
        :param bot_key: ключ транспорта

        :return: transport-адаптер

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        callAdminEvent.get_bot(bot_key = bot_key)
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
        callAdminEvent.get_user(bot_key = bot_key, chat_id = chat_id)
        ```
        """
        raise NotImplementedError()

    @abstractmethod
    def add_message_to_session(self, message: Message, bot_key: BOT_KEY, chat_id: int):
        """
        Привязывает wrapper-сообщение к активной пользовательской сессии.

        ### Аргументы:
        :param message: wrapper-сообщение, которое можно отправить, обновить или сохранить
        :param bot_key: ключ транспорта, например `vkbot` или `telebot`
        :param chat_id: идентификатор чата в конкретной платформе

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        callAdminEvent.add_message_to_session(message = message, bot_key = bot_key, chat_id = chat_id)
        ```
        """
        raise NotImplementedError()

    def run(self) -> list[Notification]:
        """
        Формирует уведомления администраторам о запросе связи с клиентом.

        :return: список уведомлений, которые нужно отправить администраторам

        ### Пример использования:
        ```py
        callAdminEvent.run()
        ```
        """
        if not self.started:
            self.started = True
            self.admin_list.clear()

            notifications: list[Notification] = []
            quantity: int = self.settings.get("quantity", 1)

            text: str = get_phrase("notification_call_admin")

            chat_id: int = self.event.chat_id
            user: User = self.get_user(self.bot_key, chat_id)
            groups: list[Message.MessagesGroup] = user.get_last_conversation(self.get_bot, self.bot_key)

            for group in groups:
                text += f"\n- {group.get_text()}"

            botkey_mes: BotkeyMessage = self.get_message(text, update_messages = True)

            for i in range(quantity):
                admin: Admin | None = self.get_next_admin()

                def process_message(message: Message):
                    self.add_message_to_session(message, self.bot_key, self.chat_id)

                if admin:
                    notification: Notification = Notification(admin, botkey_mes, process_message)
                    notifications.append(notification)

            return notifications
        else:
            pass


class AppointmentEvent(AdminEvent):

    """
    Описывает входящее событие transport-layer `AppointmentEvent`.

    ### Поля
    - `find_element`: callback для поиска доменного элемента по id.
    - `settings`: хранит настройки пользователя или GPT для операций этого объекта.
    - `notifications`: хранит уведомления администраторов для операций этого объекта.
    - `bot_key`: хранит ключ транспорта для операций этого объекта.
    - `event`: хранит событие транспорта для операций этого объекта.
    - `filial_id`: идентификатор объекта или связанной сущности, по которому runtime восстанавливает связь между слоями.
    - `date_id`: идентификатор объекта или связанной сущности, по которому runtime восстанавливает связь между слоями.
    - `phone`: телефон, связанный с записью или заявкой.
    - `name`: человекочитаемое имя бота в конфигурации и логах.

    ### Методы
    - `__init__`: Создаёт объект и сохраняет app-layer ссылки, которые нужны обработчикам.
    - `find_element`: Ищет элемент доменной модели по данным, которые пришли из вызывающего слоя.
    - `run`: Формирует уведомления администраторам о новой записи.

    ### Жизненный цикл
    Создаётся app-layer кодом, участвует в обработке пользовательского события и сохраняет изменённое состояние через существующие runtime/storage механизмы.

    ### Пример использования
    ```py
    appointmentEvent: AppointmentEvent
    ```
    """
    def __init__(self, event_id: int, context: Context, data: dict):
        """
        Создаёт уведомление `AppointmentEvent` и сохраняет данные, которые позже используются при отправке сообщения пользователю или администратору.

        ### Аргументы:
        :param event_id: id события или чата в очереди транспорта
        :param context: контекст обработки события
        :param data: сериализованный словарь

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        appointmentEvent = AppointmentEvent(event_id = event_id, context = context, data = data)
        ```
        """
        super().__init__(event_id, context, data)
        self.find_element = context.autocenter.find_element

        self.settings: dict = context.autocenter.settings.new_appointment
        self.notifications: tuple[str] = ("new_appointment",)

        self.bot_key: BOT_KEY = self.bot.get_bot_key()
        self.event: Bot.Event = context.event

        self.filial_id: int = get_int(data, -1, "filial_id")
        if self.filial_id < 0:
            filial_id = data.get("filial_id")
            raise ValueError(f"Некорректное значение под ключом {filial_id=} аргумента {data=}")

        self.date_id: int = get_int(data, -1, "date_id")
        # if self.date_id < 0:
        #     date_id = data.get("date_id")
        #     raise ValueError(f"Некорректное значение под ключом {date_id=} аргумента {data=}")

        self.phone: str = get_from(data, "phone", types = (str,), default = "")
        self.name: str = get_from(data, "name", types = (str,), default = "")

    @abstractmethod
    def find_element(self, element_id: int, element_class: type[Element]) -> Element | None:
        """
        Ищет доменный элемент в текущих данных объекта или storage.

        ### Аргументы:
        :param element_id: идентификатор доменного элемента
        :param element_class: element class

        :return: доменный элемент или None, если подходящей записи нет

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        appointmentEvent.find_element(element_id = element_id, element_class = element_class)
        ```
        """
        raise NotImplementedError()

    def run(self) -> list[Notification]:
        """
        Формирует уведомления администраторам о новой записи.

        :return: список уведомлений, которые нужно отправить администраторам

        ### Пример использования:
        ```py
        appointmentEvent.run()
        ```
        """
        if not self.started:
            self.started = True
            notifications: list[Notification] = []
            quantity: int = self.settings.get("quantity", 1)

            filial: Filial | None = self.find_element(self.filial_id)
            filial_string: str = filial.get_notification() if filial else get_phrase("empty_filial").format(f"{self.filial_id=}")

            date: Date | None = self.find_element(self.date_id)
            date_string: str = ""

            if self.date_id >= 0:
                date_string: str = date.get_notification() if date else get_phrase("empty_date").format(f"{self.date_id=}")

            if date_string:
                on_date: str = get_phrase("on_date")
                date_string = f"{on_date}{date_string}"

            name_username: str = self.name + " ({})" if self.name else "{}"
            text: str = get_phrase("notification_appointment").format(name_username, filial_string, date_string)

            if self.phone:
                phone_notification: str = get_phrase("phone_notification")
                text = f"{text}, {phone_notification}: {cut(self.phone, INPUT_LENGTH)}"

            botkey_mes: BotkeyMessage = self.get_message(text)

            for i in range(quantity):
                admin: Admin | None = self.get_next_admin()

                if admin:
                    mes = botkey_mes

                    if not admin.check_permissions(("answer_users",)):
                        mes = botkey_mes.copy(no_buttons = True)

                    notification: Notification = Notification(admin, mes)
                    notifications.append(notification)

            return notifications
