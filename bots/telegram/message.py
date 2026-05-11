"""
Описывает сообщение соответствующего транспортного или wrapper-слоя.
Модуль относится к архитектурной зоне: слой унификации транспортов `bots`, который скрывает различия Telegram и VK за общими объектами сообщений, клавиатур, вложений и событий.

### Публичные классы
- `Message`: модель сообщения или wrapper-сообщения в соответствующем слое.

### Публичные функции
- Публичные функции отсутствуют.

### Связи
Используется транспортным слоем и wrapper-логикой, чтобы app-layer работал с `Message`, `Keyboard`, `Button`, `Attachment` и `Event` без привязки к конкретной соцсети.
"""

from __future__ import annotations


from bots.constants import logger_telegram
from bots.utils.dates import get_date
from bots.utils.text import cut, preceding
from bots.compat import (
    BufferedReader,
    BytesIO,
    InlineKeyboardMarkup,
    InputMediaAudio,
    InputMediaDocument,
    InputMediaPhoto,
    InputMediaVideo,
    Iterable,
    ReplyKeyboardMarkup,
    TeleBot,
    TelebotMessage,
    datetime,
)
from bots.types import BOT_KEY, CHANGED_PARTS

from bots.base.bindings import Bot
from bots.base.attachment import Attachment as BaseAttachment
from bots.base.button import Button as BaseButton
from bots.base.keyboard import Keyboard as BaseKeyboard
from bots.base.message import Message as BaseMessageClass
from bots.base.voice_message import VoiceMessage as BaseVoiceMessage

class Message(BaseMessageClass):
    """
    Telegram-сообщение transport-layer.
    Класс хранит `telebot` client, вложения, reply/forward и умеет отправлять,
    редактировать, пересылать и удалять сообщение через Telegram API.

    ### Поля
    - `MAX_ATTACHMENTS`: ограничение размера, которое защищает transport/API от слишком длинного payload.
    - `attachments`: хранит вложения сообщения для операций этого объекта.
    - `reply`: связанные сообщения или вложения, которые transport-layer использует при отправке, сравнении или редактировании.
    - `keyboard`: хранит клавиатуру сообщения для операций этого объекта.
    - `forward_messages`: связанные сообщения или вложения, которые transport-layer использует при отправке, сравнении или редактировании.
    - `telebot`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.
    - `kwargs`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.
    - `deleted`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.

    ### Методы
    - `from_event`: Создаёт wrapper-сообщение из transport-события.
    - `__init__`: Создаёт объект и сохраняет данные, нужные transport-layer для отправки, сравнения или восстановления объекта.
    - `get_username`: Возвращает username из текущего состояния `Message`.
    - `get_bot_key`: Возвращает ключ транспорта из текущего состояния `Message`.
    - `send`: Отправляет сообщение или вложение через transport-layer.
    - `add_deleted`: Запоминает id удалённого Telegram-сообщения.
    - `check_deleted`: Проверяет deleted перед использованием.
    - `delete`: Удаляет отправленное сообщение через transport-layer.
    - `get_parse_mode`: Возвращает parse mode из текущего состояния `Message`.
    - `get_edit_reply_markup`: Возвращает edit reply markup из текущего состояния `Message`.

    ### Жизненный цикл
    Экземпляры создаются из конфигурации транспорта, принимают события платформы и отдают app-layer унифицированные wrapper-объекты.

    ### Пример использования
    ```py
    message: Message
    ```
    """

    # Максимальное количество вложений в одном сообщении
    MAX_ATTACHMENTS: int = 1

    @classmethod
    def from_event(cls: type[Telebot.Message], event: Bot.Event, bot: TeleBot):
        """
        Создаёт wrapper-сообщение из transport-события.

        ### Аргументы:
        :param event: transport-событие для обработки
        :param bot: transport-адаптер

        :return: `Telebot.Message`, восстановленное из `Bot.Event`

        ### Пример использования:
        ```py
        Message.from_event(event = event, bot = bot)
        ```
        """
        message: Telebot.Message = super().from_event(event, bot)
        message_id: int | None = Telebot.get_message_id(event)
        message.set_id(message_id) if message_id is not None else None
        message.set_chat_id(event.chat_id)
        return message

    def __init__(self, telebot: TeleBot, owner_id: int, text: str, keyboard: Telebot.Keyboard | None = None, forward: Iterable[Telebot.Message] = [], reply: Telebot.Message | None = None, attachments: Iterable[Telebot.Attachment] = []):
        """
        Создаёт wrapper `Message` и сохраняет данные сообщения или события без привязки app-layer к SDK платформы.

        ### Аргументы:
        :param telebot: Telegram transport-адаптер или API-клиент
        :param owner_id: идентификатор владельца сообщения
        :param text: текст
        :param keyboard: клавиатура
        :param forward: пересылаемое сообщение
        :param reply: сообщение, на которое дан ответ
        :param attachments: вложения

        ### Пример использования:
        ```py
        message = Message(telebot = telebot, owner_id = owner_id, text = text, keyboard = keyboard, forward = forward, reply = reply, attachments = attachments)
        ```
        """
        super().__init__(owner_id, text, keyboard, forward, reply, attachments)
        self.attachments: Telebot[Telebot.Attachment]
        self.reply: Telebot.Message | None
        self.keyboard: Telebot.Keyboard | None
        self.forward_messages: list[Telebot.Message]

        # Бот, который будет отправлять сообщение
        self.telebot: TeleBot
        self.set_telebot(telebot)

        self.kwargs: dict[str, str | bool | int | None] = {}

    def get_username(self) -> str | None:
        """
        Возвращает сохранённое имя пользователя.

        :return: имя пользователя в транспорте

        ### Пример использования:
        ```py
        message.get_username()
        ```
        """
        for event in self.events[self.__class__.CREATE_KEY]:
            for ev in event.get_events():
                return ev.from_user.username
        return None

    def get_bot_key(self) -> BOT_KEY:
        """
        Возвращает ключ транспорта из текущего состояния `Message`.

        :return: строковый ключ транспорта, например `telebot` или `vkbot`

        ### Примеры вызова:
        ```py
        message.get_bot_key()
        ```
        """
        return "telebot"

    def send(self, chat_id: int, parse_mode: str = "", forward_after: bool = False, single_caption: bool = True, has_spoiler: bool = False, show_caption_above_media: bool = False, disable_notification: bool | None = None, protect_content: bool | None = None, reply_to_message_id: int | None = None, timeout: int | None = None, allow_sending_without_reply: bool | None = None, message_thread_id: int | None = None, business_connection_id: str | None = None, message_effect_id: str | None = None, allow_paid_broadcast: bool | None = None) -> dict[str, list[TelebotMessage]]:
        """
        Отправляет сообщение или вложение через transport-layer.

        ### Аргументы:
        :param chat_id: идентификатор чата
        :param parse_mode: режим разметки сообщения
        :param forward_after: forward after
        :param single_caption: single caption
        :param has_spoiler: has spoiler
        :param show_caption_above_media: show caption above media
        :param disable_notification: disable notification
        :param protect_content: protect content
        :param reply_to_message_id: reply to message id
        :param timeout: время ожидания transport API
        :param allow_sending_without_reply: allow sending without reply
        :param message_thread_id: message thread id
        :param business_connection_id: business connection id
        :param message_effect_id: message effect id
        :param allow_paid_broadcast: allow paid broadcast

        :return: словарь ответов Telegram API по группам `messages`, `attachments`, `forward`

        :raises TelebotException: если нижележащий слой сообщает об ошибке операции

        ### Пример использования:
        ```py
        message.send(chat_id = chat_id, parse_mode = parse_mode, forward_after = forward_after, single_caption = single_caption, has_spoiler = has_spoiler, show_caption_above_media = show_caption_above_media, disable_notification = disable_notification, protect_content = protect_content, reply_to_message_id = reply_to_message_id, timeout = timeout, allow_sending_without_reply = allow_sending_without_reply, message_thread_id = message_thread_id, business_connection_id = business_connection_id, message_effect_id = message_effect_id, allow_paid_broadcast = allow_paid_broadcast)
        ```
        """
        # Сообщение может быть отправлено лишь единожды
        self.set_chat_id(chat_id)

        telebot: TeleBot = self.get_telebot()

        self.kwargs = {
            "parse_mode": str(parse_mode) if parse_mode is not None else None,
            "forward_after": bool(forward_after) if forward_after is not None else None,
            "single_caption": bool(single_caption) if single_caption is not None else None,
            "has_spoiler": bool(has_spoiler) if has_spoiler is not None else None,
            "show_caption_above_media": bool(show_caption_above_media) if show_caption_above_media is not None else None,
            "disable_notification": bool(disable_notification) if disable_notification is not None else None,
            "protect_content": bool(protect_content) if protect_content is not None else None,
            "reply_to_message_id": int(reply_to_message_id) if reply_to_message_id is not None else None,
            "timeout": int(timeout) if timeout is not None else None,
            "allow_sending_without_reply": bool(allow_sending_without_reply) if allow_sending_without_reply is not None else None,
            "message_thread_id": int(message_thread_id) if message_thread_id is not None else None,
            "business_connection_id": str(business_connection_id) if business_connection_id is not None else None,
            "message_effect_id": str(message_effect_id) if message_effect_id is not None else None,
            "allow_paid_broadcast": bool(allow_paid_broadcast) if allow_paid_broadcast is not None else None,
        }

        kwargs: dict[str, str] = {
            key: value for key, value in {
                "disable_notification": disable_notification,
                "protect_content": protect_content,
                "reply_to_message_id": reply_to_message_id,
                "timeout": timeout,
                "allow_sending_without_reply": allow_sending_without_reply,
                "message_thread_id": message_thread_id,
                "business_connection_id": business_connection_id,
                "message_effect_id": message_effect_id,
                "allow_paid_broadcast": allow_paid_broadcast
            }.items() if value is not None
        }

        if parse_mode:
            kwargs["parse_mode"] = parse_mode

        if self.keyboard:
            kwargs["reply_markup"] = self.keyboard.get_keyboard()

        # Вложения
        filenames: list[str] = []
        attachments: list[Telebot.Attachment] = self.get_attachments()
        responses: list[TelebotMessage] = []
        forward_responses: list[TelebotMessage] = []
        attachments_responses: list[TelebotMessage] = []

        if self.keyboard and attachments:
            raise TelebotException("Telebot не поддерживает отправку вложений вместе с клавиатурой")

        if not forward_after:
            # Отправка пересланных сообщений
            for message in self.get_forward():
                response: TelebotMessage = message.forward(chat_id)
                forward_responses.append(response)

        # В ответ на сообщение
        reply: Telebot.Message | None = self.get_reply()

        # if self.text == "Некорректный ответ":
        #     else:
        #         raise Exception()

        # Отправка этого сообщения
        if attachments:
            files: list[BufferedReader] = []
            media_group: list[InputMediaPhoto | InputMediaVideo | InputMediaAudio | InputMediaDocument] = []
            text: str = self.get_text(parse_mode)

            for attachment in attachments:
                media_type: type[InputMediaPhoto | InputMediaVideo | InputMediaAudio | InputMediaDocument] = attachment.get_media_type()
                content: str | BufferedReader | BytesIO
                file_id: str = attachment.get_id()

                if file_id:
                    # Вложение уже на серверах Telegram - берём file_id
                    content = file_id

                    # У значений под ключами filenames и attachments в результирующем словаре должна быть одинаковая длина (один response соответствует одному имени файла)
                    filenames.append("")
                elif attachment.check_filename(attachment.filename):
                    # Файл ещё не загружен на сервера - открываем файл и не забываем закрыть
                    filename: str = attachment.get_filename()
                    content = open(filename, "rb")
                    files.append(content)
                    filenames.append(filename)
                else:
                    # У вложения нет файла, но его можно передать и байтами
                    content = attachment.get()

                    # У значений под ключами filenames и attachments в результирующем словаре должна быть одинаковая длина (один response соответствует одному имени файла)
                    filenames.append("")

                caption: dict[str, str] = {}

                if text:
                    caption["caption"] = cut(text, Bot.Message.MAX_LENGTH)

                if single_caption:
                    text = ""

                media: InputMediaPhoto | InputMediaVideo | InputMediaAudio | InputMediaDocument = media_type(
                    content, **caption)
                media_group.append(media)

            if reply:
                kwargs["reply_to_message_id"] = reply.get_id()

            if "parse_mode" in kwargs:
                del kwargs["parse_mode"]

            try:
                attachments_responses = telebot.send_media_group(self.get_chat_id(), media_group, **kwargs)
            except Exception as err:
                logger_telegram.exception(f"Telebot.Message.send send_media_group {chat_id=} {err=}")
                attachments_responses = []

            for file in files:
                file.close()

        elif reply:
            try:
                response: TelebotMessage = telebot.reply_to(self.get_chat_id(), self.get_text(parse_mode), **kwargs)
            except Exception as err:
                logger_telegram.exception(f"Telebot.Message.send reply_to {chat_id=} {err=}")
                responses = []
            else:
                responses = [response]
        else:
            try:
                response: TelebotMessage = telebot.send_message(self.get_chat_id(), self.get_text(parse_mode), **kwargs)
            except Exception:
                try:
                    response: TelebotMessage = telebot.send_message(self.get_chat_id(), self.get_text(parse_mode).replace("_", ""), **kwargs)
                except Exception as err:
                    logger_telegram.exception(f"Telebot.Message.send send_message {chat_id=} {err=}")
                    responses = []
                else:
                    responses = [response]
            else:
                responses = [response]

        if forward_after:
            # Отправка пересланных сообщений
            for message in self.get_forward():
                response: TelebotMessage = message.forward(chat_id)

                if response:
                    forward_responses.append(response)

        if len(responses) == 1:
            response: TelebotMessage = responses[0]
            message_id: int = int(response.message_id)
            self.set_id(message_id)
        else:
            self.id = None

        for response in responses:
            event: Bot.Event = Bot.Event(self.get_owner_id(), chat_id, "", datetime.now())
            event.set_events([response])
            self.add_event(event, datetime.fromtimestamp(response.date), self.__class__.SENT_KEY)

        self.set_chat_id(chat_id)
        self.set_changed(False)

        if len(filenames) != len(attachments_responses):
            logger_telegram.warning("По неизвестной причине Telegram API количество ответов не соответствует количеству указанных вложений. Это приведёт к исключению в Telebot.parse_responses")

        return {
            "attachments": attachments_responses,
            "filenames": filenames,
            "forward": forward_responses
        }

    deleted: dict[int, list[int]] = {}

    def add_deleted(self, chat_id: int, message_id: int):
        """
        Запоминает id удалённого Telegram-сообщения.

        ### Аргументы:
        :param chat_id: идентификатор чата
        :param message_id: идентификатор сообщения

        ### Пример использования:
        ```py
        message.add_deleted(chat_id = chat_id, message_id = message_id)
        ```
        """
        if chat_id in self.__class__.deleted:
            self.__class__.deleted[chat_id].append(message_id)
        else:
            self.__class__.deleted[chat_id] = [message_id]

    def check_deleted(self, chat_id: int, message_id: int):
        """
        Проверяет значение `deleted` перед сохранением или использованием.

        ### Аргументы:
        :param chat_id: идентификатор чата
        :param message_id: идентификатор сообщения

        :return: `True`, если значение `deleted` перед сохранением или использованием; иначе `False`

        ### Пример использования:
        ```py
        message.check_deleted(chat_id = chat_id, message_id = message_id)
        ```
        """
        return message_id in self.__class__.deleted.get(chat_id, [])

    def delete(self):
        """
        Удаляет отправленное сообщение через transport-layer.

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        :raises response: если нижележащий слой сообщает об ошибке операции

        ### Пример использования:
        ```py
        message.delete()
        ```
        """
        telebot: TeleBot = self.get_telebot()
        chat_id: int = self.get_chat_id()
        message_id: int = self.get_id()

        if self.check_deleted(chat_id, message_id):
            raise ValueError(f"Некорректное значение атрибута {self.id=}. Невозможно повторно удалить сообщение.")

        if self.check_chat_id(chat_id) and self.check_id(message_id):
            try:
                response: bool = telebot.delete_message(chat_id = chat_id, message_id = message_id)
            except Exception as err:
                logger_telegram.exception(f"Telebot.Message.delete {chat_id=} {message_id=} {err=}")
                response = err
        else:
            response = ValueError(f"Некорректное значение атрибута {self.chat_id=} или {self.id=}. Перед удалением необходимо отправить сообщение.")
            raise response

        self.add_deleted(chat_id, message_id)
        self.add_event(response, datetime.now(), self.__class__.DELETE_KEY)
        self.id = None
        self.chat_id = None

        chat_id: int = self.get_chat_id()
        message_id: int = self.get_id()

    def get_parse_mode(self) -> str:
        """
        Возвращает сохранённый parse mode сообщения.

        :return: режим разметки сообщения

        ### Пример использования:
        ```py
        message.get_parse_mode()
        ```
        """
        parse_mode: str | bool | int | None = self.kwargs.get("parse_mode")

        if parse_mode:
            return str(parse_mode)
        else:
            return ""

    def get_edit_reply_markup(self) -> InlineKeyboardMarkup | None:
        """
        Возвращает inline-клавиатуру для Telegram edit-запроса или `None`.

        :return: edit reply markup

        :raises TelebotException: если нижележащий слой сообщает об ошибке операции

        ### Пример использования:
        ```py
        message.get_edit_reply_markup()
        ```
        """
        keyboard: Telebot.Keyboard | None = self.get_keyboard()

        if keyboard is None:
            return None
        elif keyboard.check_editable():
            reply_markup: InlineKeyboardMarkup | ReplyKeyboardMarkup = keyboard.get_keyboard()

            if isinstance(reply_markup, InlineKeyboardMarkup):
                return reply_markup

        raise TelebotException("Telebot поддерживает редактирование только inline-клавиатуры")

    def get_edit_kwargs(self, parse_mode: bool = True, reply_markup: bool = True, show_caption_above_media: bool = False) -> dict[str, str | int | bool | InlineKeyboardMarkup | None]:
        """
        Возвращает keyword-аргументы для Telegram edit API.

        ### Аргументы:
        :param parse_mode: режим разметки сообщения
        :param reply_markup: reply markup
        :param show_caption_above_media: show caption above media

        :return: edit kwargs

        ### Пример использования:
        ```py
        message.get_edit_kwargs(parse_mode = parse_mode, reply_markup = reply_markup, show_caption_above_media = show_caption_above_media)
        ```
        """
        kwargs: dict[str, str | int | bool | InlineKeyboardMarkup | None] = {}

        if parse_mode:
            parse_mode_value: str = self.get_parse_mode()

            if parse_mode_value:
                kwargs["parse_mode"] = parse_mode_value

        timeout: str | bool | int | None = self.kwargs.get("timeout")
        if timeout is not None:
            kwargs["timeout"] = int(timeout)

        business_connection_id: str | bool | int | None = self.kwargs.get("business_connection_id")
        if business_connection_id is not None:
            kwargs["business_connection_id"] = str(business_connection_id)

        if reply_markup and (self.keyboard is not None or self.was_changed(self.__class__.CHANGED_REPLY_MARKUP)):
            kwargs["reply_markup"] = self.get_edit_reply_markup()

        if show_caption_above_media:
            show_caption_above_media_value: str | bool | int | None = self.kwargs.get("show_caption_above_media")

            if show_caption_above_media_value is not None:
                kwargs["show_caption_above_media"] = bool(show_caption_above_media_value)

        return kwargs

    def get_media_content(self, attachment: Telebot.Attachment, files: list[BufferedReader]) -> str | BufferedReader | BytesIO:
        """
        Возвращает содержимое media attachment для Telegram input media.

        ### Аргументы:
        :param attachment: вложение
        :param files: файлы или вложения для отправки

        :return: media content

        ### Пример использования:
        ```py
        message.get_media_content(attachment = attachment, files = files)
        ```
        """
        file_id: str = attachment.get_id()

        if file_id:
            return file_id
        elif attachment.check_filename(attachment.filename):
            filename: str = attachment.get_filename()
            content: BufferedReader = open(filename, "rb")
            files.append(content)
            return content
        else:
            return attachment.get()

    def get_input_media(self, attachment: Telebot.Attachment, files: list[BufferedReader]) -> InputMediaPhoto | InputMediaVideo | InputMediaAudio | InputMediaDocument:
        """
        Возвращает `InputMedia*` объект для редактирования media-сообщения.

        ### Аргументы:
        :param attachment: вложение
        :param files: файлы или вложения для отправки

        :return: input media

        ### Пример использования:
        ```py
        message.get_input_media(attachment = attachment, files = files)
        ```
        """
        parse_mode: str = self.get_parse_mode()
        text: str = self.get_text(parse_mode)
        media_kwargs: dict[str, str] = {}

        if text:
            media_kwargs["caption"] = cut(text, Bot.Message.MAX_LENGTH)

        if parse_mode:
            media_kwargs["parse_mode"] = parse_mode

        media_type: type[InputMediaPhoto | InputMediaVideo | InputMediaAudio | InputMediaDocument] = attachment.get_media_type()
        content: str | BufferedReader | BytesIO = self.get_media_content(attachment, files)
        media: InputMediaPhoto | InputMediaVideo | InputMediaAudio | InputMediaDocument = media_type(content, **media_kwargs)
        return media

    def add_edit_response(self, response: TelebotMessage | bool):
        """
        Сохраняет ответ Telegram API после редактирования сообщения.

        ### Аргументы:
        :param response: ответ GPT, привязанный к запросу пользователя

        ### Пример использования:
        ```py
        message.add_edit_response(response = response)
        ```
        """
        date: datetime = datetime.now()

        if isinstance(response, TelebotMessage):
            event: Bot.Event = Bot.Event(self.get_owner_id(), self.get_chat_id(), "", date)
            event.set_events([response])
            self.add_event(event, get_date(response, "date", default = date), self.__class__.EDIT_KEY)
        else:
            self.add_event(response, date, self.__class__.EDIT_KEY)

        self.set_changed(False)

    def edit_message_text(self) -> TelebotMessage | bool:
        """
        Обновляет уже отправленное message text через transport-layer.

        :return: ответ `edit_message_text`: `TelebotMessage` или `True`

        ### Примеры вызова:
        ```py
        message.edit_message_text()
        ```
        """
        telebot: TeleBot = self.get_telebot()
        chat_id: int = self.get_chat_id()
        message_id: int = self.get_id()
        parse_mode: str = self.get_parse_mode()
        kwargs: dict[str, str | int | bool | InlineKeyboardMarkup | None] = self.get_edit_kwargs()
        response: TelebotMessage | bool = telebot.edit_message_text(
            text = self.get_text(parse_mode),
            chat_id = chat_id,
            message_id = message_id,
            **kwargs
        )
        self.add_edit_response(response)
        return response

    def edit_message_caption(self) -> TelebotMessage | bool:
        """
        Обновляет уже отправленное message caption через transport-layer.

        :return: ответ `edit_message_caption`: `TelebotMessage` или `True`

        ### Примеры вызова:
        ```py
        message.edit_message_caption()
        ```
        """
        telebot: TeleBot = self.get_telebot()
        chat_id: int = self.get_chat_id()
        message_id: int = self.get_id()
        parse_mode: str = self.get_parse_mode()
        caption: str = cut(self.get_text(parse_mode), Bot.Message.MAX_LENGTH)
        kwargs: dict[str, str | int | bool | InlineKeyboardMarkup | None] = self.get_edit_kwargs(show_caption_above_media = True)
        response: TelebotMessage | bool = telebot.edit_message_caption(
            caption = caption,
            chat_id = chat_id,
            message_id = message_id,
            **kwargs
        )
        self.add_edit_response(response)
        return response

    def edit_message_media(self) -> TelebotMessage | bool:
        """
        Обновляет уже отправленное message media через transport-layer.

        :return: ответ `edit_message_media`: `TelebotMessage` или `True`

        :raises TelebotException: если нижележащий слой сообщает об ошибке этой операции

        ### Примеры вызова:
        ```py
        message.edit_message_media()
        ```
        """
        telebot: TeleBot = self.get_telebot()
        chat_id: int = self.get_chat_id()
        message_id: int = self.get_id()
        attachments: list[Telebot.Attachment] = self.get_attachments()

        if len(attachments) != 1:
            raise TelebotException("Telebot поддерживает редактирование только одного media-вложения")

        files: list[BufferedReader] = []

        try:
            media: InputMediaPhoto | InputMediaVideo | InputMediaAudio | InputMediaDocument = self.get_input_media(attachments[0], files)
            kwargs: dict[str, str | int | bool | InlineKeyboardMarkup | None] = self.get_edit_kwargs(parse_mode = False)
            response: TelebotMessage | bool = telebot.edit_message_media(
                media = media,
                chat_id = chat_id,
                message_id = message_id,
                **kwargs
            )
        finally:
            for file in files:
                file.close()

        self.add_edit_response(response)
        return response

    def edit_message_reply_markup(self) -> TelebotMessage | bool:
        """
        Обновляет уже отправленное message reply markup через transport-layer.

        :return: ответ `edit_message_reply_markup`: `TelebotMessage` или `True`

        ### Примеры вызова:
        ```py
        message.edit_message_reply_markup()
        ```
        """
        telebot: TeleBot = self.get_telebot()
        chat_id: int = self.get_chat_id()
        message_id: int = self.get_id()
        reply_markup: InlineKeyboardMarkup | None = self.get_edit_reply_markup()
        kwargs: dict[str, str | int | bool | InlineKeyboardMarkup | None] = self.get_edit_kwargs(parse_mode = False, reply_markup = False)
        response: TelebotMessage | bool = telebot.edit_message_reply_markup(
            chat_id = chat_id,
            message_id = message_id,
            reply_markup = reply_markup,
            **kwargs
        )
        self.add_edit_response(response)
        return response

    def can_edit_without_resend(self) -> bool:
        """
        Сравнивает состояние объектов и возвращает флаг, который нужен перед отправкой или редактированием.

        :return: `True`, если изменения можно применить без удаления и повторной отправки

        ### Пример использования:
        ```py
        message.can_edit_without_resend()
        ```
        """
        changed_parts: set[CHANGED_PARTS] = self.get_changed_parts()

        if not changed_parts:
            return False
        elif self.__class__.CHANGED_REPLY in changed_parts or self.__class__.CHANGED_FORWARD in changed_parts:
            return False
        elif self.keyboard is not None and not self.keyboard.check_editable():
            return False
        elif self.__class__.CHANGED_MEDIA in changed_parts and len(self.get_attachments()) != 1:
            return False
        else:
            return True

    def edit_without_resend(self):
        """
        Обновляет уже отправленное without resend через transport-layer.

        ### Примеры вызова:
        ```py
        message.edit_without_resend()
        ```
        """
        attachments: list[Telebot.Attachment] = self.get_attachments()
        text_changed: bool = self.was_changed(self.__class__.CHANGED_TEXT) or self.was_changed(self.__class__.CHANGED_CAPTION)

        if self.was_changed(self.__class__.CHANGED_MEDIA):
            self.edit_message_media()
        elif attachments and text_changed:
            self.edit_message_caption()
        elif not attachments and text_changed:
            self.edit_message_text()
        elif self.was_changed(self.__class__.CHANGED_REPLY_MARKUP):
            self.edit_message_reply_markup()
        else:
            self.set_changed(False)

    def check_not_modified_error(self, err: Exception) -> bool:
        """
        Проверяет значение `not modified error` перед сохранением или использованием.

        ### Аргументы:
        :param err: исключение, которое нужно проверить или обработать

        :return: `True`, если значение `not modified error` перед сохранением или использованием; иначе `False`

        ### Пример использования:
        ```py
        message.check_not_modified_error(err = err)
        ```
        """
        return "message is not modified" in str(err).lower()

    def edit(self, prevent_resend: bool = False) -> dict[str, list[TelebotMessage] | list[str]]:
        """
        Обновляет уже отправленное сообщение, если транспорт позволяет редактирование.

        ### Аргументы:
        :param prevent_resend: prevent resend

        :return: словарь новых Telegram API responses при resend или пустой словарь

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        message.edit(prevent_resend = prevent_resend)
        ```
        """
        if not self.was_changed():
            return {}
        elif self.check_chat_id(self.chat_id) and not self.check_id(self.id):
            raise ValueError(f"Некорректное значение атрибута {self.id=}. Используйте экземпляры из результатов вызова метода Telebot.parse_responses(message, responses).")
        elif self.check_editable():
            if self.can_edit_without_resend():
                try:
                    self.edit_without_resend()
                except Exception as err:
                    if self.check_not_modified_error(err):
                        self.set_changed(False)
                        return {}

                    logger_telegram.exception(f"Telebot.Message.edit native {self.chat_id=} {self.id=} {err=}")
                else:
                    return {}

            if prevent_resend:
                return {}

            chat_id: int = self.get_chat_id()
            self.delete()
            return self.send(chat_id, **self.kwargs)
        else:
            raise ValueError(f"Некорректное значение атрибута {self.id=} или {self.chat_id=}. Перед редактированием необходимо отправить сообщение.")

    def forward(self, chat_id: int) -> TelebotMessage | None:
        """
        Пересылает сообщение в другой чат через transport-layer.

        ### Аргументы:
        :param chat_id: идентификатор чата

        :return: пересланное Telegram-сообщение или `None`, если API вызов завершился ошибкой

        ### Пример использования:
        ```py
        message.forward(chat_id = chat_id)
        ```
        """
        telebot: TeleBot = self.get_telebot()
        from_chat_id: int = self.get_chat_id()
        message_id: int = self.get_id()
        try:
            response: TelebotMessage = telebot.forward_message(chat_id, from_chat_id, message_id)
        except Exception as err:
            logger_telegram.exception(f"Telebot.Message.forward forward_message {from_chat_id=} {message_id=} {err=}")
            return None
        return response

    def reply(self, chat_id: int, message: Telebot.Message):
        """
        Отправляет ответ на исходное сообщение.

        ### Аргументы:
        :param chat_id: идентификатор чата
        :param message: сообщение проекта или сообщение конкретного транспорта

        ### Пример использования:
        ```py
        message.reply(chat_id = chat_id, message = message)
        ```
        """
        message.set_reply(self)
        message.send(chat_id)


    # Методы работы с полями


    def get_text(self, parse_mode: str = "") -> str:
        """
        Возвращает сохранённый текст сообщения.

        ### Аргументы:
        :param parse_mode: режим разметки сообщения

        :return: текст текущего сообщения

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        message.get_text(parse_mode = parse_mode)
        ```
        """
        if self.check_text(self.text):
            if parse_mode:
                return preceding(str(self.text).strip())
            else:
                return str(self.text).strip()
        elif isinstance(self.text, str):
            raise ValueError(f"Пустой текст сообщения не допускается, если нет кнопок или вложений")
        else:
            raise ValueError(f"Некорректное значение атрибута {self.text=}")


    def check_telebot(self, telebot: TeleBot) -> bool:
        """
        Проверяет значение `telebot` перед сохранением или использованием.

        ### Аргументы:
        :param telebot: Telegram transport-адаптер или API-клиент

        :return: `True`, если значение `telebot` перед сохранением или использованием; иначе `False`

        ### Пример использования:
        ```py
        message.check_telebot(telebot = telebot)
        ```
        """
        return isinstance(telebot, TeleBot)

    def set_telebot(self, telebot: TeleBot):
        """
        Проверяет и сохраняет значение `telebot`.

        ### Аргументы:
        :param telebot: Telegram transport-адаптер или API-клиент

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        message.set_telebot(telebot = telebot)
        ```
        """
        if self.check_telebot(telebot):
            self.telebot = telebot
        else:
            raise ValueError(f"Некорректное значение аргумента {telebot=}")

    def get_telebot(self) -> TeleBot:
        """
        Возвращает SDK-клиент `TeleBot`, связанный с сообщением.

        :return: telebot

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        message.get_telebot()
        ```
        """
        if self.check_telebot(self.telebot):
            return self.telebot
        else:
            raise ValueError(f"Некорректное значение атрибута {self.telebot=}")


    def check_reply(self, reply: Telebot.Message) -> bool:
        """
        Проверяет допустимость reply-сообщения.

        ### Аргументы:
        :param reply: сообщение, на которое дан ответ

        :return: `True`, если допустимость reply-сообщения; иначе `False`

        ### Пример использования:
        ```py
        message.check_reply(reply = reply)
        ```
        """
        return super().check_reply(reply)

    def set_reply(self, reply: Telebot.Message | None):
        """
        Проверяет и сохраняет сообщение, на которое дан ответ в объекте.

        ### Аргументы:
        :param reply: сообщение, на которое дан ответ

        :return: результат базового `set_reply`; метод сохраняет reply-сообщение

        ### Пример использования:
        ```py
        message.set_reply(reply = reply)
        ```
        """
        return super().set_reply(reply)

    def get_reply(self) -> Telebot.Message | None:
        """
        Возвращает сохранённое reply-сообщение.

        :return: сообщение-ответ

        ### Пример использования:
        ```py
        message.get_reply()
        ```
        """
        return super().get_reply()


    def check_attachments_types(self, attachments: Iterable[Telebot.Attachment]) -> bool:
        """
        Проверяет значение `attachments types` перед сохранением или использованием.

        ### Аргументы:
        :param attachments: вложения

        :return: `True`, если значение `attachments types` перед сохранением или использованием; иначе `False`

        ### Пример использования:
        ```py
        message.check_attachments_types(attachments = attachments)
        ```
        """
        if not attachments:
            return True

        media_types: list[type[InputMediaPhoto | InputMediaVideo | InputMediaAudio | InputMediaDocument]] = []

        for attachment in attachments:
            media_type: type[InputMediaPhoto | InputMediaVideo | InputMediaAudio | InputMediaDocument] = attachment.get_media_type()
            media_types.append(media_type)

        if InputMediaDocument in media_types and any(media_type in media_types for media_type in [InputMediaPhoto, InputMediaVideo, InputMediaAudio]):
            return False

        return True

    def check_attachments(self, attachments: Iterable[Telebot.Attachment]) -> bool:
        """
        Проверяет список вложений transport-сообщения.

        ### Аргументы:
        :param attachments: вложения

        :return: `True`, если список вложений transport-сообщения; иначе `False`

        ### Пример использования:
        ```py
        message.check_attachments(attachments = attachments)
        ```
        """
        return super().check_attachments(attachments) and self.check_attachments_types(attachments)

    def set_attachments(self, attachments: Iterable[Telebot.Attachment]):
        """
        Проверяет и сохраняет вложения сообщения в состоянии `Message`.

        ### Аргументы:
        :param attachments: вложения wrapper-сообщения

        :return: результат базового `set_attachments`; метод сохраняет список вложений

        :raises ValueError: если значение не проходит локальную проверку перед сохранением

        :raises TelebotException: если нижележащий слой сообщает об ошибке этой операции

        ### Пример использования:
        ```py
        message.set_attachments(attachments = attachments)
        ```
        """
        attachments_list: list[Telebot.Attachment] = list(attachments)

        if not self.check_attachments(attachments_list):
            raise ValueError(f"Некорректное значение аргумента {attachments=}")
        elif attachments_list and self.keyboard:
            raise TelebotException("Telebot не поддерживает отправку вложений вместе с клавиатурой")
        elif not self.check_attachments_types(attachments_list):
            raise TelebotException("Telebot не поддерживает отправку файлов и других вложений одним сообщением")
        else:
            return super().set_attachments(attachments_list)

    def get_attachments(self) -> list[Telebot.Attachment]:
        """
        Возвращает сохранённые вложения сообщения.

        :return: вложения сообщения

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        :raises TelebotException: если нижележащий слой сообщает об ошибке операции

        ### Пример использования:
        ```py
        message.get_attachments()
        ```
        """
        if not self.check_attachments(self.attachments):
            raise ValueError(f"Некорректное значение атрибута {self.attachments=}")
        elif self.attachments and self.keyboard:
            raise TelebotException("Telebot не поддерживает отправку вложений вместе с клавиатурой")
        elif not self.check_attachments_types(self.attachments):
            raise TelebotException("Telebot не поддерживает отправку файлов и других вложений одним сообщением")
        else:
            return super().get_attachments()


    def check_forward(self, forward: Iterable[Telebot.Message]) -> bool:
        """
        Проверяет допустимость forward-сообщения.

        ### Аргументы:
        :param forward: пересылаемое сообщение

        :return: `True`, если допустимость forward-сообщения; иначе `False`

        ### Пример использования:
        ```py
        message.check_forward(forward = forward)
        ```
        """
        return super().check_forward(forward)

    def set_forward(self, forward: Iterable[Telebot.Message]):
        """
        Проверяет и сохраняет пересылаемое сообщение в объекте.

        ### Аргументы:
        :param forward: пересылаемое сообщение

        :return: результат базового `set_forward`; метод сохраняет forward-сообщения

        ### Пример использования:
        ```py
        message.set_forward(forward = forward)
        ```
        """
        return super().set_forward(forward)

    def get_forward(self) -> list[Telebot.Message]:
        """
        Возвращает сохранённое forward-сообщение.

        :return: пересылаемое сообщение

        ### Пример использования:
        ```py
        message.get_forward()
        ```
        """
        return super().get_forward()


    def check_keyboard(self, keyboard: Telebot.Keyboard) -> bool:
        """
        Проверяет допустимость клавиатуры сообщения.

        ### Аргументы:
        :param keyboard: клавиатура

        :return: `True`, если допустимость клавиатуры сообщения; иначе `False`

        ### Пример использования:
        ```py
        message.check_keyboard(keyboard = keyboard)
        ```
        """
        return super().check_keyboard(keyboard)

    def set_keyboard(self, keyboard: Telebot.Keyboard | None):
        """
        Проверяет и сохраняет клавиатуру сообщения в состоянии `Message`.

        ### Аргументы:
        :param keyboard: клавиатура wrapper-сообщения

        :raises ValueError: если значение не проходит локальную проверку перед сохранением

        :raises TelebotException: если нижележащий слой сообщает об ошибке этой операции

        ### Пример использования:
        ```py
        message.set_keyboard(keyboard = keyboard)
        ```
        """
        if keyboard is None:
            if not self.compare_keyboards(self.keyboard, keyboard):
                self.set_changed(self.__class__.CHANGED_REPLY_MARKUP)
            self.keyboard = None
        elif self.check_keyboard(keyboard):
            if self.attachments:
                raise TelebotException("Telebot не поддерживает отправку вложений вместе с клавиатурой")
            else:
                if not self.compare_keyboards(self.keyboard, keyboard):
                    self.set_changed(self.__class__.CHANGED_REPLY_MARKUP)
                self.keyboard = keyboard
        else:
            raise ValueError(f"Некорректное значение аргумента {keyboard=}")

    def get_keyboard(self) -> Telebot.Keyboard | None:
        """
        Возвращает сохранённую клавиатуру сообщения.

        :return: клавиатура сообщения

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        :raises TelebotException: если нижележащий слой сообщает об ошибке операции

        ### Пример использования:
        ```py
        message.get_keyboard()
        ```
        """
        if self.keyboard is None:
            return None
        elif self.check_keyboard(self.keyboard):
            if self.attachments:
                raise TelebotException("Telebot не поддерживает отправку вложений вместе с клавиатурой")
            else:
                return self.keyboard
        else:
            raise ValueError(f"Некорректное значение атрибута {self.keyboard=}")
