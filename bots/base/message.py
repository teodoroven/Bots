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


from bots.utils.mapping import get_from, get_int, is_iterable
from bots.utils.text import cut
from bots.compat import (
    BotTypes,
    CALLBACK_REMOVE,
    Iterable,
    Literal,
    Never,
    TeleBot,
    VkApi,
    abstractmethod,
    datetime,
)
from bots.types import CHANGED_PARTS, Literal, MESSAGE_TYPE

from bots.base.base_message import BaseMessage

class Message(BaseMessage):
    """
    Расширяет `BaseMessage` клавиатурой, вложениями и callback-кнопкой удаления.
    Конкретные Telegram/VK сообщения реализуют сетевую отправку, редактирование
    и удаление, а базовый класс хранит общий снимок состояния.

    ### Поля
    - `MESSAGE_TYPE`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.
    - `CHANGED_TEXT`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.
    - `CHANGED_CAPTION`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.
    - `CHANGED_MEDIA`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.
    - `CHANGED_REPLY_MARKUP`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.
    - `CHANGED_REPLY`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.
    - `CHANGED_FORWARD`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.
    - `ALL_CHANGED_PARTS`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.
    - `EMPTY_TEXT`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.
    - `MAX_LENGTH`: ограничение размера, которое защищает transport/API от слишком длинного payload.

    ### Методы
    - `loads`: Восстанавливает объект из JSON-совместимого словаря.
    - `from_event`: Создаёт wrapper-сообщение из transport-события.
    - `__init__`: Создаёт объект и сохраняет данные, нужные transport-layer для отправки, сравнения или восстановления объекта.
    - `get_remove_callback`: Возвращает callback единственной remove-кнопки сообщения.
    - `dumps`: Возвращает JSON-совместимый снимок объекта для storage или callback payload.
    - `compare_attachments`: Сравнивает вложения сообщения с другим объектом того же слоя.
    - `compare_messages`: Сравнивает wrapper-сообщения с другим объектом того же слоя.
    - `compare_reply`: Сравнивает reply с другим объектом того же слоя.
    - `compare_forward`: Сравнивает forward с другим объектом того же слоя.
    - `compare_keyboards`: Сравнивает keyboards с другим объектом того же слоя.

    ### Жизненный цикл
    Экземпляры создаются из конфигурации транспорта, принимают события платформы и отдают app-layer унифицированные wrapper-объекты.

    ### Пример использования
    ```py
    message: Message
    ```
    """
    MESSAGE_TYPE = BotTypes.MESSAGE_TYPE
    CHANGED_TEXT: CHANGED_PARTS = "text"
    CHANGED_CAPTION: CHANGED_PARTS = "caption"
    CHANGED_MEDIA: CHANGED_PARTS = "media"
    CHANGED_REPLY_MARKUP: CHANGED_PARTS = "reply_markup"
    CHANGED_REPLY: CHANGED_PARTS = "reply"
    CHANGED_FORWARD: CHANGED_PARTS = "forward"
    ALL_CHANGED_PARTS: set[CHANGED_PARTS] = {
        CHANGED_TEXT,
        CHANGED_CAPTION,
        CHANGED_MEDIA,
        CHANGED_REPLY_MARKUP,
        CHANGED_REPLY,
        CHANGED_FORWARD
    }

    # Текст пустого сообщения
    EMPTY_TEXT: str = " "

    # Максимальная длина сообщения в символах
    MAX_LENGTH: int = 4096

    # Максимальное количество вложений в одном сообщении
    MAX_ATTACHMENTS: int = 10

    # Максимальное количество вложений в одной медиагруппе
    MAX_ATTACHMENTS_IN_GROUP: int = 10

    @classmethod
    def loads(cls, data: MESSAGE_TYPE, parent: type[BOT], bot: VkApi | TeleBot) -> Bot.Message:
        """
        Восстанавливает объект из JSON-совместимого словаря.

        ### Аргументы:
        :param data: сериализованный словарь
        :param parent: родительский объект, к которому привязан wrapper
        :param bot: transport-адаптер

        :return: восстановленный объект или загруженное состояние

        ### Пример использования:
        ```py
        Message.loads(data = data, parent = parent, bot = bot)
        ```
        """
        owner_id: int = get_int(data, -1, "owner_id")
        text: str = get_from(data, "text")

        keyboard_data: dict[str, int | bool| list[dict[str, str]]] | None = get_from(data, "keyboard")
        keyboard: Bot.Keyboard | None = None if keyboard_data is None else parent.Keyboard.loads(keyboard_data)

        reply_data: dict[str, str | int | dict | None] | None = get_from(data, "reply")
        reply: Bot.Message | None = None if reply_data is None else parent.Message.loads(reply_data, bot)

        forward: list[dict[str, str | int | dict | None]] = get_from(data, "forward")
        forward_messages: list[Bot.Message] = [parent.Message.loads(message, bot) for message in forward]

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

        message = cls(bot, owner_id, text, keyboard, forward_messages, reply, attachments)

        message_id: str | None = get_from(data, "id")
        if message_id:
            message.set_id(int(message_id))

        chat_id: str | None = get_from(data, "chat_id")

        if chat_id:
            message.set_chat_id(int(chat_id))

        events_data: dict[Literal["MESSAGE_NEW", "SENT", "EDIT", "DELETE"], list[Bot.Event.EVENT_TYPE]] = data.get("events", {})
        dates_data: dict[Literal["MESSAGE_NEW", "SENT", "EDIT", "DELETE"], list[str]] = data.get("dates", {})

        for key in cls.KEYS:
            events_list: list[Bot.Event.EVENT_TYPE] = events_data.get(key, [])
            dates_list: list[str] = dates_data.get(key, [])

            if len(events_list) == len(dates_list):
                for i in range(len(dates_list)):
                    event_data: Bot.Event.EVENT_TYPE = events_list[i]
                    date_data: str = dates_list[i]

                    event: Bot.Event = parent.Event.loads(event_data, parent)
                    date: datetime = datetime.fromisoformat(date_data)
                    message.add_event(event, date, key)
        return message

    @classmethod
    def from_event(cls: type[Vkbot.Message | Telebot.Message], event: Bot.Event, bot: VkApi | TeleBot):
        """
        Создаёт wrapper-сообщение из transport-события.
        Восстанавливает forward/reply/attachments из события, переносит
        `chat_id` и добавляет событие создания в историю сообщения.

        ### Аргументы:
        :param event: transport-событие для обработки
        :param bot: transport-адаптер

        :return: сообщение конкретного транспорта, созданное из события

        ### Пример использования:
        ```py
        Message.from_event(event = event, bot = bot)
        ```
        """
        forward: list[Vkbot.Message | Telebot.Message] = [cls.from_event(ev, bot) for ev in event.get_forward()]
        reply: Vkbot.Message | Telebot.Message | None = cls.from_event(event.get_reply(), bot) if event.reply is not None else None

        message: Vkbot.Message | Telebot.Message = cls(bot, event.get_chat_id(), event.get_text(), None, forward, reply, event.get_attachments())
        message.set_chat_id(event.chat_id)
        message.add_event(event, event.get_date(), cls.CREATE_KEY)
        return message

    def __init__(self, owner_id: int, text: str, keyboard: Bot.Keyboard | None = None, forward: Iterable[Vkbot.Message] = [], reply: Vkbot.Message | None = None, attachments: Iterable[Bot.Attachment] = []):
        """
        Создаёт wrapper `Message` и сохраняет данные сообщения или события без привязки app-layer к SDK платформы.

        ### Аргументы:
        :param owner_id: идентификатор владельца сообщения
        :param text: текст
        :param keyboard: клавиатура
        :param forward: пересылаемое сообщение
        :param reply: сообщение, на которое дан ответ
        :param attachments: вложения

        ### Пример использования:
        ```py
        message = Message(owner_id = owner_id, text = text, keyboard = keyboard, forward = forward, reply = reply, attachments = attachments)
        ```
        """
        super().__init__(owner_id, text, reply)

        # Вложения объявляются раньше, так как проверяются в set_keyboard
        self.attachments: list[Bot.Attachment] = []

        # Клавиатура
        self.keyboard: Bot.Keyboard | None = None

        # Пересланные сообщения
        self.forward_messages: list[Bot.Message] = []

        # Сообщение изменилось после отправки
        self.changed: set[CHANGED_PARTS] = set()

        self.set_attachments(attachments)
        self.set_keyboard(keyboard)
        self.set_forward(forward)

        # Текст устанавливается в последнюю очередь, потому что если он пустой и других вложений/сообщений/клавитуры не передано, то будет вызвано исключение
        self.set_text(text)

    def get_remove_callback(self) -> str:
        """
        Возвращает callback удаления из единственной кнопки сообщения.
        Callback считается remove-действием, если клавиатура содержит одну
        кнопку и её `callback_data` начинается с `CALLBACK_REMOVE`.

        :return: callback удаления или пустая строка

        ### Пример использования:
        ```py
        message.get_remove_callback()
        ```
        """
        if self.keyboard and len(self.keyboard.buttons) == 1:
            callback_data: str | None = self.keyboard.buttons[0].callback_data

            if callback_data and callback_data.startswith(CALLBACK_REMOVE):
                return callback_data

        return ""

    def __repr__(self) -> str:
        classname: str = "Vkbot.Message" if hasattr(self, "vkbot") else "Telebot.Message"
        id: int = self.id
        chat_id: int = self.get_chat_id()
        owner_id: int = self.get_owner_id()
        keyboard = self.keyboard
        text: str = cut(self.text, 40)
        text: str = self.text
        return f"{classname}({id=} {chat_id=} {owner_id=} {text=})[{keyboard=}]" + "{" + f"attachments({len(self.attachments)})={repr(self.attachments)}" + "}"

    def dumps(self) -> MESSAGE_TYPE:
        """
        Возвращает JSON-совместимый снимок объекта для storage или callback payload.

        :return: JSON-совместимый словарь для сохранения или передачи между слоями

        ### Пример использования:
        ```py
        message.dumps()
        ```
        """
        result: "Bot.Message.MESSAGE_TYPE" = super().dumps()
        keyboard: Bot.Keyboard | None = self.get_keyboard()

        result.update({
            "attachments": [attachment.dumps() for attachment in self.get_attachments()],
            "keyboard": keyboard.dumps() if keyboard is not None else None,
            "forward": [message.dumps() for message in self.get_forward()]
        })

        return result

    def compare_attachments(self, message: Message) -> bool:
        """
        Сравнивает вложения сообщения с другим объектом того же слоя.

        ### Аргументы:
        :param message: wrapper-сообщение, которое можно отправить, обновить или сохранить

        :return: `True`, если наборы вложений совпадают; иначе `False`

        ### Пример использования:
        ```py
        message.compare_attachments(message = message)
        ```
        """

        if len(self.attachments) != len(message.attachments):
            return False

        for i in range(len(self.attachments)):
            if not self.attachments[i].compare(message.attachments[i]):
                return False

        return True

    @staticmethod
    def compare_messages(message1: Bot.BaseMessage | None, message2: Bot.BaseMessage  | None) -> bool:
        """
        Сравнивает состояние объектов и возвращает флаг, который нужен перед отправкой или редактированием.

        ### Аргументы:
        :param message1: первое сообщение для сравнения
        :param message2: второе сообщение для сравнения

        :return: `True`, если оба сообщения отсутствуют или у них совпадают тип и id; иначе `False`

        ### Пример использования:
        ```py
        Message.compare_messages(message1 = message1, message2 = message2)
        ```
        """
        if int(bool(message1)) + int(bool(message2)) == 1:
            return False
        elif message1 is None and message2 is None:
            return True
        else:
            return isinstance(message1, type(message2)) and message1.get_id() == message2.get_id()

    def compare_reply(self, message: Bot.Message) -> bool:
        """
        Сравнивает reply с другим объектом того же слоя.

        ### Аргументы:
        :param message: wrapper-сообщение, которое можно отправить, обновить или сохранить

        :return: `True`, если reply-сообщения совпадают; иначе `False`

        ### Пример использования:
        ```py
        message.compare_reply(message = message)
        ```
        """
        return self.__class__.compare_messages(self.get_reply(), message.get_reply())

    def compare_forward(self, message: Message) -> bool:
        """
        Сравнивает forward с другим объектом того же слоя.

        ### Аргументы:
        :param message: wrapper-сообщение, которое можно отправить, обновить или сохранить

        :return: `True`, если списки пересланных сообщений совпадают; иначе `False`

        ### Пример использования:
        ```py
        message.compare_forward(message = message)
        ```
        """
        if len(self.forward_messages) != len(message.forward_messages):
            return False

        for i in range(len(self.forward_messages)):
            message1: Bot.Message = self.forward_messages[i]
            message2: Bot.Message = message.forward_messages[i]

            if not self.__class__.compare_messages(message1, message2):
                return False

        return True

    def compare_keyboards(self, keyboard1: Bot.Keyboard | None, keyboard2: Bot.Keyboard | None) -> bool:
        """
        Сравнивает состояние объектов и возвращает флаг, который нужен перед отправкой или редактированием.

        ### Аргументы:
        :param keyboard1: первая клавиатура для сравнения
        :param keyboard2: вторая клавиатура для сравнения

        :return: `True`, если обе клавиатуры отсутствуют или их сериализованное состояние совпадает; иначе `False`

        ### Пример использования:
        ```py
        message.compare_keyboards(keyboard1 = keyboard1, keyboard2 = keyboard2)
        ```
        """
        if keyboard1 is None and keyboard2 is None:
            return True
        elif keyboard1 is None or keyboard2 is None:
            return False
        else:
            return keyboard1.dumps() == keyboard2.dumps()

    def compare_attachments_list(self, attachments1: Iterable[Bot.Attachment], attachments2: Iterable[Bot.Attachment]) -> bool:
        """
        Сравнивает состояние объектов и возвращает флаг, который нужен перед отправкой или редактированием.

        ### Аргументы:
        :param attachments1: первый набор вложений для сравнения
        :param attachments2: второй набор вложений для сравнения

        :return: `True`, если списки вложений одинаковой длины и все вложения попарно совпадают; иначе `False`

        ### Пример использования:
        ```py
        message.compare_attachments_list(attachments1 = attachments1, attachments2 = attachments2)
        ```
        """
        attachments1_list: list[Bot.Attachment] = list(attachments1)
        attachments2_list: list[Bot.Attachment] = list(attachments2)

        if len(attachments1_list) != len(attachments2_list):
            return False

        for i in range(len(attachments1_list)):
            if not attachments1_list[i].compare(attachments2_list[i]):
                return False

        return True

    def compare_messages_list(self, messages1: Iterable[Bot.BaseMessage], messages2: Iterable[Bot.BaseMessage]) -> bool:
        """
        Сравнивает состояние объектов и возвращает флаг, который нужен перед отправкой или редактированием.

        ### Аргументы:
        :param messages1: первый список сообщений для сравнения
        :param messages2: второй список сообщений для сравнения

        :return: `True`, если списки сообщений одинаковой длины и все сообщения попарно совпадают; иначе `False`

        ### Пример использования:
        ```py
        message.compare_messages_list(messages1 = messages1, messages2 = messages2)
        ```
        """
        messages1_list: list[Bot.BaseMessage] = list(messages1)
        messages2_list: list[Bot.BaseMessage] = list(messages2)

        if len(messages1_list) != len(messages2_list):
            return False

        for i in range(len(messages1_list)):
            message1: Bot.BaseMessage = messages1_list[i]
            message2: Bot.BaseMessage = messages2_list[i]

            if not self.__class__.compare_messages(message1, message2):
                return False

        return True

    def compare(self, message: Message) -> bool:
        """
        Сравнивает сообщение с другим сообщением того же transport-типа.

        ### Аргументы:
        :param message: wrapper-сообщение, которое можно отправить, обновить или сохранить

        :return: `True`, если вложения, reply и forward совпадают; иначе `False`

        ### Пример использования:
        ```py
        message.compare(message = message)
        ```
        """
        return self.compare_attachments(message) and self.compare_forward(message) and self.compare_reply(message)

    @abstractmethod
    def edit(self, prevent_resend: bool = False) -> Never:
        """
        Базовый контракт обновления уже отправленного сообщения.
        Наследники редактируют сообщение через Telegram/VK API или переотправляют
        его, если редактирование невозможно и `prevent_resend=False`.

        ### Аргументы:
        :param prevent_resend: запрещать ли fallback на переотправку

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        message.edit(prevent_resend = prevent_resend)
        ```
        """
        raise NotImplementedError("Вместо используйте Vkbot.Message или Telebot.Message")

    def check_changed_part(self, changed_part: CHANGED_PARTS | str) -> bool:
        """
        Проверяет значение `changed part` перед сохранением или использованием.

        ### Аргументы:
        :param changed_part: часть сообщения, которую нужно проверить на изменение

        :return: `True`, если значение `changed part` перед сохранением или использованием; иначе `False`

        ### Пример использования:
        ```py
        message.check_changed_part(changed_part = changed_part)
        ```
        """
        return changed_part in self.__class__.ALL_CHANGED_PARTS

    def set_changed(self, changed: bool | CHANGED_PARTS | Iterable[CHANGED_PARTS]):
        """
        Проверяет и сохраняет значение `changed`.

        ### Аргументы:
        :param changed: список успешно изменённых элементов

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        message.set_changed(changed = changed)
        ```
        """
        if isinstance(changed, bool):
            if changed:
                if self.was_sent():
                    self.changed = set(self.__class__.ALL_CHANGED_PARTS)
            else:
                self.changed.clear()
        elif isinstance(changed, str):
            if not self.check_changed_part(changed):
                raise ValueError(f"Некорректное значение аргумента {changed=}")
            elif self.was_sent():
                self.changed.add(changed)
        elif is_iterable(changed):
            changed_parts: list[CHANGED_PARTS] = list(changed)

            for changed_part in changed_parts:
                if not self.check_changed_part(changed_part):
                    raise ValueError(f"Некорректное значение аргумента {changed=}")

            if self.was_sent():
                self.changed.update(changed_parts)
        else:
            raise ValueError(f"Некорректное значение аргумента {changed=}")

    def get_changed_parts(self) -> set[CHANGED_PARTS]:
        """
        Возвращает набор частей сообщения, изменённых после отправки.

        :return: changed parts

        ### Пример использования:
        ```py
        message.get_changed_parts()
        ```
        """
        if self.was_sent():
            return set(self.changed)
        else:
            return set()

    def was_changed(self, changed_part: CHANGED_PARTS | None = None) -> bool:
        """
        Проверяет, отличается ли новое представление сообщения от уже отправленного.

        ### Аргументы:
        :param changed_part: часть сообщения, которую нужно проверить на изменение

        :return: `True`, если отличается ли новое представление сообщения от уже отправленного; иначе `False`

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        message.was_changed(changed_part = changed_part)
        ```
        """
        if not self.was_sent():
            return False
        elif changed_part is None:
            return bool(self.changed)
        elif self.check_changed_part(changed_part):
            return changed_part in self.changed
        else:
            raise ValueError(f"Некорректное значение аргумента {changed_part=}")


    def check_keyboard(self, keyboard: Bot.Keyboard) -> bool:
        """
        Проверяет клавиатуру сообщения.

        ### Аргументы:
        :param keyboard: клавиатура

        :return: `True`, если передан `Bot.Keyboard`; иначе `False`

        ### Пример использования:
        ```py
        message.check_keyboard(keyboard = keyboard)
        ```
        """
        return isinstance(keyboard, Bot.Keyboard)

    def set_keyboard(self, keyboard: Bot.Keyboard | None):
        """
        Проверяет и сохраняет клавиатуру сообщения в состоянии `Message`.

        ### Аргументы:
        :param keyboard: клавиатура wrapper-сообщения

        :raises ValueError: если значение не проходит локальную проверку перед сохранением

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
            if not self.compare_keyboards(self.keyboard, keyboard):
                self.set_changed(self.__class__.CHANGED_REPLY_MARKUP)
            self.keyboard = keyboard
        else:
            raise ValueError(f"Некорректное значение аргумента {keyboard=}")

    def get_keyboard(self) -> Bot.Keyboard | None:
        """
        Возвращает сохранённую клавиатуру сообщения.

        :return: клавиатура сообщения

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        message.get_keyboard()
        ```
        """
        if self.keyboard is None:
            return None
        elif self.check_keyboard(self.keyboard):
            return self.keyboard
        else:
            raise ValueError(f"Некорректное значение атрибута {self.keyboard=}")

    def clear_keyboard(self):
        """
        Убирает клавиатуру из wrapper-сообщения.

        ### Пример использования:
        ```py
        message.clear_keyboard()
        ```
        """
        if self.keyboard:
            buttons: list[Bot.Keyboard.Button] = []

            for button in self.keyboard.buttons:
                button.set_url(None)
                button.set_callback_data(";")
                buttons.append(button)

            self.keyboard.update(buttons)


    def check_attachments(self, attachments: Iterable[Bot.Attachment]) -> bool:
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
        return is_iterable(attachments) and all(isinstance(attachment, Bot.Attachment) and attachment.check() for attachment in attachments)

    def set_attachments(self, attachments: Iterable[Bot.Attachment]):
        """
        Проверяет и сохраняет вложения сообщения в состоянии `Message`.

        ### Аргументы:
        :param attachments: вложения wrapper-сообщения

        :raises ValueError: если значение не проходит локальную проверку перед сохранением

        ### Пример использования:
        ```py
        message.set_attachments(attachments = attachments)
        ```
        """
        attachments_list: list[Bot.Attachment] = list(attachments)

        if self.check_attachments(attachments_list):
            if not self.compare_attachments_list(self.attachments, attachments_list):
                self.set_changed(self.__class__.CHANGED_MEDIA)
            self.attachments = attachments_list
        else:
            raise ValueError(f"Некорректное значение аргумента {attachments=}")

    def get_attachments(self) -> list[Bot.Attachment]:
        """
        Возвращает сохранённые вложения сообщения.

        :return: вложения сообщения

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        message.get_attachments()
        ```
        """
        if self.check_attachments(self.attachments):
            return self.attachments
        else:
            raise ValueError(f"Некорректное значение атрибута {self.attachments=}")


    def check_reply(self, reply: Bot.BaseMessage) -> bool:
        """
        Проверяет reply-сообщение.

        ### Аргументы:
        :param reply: сообщение, на которое дан ответ

        :return: `True`, если reply является корректным `Bot.BaseMessage`; иначе `False`

        ### Пример использования:
        ```py
        message.check_reply(reply = reply)
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
        message.set_reply(reply = reply)
        ```
        """
        if reply is None:
            if not self.__class__.compare_messages(self.reply, reply):
                self.set_changed(self.__class__.CHANGED_REPLY)
            self.reply = None
        elif hasattr(self, "forward_messages") and self.forward_messages:
            raise ValueError(f"Некорректное значение атрибута {self.forward_messages=}. Невозможно отвечать на сообщение, если уже включены пересланные сообщения")
        elif self.check_reply(reply):
            if not self.__class__.compare_messages(self.reply, reply):
                self.set_changed(self.__class__.CHANGED_REPLY)
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
        message.get_reply()
        ```
        """
        if self.reply is None:
            return None
        elif self.forward_messages:
            raise ValueError(f"Некорректное значение атрибута {self.forward_messages=}. Невозможно отвечать на сообщение, если уже включены пересланные сообщения")
        elif self.check_reply(self.reply):
            return self.reply
        else:
            raise ValueError(f"Некорректное значение атрибута {self.reply=}")


    def check_forward(self, forward: Iterable[Bot.BaseMessage]) -> bool:
        """
        Проверяет список forward-сообщений.

        ### Аргументы:
        :param forward: пересылаемые сообщения

        :return: `True`, если значение является iterable из `Bot.BaseMessage`; иначе `False`

        ### Пример использования:
        ```py
        message.check_forward(forward = forward)
        ```
        """
        return is_iterable(forward) and all(isinstance(message, Bot.BaseMessage) for message in forward)

    def set_forward(self, forward: Iterable[Bot.BaseMessage]):
        """
        Проверяет и сохраняет пересылаемое сообщение в объекте.

        ### Аргументы:
        :param forward: пересылаемое сообщение

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        message.set_forward(forward = forward)
        ```
        """
        forward_list: list[Bot.BaseMessage] = list(forward)

        if self.check_forward(forward_list):
            if forward_list and self.reply:
                raise ValueError(f"Некорректное значение атрибута {self.reply=}. Невозможно пересылать сообщения в ответ на сообщение")
            else:
                if not self.compare_messages_list(self.forward_messages, forward_list):
                    self.set_changed(self.__class__.CHANGED_FORWARD)
                self.forward_messages = forward_list
        else:
            raise ValueError(f"Некорректное значение аргумента {forward=} для\n{self}")

    def get_forward(self) -> list[Bot.BaseMessage]:
        """
        Возвращает сохранённое forward-сообщение.

        :return: пересылаемое сообщение

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        message.get_forward()
        ```
        """
        if self.check_forward(self.forward_messages):
            if self.forward_messages and self.reply:
                raise ValueError(f"Некорректное значение атрибута {self.reply=}. Невозможно пересылать сообщения в ответ на сообщение")
            else:
                return self.forward_messages
        else:
            raise ValueError(f"Некорректное значение атрибута {self.forward_messages=}")


    def check_text(self, text: str) -> bool:
        """
        Проверяет текст сообщения.

        ### Аргументы:
        :param text: текст

        :return: `True`, если передана строка; иначе `False`

        ### Пример использования:
        ```py
        message.check_text(text = text)
        ```
        """
        return isinstance(text, str)

    def set_text(self, text: str):
        """
        Проверяет и сохраняет значение `text` в `Message`.

        ### Аргументы:
        :param text: текст сообщения или пользовательского ввода

        :raises ValueError: если значение не проходит локальную проверку перед сохранением

        ### Пример использования:
        ```py
        message.set_text(text = text)
        ```
        """
        if self.check_text(text):
            old_text: str = str(getattr(self, "text", "")).strip()
            new_text: str = str(text).strip()

            if old_text != new_text:
                attachments: list[Bot.Attachment] = getattr(self, "attachments", [])
                changed_part: CHANGED_PARTS = self.__class__.CHANGED_CAPTION if attachments else self.__class__.CHANGED_TEXT
                self.set_changed(changed_part)
            self.text = text
        elif isinstance(text, str):
            raise ValueError(f"Пустой текст сообщения не допускается, если нет кнопок или вложений")
        else:
            raise ValueError(f"Некорректное значение аргумента {text=}")

    def get_text(self) -> str:
        """
        Возвращает сохранённый текст сообщения.

        :return: текст текущего сообщения

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        message.get_text()
        ```
        """
        if self.check_text(self.text):
            return str(self.text).strip()
        elif isinstance(self.text, str):
            raise ValueError(f"Пустой текст сообщения не допускается, если нет кнопок или вложений")
        else:
            raise ValueError(f"Некорректное значение атрибута {self.text=}")
