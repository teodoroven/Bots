"""
Описывает транспортный бот и операции отправки или получения событий.
Модуль относится к архитектурной зоне: слой унификации транспортов `bots`, который скрывает различия Telegram и VK за общими объектами сообщений, клавиатур, вложений и событий.

### Публичные классы
- `Telebot`: Telegram-адаптер общего интерфейса бота.

### Публичные функции
- Публичные функции отсутствуют.

### Связи
Используется транспортным слоем и wrapper-логикой, чтобы app-layer работал с `Message`, `Keyboard`, `Button`, `Attachment` и `Event` без привязки к конкретной соцсети.
"""

from __future__ import annotations


from bots.constants import logger_telegram
from bots.utils.dates import get_date
from bots.utils.files import only_extension
from bots.utils.mapping import is_int
from bots.compat import (
    Callable,
    CallbackQuery,
    InputMediaAudio,
    InputMediaDocument,
    InputMediaPhoto,
    InputMediaVideo,
    Iterable,
    Literal,
    PhotoSize,
    TeleBot,
    TelebotMessage,
    datetime,
    timedelta,
    warn,
)
from bots.types import Literal

from bots.base.bindings import Bot

class Telebot(Bot):
    """
    Telegram transport-адаптер поверх `telebot`.
    Класс создаёт SDK-клиент, парсит Telegram messages/callbacks/files в
    `Bot.Event`, отправляет wrapper-сообщения и запускает polling.

    ### Поля
    - `BOT_KEY`: строковый ключ транспорта, по которому app-layer различает Telegram и VK.
    - `URL`: базовый адрес API или служебного endpoint конкретного транспорта.
    - `bot`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.
    - `attachments`: хранит вложения сообщения для операций этого объекта.

    ### Методы
    - `check_event`: Проверяет событие транспорта перед использованием.
    - `get_message_id`: Возвращает message id из текущего состояния `Telebot`.
    - `__init__`: Создаёт объект и сохраняет данные, нужные transport-layer для отправки, сравнения или восстановления объекта.
    - `initAPI`: Инициализирует SDK конкретного транспорта с сохранёнными token и group_id.
    - `check_callback`: Проверяет callback-событие перед использованием.
    - `split`: Разбивает сообщение и вложения на части, допустимые для транспорта.
    - `typing`: Отправляет в транспорт индикатор набора сообщения.
    - `get_attachment`: Возвращает вложение сообщения из текущего состояния `Telebot`.
    - `get_attachments`: Возвращает вложения сообщения из текущего состояния `Telebot`.
    - `split_attachments`: Делит вложения сообщения на части, допустимые для transport-layer.

    ### Жизненный цикл
    Экземпляры создаются из конфигурации транспорта, принимают события платформы и отдают app-layer унифицированные wrapper-объекты.

    ### Пример использования
    ```py
    bot: Telebot
    ```
    """
    BOT_KEY: Literal["telebot"] = "telebot"
    URL: str = "http://t.me/"

    def check_event(event: TelebotMessage | CallbackQuery) -> bool:
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
        return isinstance(event, TelebotMessage) or isinstance(event, CallbackQuery)


    def get_message_id(event: Bot.Event) -> int:
        """
        Возвращает сохранённый id transport-сообщения.

        ### Аргументы:
        :param event: transport-событие для обработки

        :return: идентификатор сообщения

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        bot.get_message_id(event = event)
        ```
        """
        for ev in event.get_events():
            if isinstance(ev, TelebotMessage):
                return ev.message_id
            elif isinstance(ev, CallbackQuery):
                return ev.message.message_id
            else:
                raise ValueError(f"Некорректное значение поля {event.event=}. Ожидался telebot.types.Message или telebot.types.CallbackQuery")

    def __init__(self, token: str, name: str, group_id: int):
        """
        Создаёт `Telebot` и сохраняет данные, нужные transport-layer для отправки, сравнения или восстановления объекта.

        ### Аргументы:
        :param token: секретный token transport-бота из безопасной конфигурации или storage
        :param name: служебное имя бота, элемента, команды или настройки
        :param group_id: идентификатор группы или сообщества транспорта

        ### Пример использования:
        ```py
        bot: Telebot = Telebot(token = token, name = name, group_id = group_id)
        ```
        """
        super().__init__(token, name, group_id)
        self.bot: TeleBot = self.initAPI()

        self.attachments: dict[Telebot.Attachment] = []

    def initAPI(self) -> TeleBot:
        """
        Инициализирует SDK конкретного транспорта с сохранёнными token и group_id.

        :return: инициализированный `telebot.TeleBot` с текущим token

        ### Пример использования:
        ```py
        bot.initAPI()
        ```
        """
        return TeleBot(self.token)

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
            if isinstance(ev, CallbackQuery):
                return True

        return False

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

        :return: список `Telebot.Message`, разбитых по ограничениям Telegram

        ### Пример использования:
        ```py
        bot.split(text = text, buttons = buttons, attachments = attachments, reply = reply, forward = forward, max_width = max_width, inline = inline)
        ```
        """
        attachments_groups: list[tuple[Telebot.Attachment]] = self.split_attachments(attachments)
        texts: list[str] = self.split_text(text)
        messages: list[Telebot.Message] = []

        for attachments in attachments_groups:
            message: Telebot.Message = self.__class__.Message(self.bot, self.group_id, "", attachments = attachments)
            messages.append(message)

        for i, text in enumerate(texts):
            if i == 0 and messages and ((not messages[-1].attachments) or (not buttons)):
                messages[-1].set_text(text)
            else:
                message: Telebot.Message = self.__class__.Message(self.bot, self.group_id, text)
                messages.append(message)

        if buttons:
            keyboard: Telebot.Keyboard = self.__class__.Keyboard(buttons, max_width = max_width, inline = inline)

            if messages and not messages[-1].attachments:
                messages[-1].set_keyboard(keyboard)
            else:
                message: Telebot.Message = self.__class__.Message(self.bot, self.group_id, "", keyboard = keyboard)
                messages.append(message)

        if forward:
            if messages:
                messages[0].set_forward(forward)
            else:
                message: Telebot.Message = self.__class__.Message(self.bot, self.group_id, self.__class__.Message.EMPTY_TEXT, forward = forward)
                messages.append(message)
        elif reply:
            if messages:
                messages[0].set_reply(reply)
            else:
                message: Telebot.Message = self.__class__.Message(self.bot, self.group_id, self.__class__.Message.EMPTY_TEXT, reply = reply)
                messages.append(message)

        return messages


    #


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
        self.bot.send_chat_action(chat_id, "typing")


    def get_attachment(self, filename: str, compression: bool = True) -> Telebot.Attachment:
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

        def get_attachment_type(extension: str) -> type[InputMediaPhoto] | type[InputMediaVideo] | type[InputMediaVideo] | type[InputMediaAudio] | type[InputMediaDocument]:
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
        uploads: dict[type[InputMediaPhoto] | type[InputMediaVideo] | type[InputMediaVideo] | type[InputMediaAudio] | type[InputMediaDocument], Callable] = {
            InputMediaPhoto: self.__class__.PhotoAttachment.from_filename,
            InputMediaVideo: self.__class__.VideoAttachment.from_filename,
            InputMediaVideo: self.__class__.AudioAttachment.from_filename,
            InputMediaDocument: self.__class__.DocAttachment.from_filename
        }

        # Значение по умолчанию
        attachment_type: type[InputMediaPhoto] | type[InputMediaVideo] | type[InputMediaVideo] | type[InputMediaAudio] | type[InputMediaDocument] = self.__class__.Attachment.DEFAULT_ATTACHMENT_TYPE

        # Значение по расширению файла только если загрузка со сжатием, без сжатия всегда "doc"
        if compression:
            extension: str = only_extension(filename).lower()
            attachment_type = get_attachment_type(extension)

        # Вызов соответствующего метода загрузки вложения
        upload: Callable = uploads[attachment_type]
        attachment: Telebot.Attachment = upload(filename)
        return attachment

    def get_attachments(self, filenames: Iterable[str], compression: bool = True) -> list[Telebot.Attachment]:
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
        attachments: list[Telebot.Attachment] = []

        for filename in filenames:
            attachment: Telebot.Attachment = self.get_attachment(filename, compression)
            attachments.append(attachment)

        return attachments

    def split_attachments(self, attachments: Iterable[Attachment]) -> list[tuple[Attachment]]:
        """
        Делит вложения сообщения на части, допустимые для transport-layer.

        ### Аргументы:
        :param attachments: вложения wrapper-сообщения

        :return: группы вложений, совместимые с Telegram media group

        ### Пример использования:
        ```py
        bot.split_attachments(attachments = attachments)
        ```
        """
        max_attachments: int = self.__class__.Message.MAX_ATTACHMENTS_IN_GROUP
        result: list[tuple[Telebot.Attachment, ...]] = []
        current_batch: list[Telebot.Attachment] = []
        current_media_types: set[type[InputMediaPhoto | InputMediaVideo | InputMediaAudio | InputMediaDocument]] = set()

        for attachment in attachments:
            media_type = attachment.get_media_type()

            if (len(current_batch) >= max_attachments or
                (InputMediaDocument in current_media_types and media_type != InputMediaDocument) or
                (current_media_types and InputMediaDocument not in current_media_types and media_type == InputMediaDocument)):

                result.append(current_batch)
                current_batch = [attachment]
                current_media_types = {media_type}
            else:
                current_batch.append(attachment)
                current_media_types.add(media_type)

        if current_batch:
            result.append(current_batch)

        return result

    def send(self, chat_id: int, text: str, buttons: Iterable[str] = [], filenames: Iterable[str] = [], inline: bool = True, max_width: int = 2, compression: bool = True, reply: Message | None = None, forward: Iterable[Message] = [], parse_mode: str = "") -> list[Message]:
        """
        Отправляет сообщение или вложение через transport-layer.

        ### Аргументы:
        :param chat_id: идентификатор чата
        :param text: текст
        :param buttons: кнопки, которые нужно показать пользователю
        :param filenames: имена файлов
        :param inline: признак inline-клавиатуры
        :param max_width: максимальная ширина строки кнопок
        :param compression: признак сжатия вложения
        :param reply: сообщение, на которое дан ответ
        :param forward: пересылаемое сообщение
        :param parse_mode: режим разметки сообщения

        :return: отправленные Telegram-сообщения, разобранные в `Telebot.Message`

        ### Пример использования:
        ```py
        bot.send(chat_id = chat_id, text = text, buttons = buttons, filenames = filenames, inline = inline, max_width = max_width, compression = compression, reply = reply, forward = forward, parse_mode = parse_mode)
        ```
        """
        keyboard: Telebot.Keyboard | None = None

        if buttons:
            keyboard = self.__class__.Keyboard(buttons, max_width = max_width, inline = inline)

        attachments: list[Telebot.PhotoAttachment | Telebot.VideoAttachment | Telebot.AudioAttachment | Telebot.DocAttachment] = self.get_attachments(filenames, compression = compression)
        message: Telebot.Message = Telebot.Message(self.bot, self.group_id, text, keyboard, forward, reply, attachments)
        responses: dict[str, list[TelebotMessage]] = message.send(chat_id, parse_mode = parse_mode)
        messages: list[Telebot.Message] = self.parse_responses(responses, datetime.now(), self.group_id)
        return messages

    def send_voice(self, chat_id: int, text: str, reply: Message | None = None) -> list[Message]:
        """
        Отправляет или переотправляет подготовленное сообщение через доступный transport/API.

        ### Аргументы:
        :param chat_id: идентификатор чата
        :param text: текст
        :param reply: сообщение, на которое дан ответ

        :return: метод отправляет voice-сообщение через Telegram API и не возвращает значение

        ### Пример использования:
        ```py
        bot.send_voice(chat_id = chat_id, text = text, reply = reply)
        ```
        """
        message: Telebot.VoiceMessage = Telebot.VoiceMessage(self.bot, self.group_id, text, None, reply)
        message.synthesize()
        message.send(chat_id)


    # Обработчики


    def parse_responses(self, responses: dict[str, list[TelebotMessage]], date: datetime, owner_id: int | None) -> list[Telebot.Message]:
        """
        Разбирает входные данные платформы и возвращает wrapper-объект для app-layer.

        ### Аргументы:
        :param responses: ответы Telegram API
        :param date: время сообщения или события
        :param owner_id: идентификатор владельца сообщения

        :return: список `Telebot.Message`, восстановленных из ответов Telegram API

        :raises IndexError: если нижележащий слой сообщает об ошибке операции

        ### Пример использования:
        ```py
        bot.parse_responses(responses = responses, date = date, owner_id = owner_id)
        ```
        """
        attachments_responses: list[TelebotMessage] = responses.get("attachments", [])
        attachments_filenames: list[str] = responses.get("filenames", [])
        forward_responses: list[TelebotMessage] = responses.get("forward", [])
        messages: list[Telebot.Message] = []

        for response in forward_responses:
            message_id: str = response.id
            chat_id: int = response.chat.id
            event: Bot.Event = self.parse_message(response, get_date(response, "date", default = date), owner_id)

            mes: Telebot.Message = Telebot.Message.from_event(event, self.bot)
            mes.set_id(message_id)
            mes.set_chat_id(chat_id)
            messages.append(mes)

        for i, response in enumerate(attachments_responses):
            if i >= len(attachments_filenames):
                raise IndexError(f"Некорректное значение аргумента {responses=}. Словарь обязан содержать идентичное количество элементов в значениях с ключами 'attachments' и 'filenames'.")

            message_id: str = response.id
            chat_id: int = response.chat.id
            event: Bot.Event = self.parse_files(response, get_date(response, "date", default = date), owner_id)

            message: Telebot.Message = Telebot.Message.from_event(event, self.bot)
            message.set_id(message_id)
            message.set_chat_id(chat_id)
            try:
                message.attachments[0].set_filename(attachments_filenames[i])  # После отправки сообщения (загрузки вложения) в responses должно быть ровно 1 вложение на 1 сообщение
            except IndexError:
                pass
            messages.append(message)

        return messages


    def parse_message(self, message: TelebotMessage, date: datetime, owner_id: int | None = None) -> Bot.Event:
        """
        Разбирает входные данные платформы и возвращает wrapper-объект для app-layer.

        ### Аргументы:
        :param message: сообщение проекта или сообщение конкретного транспорта
        :param date: время сообщения или события
        :param owner_id: идентификатор владельца сообщения

        :return: `Bot.Event` с текстом Telegram-сообщения и данными отправителя

        ### Пример использования:
        ```py
        bot.parse_message(message = message, date = date, owner_id = owner_id)
        ```
        """
        chat_id: int = message.from_user.id
        owner_id: int = chat_id if owner_id is None else owner_id
        text: str = message.text or ""
        self.add_id(chat_id)

        event: Bot.Event = self.__class__.Event(owner_id, chat_id, text, date)
        event.set_events([message])

        first_name = message.from_user.first_name
        last_name = message.from_user.last_name or ""
        event.set_name(first_name, last_name)

        return event

    def parse_callback(self, callback: CallbackQuery, date: datetime, owner_id: int | None = None) -> Bot.Event:
        """
        Разбирает входные данные платформы и возвращает wrapper-объект для app-layer.

        ### Аргументы:
        :param callback: callback-событие transport API
        :param date: время сообщения или события
        :param owner_id: идентификатор владельца сообщения

        :return: `Bot.Event` с callback payload из `CallbackQuery.data`

        ### Пример использования:
        ```py
        bot.parse_callback(callback = callback, date = date, owner_id = owner_id)
        ```
        """
        chat_id: int = callback.message.chat.id
        owner_id: int = chat_id if owner_id is None else owner_id
        text: str = callback.data or ""
        self.add_id(chat_id)

        event: Bot.Event = self.__class__.Event(owner_id, chat_id, text, date)
        event.set_events([callback])

        first_name: str = callback.from_user.first_name
        last_name: str = callback.from_user.last_name or ""
        event.set_name(first_name, last_name)

        return event

    def parse_voice(self, message: TelebotMessage, date: datetime, owner_id: int | None = None) -> Bot.Event:
        """
        Разбирает входные данные платформы и возвращает wrapper-объект для app-layer.

        ### Аргументы:
        :param message: сообщение проекта или сообщение конкретного транспорта
        :param date: время сообщения или события
        :param owner_id: идентификатор владельца сообщения

        :return: `Bot.Event` с voice/audio attachment из Telegram-сообщения

        ### Пример использования:
        ```py
        bot.parse_voice(message = message, date = date, owner_id = owner_id)
        ```
        """
        chat_id: int = message.chat.id
        owner_id: int = chat_id if owner_id is None else owner_id
        self.add_id(chat_id)
        attachment: Telebot.AudioAttachment = self.__class__.AudioAttachment(message.voice)

        event: Bot.Event = self.__class__.Event(owner_id, chat_id, "", date, attachments = [attachment])
        event.set_events([message])

        first_name = message.from_user.first_name
        last_name = message.from_user.last_name or ""
        event.set_name(first_name, last_name)

        return event

    def parse_files(self, message: TelebotMessage, date: datetime, owner_id: int | None = None):
        """
        Разбирает входные данные платформы и возвращает wrapper-объект для app-layer.

        ### Аргументы:
        :param message: сообщение проекта или сообщение конкретного транспорта
        :param date: время сообщения или события
        :param owner_id: идентификатор владельца сообщения

        :return: `Bot.Event` с файловыми вложениями и caption

        ### Пример использования:
        ```py
        bot.parse_files(message = message, date = date, owner_id = owner_id)
        ```
        """
        chat_id: int = message.from_user.id
        owner_id: int = chat_id if owner_id is None else owner_id
        text: str = message.caption or ""
        self.add_id(chat_id)
        attachments: list[Telebot.Attachment] = []

        if message.photo:
            photo: PhotoSize = message.photo[-1]
            sizes: list[PhotoSize] = message.photo[:-1]
            attachment: Telebot.PhotoAttachment = Telebot.PhotoAttachment(photo, sizes)
            attachments.append(attachment)

        if message.video:
            attachment: Telebot.VideoAttachment = Telebot.VideoAttachment(message.video)
            attachments.append(attachment)

        if message.audio:
            attachment: Telebot.AudioAttachment = Telebot.AudioAttachment(message.audio)
            attachments.append(attachment)

        if message.document:
            attachment: Telebot.DocAttachment = Telebot.DocAttachment(message.document)
            attachments.append(attachment)

        event: Bot.Event = self.__class__.Event(owner_id, chat_id, text, date, attachments = attachments)
        event.set_events([message])

        first_name = message.from_user.first_name
        last_name = message.from_user.last_name or ""
        event.set_name(first_name, last_name)

        return event


    def process_message(self, message: TelebotMessage, date: datetime):
        """
        Обрабатывает message в текущем runtime-контексте.

        ### Аргументы:
        :param message: сообщение проекта или сообщение конкретного транспорта
        :param date: время сообщения или события

        :return: результат обработки нормализованного события через `process_event`

        ### Пример использования:
        ```py
        bot.process_message(message = message, date = date)
        ```
        """
        event = self.parse_message(message, date)
        return self.process_event(event)

    def process_callback(self, callback: CallbackQuery, date: datetime):
        """
        Обрабатывает callback в текущем runtime-контексте.

        ### Аргументы:
        :param callback: callback-событие transport API
        :param date: время сообщения или события

        :return: результат обработки callback-события через `process_event`

        ### Пример использования:
        ```py
        bot.process_callback(callback = callback, date = date)
        ```
        """
        event = self.parse_callback(callback, date)
        return self.process_event(event, combine_events = False)

    def process_voice(self, message: TelebotMessage, date: datetime):
        """
        Обрабатывает voice в текущем runtime-контексте.

        ### Аргументы:
        :param message: сообщение проекта или сообщение конкретного транспорта
        :param date: время сообщения или события

        :return: результат обработки voice-события через `process_event`

        ### Пример использования:
        ```py
        bot.process_voice(message = message, date = date)
        ```
        """
        event = self.parse_voice(message, date)
        return self.process_event(event)

    def process_file(self, message: TelebotMessage, date: datetime):
        """
        Обрабатывает file в текущем runtime-контексте.

        ### Аргументы:
        :param message: сообщение проекта или сообщение конкретного транспорта
        :param date: время сообщения или события

        :return: результат обработки file-события через `process_event`

        ### Пример использования:
        ```py
        bot.process_file(message = message, date = date)
        ```
        """
        event = self.parse_files(message, date)
        return self.process_event(event)

    def polling(self, skip: float = 0, warning: bool = True):
        """
        Запускает получение входящих событий из API транспорта.

        ### Аргументы:
        :param skip: нужно ли пропустить предупреждение или действие
        :param warning: нужно ли вывести предупреждение

        :return: метод запускает `telebot.infinity_polling`

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
                logger_telegram.warning("Пропущено событие %s", datetime.now())

        def polling():
            # Обработчик текстовых сообщений
            @self.bot.message_handler(content_types = ["text"])
            def message_handler(message: TelebotMessage):
                return self.process_message(message, get_date(message.date)) if check() else show_warn()

            # Обработчик нажатий на кнопки
            @self.bot.callback_query_handler(func = lambda call: True)
            def callback_query_handler(callback: CallbackQuery):
                return self.process_callback(callback, datetime.now()) if check() else show_warn()

            # Обработчик голосовых сообщений
            @self.bot.message_handler(content_types = ["voice"])
            def voice_message_handler(voice: TelebotMessage):
                return self.process_voice(voice, get_date(voice.date)) if check() else show_warn()

            # Обработчик файлов
            @self.bot.message_handler(content_types = ["photo", "video", "audio", "document"])
            def file_handler(message):
                return self.process_file(message, get_date(message.date)) if check() else show_warn()

            return self.bot.polling(none_stop = True, interval = 0)

        while self.check_working():
            polling()


    # Переопределённые методы работы с полями


    @classmethod
    def check_name(cls, name: str) -> bool:
        """
        Проверяет, можно ли использовать строку как имя transport-бота.

        ### Аргументы:
        :param name: имя

        :return: `True`, если строку можно использовать как имя transport-бота; иначе `False`

        ### Пример использования:
        ```py
        Telebot.check_name(name = name)
        ```
        """
        return super().check_name(name) and name.endswith("bot")

    def set_name(self, name: str):
        """
        Проверяет и сохраняет служебное имя в состоянии `Telebot`.

        ### Аргументы:
        :param name: служебное имя бота, элемента, команды или настройки

        :return: метод изменяет `self.name` и не возвращает значение

        ### Пример использования:
        ```py
        bot.set_name(name = name)
        ```
        """
        return super().set_name(name)

    def get_name(self) -> str:
        """
        Возвращает сохранённое имя.

        :return: служебное имя

        ### Пример использования:
        ```py
        bot.get_name()
        ```
        """
        return super().get_name()


    @classmethod
    def check_group_id(cls, group_id: int) -> bool:
        """
        Проверяет, что group_id транспорта является неотрицательным целым числом.

        ### Аргументы:
        :param group_id: идентификатор группы или сообщества транспорта

        :return: `True`, если что group_id транспорта является неотрицательным целым числом; иначе `False`

        :raises Exception: если нижележащий слой сообщает об ошибке операции

        ### Пример использования:
        ```py
        Telebot.check_group_id(group_id = group_id)
        ```
        """
        if isinstance(group_id, str):
            raise Exception()
        return isinstance(group_id, int) and group_id >= 0

    def set_group_id(self, group_id: int):
        """
        Проверяет и сохраняет идентификатор группы или сообщества в состоянии `Telebot`.

        ### Аргументы:
        :param group_id: идентификатор группы или сообщества транспорта

        :raises ValueError: если значение не проходит локальную проверку перед сохранением

        ### Пример использования:
        ```py
        bot.set_group_id(group_id = group_id)
        ```
        """
        if self.__class__.check_group_id(group_id):
            token_group_id: int = self.token[:self.token.find(":")]

            if group_id != token_group_id and self.token:
                warn(f"Значение аргумента {group_id=} не совпадает с идентификатором группы в поле self.token")

            self.group_id = group_id
        else:
            raise ValueError(f"Некорректное значение аргумента {group_id=}")

    def get_group_id(self) -> int:
        """
        Возвращает сохранённый идентификатор группы или сообщества транспорта.

        :return: идентификатор группы или сообщества транспорта

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        bot.get_group_id()
        ```
        """
        if self.__class__.check_group_id(self.group_id):
            token_group_id: str | int = self.token[:self.token.find(":")]

            if token_group_id and is_int(token_group_id):
                token_group_id = int(token_group_id)
            else:
                self.get_token()
                raise NotImplementedError("Недостижимый код: get_token должен вызвать исключение")

            if self.group_id == token_group_id:
                return self.group_id
            else:
                raise ValueError(f"Значение атрибута {self.group_id=} не совпадает с идентификатором группы в поле self.token")
        else:
            raise ValueError(f"Некорректное значение атрибута {self.group_id=}")

    @classmethod
    def check_token(cls, token: str) -> bool:
        """
        Проверяет минимальный формат token транспортного бота.

        ### Аргументы:
        :param token: секретный token, полученный из конфигурации или storage

        :return: `True`, если минимальный формат token транспортного бота; иначе `False`

        ### Пример использования:
        ```py
        Telebot.check_token(token = token)
        ```
        """
        return super().check_token(token) and ":" in token and is_int(token[:token.find(":")])

    def set_token(self, token: str):
        """
        Проверяет и сохраняет token транспортного адаптера в состоянии `Telebot`.

        ### Аргументы:
        :param token: секретный token transport-бота из безопасной конфигурации или storage

        :raises ValueError: если значение не проходит локальную проверку перед сохранением

        ### Пример использования:
        ```py
        bot.set_token(token = token)
        ```
        """
        if self.__class__.check_token(token):
            group_id: int = int(token[:token.find(":")])

            if self.__class__.check_group_id(group_id):
                if group_id != self.group_id:
                    warn(f"Идентификатор группы в поле token не совпадает с идентификатором группы в поле group_id")

                self.token = token
                return

        raise ValueError(f"Некорректное значение аргумента token")

    def get_token(self) -> str:
        """
        Возвращает сохранённый token transport-бота после проверки формата.

        :return: секретный token transport-бота

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        bot.get_token()
        ```
        """
        if self.__class__.check_token(self.token):
            group_id: int = self.token[:self.token.find(":")]

            if is_int(group_id) and self.__class__.check_group_id(int(group_id)):
                group_id = int(group_id)

                if group_id == self.group_id:
                    return str(self.token).strip()
                else:
                    raise ValueError(f"Идентификатор группы в поле {self.token=} не совпадает с идентификатором группы в поле self.group_id")
            else:
                raise ValueError(f"Некорректное значение атрибута {self.token=}. Идентификатор группы в поле не прошёл проверку")
        else:
            raise ValueError(f"Некорректное значение атрибута {self.token=}")
