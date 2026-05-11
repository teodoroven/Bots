"""
Описывает общую часть транспортного сообщения.
Модуль относится к архитектурной зоне: слой унификации транспортов `bots`, который скрывает различия Telegram и VK за общими объектами сообщений, клавиатур, вложений и событий.

### Публичные классы
- `BaseMessage`: базовая модель транспортного сообщения.

### Публичные функции
- Публичные функции отсутствуют.

### Связи
Используется транспортным слоем и wrapper-логикой, чтобы app-layer работал с `Message`, `Keyboard`, `Button`, `Attachment` и `Event` без привязки к конкретной соцсети.
"""

from __future__ import annotations

from bots.compat import (
    Any,
    BotTypes,
    Literal,
    Never,
    abstractmethod,
    datetime,
)
from bots.types import Any, BOT_KEY, Literal, MESSAGE_TYPE

class BaseMessage():
    """
    Общий контракт transport-сообщения.
    Хранит текст, chat id, связи reply/forward и события жизненного цикла;
    наследники добавляют реальные сетевые вызовы Telegram или VK.

    ### Поля
    - `MESSAGE_TYPE`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.
    - `CREATE_KEY`: ключ сериализации или transport-события, по которому объект отличает один вариант данных от другого.
    - `SENT_KEY`: ключ сериализации или transport-события, по которому объект отличает один вариант данных от другого.
    - `EDIT_KEY`: ключ локализации сообщения о запрете изменения.
    - `DELETE_KEY`: ключ сериализации или transport-события, по которому объект отличает один вариант данных от другого.
    - `KEYS`: ключ сериализации или transport-события, по которому объект отличает один вариант данных от другого.
    - `text`: текстовое содержимое, которое показывается пользователю, отправляется в GPT или сохраняется в доменной модели.
    - `owner_id`: идентификатор объекта или связанной сущности, по которому runtime восстанавливает связь между слоями.
    - `reply`: связанные сообщения или вложения, которые transport-layer использует при отправке, сравнении или редактировании.
    - `chat_id`: идентификатор объекта или связанной сущности, по которому runtime восстанавливает связь между слоями.

    ### Методы
    - `__init__`: Создаёт объект и сохраняет данные, нужные transport-layer для отправки, сравнения или восстановления объекта.
    - `dumps`: Возвращает JSON-совместимый снимок объекта для storage или callback payload.
    - `get_bot_key`: Возвращает ключ транспорта из текущего состояния `BaseMessage`.
    - `was_sent`: Проверяет, есть ли у wrapper-сообщения не удалённое событие создания или отправки.
    - `check_editable`: Проверяет editable перед использованием.
    - `send`: Отправляет сообщение или вложение через transport-layer.
    - `delete`: Удаляет отправленное сообщение через transport-layer.
    - `get_username`: Возвращает username из текущего состояния `BaseMessage`.
    - `check_event`: Проверяет событие транспорта перед использованием.
    - `add_event`: Сохраняет transport-событие в очереди или истории объекта.

    ### Жизненный цикл
    Экземпляры создаются из конфигурации транспорта, принимают события платформы и отдают app-layer унифицированные wrapper-объекты.

    ### Пример использования
    ```py
    baseMessage: BaseMessage
    ```
    """
    MESSAGE_TYPE = BotTypes.MESSAGE_TYPE
    CREATE_KEY: str = "MESSAGE_NEW"
    SENT_KEY: str = "SENT"
    EDIT_KEY: str = "EDIT"
    DELETE_KEY: str = "DELETE"
    KEYS: tuple[Literal["MESSAGE_NEW", "SENT", "EDIT", "DELETE"]] = (CREATE_KEY, SENT_KEY, EDIT_KEY, DELETE_KEY)

    def __init__(self, owner_id: int, text: str, reply: Bot.Message | None = None):
        """
        Создаёт wrapper `BaseMessage` и сохраняет данные сообщения или события без привязки app-layer к SDK платформы.

        ### Аргументы:
        :param owner_id: идентификатор владельца сообщения
        :param text: текст
        :param reply: сообщение, на которое дан ответ

        ### Пример использования:
        ```py
        baseMessage = BaseMessage(owner_id = owner_id, text = text, reply = reply)
        ```
        """
        # Текст сообщения
        self.text: str

        # ID пользователя или сообщества, которое отправило/отправит сообщение
        self.owner_id: int

        # В ответ на сообщение
        self.reply: Bot.BaseMessage | None = None

        # Идентификатор чата (пользователя), куда будет отправлено сообщение
        self.chat_id: int | None = None  # Устанавливается после отправки методом send

        # Идентификатор сообщения
        self.id: int | None = None  # Устанавливается после отправки методом send

        # Если сообщение создаётся из события, то событие хранится в этом поле
        self.events: dict[Literal["MESSAGE_NEW", "SENT", "EDIT", "DELETE"], list[Bot.Event]] = {
            # События, из которых было создано сообщение
            self.__class__.CREATE_KEY: [],
            # События отправки сообщения
            self.__class__.SENT_KEY: [],
            # Остальные события
            self.__class__.EDIT_KEY: [],
            self.__class__.DELETE_KEY: []
        }

        # Даты сообщения
        self.dates: dict[Literal["MESSAGE_NEW", "SENT", "EDIT", "DELETE"], list[datetime]] = {
            # Сообщение получено
            self.__class__.CREATE_KEY: [],
            # Сообщение отправлено
            self.__class__.SENT_KEY: [],
            # Сообщение отредактировано
            self.__class__.EDIT_KEY: [],
            # Сообщение удалено
            self.__class__.DELETE_KEY: []
        }

        self.set_owner_id(owner_id)
        self.set_text(text)
        self.set_reply(reply)

    def dumps(self) -> MESSAGE_TYPE:
        """
        Возвращает JSON-совместимый снимок объекта для storage или callback payload.

        :return: JSON-совместимый словарь для сохранения или передачи между слоями

        ### Пример использования:
        ```py
        baseMessage.dumps()
        ```
        """
        reply: Bot.BaseMessage | None = self.get_reply()

        return {
            "events": {
                key: [
                    event.dumps() for event in events
                ] for key, events in self.events.items()
            },
            "dates": {
                key: [
                    date.isoformat() for date in dates
                ] for key, dates in self.dates.items()
            },
            "text": self.get_text(),
            "owner_id": self.get_owner_id(),
            "reply": reply.dumps() if reply is not None else None,
            "chat_id": self.get_chat_id(),
            "id": self.get_id()
        }

    @abstractmethod
    def get_bot_key(self) -> BOT_KEY:
        """
        Возвращает ключ транспорта из текущего состояния `BaseMessage`.

        :return: строковый ключ транспорта, например `telebot` или `vkbot`

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Примеры вызова:
        ```py
        baseMessage.get_bot_key()
        ```
        """
        raise NotImplementedError()

    def was_sent(self) -> bool:
        """
        Проверяет, есть ли у wrapper-сообщения не удалённое событие создания или отправки.

        :return: `True`, если событий создания и отправки больше, чем событий удаления; иначе `False`

        ### Пример использования:
        ```py
        baseMessage.was_sent()
        ```
        """
        return (len(self.events[self.__class__.CREATE_KEY]) + len(self.events[self.__class__.SENT_KEY])) > len(self.events[self.__class__.DELETE_KEY])

    def check_editable(self) -> bool:
        """
        Проверяет, можно ли редактировать сообщение по сохранённым событиям отправки и удаления.

        :return: `True`, если событий отправки больше, чем событий удаления; иначе `False`

        ### Пример использования:
        ```py
        baseMessage.check_editable()
        ```
        """
        message = self
        return len(self.events[self.__class__.SENT_KEY]) > len(self.events[self.__class__.DELETE_KEY])

    @abstractmethod
    def send(self, chat_id: int) -> list[Bot.Message]:
        """
        Базовый контракт отправки сообщения через transport-layer.
        Наследники выполняют сетевой вызов Telegram/VK и возвращают созданные
        platform-specific сообщения.

        ### Аргументы:
        :param chat_id: идентификатор чата

        :return: список отправленных сообщений транспорта

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        baseMessage.send(chat_id = chat_id)
        ```
        """
        raise NotImplementedError("Вместо Bot.Message используйте Vkbot.Message или Telebot.Message")

    @abstractmethod
    def delete(self) -> Never:
        """
        Базовый контракт удаления отправленного сообщения через transport-layer.
        Наследники делают сетевой вызов Telegram/VK и записывают событие
        удаления в историю сообщения.

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        baseMessage.delete()
        ```
        """
        raise NotImplementedError("Вместо Bot.Message используйте Vkbot.Message или Telebot.Message")

    @abstractmethod
    def get_username(self) -> str | None:
        """
        Возвращает сохранённое имя пользователя.

        :return: имя пользователя в транспорте

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        baseMessage.get_username()
        ```
        """
        raise NotImplementedError("Вместо Bot.Message используйте Vkbot.Message или Telebot.Message")


    def check_event(self, event: Bot.Event) -> bool:
        """
        Проверяет, что значение является transport-событием.

        ### Аргументы:
        :param event: transport-событие для обработки

        :return: `True`, если передан `Bot.Event`; иначе `False`

        ### Пример использования:
        ```py
        baseMessage.check_event(event = event)
        ```
        """
        return isinstance(event, Bot.Event)

    def add_event(self,  event: Bot.Event | Any, date: datetime, key: Literal["MESSAGE_NEW", "SENT", "EDIT", "DELETE"]):
        """
        Добавляет transport-событие в историю пользователя.

        ### Аргументы:
        :param event: transport-событие для обработки
        :param date: время сообщения или события
        :param key: ключ записи или настройки

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        baseMessage.add_event(event = event, date = date, key = key)
        ```
        """
        if not isinstance(event, Bot.Event):
            message_id: int | None = None

            if Bot.Message.check_id(None, event):
                message_id = int(event)

            event = Bot.Event(self.get_owner_id(), self.get_chat_id(), key, date)

            if message_id is not None:
                event.events.append(message_id)

        if self.check_event(event):
            if isinstance(date, datetime):
                if key in self.__class__.KEYS:
                    self.events[key].append(event)
                    self.dates[key].append(date)
                else:
                    raise ValueError(f"Некорректное значение аргумента {key=}")
            else:
                raise ValueError(f"Некорректное значение аргумента {date=}")
        else:
            raise ValueError(f"Некорректное значение аргумента {event=}")


    def check_owner_id(self, owner_id: int) -> bool:
        """
        Проверяет owner id transport-сообщения.

        ### Аргументы:
        :param owner_id: идентификатор владельца сообщения

        :return: `True`, если owner id является неотрицательным `int`; иначе `False`

        ### Пример использования:
        ```py
        baseMessage.check_owner_id(owner_id = owner_id)
        ```
        """
        return isinstance(owner_id, int) and owner_id >= 0

    def set_owner_id(self, owner_id: int):
        """
        Проверяет и сохраняет идентификатор владельца сообщения в объекте.

        ### Аргументы:
        :param owner_id: идентификатор владельца сообщения

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        baseMessage.set_owner_id(owner_id = owner_id)
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
        baseMessage.get_owner_id()
        ```
        """
        if self.check_owner_id(self.owner_id):
            return self.owner_id
        else:
            raise ValueError(f"Некорректное значение атрибута {self.owner_id=}")


    def check_text(self, text: str) -> bool:
        """
        Проверяет текст сообщения.

        ### Аргументы:
        :param text: текст

        :return: `True`, если передана непустая строка; иначе `False`

        ### Пример использования:
        ```py
        baseMessage.check_text(text = text)
        ```
        """
        return isinstance(text, str) and str(text).strip()

    def set_text(self, text: str):
        """
        Проверяет и сохраняет значение `text` в `BaseMessage`.

        ### Аргументы:
        :param text: текст сообщения или пользовательского ввода

        :raises ValueError: если значение не проходит локальную проверку перед сохранением

        ### Пример использования:
        ```py
        baseMessage.set_text(text = text)
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
        baseMessage.get_text()
        ```
        """
        if self.check_text(self.text):
            return str(self.text).strip()
        else:
            raise ValueError(f"Некорректное значение атрибута {self.text=}")


    def check_reply(self, reply: Bot.BaseMessage) -> bool:
        """
        Проверяет reply-сообщение.

        ### Аргументы:
        :param reply: сообщение, на которое дан ответ

        :return: `True`, если reply является корректным `Bot.BaseMessage`; иначе `False`

        ### Пример использования:
        ```py
        baseMessage.check_reply(reply = reply)
        ```
        """
        return isinstance(reply, Bot.BaseMessage) and reply.check()

    def set_reply(self, reply: Bot.BaseMessage | None):
        """
        Проверяет и сохраняет сообщение, на которое дан ответ в объекте.

        ### Аргументы:
        :param reply: сообщение, на которое дан ответ

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        baseMessage.set_reply(reply = reply)
        ```
        """
        if reply is None:
            self.reply = None
        elif self.check_reply(reply):
            self.reply = reply
        else:
            raise ValueError(f"Некорректное значение аргумента {reply=}")

    def get_reply(self) -> Bot.BaseMessage | None:
        """
        Возвращает сохранённое reply-сообщение.

        :return: сообщение-ответ

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        baseMessage.get_reply()
        ```
        """
        if self.reply is None:
            return None
        elif self.check_reply(self.reply):
            return self.reply
        else:
            raise ValueError(f"Некорректное значение атрибута {self.reply=}")


    def check_chat_id(self, chat_id: int) -> bool:
        """
        Проверяет chat id transport-сообщения.

        ### Аргументы:
        :param chat_id: идентификатор чата

        :return: `True`, если chat id является неотрицательным `int`; иначе `False`

        ### Пример использования:
        ```py
        baseMessage.check_chat_id(chat_id = chat_id)
        ```
        """
        return isinstance(chat_id, int) and chat_id >= 0

    def set_chat_id(self, chat_id: int):
        """
        Проверяет и сохраняет значение `chat id` в `BaseMessage`.

        ### Аргументы:
        :param chat_id: идентификатор чата в конкретной платформе

        :raises ValueError: если значение не проходит локальную проверку перед сохранением

        ### Пример использования:
        ```py
        baseMessage.set_chat_id(chat_id = chat_id)
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
        baseMessage.get_chat_id()
        ```
        """
        if self.chat_id is None:
            return None
        elif self.check_chat_id(self.chat_id):
            return self.chat_id
        else:
            raise ValueError(f"Некорректное значение атрибута {self.chat_id=}")


    def check_id(self, message_id: int) -> bool:
        """
        Проверяет идентификатор сообщения.

        ### Аргументы:
        :param message_id: идентификатор сообщения

        :return: `True`, если идентификатор является неотрицательным `int`; иначе `False`

        ### Пример использования:
        ```py
        baseMessage.check_id(message_id = message_id)
        ```
        """
        return isinstance(message_id, int) and message_id >= 0

    def set_id(self, message_id: int):
        """
        Проверяет и сохраняет идентификатор в объекте.

        ### Аргументы:
        :param message_id: идентификатор сообщения

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        baseMessage.set_id(message_id = message_id)
        ```
        """
        if self.check_id(message_id):
            self.id = message_id
        else:
            raise ValueError(f"Некорректное значение аргумента {message_id=}")

    def get_id(self) -> int | None:
        """
        Возвращает сохранённый идентификатор объекта.

        :return: идентификатор текущего объекта

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        baseMessage.get_id()
        ```
        """
        if self.id is None:
            return None
        elif self.check_id(self.id):
            return self.id
        else:
            raise ValueError(f"Некорректное значение атрибута {self.id=}")


    def get_date(self, key: Literal["MESSAGE_NEW", "SENT", "EDIT", "DELETE"] = "MESSAGE_NEW") -> datetime | None:
        """
        Возвращает сохранённую дату или время события.

        ### Аргументы:
        :param key: ключ записи или настройки

        :return: время сообщения или события

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        baseMessage.get_date(key = key)
        ```
        """
        if key in self.dates:
            if self.dates[key]:
                return self.dates[key][-1]
            else:
                return None
        else:
            raise ValueError(f"Некорректное значение аргумента {key=}")
