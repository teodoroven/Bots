"""
Описывает событие, полученное от транспорта.
Модуль относится к архитектурной зоне: слой унификации транспортов `bots`, который скрывает различия Telegram и VK за общими объектами сообщений, клавиатур, вложений и событий.

### Публичные классы
- `Event`: модель события, полученного от транспорта.

### Публичные функции
- Публичные функции отсутствуют.

### Связи
Используется транспортным слоем и wrapper-логикой, чтобы app-layer работал с `Message`, `Keyboard`, `Button`, `Attachment` и `Event` без привязки к конкретной соцсети.
"""

from __future__ import annotations


from bots.constants import EVENT_PERIOD
from bots.utils.dates import diff_sec
from bots.utils.mapping import get_from, get_int, is_iterable
from bots.compat import (
    BotTypes,
    CallbackQuery,
    DotDict,
    Iterable,
    Literal,
    TelebotMessage,
    VkBotEvent,
    VkBotMessageEvent,
    datetime,
)
from bots.types import EVENT_TYPE, Literal

class Event():
    """
    Нормализованное входящее событие transport-layer.
    Объединяет Telegram/VK message или callback в общий объект с bot/chat id,
    текстом, вложениями, callback payload и ссылкой на исходное сообщение.

    ### Поля
    - `EVENT_TYPE`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.
    - `events`: очередь входящих событий по chat_id до объединения и обработки.
    - `chat_id`: идентификатор объекта или связанной сущности, по которому runtime восстанавливает связь между слоями.
    - `date`: хранит доступную дату записи для операций этого объекта.
    - `text`: текстовое содержимое, которое показывается пользователю, отправляется в GPT или сохраняется в доменной модели.
    - `DEBUG_CALLBACK`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.
    - `reply`: связанные сообщения или вложения, которые transport-layer использует при отправке, сравнении или редактировании.
    - `forward_messages`: связанные сообщения или вложения, которые transport-layer использует при отправке, сравнении или редактировании.
    - `attachments`: хранит вложения сообщения для операций этого объекта.
    - `first_name`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.

    ### Методы
    - `loads`: Восстанавливает объект из JSON-совместимого словаря.
    - `__init__`: Создаёт объект и сохраняет данные, нужные transport-layer для отправки, сравнения или восстановления объекта.
    - `dumps`: Возвращает JSON-совместимый снимок объекта для storage или callback payload.
    - `prev_for`: Проверяет, является ли событие предыдущим для переданного события.
    - `get_username`: Возвращает username из текущего состояния `Event`.
    - `get_name`: Возвращает служебное имя из текущего состояния `Event`.
    - `check_event`: Проверяет событие транспорта перед использованием.
    - `set_events`: Проверяет и сохраняет очередь событий транспорта в состоянии `Event`.
    - `get_events`: Возвращает очередь событий транспорта из текущего состояния `Event`.
    - `check_owner_id`: Проверяет owner id перед использованием.

    ### Жизненный цикл
    Экземпляры создаются из конфигурации транспорта, принимают события платформы и отдают app-layer унифицированные wrapper-объекты.

    ### Пример использования
    ```py
    event: Event
    ```
    """
    EVENT_TYPE = BotTypes.EVENT_TYPE

    @classmethod
    def loads(cls, data: EVENT_TYPE, parent: type[BOT]) -> Bot.Event:
        """
        Восстанавливает объект из JSON-совместимого словаря.

        ### Аргументы:
        :param data: сериализованный словарь
        :param parent: родительский объект, к которому привязан wrapper

        :return: восстановленный объект или загруженное состояние

        ### Пример использования:
        ```py
        Event.loads(data = data, parent = parent)
        ```
        """
        owner_id: int = get_int(data, -1, "owner_id")
        chat_id: int = get_int(data, -1, "chat_id")
        isoformat: str = data.get("date", "")
        text: str = data.get("text", "")
        reply_data: Bot.Event.EVENT_TYPE | None = data.get("reply", {})
        forward_data: list[Bot.Event.EVENT_TYPE] = data.get("forward", "")

        date: datetime = datetime.fromisoformat(isoformat)
        reply: Bot.Event | None = None if reply_data is None else cls.loads(reply_data)

        forward_messages: list[Bot.Event] = []
        for event_data in forward_data:
            event: Bot.Event = cls.loads(event_data)
            forward_messages.append(event)

        attachments: list[Bot.Attachment] = []
        attachments_list: list[dict[str, str | int]] = get_from(data, "attachments")
        attachments_keys: dict[str, type[Bot.Attachment]] = {
            "Attachment": parent.Attachment,
            "PhotoAttachment": parent.PhotoAttachment,
            "VideoAttachment": parent.VideoAttachment,
            "AudioAttachment": parent.AudioAttachment,
            "DocAttachment": parent.DocAttachment,
        }

        for attachment_data in attachments_list:
            attachment_classname: str = attachment_data["classname"]
            attachment_class: type[Bot.Attachment] = attachments_keys[attachment_classname]
            attachment: Bot.Attachment = attachment_class.loads(attachment_data)
            attachments.append(attachment)

        result = cls(owner_id, chat_id, text, date, attachments, reply, forward_messages)
        first_name = data.get("first_name", "")
        last_name = data.get("last_name", "")
        result.set_name(first_name, last_name)
        return result


    def __init__(self, owner_id: int, chat_id: int, text: str, date: datetime, attachments: Iterable[Bot.Attachment] = [], reply: Bot.Message | None = None, forward: Iterable[Bot.Message] = []):
        """
        Создаёт wrapper `Event` и сохраняет данные сообщения или события без привязки app-layer к SDK платформы.

        ### Аргументы:
        :param owner_id: идентификатор владельца сообщения
        :param chat_id: идентификатор чата
        :param text: текст
        :param date: время сообщения или события
        :param attachments: вложения
        :param reply: сообщение, на которое дан ответ
        :param forward: пересылаемое сообщение

        ### Пример использования:
        ```py
        event = Event(owner_id = owner_id, chat_id = chat_id, text = text, date = date, attachments = attachments, reply = reply, forward = forward)
        ```
        """
        self.events: list[VkBotMessageEvent | VkBotEvent | DotDict | dict | TelebotMessage | CallbackQuery | int] = []
        self.chat_id: int
        self.date: datetime
        self.text: str
        self.DEBUG_CALLBACK: bool = False

        self.reply: Bot.Event | None = None
        self.forward_messages: list[Bot.Event] = []
        self.attachments: list[Bot.Attachment] = []

        self.first_name: str = ""
        self.last_name: str = ""

        self.set_owner_id(owner_id)
        self.set_chat_id(chat_id)
        self.set_date(date)
        self.set_text(text)
        self.set_reply(reply)
        self.set_forward(forward)
        self.set_attachments(attachments)

    def dumps(self) -> EVENT_TYPE:
        """
        Возвращает JSON-совместимый снимок объекта для storage или callback payload.

        :return: JSON-совместимый словарь для сохранения или передачи между слоями

        ### Пример использования:
        ```py
        event.dumps()
        ```
        """
        reply: Bot.Event | None = self.get_reply()
        return {
            "chat_id": self.get_chat_id(),
            "date": self.get_date().isoformat(),
            "text": self.get_text(),
            "reply": reply.dumps() if reply is not None else None,
            "forward": [event.dumps() for event in self.get_forward()],
            "attachments": [attachment.dumps() for attachment in self.get_attachments()],
            "first_name": str(self.first_name),
            "last_name": str(self.last_name)
        }

    def prev_for(self, event: Bot.Event) -> bool:
        """
        Возвращает является ли текущее событие (self) предыдущим для указанного (event:Event)
        Если событие является предыдущим для указанного, то они могут быть объединены в одно событие
        Событие является предыдущим для указанного, если между их датами разница не более EVENT_PERIOD (const) и дата текущего события была раньше, чем дата указанного события

        :param event: Событие для которого выполняется проверка
        """
        return abs(diff_sec(event.date, self.date)) < EVENT_PERIOD and self.date <= event.date and self is not event

    def get_username(self) -> str | Literal[""]:
        """
        Возвращает сохранённое имя пользователя.

        :return: имя пользователя в транспорте

        ### Пример использования:
        ```py
        event.get_username()
        ```
        """
        for event in self.events:
            if Vkbot.check_event(event):
                return f"@id{self.get_chat_id()}"
            elif Telebot.check_event(event):
                return f"@{event.from_user.username}"
        return ""

    def get_name(self) -> str | Literal[""]:
        """
        Возвращает сохранённое имя.

        :return: служебное имя

        ### Пример использования:
        ```py
        event.get_name()
        ```
        """
        return "here!"


    def check_event(self, event: VkBotMessageEvent | VkBotEvent | DotDict | dict | TelebotMessage | CallbackQuery) -> bool:
        """
        Проверяет значение `event` перед сохранением или использованием.

        ### Аргументы:
        :param event: transport-событие для обработки

        :return: `True`, если значение `event` перед сохранением или использованием; иначе `False`

        ### Пример использования:
        ```py
        event.check_event(event = event)
        ```
        """
        if Vkbot.check_event(event):
            return True
        elif Telebot.check_event(event):
            return True
        else:
            return False

    def set_events(self, events: list[VkBotMessageEvent | VkBotEvent | DotDict | dict | TelebotMessage | CallbackQuery]):
        """
        Проверяет и сохраняет очередь событий транспорта в состоянии `Event`.

        ### Аргументы:
        :param events: последовательность wrapper-событий одного чата

        :raises ValueError: если значение не проходит локальную проверку перед сохранением

        ### Пример использования:
        ```py
        event.set_events(events = events)
        ```
        """
        if all(self.check_event(event) for event in events):
            self.events = list(events)
        else:
            raise ValueError(f"Некорректное значение аргумента {events=}")

    def get_events(self) -> list[VkBotMessageEvent | VkBotEvent | DotDict | dict | TelebotMessage | CallbackQuery]:
        """
        Возвращает исходные transport-события, из которых собран `Event`.

        :return: events

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        event.get_events()
        ```
        """
        if all(self.check_event(event) for event in self.events):
            return list(self.events)
        else:
            raise ValueError(f"Некорректное значение атрибута {self.events=}")


    def check_owner_id(self, owner_id: int) -> bool:
        """
        Проверяет допустимость owner id transport-сообщения.

        ### Аргументы:
        :param owner_id: идентификатор владельца сообщения

        :return: `True`, если допустимость owner id transport-сообщения; иначе `False`

        ### Пример использования:
        ```py
        event.check_owner_id(owner_id = owner_id)
        ```
        """
        return isinstance(owner_id, int)

    def set_owner_id(self, owner_id: int):
        """
        Проверяет и сохраняет идентификатор владельца сообщения в объекте.

        ### Аргументы:
        :param owner_id: идентификатор владельца сообщения

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        event.set_owner_id(owner_id = owner_id)
        ```
        """
        if self.check_owner_id(owner_id):
            self.owner_id = owner_id
        else:
            raise ValueError(f"Некорректное значение аргумента {owner_id=}")

    def get_owner_id(self) -> int:
        """
        Возвращает сохранённый owner id сообщения.

        :return: идентификатор владельца сообщения

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        event.get_owner_id()
        ```
        """
        if self.check_owner_id(self.owner_id):
            return self.owner_id
        else:
            raise ValueError(f"Некорректное значение атрибута {self.owner_id=}")


    def check_chat_id(self, chat_id: int) -> bool:
        """
        Проверяет, подходит ли chat id для transport-сообщения или события.

        ### Аргументы:
        :param chat_id: идентификатор чата

        :return: `True`, если подходит ли chat id для transport-сообщения или события; иначе `False`

        ### Пример использования:
        ```py
        event.check_chat_id(chat_id = chat_id)
        ```
        """
        return isinstance(chat_id, int) and chat_id >= 0

    def set_chat_id(self, chat_id: int):
        """
        Проверяет и сохраняет значение `chat id` в `Event`.

        ### Аргументы:
        :param chat_id: идентификатор чата в конкретной платформе

        :raises ValueError: если значение не проходит локальную проверку перед сохранением

        ### Пример использования:
        ```py
        event.set_chat_id(chat_id = chat_id)
        ```
        """
        if self.check_chat_id(chat_id):
            self.chat_id = chat_id
        else:
            raise ValueError(f"Некорректное значение аргумента {chat_id=}")

    def get_chat_id(self) -> int | None:
        """
        Возвращает сохранённый chat id.

        :return: идентификатор чата

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        event.get_chat_id()
        ```
        """
        if self.check_chat_id(self.chat_id):
            return self.chat_id
        else:
            raise ValueError(f"Некорректное значение атрибута {self.chat_id=}")


    def check_date(self, date: datetime) -> bool:
        """
        Проверяет допустимость даты transport-события.

        ### Аргументы:
        :param date: время сообщения или события

        :return: `True`, если допустимость даты transport-события; иначе `False`

        ### Пример использования:
        ```py
        event.check_date(date = date)
        ```
        """
        return isinstance(date, datetime)  # and date.tzinfo is not None

    def set_date(self, date: datetime):
        """
        Проверяет и сохраняет время сообщения или события в объекте.

        ### Аргументы:
        :param date: время сообщения или события

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        event.set_date(date = date)
        ```
        """
        if self.check_date(date):
            self.date = date
        else:
            raise ValueError(f"Некорректное значение аргумента {date=}")

    def get_date(self) -> datetime:
        """
        Возвращает сохранённую дату или время события.

        :return: время сообщения или события

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        event.get_date()
        ```
        """
        if self.check_date(self.date):
            return self.date
        else:
            raise ValueError(f"Некорректное значение атрибута {self.date=}")


    def check_text(self, text: str) -> bool:
        """
        Проверяет допустимость текста сообщения.

        ### Аргументы:
        :param text: текст

        :return: `True`, если допустимость текста сообщения; иначе `False`

        ### Пример использования:
        ```py
        event.check_text(text = text)
        ```
        """
        return isinstance(text, str)

    def set_text(self, text: str):
        """
        Проверяет и сохраняет значение `text` в `Event`.

        ### Аргументы:
        :param text: текст сообщения или пользовательского ввода

        :raises ValueError: если значение не проходит локальную проверку перед сохранением

        ### Пример использования:
        ```py
        event.set_text(text = text)
        ```
        """
        if self.check_text(text):
            self.text = text
        else:
            raise ValueError(f"Некорректное значение аргумента {text=}")

    def get_text(self) -> str:
        """
        Возвращает сохранённый текст сообщения.

        :return: текст текущего сообщения

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        event.get_text()
        ```
        """
        if self.check_text(self.text):
            return self.text
        else:
            raise ValueError(f"Некорректное значение атрибута {self.text=}")


    def check_reply(self, reply: Bot.Event) -> bool:
        """
        Проверяет допустимость reply-сообщения.

        ### Аргументы:
        :param reply: сообщение, на которое дан ответ

        :return: `True`, если допустимость reply-сообщения; иначе `False`

        ### Пример использования:
        ```py
        event.check_reply(reply = reply)
        ```
        """
        return isinstance(reply, Bot.Event) and reply.check()

    def set_reply(self, reply: Bot.Event | None):
        """
        Проверяет и сохраняет сообщение, на которое дан ответ в объекте.

        ### Аргументы:
        :param reply: сообщение, на которое дан ответ

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        event.set_reply(reply = reply)
        ```
        """
        if reply is None:
            self.reply = None
        elif self.check_reply(reply):
            self.reply = reply
        else:
            raise ValueError(f"Некорректное значение аргумента {reply=}")

    def get_reply(self) -> Bot.Event | None:
        """
        Возвращает сохранённое reply-сообщение.

        :return: сообщение-ответ

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        event.get_reply()
        ```
        """
        if self.reply is None:
            return None
        elif self.check_reply(self.reply):
            return self.reply
        else:
            raise ValueError(f"Некорректное значение атрибута {self.reply=}")


    def check_forward(self, forward: Iterable[Bot.Event]) -> bool:
        """
        Проверяет допустимость forward-сообщения.

        ### Аргументы:
        :param forward: пересылаемое сообщение

        :return: `True`, если допустимость forward-сообщения; иначе `False`

        ### Пример использования:
        ```py
        event.check_forward(forward = forward)
        ```
        """
        return is_iterable(forward) and all(isinstance(message, Bot.Event) for message in forward)

    def set_forward(self, forward: Iterable[Bot.Event]):
        """
        Проверяет и сохраняет пересылаемое сообщение в объекте.

        ### Аргументы:
        :param forward: пересылаемое сообщение

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        event.set_forward(forward = forward)
        ```
        """
        if self.check_forward(forward):
            if forward and self.reply:
                raise ValueError(f"Некорректное значение атрибута {self.reply=}. Невозможно пересылать сообщения в ответ на сообщение")
            else:
                self.forward_messages = list(forward)
        else:
            raise ValueError(f"Некорректное значение аргумента {forward=}")

    def get_forward(self) -> list[Bot.Event]:
        """
        Возвращает сохранённое forward-сообщение.

        :return: пересылаемое сообщение

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        event.get_forward()
        ```
        """
        if self.check_forward(self.forward_messages):
            if self.forward_messages and self.reply:
                raise ValueError(f"Некорректное значение атрибута {self.reply=}. Невозможно пересылать сообщения в ответ на сообщение")
            else:
                return self.forward_messages
        else:
            raise ValueError(f"Некорректное значение атрибута {self.forward_messages=}")


    def check_attachments(self, attachments: Iterable[Bot.Attachment]) -> bool:
        """
        Проверяет список вложений transport-сообщения.

        ### Аргументы:
        :param attachments: вложения

        :return: `True`, если список вложений transport-сообщения; иначе `False`

        ### Пример использования:
        ```py
        event.check_attachments(attachments = attachments)
        ```
        """
        return is_iterable(attachments) and all(isinstance(attachment, Bot.Attachment) for attachment in attachments)

    def set_attachments(self, attachments: Iterable[Bot.Attachment]):
        """
        Проверяет и сохраняет вложения сообщения в состоянии `Event`.

        ### Аргументы:
        :param attachments: вложения wrapper-сообщения

        :raises ValueError: если значение не проходит локальную проверку перед сохранением

        ### Пример использования:
        ```py
        event.set_attachments(attachments = attachments)
        ```
        """
        if self.check_attachments(attachments):
            self.attachments = list(attachments)
        else:
            raise ValueError(f"Некорректное значение аргумента {attachments=}")

    def get_attachments(self) -> list[Bot.Attachment]:
        """
        Возвращает сохранённые вложения сообщения.

        :return: вложения сообщения

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        event.get_attachments()
        ```
        """
        if self.check_attachments(self.attachments):
            return self.attachments
        else:
            raise ValueError(f"Некорректное значение атрибута {self.attachments=}")


    def set_name(self, first_name: str, last_name: str):
        """
        Проверяет и сохраняет имя в объекте.

        ### Аргументы:
        :param first_name: first name
        :param last_name: last name

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        event.set_name(first_name = first_name, last_name = last_name)
        ```
        """
        if isinstance(first_name, str) and isinstance(last_name, str):
            self.first_name = first_name
            self.last_name = last_name
        else:
            raise ValueError(f"Некорректное значение аргумента {first_name=} или {last_name=}")

    def get_name(self) -> tuple[str, str]:
        """
        Возвращает сохранённое имя.

        :return: служебное имя

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        event.get_name()
        ```
        """
        if isinstance(self.first_name, str) and isinstance(self.last_name, str):
            return (self.first_name, self.last_name)
        else:
            raise ValueError(f"Некорректное значение атрибута {self.first_name=} или {self.last_name=}")
