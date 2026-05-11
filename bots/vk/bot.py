"""
Описывает транспортный бот и операции отправки или получения событий.
Модуль относится к архитектурной зоне: слой унификации транспортов `bots`, который скрывает различия Telegram и VK за общими объектами сообщений, клавиатур, вложений и событий.

### Публичные классы
- `Vkbot`: VK-адаптер общего интерфейса бота.

### Публичные функции
- Публичные функции отсутствуют.

### Связи
Используется транспортным слоем и wrapper-логикой, чтобы app-layer работал с `Message`, `Keyboard`, `Button`, `Attachment` и `Event` без привязки к конкретной соцсети.
"""

from __future__ import annotations


from bots.constants import logger_vk
from bots.utils.dates import get_date
from bots.utils.files import only_extension
from bots.utils.mapping import get_from, get_int
from bots.compat import (
    Any,
    Callable,
    DotDict,
    Iterable,
    Literal,
    VkApi,
    VkBotEvent,
    VkBotEventType,
    VkBotLongPoll,
    VkBotMessageEvent,
    VkUpload,
    datetime,
    json,
    timedelta,
    warn,
)
from bots.types import Any, Literal

from bots.base.bindings import Bot

class Vkbot(Bot):
    """
    VK transport-адаптер поверх `vk_api`.
    Класс создаёт VK API client и Long Poll, разбирает сообщения и payload
    события в `Bot.Event`, загружает вложения через VK upload и отправляет
    wrapper-сообщения через `messages.send`.

    ### Поля
    - `BOT_KEY`: строковый ключ транспорта, по которому app-layer различает Telegram и VK.
    - `URL`: базовый адрес API или служебного endpoint конкретного транспорта.
    - `bot`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.
    - `upload`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.
    - `attachments`: хранит вложения сообщения для операций этого объекта.

    ### Методы
    - `check_event`: Проверяет событие транспорта перед использованием.
    - `get_message_id`: Возвращает message id из текущего состояния `Vkbot`.
    - `__init__`: Создаёт объект и сохраняет данные, нужные transport-layer для отправки, сравнения или восстановления объекта.
    - `initAPI`: Инициализирует SDK конкретного транспорта с сохранёнными token и group_id.
    - `check_callback`: Проверяет callback-событие перед использованием.
    - `split_buttons`: Делит кнопки клавиатуры на части, допустимые для transport-layer.
    - `split`: Разбивает сообщение и вложения на части, допустимые для транспорта.
    - `send`: Отправляет сообщение или вложение через transport-layer.
    - `typing`: Отправляет в транспорт индикатор набора сообщения.
    - `get_attachment`: Возвращает вложение сообщения из текущего состояния `Vkbot`.

    ### Жизненный цикл
    Экземпляры создаются из конфигурации транспорта, принимают события платформы и отдают app-layer унифицированные wrapper-объекты.

    ### Пример использования
    ```py
    bot: Vkbot
    ```
    """
    BOT_KEY: Literal["vkbot"] = "vkbot"
    URL: str = "http://vk.com/"

    def check_event(event: VkBotMessageEvent | VkBotEvent | DotDict) -> bool:
        """
        Проверяет значение `event` перед сохранением или использованием.

        ### Аргументы:
        :param event: transport-событие для обработки

        :return: `True`, если значение `event` перед сохранением или использованием; иначе `False`

        ### Пример использования:
        ```py
        bot.check_event(event = event)
        ```
        """
        return isinstance(event, VkBotMessageEvent) or isinstance(event, VkBotEvent) or isinstance(event, DotDict) or isinstance(event, dict)


    def get_message_id(event: Bot.Event) -> int | None:
        """
        Возвращает сохранённый id transport-сообщения.

        ### Аргументы:
        :param event: transport-событие для обработки

        :return: идентификатор сообщения

        ### Пример использования:
        ```py
        bot.get_message_id(event = event)
        ```
        """
        for elem in event.events:
            if Vkbot.Message.check_id(None, elem):
                return int(elem)
        return None

    def __init__(self, token: str, name: str, group_id: int):
        """
        Создаёт `Vkbot` и сохраняет данные, нужные transport-layer для отправки, сравнения или восстановления объекта.

        ### Аргументы:
        :param token: секретный token transport-бота из безопасной конфигурации или storage
        :param name: служебное имя бота, элемента, команды или настройки
        :param group_id: идентификатор группы или сообщества транспорта

        ### Пример использования:
        ```py
        bot: Vkbot = Vkbot(token = token, name = name, group_id = group_id)
        ```
        """
        super().__init__(token, name, group_id)

        # Бот
        self.bot: VkApi

        # Загрузчик вложений
        self.upload: VkUpload

        self.initAPI()

        # Список загруженных вложений для предотвращения повторной загрузки
        self.attachments: dict[Vkbot.Attachment] = []

    def initAPI(self):
        """
        Инициализирует SDK конкретного транспорта с сохранёнными token и group_id.

        ### Пример использования:
        ```py
        bot.initAPI()
        ```
        """
        self.bot: VkApi = VkApi(token = self.token)
        self.upload: VkUpload = VkUpload(self.bot)

    def check_callback(self, event: Bot.Event) -> bool:
        """
        Проверяет, является ли transport-событие callback payload.

        ### Аргументы:
        :param event: transport-событие для обработки

        :return: `True`, если является ли transport-событие callback payload; иначе `False`

        ### Пример использования:
        ```py
        bot.check_callback(event = event)
        ```
        """
        if event.DEBUG_CALLBACK:
            return True

        for ev in event.events:
            if isinstance(ev, VkBotEvent) and not isinstance(ev, VkBotMessageEvent):
                return True

        return False


    def split_buttons(self, buttons: Iterable[Keyboard.Button], max_width: int) -> list[Keyboard]:
        """
        Делит сообщение или набор элементов на части, подходящие под ограничения transport/API.

        ### Аргументы:
        :param buttons: кнопки, которые нужно показать пользователю
        :param max_width: максимальная ширина строки кнопок

        :return: список VK keyboard-объектов, разбитых по `max_width`

        ### Пример использования:
        ```py
        bot.split_buttons(buttons = buttons, max_width = max_width)
        ```
        """
        keyboards: list[Vkbot.Keyboard] = []

        while buttons:
            keyboard: Vkbot.Keyboard = self.__class__.Keyboard(buttons, max_width = max_width, inline = True)
            buttons = keyboard.get_unused_buttons()
            keyboards.append(keyboard)

        return keyboards

    def split(self, text: str, buttons: Iterable[Keyboard.Button], attachments: Iterable[Attachment], reply: Message | None, forward: Iterable[Message], max_width: int, inline: bool) -> list[Message]:
        """
        Разбивает сообщение и вложения на части, допустимые для транспорта.

        ### Аргументы:
        :param text: текст
        :param buttons: кнопки, которые нужно показать пользователю
        :param attachments: вложения
        :param reply: сообщение, на которое дан ответ
        :param forward: пересылаемое сообщение
        :param max_width: максимальная ширина строки кнопок
        :param inline: признак inline-клавиатуры

        :return: список `Vkbot.Message`, разбитых по лимитам VK

        ### Пример использования:
        ```py
        bot.split(text = text, buttons = buttons, attachments = attachments, reply = reply, forward = forward, max_width = max_width, inline = inline)
        ```
        """
        attachments_groups: list[tuple[Vkbot.Attachment]] = self.split_attachments(attachments)
        texts: list[str] = self.split_text(text)
        keyboards: list[Vkbot.Keyboard] = self.split_buttons(buttons, max_width) if inline else [self.__class__.Keyboard(buttons, max_width = max_width, inline = inline)]
        messages: list[Vkbot.Message] = []

        for attachments in attachments_groups:
            message: Vkbot.Message = self.__class__.Message(self.bot, self.group_id, "", attachments = attachments)
            messages.append(message)

        for i, text in enumerate(texts):
            if i == 0 and messages:
                messages[-1].set_text(text)
            else:
                message: Vkbot.Message = self.__class__.Message(self.bot, self.group_id, text)
                messages.append(message)

        for i, keyboard in enumerate(keyboards):
            if i == 0 and messages:
                messages[-1].set_keyboard(keyboard)
            else:
                message: Vkbot.Message = self.__class__.Message(self.bot, self.group_id, self.__class__.Message.EMPTY_TEXT, keyboard = keyboard)
                messages.append(message)

        if forward:
            if messages:
                messages[0].set_forward(forward)
            else:
                message: Vkbot.Message = self.__class__.Message(self.bot, self.group_id, self.__class__.Message.EMPTY_TEXT, forward = forward)
                messages.append(message)
        elif reply:
            if messages:
                messages[0].set_reply(reply)
            else:
                message: Vkbot.Message = self.__class__.Message(self.bot, self.group_id, self.__class__.Message.EMPTY_TEXT, reply = reply)
                messages.append(message)

        return messages


    # Методы API


    def send(self, chat_id: int, text: str, buttons: Iterable[str] = [], filenames: Iterable[str] = [], compression: bool = True, inline: bool = True, max_width: int = 2, reply: Message | None = None, forward: Iterable[Message] = [], parse_mode: str = "") -> list[Message]:
        """
        Отправляет сообщение или вложение через transport-layer.

        ### Аргументы:
        :param chat_id: идентификатор чата
        :param text: текст
        :param buttons: кнопки, которые нужно показать пользователю
        :param filenames: имена файлов
        :param compression: признак сжатия вложения
        :param inline: признак inline-клавиатуры
        :param max_width: максимальная ширина строки кнопок
        :param reply: сообщение, на которое дан ответ
        :param forward: пересылаемое сообщение
        :param parse_mode: режим разметки сообщения

        :return: отправленные VK-сообщения, разобранные в `Vkbot.Message`

        ### Пример использования:
        ```py
        bot.send(chat_id = chat_id, text = text, buttons = buttons, filenames = filenames, compression = compression, inline = inline, max_width = max_width, reply = reply, forward = forward, parse_mode = parse_mode)
        ```
        """
        keyboard: Vkbot.Keyboard | None = None

        if buttons:
            keyboard = self.__class__.Keyboard(buttons, max_width = max_width, inline = inline)

        attachments: list[Vkbot.Attachment | Vkbot.PhotoAttachment | Vkbot.VideoAttachment | Vkbot.DocAttachment] = self.get_attachments(filenames, compression = compression)
        message: Vkbot.Message = Vkbot.Message(self.bot, self.group_id, text, keyboard, forward, reply, attachments)
        message.send(chat_id, parse_mode = parse_mode)
        return [message]

    def typing(self, chat_id: int):
        """
        Отправляет в транспорт индикатор набора сообщения.

        ### Аргументы:
        :param chat_id: идентификатор чата

        ### Пример использования:
        ```py
        bot.typing(chat_id = chat_id)
        ```
        """
        self.bot.method("messages.setActivity", {"peer_id": chat_id, "type": "typing"})


    def get_attachment(self, filename: str, compression: bool = True) -> Vkbot.Attachment:
        """
        Возвращает сохранённое transport-вложение.

        ### Аргументы:
        :param filename: имя файла
        :param compression: признак сжатия вложения

        :return: вложение сообщения

        :raises RuntimeError: если объект ещё не связан с необходимым runtime-состоянием

        ### Пример использования:
        ```py
        bot.get_attachment(filename = filename, compression = compression)
        ```
        """
        if not self.get_bot_key:
            raise RuntimeError("Метод get_attachments доступен только для дочерних классов")

        def get_attachment_type(extension: str) -> Literal["photo", "video", "doc"]:
            """
            Возвращает тип вложения основываясь на указанном расширении файла
            Сопоставление расширений и типов вложений хранится в словаре EXTENSIONS
            :param extension: Обязательно в нижнем регистре и с точкой ".jpg"
            Иначе возвращает тип вложения по умолчанию, который хранится в DEFAULT_ATTACHMENT_TYPE
            """
            for attachment_type, extensions in self.__class__.Attachment.EXTENSIONS.items():
                if extension in extensions:
                    return attachment_type

            return self.__class__.Attachment.DEFAULT_ATTACHMENT_TYPE

        # Методы загрузки на сервер для разных типов вложений
        uploads: dict[str, Callable] = {
            "photo": self.__class__.PhotoAttachment.from_filename,
            "video": self.__class__.VideoAttachment.from_filename,
            "doc": self.__class__.DocAttachment.from_filename,
        }

        # Значение по умолчанию
        attachment_type: str = self.__class__.Attachment.DEFAULT_ATTACHMENT_TYPE

        # Значение по расширению файла только если загрузка со сжатием, без сжатия всегда "doc"
        if compression:
            extension: str = only_extension(filename).lower()
            attachment_type = get_attachment_type(extension)

        # Вызов соответствующего метода загрузки вложения
        attachment_type = str(attachment_type).lower()
        upload: Callable = uploads[attachment_type]
        attachment: Vkbot.Attachment = upload(filename, self)
        return attachment

    def get_attachments(self, filenames: Iterable[str], compression: bool = True) -> list[Vkbot.Attachment]:
        """
        Возвращает сохранённые вложения сообщения.

        ### Аргументы:
        :param filenames: имена файлов
        :param compression: признак сжатия вложения

        :return: вложения сообщения

        ### Пример использования:
        ```py
        bot.get_attachments(filenames = filenames, compression = compression)
        ```
        """
        attachments: list[Vkbot.Attachment] = []

        for filename in filenames:
            attachment: Vkbot.Attachment = self.get_attachment(filename, compression)
            attachments.append(attachment)

        return attachments


    # Обработчики


    def extract_name(self, event: Bot.Event, chat_id: int) -> tuple[str, str]:
        """
        Формирует имя файла для локального сохранения transport-вложения.

        ### Аргументы:
        :param event: transport-событие для обработки
        :param chat_id: идентификатор чата

        :return: имя и фамилия отправителя, полученные из VK users API

        ### Пример использования:
        ```py
        bot.extract_name(event = event, chat_id = chat_id)
        ```
        """
        first_name: str = ""
        last_name: str = ""

        try:
            vk = self.bot.get_api()
            user_info = vk.users.get(user_ids=chat_id, fields="first_name,last_name")[0]
            first_name = user_info["first_name"]
            last_name = user_info["last_name"]
            event.set_name(first_name, last_name)
        except Exception as err:
            logger_vk.exception(f"Ошибка при получении данных пользователя {chat_id=} {err=}")

        return (first_name, last_name)

    def parse_message(self, message: DotDict | dict, date: datetime, owner_id: int | None = None) -> Bot.Event:
        """
        Разбирает входные данные платформы и возвращает wrapper-объект для app-layer.

        ### Аргументы:
        :param message: сообщение проекта или сообщение конкретного транспорта
        :param date: время сообщения или события
        :param owner_id: идентификатор владельца сообщения

        :return: `Bot.Event` с текстом, payload и вложениями VK-сообщения

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        bot.parse_message(message = message, date = date, owner_id = owner_id)
        ```
        """
        chat_id: int = get_int(message, -1, "from_id")
        _owner_id: int | None = owner_id
        owner_id: int = chat_id if owner_id is None else owner_id

        if chat_id < 0:
            # Только для reply_message и fwd_messages
            chat_id = get_int(message, -1, "peer_id")

        if chat_id < 0:
            raise ValueError(f"Некорректное значение словаря с ключом from_id или peer_id={repr(chat_id)}")

        self.add_id(chat_id)

        text: str = get_from(message, "text", types = (str,), default = "")
        date: datetime = get_date(message, "date")

        # reply
        reply: DotDict | None = get_from(message, "reply_message")
        reply_event: Bot.Event | None = None

        if reply:
            reply_event = self.parse_message(reply, date, _owner_id)
            reply_event.set_events([reply])

        # fwd_messages
        forward_events: list[Bot.Event] = []
        fwd_messages: list[dict] = get_from(message, "fwd_messages") or []

        for fwd in fwd_messages:
            fwd_date: datetime = get_date(fwd, "date")
            fwd_event: Bot.Event = self.parse_message(fwd, fwd_date, _owner_id)
            fwd_event.set_events([fwd])
            forward_events.append(fwd_event)

        # Обработка вложений
        attachments_list: list[dict | DotDict] = get_from(message, "attachments", types = (list,), default = [])
        attachments: list[Vkbot.Attachment] = []

        for attachment_data in attachments_list:
            attachment_type: Literal["photo", "video", "doc", "audio_message"] = attachment_data.type if "type" in dir(attachment_data) else attachment_data.get("type", None)
            attachment: Vkbot.PhotoAttachment | Vkbot.VideoAttachment | Vkbot.DocAttachment | Vkbot.AudioAttachment

            match attachment_type:
                case "photo":
                    attachment = self.__class__.PhotoAttachment(attachment_data)
                    attachments.append(attachment)
                case "video":
                    attachment = self.__class__.VideoAttachment(attachment_data)
                    attachments.append(attachment)
                case "doc":
                    attachment = self.__class__.DocAttachment(attachment_data)
                    attachments.append(attachment)
                case "audio_message":
                    attachment = self.__class__.AudioAttachment(attachment_data)
                    attachments.append(attachment)
                case _:
                    warn(f"Некорректное значение словаря с ключом type={repr(attachment_type)} во вложении сообщения")
                    continue


        event: Bot.Event = self.__class__.Event(owner_id, chat_id, text, date, attachments = attachments, reply = reply_event, forward = forward_events)
        event.set_events([message])
        self.extract_name(event, chat_id)
        return event


    def process_message(self, event: VkBotMessageEvent, date: datetime):
        """
        Обрабатывает message в текущем runtime-контексте.

        ### Аргументы:
        :param event: transport-событие для обработки
        :param date: время сообщения или события

        :return: результат обработки нормализованного VK message-события

        ### Пример использования:
        ```py
        bot.process_message(event = event, date = date)
        ```
        """
        match event.type:
            case VkBotEventType.MESSAGE_NEW:
                ev: Bot.Event = self.parse_message(event.message, date)
                ev.set_events([event])
                return self.process_event(ev)


    def process_payload(self, event: VkBotEvent, date: datetime):
        """
        Обрабатывает JSON-совместимое состояние в текущем runtime-контексте.

        ### Аргументы:
        :param event: transport-событие для обработки
        :param date: время сообщения или события

        :return: результат обработки VK callback/payload-события

        ### Пример использования:
        ```py
        bot.process_payload(event = event, date = date)
        ```
        """
        match event.type:
            case VkBotEventType.MESSAGE_EVENT:
                payload: Any = get_from(event, "object", "payload")
                callback_data: str = ""

                if isinstance(payload, str):
                    callback_data = payload
                elif isinstance(payload, dict):
                    if "type" in payload:
                        callback_data = payload["type"]
                    else:
                        callback_data = json.dumps(event.object["payload"])
                elif payload:
                    callback_data = json.dumps(event.object["payload"])

                user_id: int = get_int(event, -1, "object", "peer_id")
                ev: Bot.Event = self.__class__.Event(user_id, user_id, callback_data, datetime.now())
                ev.set_events([event])
                self.extract_name(ev, user_id)
                return self.process_event(ev, combine_events = False)

    def polling(self, skip: float = 0, warning: bool = True):
        """
        Запускает получение входящих событий из API транспорта.

        ### Аргументы:
        :param skip: нужно ли пропустить предупреждение или действие
        :param warning: нужно ли вывести предупреждение

        :return: метод запускает цикл VK Long Poll и не возвращает значение

        :raises err: если нижележащий слой сообщает об ошибке операции

        ### Пример использования:
        ```py
        bot.polling(skip = skip, warning = warning)
        ```
        """

        from_date: datetime = datetime.now()

        if skip > 0:
            from_date += timedelta(seconds = skip)

        def check():
            return skip <= 0 or datetime.now() >= from_date

        def show_warn():
            if warning:
                logger_vk.warning("Пропущено событие %s", datetime.now())

        def polling():
            """
            Непосредственный обработчик событий
            """
            longpoll: VkBotLongPoll = VkBotLongPoll(self.bot, self.group_id)

            for event in longpoll.listen():
                event: VkBotEvent | VkBotMessageEvent = event

                if self.check_working():
                    if check():
                        message: DotDict | None = get_from(event, "message")

                        if message:
                            date: datetime = get_date(message, "date")
                            # Обработка события в отдельном потоке
                            return self.process_message(event, date)
                        elif "object" in dir(event) and isinstance(event.object, DotDict) and "payload" in event.object:
                            return self.process_payload(event, datetime.now())
                    else:
                        show_warn()
                else:
                    return   # Выход из polling


        while self.check_working():
            try:
                polling()
            # Перехват конкретной ошибки TypeError после удаления сообщения
            except TypeError as err:
                # После bot.method("messages.delete",{}) прилетает event и вместе с ним TypeError
                if not str(err) == "'<' not supported between instances of 'NoneType' and 'int'":
                    raise err


    # Переопределённые методы для работы с полями класса


    @classmethod
    def check_token(cls, token: str) -> bool:
        """
        Проверяет минимальный формат token транспортного бота.

        ### Аргументы:
        :param token: секретный token, полученный из конфигурации или storage

        :return: `True`, если минимальный формат token транспортного бота; иначе `False`

        ### Пример использования:
        ```py
        Vkbot.check_token(token = token)
        ```
        """
        return super().check_token(token) and len(token) >= 220 and token.startswith("vk")

    def set_token(self, token: str):
        """
        Проверяет и сохраняет token транспортного адаптера в состоянии `Vkbot`.

        ### Аргументы:
        :param token: секретный token transport-бота из безопасной конфигурации или storage

        :return: метод изменяет `self.token` и переинициализирует VK API

        ### Пример использования:
        ```py
        bot.set_token(token = token)
        ```
        """
        return super().set_token(token)

    def get_token(self) -> str:
        """
        Возвращает сохранённый token transport-бота после проверки формата.

        :return: секретный token transport-бота

        ### Пример использования:
        ```py
        bot.get_token()
        ```
        """
        return super().get_token()
