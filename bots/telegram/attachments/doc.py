"""
Описывает документ-вложение для конкретного транспорта.
Модуль относится к архитектурной зоне: слой унификации транспортов `bots`, который скрывает различия Telegram и VK за общими объектами сообщений, клавиатур, вложений и событий.

### Публичные классы
- `DocAttachment`: модель документа-вложения сообщения.

### Публичные функции
- Публичные функции отсутствуют.

### Связи
Используется транспортным слоем и wrapper-логикой, чтобы app-layer работал с `Message`, `Keyboard`, `Button`, `Attachment` и `Event` без привязки к конкретной соцсети.
"""

from __future__ import annotations


from bots.utils.mapping import get_from, get_int
from bots.compat import (
    BotTypes,
    BytesIO,
    Document,
    InputMediaDocument,
    Literal,
    PhotoSize,
)
from bots.types import ATTACHMENT_TYPE, Literal

from bots.base.bindings import Bot
from bots.base.attachment import Attachment as BaseAttachment
from bots.base.button import Button as BaseButton
from bots.base.keyboard import Keyboard as BaseKeyboard
from bots.base.message import Message as BaseMessageClass
from bots.base.voice_message import VoiceMessage as BaseVoiceMessage

from bots.telegram.attachments.base import Attachment

class DocAttachment(Attachment):
    """
    Telegram-документ с исходным именем файла и миниатюрой.
    Класс хранит `file_id`, `file_name` и необязательный thumbnail, чтобы
    wrapper-сообщение могло сериализовать документ и повторно отправить его.

    ### Поля
    - `ATTACHMENT_TYPE`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.
    - `original_filename`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.
    - `attachment`: хранит вложение сообщения для операций этого объекта.
    - `thumb`: связанные сообщения или вложения, которые transport-layer использует при отправке, сравнении или редактировании.

    ### Методы
    - `from_filename`: Создаёт вложение из локального файла.
    - `from_bytes`: Создаёт вложение из байтового содержимого.
    - `loads`: Восстанавливает объект из JSON-совместимого словаря.
    - `__init__`: Создаёт объект и сохраняет данные, нужные transport-layer для отправки, сравнения или восстановления объекта.
    - `get_media_type`: Возвращает media type из текущего состояния `DocAttachment`.
    - `dumps`: Возвращает JSON-совместимый снимок объекта для storage или callback payload.

    ### Жизненный цикл
    Экземпляры создаются из конфигурации транспорта, принимают события платформы и отдают app-layer унифицированные wrapper-объекты.

    ### Пример использования
    ```py
    docAttachment: DocAttachment
    ```
    """
    ATTACHMENT_TYPE = BotTypes.ATTACHMENT_TYPE

    def from_filename(filename: str) -> Telebot.DocAttachment:
        """
        Создаёт вложение из локального файла.

        ### Аргументы:
        :param filename: имя файла

        :return: `DocAttachment` с установленным локальным filename

        ### Пример использования:
        ```py
        docAttachment.from_filename(filename = filename)
        ```
        """
        class Sentinel():
            """
            Временный объект `Sentinel` повторяет поля ответа SDK, чтобы переиспользовать общий parser без настоящего API-объекта.
            Временный объект повторяет поля Telegram `Document`, чтобы
            использовать общий конструктор без настоящего ответа SDK.

            ### Поля
            - `file_id`: идентификатор объекта или связанной сущности, по которому runtime восстанавливает связь между слоями.
            - `file_size`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.
            - `file_name`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.
            - `thumb`: связанные сообщения или вложения, которые transport-layer использует при отправке, сравнении или редактировании.

            ### Жизненный цикл
            Экземпляры создаются из конфигурации транспорта, принимают события платформы и отдают app-layer унифицированные wrapper-объекты.

            ### Пример использования
            ```py
            sentinel: Sentinel
            ```
            """
            file_id: Literal[""] = ""
            file_size: Literal[0] = 0
            file_name: Literal[None] = None
            thumb: Literal[None] = None

        attachment: Telebot.DocAttachment = Telebot.DocAttachment(Sentinel)
        attachment.set_filename(filename)
        return attachment

    def from_bytes(data: BytesIO) -> Telebot.DocAttachment:
        """
        Создаёт вложение из байтового содержимого.

        ### Аргументы:
        :param data: сериализованный словарь

        :return: `DocAttachment` с байтами документа в `data`

        ### Пример использования:
        ```py
        docAttachment.from_bytes(data = data)
        ```
        """
        class Sentinel():
            """
            Временный объект `Sentinel` повторяет поля ответа SDK, чтобы переиспользовать общий parser без настоящего API-объекта.
            Временный объект повторяет поля Telegram `Document`, чтобы
            использовать общий конструктор без настоящего ответа SDK.

            ### Поля
            - `file_id`: идентификатор объекта или связанной сущности, по которому runtime восстанавливает связь между слоями.
            - `file_size`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.
            - `file_name`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.
            - `thumb`: связанные сообщения или вложения, которые transport-layer использует при отправке, сравнении или редактировании.

            ### Жизненный цикл
            Экземпляры создаются из конфигурации транспорта, принимают события платформы и отдают app-layer унифицированные wrapper-объекты.

            ### Пример использования
            ```py
            sentinel: Sentinel
            ```
            """
            file_id: Literal[""] = ""
            file_size: Literal[0] = 0
            file_name: Literal[None] = None
            thumb: Literal[None] = None

        attachment: Telebot.DocAttachment = Telebot.DocAttachment(Sentinel)
        attachment.data = data
        return attachment

    def loads(data: ATTACHMENT_TYPE) -> Telebot.DocAttachment:
        """
        Восстанавливает объект из JSON-совместимого словаря.

        ### Аргументы:
        :param data: сериализованный словарь

        :return: восстановленный объект или загруженное состояние

        ### Пример использования:
        ```py
        docAttachment.loads(data = data)
        ```
        """
        attachment: "Telebot.DocAttachment.ATTACHMENT_TYPE" = get_from(data, "attachment")

        class SentinelThumb():
            """
            Временный объект `SentinelThumb` повторяет поля ответа SDK, чтобы переиспользовать общий parser без настоящего API-объекта.
            Временный объект повторяет поля thumbnail, сохранённые в JSON.

            ### Поля
            - `file_id`: идентификатор объекта или связанной сущности, по которому runtime восстанавливает связь между слоями.
            - `id`: внутренний идентификатор записи или доменного объекта.
            - `size`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.
            - `width`: идентификатор объекта или связанной сущности, по которому runtime восстанавливает связь между слоями.
            - `height`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.

            ### Жизненный цикл
            Экземпляры создаются из конфигурации транспорта, принимают события платформы и отдают app-layer унифицированные wrapper-объекты.

            ### Пример использования
            ```py
            sentinelThumb: SentinelThumb
            ```
            """
            file_id: str = get_from(attachment, "id")
            id: str = get_from(attachment, "id")
            size: int = get_int(attachment, -1, "size")
            width: int = get_int(attachment, -1, "width")
            height: int = get_int(attachment, -1, "height")

        class Sentinel():
            """
            Временный объект `Sentinel` повторяет поля ответа SDK, чтобы переиспользовать общий parser без настоящего API-объекта.
            Временный объект повторяет поля Telegram `Document`, сохранённые
            в JSON-снимке вложения.

            ### Поля
            - `file_id`: идентификатор объекта или связанной сущности, по которому runtime восстанавливает связь между слоями.
            - `id`: внутренний идентификатор записи или доменного объекта.
            - `size`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.
            - `file_name`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.
            - `thumb`: связанные сообщения или вложения, которые transport-layer использует при отправке, сравнении или редактировании.

            ### Жизненный цикл
            Экземпляры создаются из конфигурации транспорта, принимают события платформы и отдают app-layer унифицированные wrapper-объекты.

            ### Пример использования
            ```py
            sentinel: Sentinel
            ```
            """
            file_id: str = get_from(data, "id")
            id: str = get_from(data, "id")
            size: int = get_int(data, -1, "size")
            file_name: str = get_from(data, "original_filename")
            thumb: SentinelThumb = SentinelThumb

        filename: str = get_from(data, "filename")

        attachment: Telebot.DocAttachment = Telebot.DocAttachment(Sentinel)
        if filename:
            attachment.set_filename(filename)
        return attachment

    def __init__(self, attachment: Document):
        """
        Создаёт `DocAttachment` и сохраняет данные, нужные transport-layer для отправки, сравнения или восстановления объекта.

        ### Аргументы:
        :param attachment: вложение wrapper-сообщения

        ### Пример использования:
        ```py
        docAttachment: DocAttachment = DocAttachment(attachment = attachment)
        ```
        """
        super().__init__(attachment)
        self.original_filename: str = attachment.file_name or ""
        self.attachment: Telebot.PhotoAttachment | None = None

        thumb: PhotoSize | None = attachment.thumb
        if thumb is None or isinstance(thumb, PhotoSize):
            if thumb:
                self.attachment = Telebot.PhotoAttachment(thumb)

    def get_media_type(self) -> type[InputMediaDocument]:
        """
        Возвращает media type для Telegram media group.

        :return: media type

        ### Пример использования:
        ```py
        docAttachment.get_media_type()
        ```
        """
        return InputMediaDocument

    def dumps(self) -> ATTACHMENT_TYPE:
        """
        Возвращает JSON-совместимый снимок объекта для storage или callback payload.

        :return: JSON-совместимый словарь для сохранения или передачи между слоями

        ### Пример использования:
        ```py
        docAttachment.dumps()
        ```
        """
        result: "Telebot.DocAttachment.ATTACHMENT_TYPE" = super().dumps()

        result.update({
            "original_filename": str(self.original_filename),
            "attachment": self.attachment.dumps() if self.attachment is not None else None
        })

        return result
