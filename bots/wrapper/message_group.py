"""
Описывает группу сообщений, отправленных одному получателю.
Модуль относится к архитектурной зоне: слой унификации транспортов `bots`, который скрывает различия Telegram и VK за общими объектами сообщений, клавиатур, вложений и событий.

### Публичные классы
- `MessagesGroup`: группа транспортных сообщений одного получателя.

### Публичные функции
- Публичные функции отсутствуют.

### Связи
Используется транспортным слоем и wrapper-логикой, чтобы app-layer работал с `Message`, `Keyboard`, `Button`, `Attachment` и `Event` без привязки к конкретной соцсети.
"""

from __future__ import annotations


from bots.constants import BOT
from bots.utils.dates import get_date, get_timestamp
from bots.utils.mapping import get_from, get_int
from bots.compat import BotTypes, Iterable, datetime
from bots.types import BOT_KEY

from bots.base.bindings import Bot

class MessagesGroup():
    """
    Группа platform-specific сообщений одного wrapper-сообщения.
    Хранит bot/chat, владельца, username, дату и список отправленных transport
    messages, чтобы wrapper мог редактировать или удалить их как одну сущность.

    ### Поля
    - `GROUP_TYPE`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.
    - `bot`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.
    - `chat_id`: идентификатор объекта или связанной сущности, по которому runtime восстанавливает связь между слоями.
    - `owner_id`: идентификатор объекта или связанной сущности, по которому runtime восстанавливает связь между слоями.
    - `messages`: сообщения, которые приложение хранит для обновления интерфейса пользователя.
    - `compression`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.
    - `username`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.
    - `date`: хранит доступную дату записи для операций этого объекта.

    ### Методы
    - `loads`: Восстанавливает объект из JSON-совместимого словаря.
    - `__init__`: Создаёт объект и сохраняет данные, нужные transport-layer для отправки, сравнения или восстановления объекта.
    - `dumps`: Возвращает JSON-совместимый снимок объекта для storage или callback payload.
    - `get_text`: Возвращает text из текущего состояния `MessagesGroup`.
    - `check_bot`: Проверяет bot перед использованием.
    - `set_bot`: Проверяет и сохраняет значение `bot` в `MessagesGroup`.
    - `get_bot`: Возвращает bot из текущего состояния `MessagesGroup`.
    - `check_chat_id`: Проверяет chat id перед использованием.
    - `set_chat_id`: Проверяет и сохраняет значение `chat id` в `MessagesGroup`.
    - `get_chat_id`: Возвращает chat id из текущего состояния `MessagesGroup`.

    ### Жизненный цикл
    Экземпляры создаются из конфигурации транспорта, принимают события платформы и отдают app-layer унифицированные wrapper-объекты.

    ### Пример использования
    ```py
    group: MessagesGroup
    ```
    """
    GROUP_TYPE = BotTypes.MESSAGE_GROUP_TYPE

    def loads(data: GROUP_TYPE, bot: BOT) -> Message.MessagesGroup:
        """
        Восстанавливает объект из JSON-совместимого словаря.

        ### Аргументы:
        :param data: сериализованный словарь
        :param bot: transport-адаптер

        :return: восстановленный объект или загруженное состояние

        ### Пример использования:
        ```py
        messagesGroup.loads(data = data, bot = bot)
        ```
        """
        chat_id: int = get_int(data, -1, "chat_id")
        owner_id: int = get_int(data, -1, "owner_id")
        compression: bool = get_from(data, "inline")
        messages: list[dict[str, str | int | dict | list[dict] | None]] = get_from(data, "messages")

        group: Message.MessagesGroup = Message.MessagesGroup(bot, chat_id, owner_id,
            [bot.__class__.Message.loads(message, bot.__class__, bot.bot) for message in messages], get_from(data, "username"), get_date(data, "date"), compression
        )
        return group

    def __init__(self, bot: BOT, chat_id: int, owner_id: int, messages: Iterable[Bot.Message], username: str, date: datetime, compression: bool = True):
        """
        Создаёт группу сообщений `MessagesGroup` и сохраняет элементы, которые нужно отправить или сравнить вместе.

        ### Аргументы:
        :param bot: transport-адаптер
        :param chat_id: идентификатор чата
        :param owner_id: идентификатор владельца сообщения
        :param messages: сообщения или группы сообщений для обработки
        :param username: имя пользователя
        :param date: время сообщения или события
        :param compression: признак сжатия вложения

        ### Пример использования:
        ```py
        messagesGroup = MessagesGroup(bot = bot, chat_id = chat_id, owner_id = owner_id, messages = messages, username = username, date = date, compression = compression)
        ```
        """
        self.bot: BOT = None
        self.chat_id: int | None = None
        self.owner_id: int | None = None
        self.messages: list[Bot.Message] = list(messages)
        self.compression: bool = bool(compression)
        self.username: str = username
        self.date: datetime = date

        self.set_bot(bot)
        self.set_chat_id(chat_id)
        self.set_owner_id(owner_id)

    def __repr__(self) -> str:
        bot_key: BOT_KEY = self.bot.get_bot_key()
        chat_id: int = self.chat_id
        owner_id: int = self.owner_id
        messages: int = len(self.messages)
        username: str | None = self.username
        date: datetime | None = self.date
        result: str = f"MessagesGroup({bot_key} {chat_id=} {owner_id=} {username=} {date=} {messages=})["

        if self.messages:
            for message in self.messages:
                result += f"\n\t{repr(message)}"

            return f"{result}\n]"
        else:
            return f"{result}]"


    def dumps(self) -> GROUP_TYPE:
        """
        Возвращает JSON-совместимый снимок объекта для storage или callback payload.

        :return: JSON-совместимый словарь для сохранения или передачи между слоями

        ### Пример использования:
        ```py
        messagesGroup.dumps()
        ```
        """
        return {
            "bot_key": self.bot.get_bot_key(),
            "chat_id": int(self.chat_id),
            "owner_id": int(self.owner_id),
            "compression": bool(self.compression),
            "messages": [message.dumps() for message in self.messages],
            "username": self.username,
            "date": get_timestamp(self.date) if self.date is not None else None
        }

    def get_text(self) -> str:
        """
        Возвращает сохранённый текст сообщения.

        :return: текст текущего сообщения

        ### Пример использования:
        ```py
        messagesGroup.get_text()
        ```
        """
        return "\n".join(message.get_text() for message in self.messages)


    # Методы работы с полями


    def check_bot(self, bot: BOT) -> bool:
        """
        Проверяет, что значение является transport-адаптером.

        ### Аргументы:
        :param bot: transport-адаптер

        :return: `True`, если что значение является transport-адаптером; иначе `False`

        ### Пример использования:
        ```py
        messagesGroup.check_bot(bot = bot)
        ```
        """
        return isinstance(bot, Vkbot) or isinstance(bot, Telebot)

    def set_bot(self, bot: BOT):
        """
        Проверяет и сохраняет transport-адаптер в объекте.

        ### Аргументы:
        :param bot: transport-адаптер

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        messagesGroup.set_bot(bot = bot)
        ```
        """
        if self.check_bot(bot):
            self.bot = bot
        else:
            raise ValueError(f"Некорректное значение аргумента {bot=}")

    def get_bot(self) -> BOT:
        """
        Возвращает привязанный transport-адаптер.

        :return: transport-адаптер

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        messagesGroup.get_bot()
        ```
        """
        if self.check_bot(self.bot):
            return self.bot
        else:
            raise ValueError(f"Некорректное значение атрибута {self.bot=}")


    def check_chat_id(self, chat_id: int) -> bool:
        """
        Проверяет, подходит ли chat id для transport-сообщения или события.

        ### Аргументы:
        :param chat_id: идентификатор чата

        :return: `True`, если подходит ли chat id для transport-сообщения или события; иначе `False`

        ### Пример использования:
        ```py
        messagesGroup.check_chat_id(chat_id = chat_id)
        ```
        """
        return isinstance(chat_id, int) and chat_id >= 0

    def set_chat_id(self, chat_id: int):
        """
        Проверяет и сохраняет значение `chat id` в `MessagesGroup`.

        ### Аргументы:
        :param chat_id: идентификатор чата в конкретной платформе

        :raises ValueError: если значение не проходит локальную проверку перед сохранением

        ### Пример использования:
        ```py
        group.set_chat_id(chat_id = chat_id)
        ```
        """
        if self.chat_id is not None:
            raise ValueError(f"Поле self.chat_id уже содержит значение и не может быть установлено повторно. Сообщение может быть отправлено только один раз.")
        elif self.check_chat_id(chat_id):
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
        messagesGroup.get_chat_id()
        ```
        """
        if self.chat_id is None:
            return None
        elif self.check_chat_id(self.chat_id):
            return self.chat_id
        else:
            raise ValueError(f"Некорректное значение атрибута {self.chat_id=}")


    def check_owner_id(self, owner_id: int) -> bool:
        """
        Проверяет допустимость owner id transport-сообщения.

        ### Аргументы:
        :param owner_id: идентификатор владельца сообщения

        :return: `True`, если допустимость owner id transport-сообщения; иначе `False`

        ### Пример использования:
        ```py
        messagesGroup.check_owner_id(owner_id = owner_id)
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
        messagesGroup.set_owner_id(owner_id = owner_id)
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
        messagesGroup.get_owner_id()
        ```
        """
        if self.check_owner_id(self.owner_id):
            return self.owner_id
        else:
            raise ValueError(f"Некорректное значение атрибута {self.owner_id=}")
