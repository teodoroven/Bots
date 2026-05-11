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


from bots.constants import logger_vk
from bots.compat import (
    Iterable,
    Literal,
    TeleBot,
    VkApi,
    datetime,
    get_random_id,
    json,
    re,
)
from bots.types import BOT_KEY, Literal

from bots.base.bindings import Bot
from bots.base.attachment import Attachment as BaseAttachment
from bots.base.button import Button as BaseButton
from bots.base.keyboard import Keyboard as BaseKeyboard
from bots.base.message import Message as BaseMessageClass
from bots.base.voice_message import VoiceMessage as BaseVoiceMessage

class Message(BaseMessageClass):
    """
    VK-сообщение transport-layer.
    Класс хранит `peer_id`, `conversation_message_id`, `random_id`,
    вложения и клавиатуру, а отправку/редактирование/удаление выполняет через
    VK `messages.*` API.

    ### Поля
    - `EMPTY_TEXT`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.
    - `reply`: связанные сообщения или вложения, которые transport-layer использует при отправке, сравнении или редактировании.
    - `attachments`: хранит вложения сообщения для операций этого объекта.
    - `keyboard`: хранит клавиатуру сообщения для операций этого объекта.
    - `forward_messages`: связанные сообщения или вложения, которые transport-layer использует при отправке, сравнении или редактировании.
    - `random_id`: идентификатор объекта или связанной сущности, по которому runtime восстанавливает связь между слоями.
    - `vkbot`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.
    - `kwargs`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.

    ### Методы
    - `from_event`: Создаёт wrapper-сообщение из transport-события.
    - `__init__`: Создаёт объект и сохраняет данные, нужные transport-layer для отправки, сравнения или восстановления объекта.
    - `get_bot_key`: Возвращает ключ транспорта из текущего состояния `Message`.
    - `get_username`: Возвращает username из текущего состояния `Message`.
    - `get_json_request`: Возвращает json request из текущего состояния `Message`.
    - `send`: Отправляет сообщение или вложение через transport-layer.
    - `edit`: Обновляет уже отправленное сообщение, если транспорт позволяет редактирование.
    - `delete`: Удаляет отправленное сообщение через transport-layer.
    - `forward`: Пересылает сообщение в другой чат через transport-layer.
    - `reply`: Отправляет ответ на исходное сообщение.

    ### Жизненный цикл
    Экземпляры создаются из конфигурации транспорта, принимают события платформы и отдают app-layer унифицированные wrapper-объекты.

    ### Пример использования
    ```py
    message: Message
    ```
    """

    # Текст пустого сообщения (у пользователя текст не отображается, нужно для отправки кнопок без описания)
    EMPTY_TEXT: str = "ㅤ" # "&#00000013;"

    @classmethod
    def from_event(cls: type[Vkbot.Message], event: Bot.Event, bot: TeleBot):
        """
        Создаёт wrapper-сообщение из transport-события.

        ### Аргументы:
        :param event: transport-событие для обработки
        :param bot: transport-адаптер

        :return: `Vkbot.Message`, восстановленное из `Bot.Event`

        ### Пример использования:
        ```py
        Message.from_event(event = event, bot = bot)
        ```
        """
        message: Vkbot.Message = super().from_event(event, bot)
        message_id: None = Vkbot.get_message_id(event)
        message.set_id(message_id) if message_id is not None else None
        return message

    def __init__(self, vkbot: VkApi, owner_id: int, text: str, keyboard: Vkbot.Keyboard | None = None, forward: Iterable[Vkbot.Message] = [], reply: Vkbot.Message | None = None, attachments: Iterable[Vkbot.Attachment] = []):
        """
        Создаёт wrapper `Message` и сохраняет данные сообщения или события без привязки app-layer к SDK платформы.

        ### Аргументы:
        :param vkbot: VK transport-адаптер или API-клиент
        :param owner_id: идентификатор владельца сообщения
        :param text: текст
        :param keyboard: клавиатура
        :param forward: пересылаемое сообщение
        :param reply: сообщение, на которое дан ответ
        :param attachments: вложения

        ### Пример использования:
        ```py
        message = Message(vkbot = vkbot, owner_id = owner_id, text = text, keyboard = keyboard, forward = forward, reply = reply, attachments = attachments)
        ```
        """
        super().__init__(owner_id, text, keyboard, forward, reply, attachments)
        self.reply: Vkbot.Message | None
        self.attachments: list[Vkbot.Attachment]
        self.keyboard: Vkbot.Keyboard | None
        self.forward_messages: list[Vkbot.Message]

        # Случайный идентификатор сообщения нужен для отправки сообщения, должен быть уникальным (не повторяться среди сообщений, отправляемых одному пользователю), иначе сообщение до пользователя не дойдёт
        self.random_id: int | None = None  # Устанавливается при отправке

        # Бот, который будет отправлять сообщение
        self.vkbot: VkApi
        self.set_vkbot(vkbot)

        self.kwargs: dict[str, str] = {}

    def get_bot_key(self) -> BOT_KEY:
        """
        Возвращает ключ транспорта из текущего состояния `Message`.

        :return: строковый ключ транспорта, например `telebot` или `vkbot`

        ### Примеры вызова:
        ```py
        message.get_bot_key()
        ```
        """
        return "vkbot"

    def get_username(self) -> str | None:
        """
        Возвращает сохранённое имя пользователя.

        :return: имя пользователя в транспорте

        ### Пример использования:
        ```py
        message.get_username()
        ```
        """
        chat_id: int | None = self.get_chat_id()

        if chat_id is not None:
            return f"@id{chat_id}"
        else:
            return None


    def get_json_request(self, parse_mode: str = "") -> dict:
        """
        Возвращает payload для VK `messages.send`.

        ### Аргументы:
        :param parse_mode: режим разметки сообщения

        :return: json request

        ### Пример использования:
        ```py
        message.get_json_request(parse_mode = parse_mode)
        ```
        """
        format_data: str = ""
        text: str = self.get_text()

        if parse_mode:
            text, format_data = self.get_text_json()

        chat_id: int = self.get_chat_id()
        random_id: int = self.get_random_id()
        json_request: dict = {"user_id": chat_id, "message": text, "random_id": random_id}

        if format_data:
            json_request["format_data"] = format_data

        # Пересланные сообщения
        forward: dict = self.get_forward_json()

        # Ответ на сообщение
        reply: dict = self.get_reply_json()

        # Вложения
        attachments: dict = self.get_attachments_json()
        json_request.update(**attachments)

        # Кнопки
        keyboard: str = self.get_keyboard()

        if forward:
            json_request.update(**forward)
        elif reply:
            json_request.update(**reply)

        # Кнопки
        if keyboard:
            json_request.update(keyboard = self.get_keyboard_json())

        return json_request

    def send(self, chat_id: int, parse_mode: str = "") -> list[Vkbot.Message]:
        """
        Отправляет сообщение или вложение через transport-layer.

        ### Аргументы:
        :param chat_id: идентификатор чата
        :param parse_mode: режим разметки сообщения

        :return: список отправленных `Vkbot.Message` с VK ids

        ### Пример использования:
        ```py
        message.send(chat_id = chat_id, parse_mode = parse_mode)
        ```
        """
        self.kwargs = {
            "parse_mode": str(parse_mode)
        }

        # Сообщение может быть отправлено лишь единожды
        self.set_chat_id(chat_id)

        vkbot: VkApi = self.get_vkbot()

        # Формирование JSON
        json_request = self.get_json_request(parse_mode = parse_mode)

        try:
            # Отправка запроса
            response: int = vkbot.method("messages.send", json_request)
        except Exception as err:
            logger_vk.exception(f"Vkbot.Message.send {chat_id=} {err=}")
            return []

        # Распаковка ответа
        message_id: int = int(response)

        # Установка идентификатора сообщения после отправки
        self.set_id(message_id)

        self.set_changed(False)

        self.add_event(response, datetime.now(), self.__class__.SENT_KEY)

    def edit(self, prevent_resend: bool = False):
        """
        Обновляет уже отправленное сообщение, если транспорт позволяет редактирование.

        ### Аргументы:
        :param prevent_resend: prevent resend

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        message.edit(prevent_resend = prevent_resend)
        ```
        """
        if not self.was_changed():
            return

        if self.check_chat_id(self.chat_id):
            vkbot: VkApi = self.get_vkbot()
            message_id: int = self.get_id()
            chat_id: int = self.get_chat_id()

            json_request = self.get_json_request(**self.kwargs)
            json_request.update(peer_id = chat_id, message_id = message_id)

            if self.check_keyboard(self.keyboard) and not self.keyboard.check_editable():
                raise ValueError(f"Некорректное значение атрибута {self.keyboard=}. Невозможно редактировать сообщение с не inline-клавиатурой. Удалите её прежде чем редактировать сообщение")

            try:
                response = vkbot.method("messages.edit", json_request)  # <class 'int'> 1
            except Exception as err:
                logger_vk.exception(f"Vkbot.Message.edit {chat_id=} {message_id=} {err=}")
                return
            self.set_changed(False)
            self.add_event(response, datetime.now(), self.__class__.EDIT_KEY)
        else:
            raise ValueError(f"Некорректное значение атрибута {self.chat_id=}. Перед редактированием необходимо отправить сообщение.")

    def delete(self):
        """
        Удаляет отправленное сообщение через transport-layer.

        ### Пример использования:
        ```py
        message.delete()
        ```
        """
        vkbot: VkApi = self.get_vkbot()
        message_id: int = self.get_id()
        json_request: dict = {"message_ids": int(message_id), "delete_for_all": True}

        try:
            result: dict[str, int] = vkbot.method("messages.delete", json_request)  # <class 'dict'> {'34260': 1}
        except Exception as err:
            logger_vk.exception(f"Vkbot.Message.delete {message_id=} {err=}")
            return

        if result:
            if str(message_id) in result:
                if result[str(message_id)] != 1:
                    logger_vk.warning(f"Не удалось удалить сообщение {message_id=}")

        self.add_event(result, datetime.now(), self.__class__.DELETE_KEY)
        self.id = None
        self.chat_id = None
        self.random_id = None

    def forward(self, chat_id: int, message: Vkbot.Message | None) -> Vkbot.Message:
        """
        Пересылает сообщение в другой чат через transport-layer.

        ### Аргументы:
        :param chat_id: идентификатор чата
        :param message: сообщение проекта или сообщение конкретного транспорта

        :return: пересланное `Vkbot.Message`, созданное после `messages.send`

        ### Пример использования:
        ```py
        message.forward(chat_id = chat_id, message = message)
        ```
        """
        vkbot: VkApi = self.get_vkbot()

        if message:
            message.set_forward([self])
        else:
            # WARNING: owner_id может отличаться
            message: Vkbot.Message = Vkbot.Message(vkbot, self.owner_id, Vkbot.Message.EMPTY_TEXT, forward = [self])

        message.send(chat_id)
        return message

    def reply(self, chat_id: int, message: Vkbot.Message):
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
        vkbot: VkApi = self.get_vkbot()
        message.set_reply(self)
        message.send(chat_id)


    # Методы работы с полями


    def check_vkbot(self, vkbot: VkApi) -> bool:
        """
        Проверяет значение `vkbot` перед сохранением или использованием.

        ### Аргументы:
        :param vkbot: VK transport-адаптер или API-клиент

        :return: `True`, если значение `vkbot` перед сохранением или использованием; иначе `False`

        ### Пример использования:
        ```py
        message.check_vkbot(vkbot = vkbot)
        ```
        """
        return isinstance(vkbot, VkApi)

    def set_vkbot(self, vkbot: VkApi):
        """
        Проверяет и сохраняет значение `vkbot`.

        ### Аргументы:
        :param vkbot: VK transport-адаптер или API-клиент

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        message.set_vkbot(vkbot = vkbot)
        ```
        """
        if self.check_vkbot(vkbot):
            self.vkbot = vkbot
        else:
            raise ValueError(f"Некорректное значение аргумента {vkbot=}")

    def get_vkbot(self) -> VkApi:
        """
        Возвращает связанный VK transport-адаптер.

        :return: vkbot

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        message.get_vkbot()
        ```
        """
        if self.check_vkbot(self.vkbot):
            return self.vkbot
        else:
            raise ValueError(f"Некорректное значение атрибута {self.vkbot=}")


    def set_random_id(self):
        """
        Проверяет и сохраняет значение `random id` в `Message`.

        :raises ValueError: если значение не проходит локальную проверку перед сохранением

        ### Примеры вызова:
        ```py
        message.set_random_id()
        ```
        """
        if self.random_id is None:
            self.random_id = get_random_id()
        else:
            raise ValueError(f"Поле self.random_id уже содержит значение и не может быть установлено повторно. Сообщение может быть отправлено только один раз.")

    def get_random_id(self) -> int | None:
        """
        Возвращает `random_id`, использованный при отправке VK-сообщения.

        :return: random id

        ### Пример использования:
        ```py
        message.get_random_id()
        ```
        """
        if self.random_id is None:
            self.set_random_id()
        return int(self.random_id)


    # Переопределённые методы работы с полями


    def check_id(self, message_id: int) -> bool:
        """
        Проверяет допустимость идентификатора.

        ### Аргументы:
        :param message_id: идентификатор сообщения

        :return: `True`, если допустимость идентификатора; иначе `False`

        ### Пример использования:
        ```py
        message.check_id(message_id = message_id)
        ```
        """
        return isinstance(message_id, int)


    def get_text_json(self) -> tuple[str, str]:
        """
        Возвращает пару ключ/значение для текста VK send-запроса.

        :return: text json
        """
        format_items: list[dict[str, str | int]] = []
        plain_text: str = self.get_text()

        # Улучшенные регулярные выражения
        bold_pattern: re.Pattern = re.compile(r'\*(?P<text>[^*]+)\*')
        italic_pattern: re.Pattern = re.compile(r'_(?P<text>[^_]+)_')
        code_pattern: re.Pattern = re.compile(r'```(?P<text>[^`]+)```')

        def extract_spans(pattern: re.Pattern, fmt_type: str, s: str) -> tuple[str, list[dict[str, str | int]]]:
            items: list[dict[str, str | int]] = []
            result: str = ""
            last_idx: int = 0

            for match in pattern.finditer(s):
                start, end = match.span()
                inner_text: str = match.group("text")

                result += s[last_idx:start]
                item_offset: int = len(result)
                result += inner_text
                item_length: int = len(inner_text)

                items.append({
                    "offset": item_offset,
                    "length": item_length,
                    "type": fmt_type
                })
                last_idx = end

            result += s[last_idx:]
            return result, items

        # Измененный порядок обработки: сначала код, потом курсив, затем жирный
        plain_text, code_items = extract_spans(code_pattern, "code", plain_text)
        plain_text, italic_items = extract_spans(italic_pattern, "italic", plain_text)
        plain_text, bold_items = extract_spans(bold_pattern, "bold", plain_text)

        format_items = code_items + italic_items + bold_items
        format_items.sort(key=lambda x: x["offset"])

        format_data: dict[str, str | list[dict[str, str | int]]] = {
            "version": "1",
            "items": format_items
        }

        return plain_text, json.dumps(format_data)


    def check_reply(self, reply: Vkbot.Message) -> bool:
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

    def set_reply(self, reply: Vkbot.Message | None):
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

    def get_reply(self) -> Vkbot.Message | None:
        """
        Возвращает сохранённое reply-сообщение.

        :return: сообщение-ответ

        ### Пример использования:
        ```py
        message.get_reply()
        ```
        """
        return super().get_reply()

    def get_reply_json(self) -> dict[str, int]:
        """
        Возвращает параметры reply для VK send-запроса.

        :return: reply json

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        message.get_reply_json()
        ```
        """
        if self.reply is None:
            return {}
        elif self.forward_messages:
            raise ValueError(f"Некорректное значение атрибута {self.forward_messages=}. Невозможно отвечать на сообщение, если уже включены пересланные сообщения")
        elif self.check_reply(self.reply):
            return {
                "peer_id": self.reply.get_owner_id(),
                "reply_to": self.reply.get_id()
            }
        else:
            raise ValueError(f"Некорректное значение атрибута {self.reply=}")


    def check_attachments(self, attachments: Iterable[Vkbot.Attachment]) -> bool:
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
        return super().check_attachments(attachments) and len(attachments) <= self.__class__.MAX_ATTACHMENTS

    def set_attachments(self, attachments: Iterable[Vkbot.Attachment]):
        """
        Проверяет и сохраняет вложения сообщения в состоянии `Message`.

        ### Аргументы:
        :param attachments: вложения wrapper-сообщения

        :return: результат базового `set_attachments`; метод сохраняет VK-вложения

        ### Пример использования:
        ```py
        message.set_attachments(attachments = attachments)
        ```
        """
        return super().set_attachments(attachments)

    def get_attachments(self) -> list[Vkbot.Attachment]:
        """
        Возвращает сохранённые вложения сообщения.

        :return: вложения сообщения

        ### Пример использования:
        ```py
        message.get_attachments()
        ```
        """
        return super().get_attachments()

    def get_attachments_json(self) -> dict[str, str]:
        """
        Возвращает строку вложений для VK send-запроса.

        :return: attachments json

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        message.get_attachments_json()
        ```
        """
        if self.check_attachments(self.attachments):
            if self.attachments:
                return {"attachment": ",".join(tuple(map(str, self.attachments)))}
            else:
                return {}
        else:
            raise ValueError(f"Некорректное значение атрибута {self.attachments=}")


    def check_forward(self, forward: Iterable[Vkbot.Message]) -> bool:
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

    def set_forward(self, forward: Iterable[Vkbot.Message]):
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

    def get_forward(self) -> list[Vkbot.Message]:
        """
        Возвращает сохранённое forward-сообщение.

        :return: пересылаемое сообщение

        ### Пример использования:
        ```py
        message.get_forward()
        ```
        """
        return super().get_forward()

    def get_forward_json(self) -> dict[str, int | str]:
        """
        Возвращает параметры пересылки для VK send-запроса.

        :return: forward json

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        message.get_forward_json()
        ```
        """
        if self.forward_messages == []:
            return {}
        elif self.check_forward(self.forward_messages):
            return {
                "peer_id": self.forward_messages[0].get_owner_id(),
                "forward_messages": ",".join(str(message.get_id()) for message in self.forward_messages)
            }
        else:
            raise ValueError(f"Некорректное значение атрибута {self.forward_messages=}")


    def check_keyboard(self, keyboard: Vkbot.Keyboard) -> bool:
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

    def set_keyboard(self, keyboard: Vkbot.Keyboard | None):
        """
        Проверяет и сохраняет клавиатуру сообщения в состоянии `Message`.

        ### Аргументы:
        :param keyboard: клавиатура wrapper-сообщения

        :return: результат базового `set_keyboard`; метод сохраняет VK-клавиатуру

        ### Пример использования:
        ```py
        message.set_keyboard(keyboard = keyboard)
        ```
        """
        return super().set_keyboard(keyboard)

    def get_keyboard(self) -> Vkbot.Keyboard | None:
        """
        Возвращает сохранённую клавиатуру сообщения.

        :return: клавиатура сообщения

        ### Пример использования:
        ```py
        message.get_keyboard()
        ```
        """
        return super().get_keyboard()

    def get_keyboard_json(self) -> str | Literal[""]:
        """
        Возвращает JSON-представление VK-клавиатуры для send-запроса.

        :return: keyboard json

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        message.get_keyboard_json()
        ```
        """
        if self.keyboard is None:
            return ""
        elif self.check_keyboard(self.keyboard):
            return self.keyboard.get_keyboard()
        else:
            raise ValueError(f"Некорректное значение атрибута {self.keyboard=}")
