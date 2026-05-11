"""
Описывает URL-вложение для конкретного транспорта.
Модуль относится к архитектурной зоне: слой унификации транспортов `bots`, который скрывает различия Telegram и VK за общими объектами сообщений, клавиатур, вложений и событий.

### Публичные классы
- `UrlAttachment`: модель URL-вложения сообщения.

### Публичные функции
- Публичные функции отсутствуют.

### Связи
Используется транспортным слоем и wrapper-логикой, чтобы app-layer работал с `Message`, `Keyboard`, `Button`, `Attachment` и `Event` без привязки к конкретной соцсети.
"""

from __future__ import annotations


from bots.utils.mapping import get_from, get_int
from bots.compat import BotTypes, DotDict, Literal, warn
from bots.types import ATTACHMENT_TYPE, Literal

from bots.base.bindings import Bot
from bots.base.attachment import Attachment as BaseAttachment
from bots.base.button import Button as BaseButton
from bots.base.keyboard import Keyboard as BaseKeyboard
from bots.base.message import Message as BaseMessageClass
from bots.base.voice_message import VoiceMessage as BaseVoiceMessage

class UrlAttachment():
    """
    VK-ссылка из payload вложения `link`.
    В отличие от файловых вложений не имеет локального filename и не скачивается:
    объект хранит URL и metadata, которые VK прислал вместе с сообщением.

    ### Поля
    - `ATTACHMENT_TYPE`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.
    - `height`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.
    - `width`: идентификатор объекта или связанной сущности, по которому runtime восстанавливает связь между слоями.
    - `url`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.
    - `type`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.
    - `with_padding`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.

    ### Методы
    - `__init__`: Создаёт объект и сохраняет данные, нужные transport-layer для отправки, сравнения или восстановления объекта.
    - `dumps`: Возвращает JSON-совместимый снимок объекта для storage или callback payload.

    ### Жизненный цикл
    Экземпляры создаются из конфигурации транспорта, принимают события платформы и отдают app-layer унифицированные wrapper-объекты.

    ### Пример использования
    ```py
    urlAttachment: UrlAttachment
    ```
    """
    ATTACHMENT_TYPE = BotTypes.ATTACHMENT_TYPE

    def __init__(self, attachment: DotDict | dict):
        """
        Создаёт `UrlAttachment` и сохраняет данные, нужные transport-layer для отправки, сравнения или восстановления объекта.

        ### Аргументы:
        :param attachment: вложение wrapper-сообщения

        ### Пример использования:
        ```py
        urlAttachment: UrlAttachment = UrlAttachment(attachment = attachment)
        ```
        """
        self.height: int = get_int(attachment, -1, "height")
        self.width: int = get_int(attachment, -1, "width")
        self.url: str = get_from(attachment, "url", types = (str,), default = "")

        self.type: Literal["s", "m", "x", "o", "p", "r", "base"]  | str = get_from(attachment, "type", types = (str,), default = "")
        self.with_padding: bool | None = get_from(attachment, "video", "can_dislike", default = None)

        if type(self.with_padding) is int:
            self.with_padding = bool(self.with_padding)

        if not self.type:
            self.type = ""

        if self.height < 0:
            warn("Некорректное значение поля attachment.height или attachment['height']")
            self.height = 0

        if self.width < 0:
            warn("Некорректное значение поля attachment.width или attachment['width']")
            self.width = 0

        if not self.url:
            warn("Некорректное значение поля attachment.url или attachment['url']")
            self.url = ""

    def dumps(self) -> ATTACHMENT_TYPE:
        """
        Возвращает JSON-совместимый снимок объекта для storage или callback payload.

        :return: JSON-совместимый словарь для сохранения или передачи между слоями

        ### Пример использования:
        ```py
        urlAttachment.dumps()
        ```
        """
        result: "Vkbot.UrlAttachment.ATTACHMENT_TYPE" = {}

        if isinstance(self.height, int) and self.height > 0:
            result["height"] = self.height

        if isinstance(self.width, int) and self.width > 0:
            result["width"] = self.width

        if isinstance(self.url, str) and self.url:
            result["url"] = self.url

        if isinstance(self.type, str) and self.type:
            result["type"] = self.type

        return result
