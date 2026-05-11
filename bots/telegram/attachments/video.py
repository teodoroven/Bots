"""
Описывает видеовложение для конкретного транспорта.
Модуль относится к архитектурной зоне: слой унификации транспортов `bots`, который скрывает различия Telegram и VK за общими объектами сообщений, клавиатур, вложений и событий.

### Публичные классы
- `VideoAttachment`: модель видеовложения сообщения.

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
    InputMediaVideo,
    Literal,
    PhotoSize,
    Video,
)
from bots.types import ATTACHMENT_TYPE, Literal

from bots.base.bindings import Bot
from bots.base.attachment import Attachment as BaseAttachment
from bots.base.button import Button as BaseButton
from bots.base.keyboard import Keyboard as BaseKeyboard
from bots.base.message import Message as BaseMessageClass
from bots.base.voice_message import VoiceMessage as BaseVoiceMessage

from bots.telegram.attachments.base import Attachment

class VideoAttachment(Attachment):
    """
    Telegram-видео с размером, длительностью и thumbnail.
    Класс хранит поля `Video` из Telegram API, сериализует их для wrapper-сообщений
    и открывает уже загруженные байты через OpenCV-compatible `VideoCapture`.

    ### Поля
    - `ATTACHMENT_TYPE`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.
    - `width`: идентификатор объекта или связанной сущности, по которому runtime восстанавливает связь между слоями.
    - `height`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.
    - `duration`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.
    - `thumb`: связанные сообщения или вложения, которые transport-layer использует при отправке, сравнении или редактировании.
    - `attachment`: хранит вложение сообщения для операций этого объекта.

    ### Методы
    - `from_filename`: Создаёт вложение из локального файла.
    - `from_bytes`: Создаёт вложение из байтового содержимого.
    - `loads`: Восстанавливает объект из JSON-совместимого словаря.
    - `__init__`: Создаёт объект и сохраняет данные, нужные transport-layer для отправки, сравнения или восстановления объекта.
    - `get_media_type`: Возвращает `InputMediaVideo` для Telegram media group.
    - `dumps`: Возвращает JSON-совместимый снимок объекта для storage или callback payload.
    - `get_video`: Создаёт временный файл и возвращает `VideoCapture`.

    ### Жизненный цикл
    Экземпляры создаются из конфигурации транспорта, принимают события платформы и отдают app-layer унифицированные wrapper-объекты.

    ### Пример использования
    ```py
    videoAttachment: VideoAttachment
    ```
    """
    ATTACHMENT_TYPE = BotTypes.ATTACHMENT_TYPE

    def from_filename(filename: str) -> Telebot.VideoAttachment:
        """
        Создаёт вложение из локального файла.

        ### Аргументы:
        :param filename: имя файла

        :return: `VideoAttachment` с установленным локальным filename

        ### Пример использования:
        ```py
        videoAttachment.from_filename(filename = filename)
        ```
        """
        class Sentinel():
            """
            Временный объект `Sentinel` повторяет поля ответа SDK, чтобы переиспользовать общий parser без настоящего API-объекта.
            Временный объект повторяет поля Telegram `Video`, чтобы
            использовать общий конструктор без настоящего ответа SDK.

            ### Поля
            - `file_id`: идентификатор объекта или связанной сущности, по которому runtime восстанавливает связь между слоями.
            - `file_size`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.
            - `width`: идентификатор объекта или связанной сущности, по которому runtime восстанавливает связь между слоями.
            - `height`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.
            - `duration`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.
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
            width: Literal[0] = 0
            height: Literal[0] = 0
            duration: Literal[0] = 0
            thumb: None = None

        attachment: Telebot.VideoAttachment = Telebot.VideoAttachment(Sentinel)
        attachment.set_filename(filename)
        return attachment

    def from_bytes(data: BytesIO) -> Telebot.VideoAttachment:
        """
        Создаёт вложение из байтового содержимого.

        ### Аргументы:
        :param data: сериализованный словарь

        :return: `VideoAttachment` с байтами видео в `data`

        ### Пример использования:
        ```py
        videoAttachment.from_bytes(data = data)
        ```
        """
        class Sentinel():
            """
            Временный объект `Sentinel` повторяет поля ответа SDK, чтобы переиспользовать общий parser без настоящего API-объекта.
            Временный объект повторяет поля Telegram `Video`, чтобы
            использовать общий конструктор без настоящего ответа SDK.

            ### Поля
            - `file_id`: идентификатор объекта или связанной сущности, по которому runtime восстанавливает связь между слоями.
            - `file_size`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.
            - `width`: идентификатор объекта или связанной сущности, по которому runtime восстанавливает связь между слоями.
            - `height`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.
            - `duration`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.
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
            width: Literal[0] = 0
            height: Literal[0] = 0
            duration: Literal[0] = 0
            thumb: Literal[None] = None

        attachment: Telebot.VideoAttachment = Telebot.VideoAttachment(Sentinel)
        attachment.data = data
        return attachment

    def loads(data: ATTACHMENT_TYPE) -> Telebot.VideoAttachment:
        """
        Восстанавливает объект из JSON-совместимого словаря.

        ### Аргументы:
        :param data: сериализованный словарь

        :return: восстановленный объект или загруженное состояние

        ### Пример использования:
        ```py
        videoAttachment.loads(data = data)
        ```
        """
        attachment: "Telebot.VideoAttachment.ATTACHMENT_TYPE" = get_from(data, "attachment")

        class SentinelThumb():
            """
            Временный объект `SentinelThumb` повторяет поля ответа SDK, чтобы переиспользовать общий parser без настоящего API-объекта.
            Временный объект повторяет поля thumbnail, сохранённые в JSON.

            ### Поля
            - `file_id`: идентификатор объекта или связанной сущности, по которому runtime восстанавливает связь между слоями.
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
            size: int = get_int(attachment, -1, "size")
            width: int = get_int(attachment, -1, "width")
            height: int = get_int(attachment, -1, "height")

        class Sentinel():
            """
            Временный объект `Sentinel` повторяет поля ответа SDK, чтобы переиспользовать общий parser без настоящего API-объекта.
            Временный объект повторяет поля Telegram `Video`, сохранённые
            в JSON-снимке вложения.

            ### Поля
            - `file_id`: идентификатор объекта или связанной сущности, по которому runtime восстанавливает связь между слоями.
            - `size`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.
            - `width`: идентификатор объекта или связанной сущности, по которому runtime восстанавливает связь между слоями.
            - `height`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.
            - `duration`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.
            - `thumb`: связанные сообщения или вложения, которые transport-layer использует при отправке, сравнении или редактировании.

            ### Жизненный цикл
            Экземпляры создаются из конфигурации транспорта, принимают события платформы и отдают app-layer унифицированные wrapper-объекты.

            ### Пример использования
            ```py
            sentinel: Sentinel
            ```
            """
            file_id: str = get_from(data, "id")
            size: int = get_int(data, -1, "size")
            width: int = get_int(data, -1, "width")
            height: int = get_int(data, -1, "height")
            duration: int = get_int(data, -1, "height")
            thumb: SentinelThumb = SentinelThumb

        filename: str = get_from(data, "filename")

        attachment: Telebot.VideoAttachment = Telebot.VideoAttachment(Sentinel)
        if filename:
            attachment.set_filename(filename)
        return attachment

    def __init__(self, attachment: Video):
        """
        Создаёт `VideoAttachment` и сохраняет данные, нужные transport-layer для отправки, сравнения или восстановления объекта.

        ### Аргументы:
        :param attachment: вложение wrapper-сообщения

        ### Пример использования:
        ```py
        videoAttachment: VideoAttachment = VideoAttachment(attachment = attachment)
        ```
        """
        super().__init__(attachment)
        self.width: int = int(attachment.width)
        self.height: int = int(attachment.height)
        self.duration: int = int(attachment.duration)
        self.thumb: Telebot.PhotoAttachment | None = None

        thumb: PhotoSize | None = attachment.thumb
        if thumb is None or isinstance(thumb, PhotoSize):
            if thumb:
                self.attachment = Telebot.PhotoAttachment(thumb)

    def get_media_type(self) -> type[InputMediaVideo]:
        """
        Возвращает media type для Telegram media group.

        :return: media type

        ### Пример использования:
        ```py
        videoAttachment.get_media_type()
        ```
        """
        return InputMediaVideo

    def dumps(self) -> ATTACHMENT_TYPE:
        """
        Возвращает JSON-совместимый снимок объекта для storage или callback payload.

        :return: JSON-совместимый словарь для сохранения или передачи между слоями

        ### Пример использования:
        ```py
        videoAttachment.dumps()
        ```
        """
        result: "Telebot.VideoAttachment.ATTACHMENT_TYPE" = super().dumps()

        result.update({
            "width": int(self.width),
            "height": int(self.height),
            "duration": int(self.duration),
            "attachment": self.attachment.dumps() if self.attachment is not None else None
        })

        return result

    def get_video(self, temp_filename: str) -> VideoCapture:
        """
        Записывает загруженные байты во временный файл и открывает видео.

        ### Аргументы:
        :param temp_filename: путь временного файла, который можно передать в `VideoCapture`

        :return: объект `VideoCapture` для временного файла

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        videoAttachment.get_video(temp_filename = temp_filename)
        ```
        """
        if not self.check():
            raise ValueError(f"Некорректное значение атрибута {self.data=}. Перед получением необходимо загрузить файл методом download.")

        self.data.seek(0)
        with open(temp_filename, "wb") as file:
            file.write(self.data.read())

        return VideoCapture(temp_filename)  # .isOpened()
