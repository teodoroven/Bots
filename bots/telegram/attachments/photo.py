"""
Описывает фотовложение для конкретного транспорта.
Модуль относится к архитектурной зоне: слой унификации транспортов `bots`, который скрывает различия Telegram и VK за общими объектами сообщений, клавиатур, вложений и событий.

### Публичные классы
- `PhotoAttachment`: модель фотовложения сообщения.

### Публичные функции
- Публичные функции отсутствуют.

### Связи
Используется транспортным слоем и wrapper-логикой, чтобы app-layer работал с `Message`, `Keyboard`, `Button`, `Attachment` и `Event` без привязки к конкретной соцсети.
"""

from __future__ import annotations


from bots.constants import logger_telegram
from bots.utils.files import only_extension
from bots.utils.mapping import get_from, get_int
from bots.compat import (
    BotTypes,
    BytesIO,
    Image,
    InputMediaPhoto,
    Iterable,
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

class PhotoAttachment(Attachment):
    """
    Telegram-фото с размером изображения и вариантами, которые присылает API.
    Хранит основной `PhotoSize`, список альтернативных размеров, умеет
    восстановиться из JSON-снимка и сохранять загруженное изображение через PIL.

    ### Поля
    - `ATTACHMENT_TYPE`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.
    - `width`: идентификатор объекта или связанной сущности, по которому runtime восстанавливает связь между слоями.
    - `height`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.
    - `attachments`: хранит вложения сообщения для операций этого объекта.
    - `attachment`: хранит вложение сообщения для операций этого объекта.

    ### Методы
    - `from_filename`: Создаёт вложение из локального файла.
    - `from_bytes`: Создаёт вложение из байтового содержимого.
    - `loads`: Восстанавливает объект из JSON-совместимого словаря.
    - `__init__`: Создаёт объект и сохраняет данные, нужные transport-layer для отправки, сравнения или восстановления объекта.
    - `get_media_type`: Возвращает `InputMediaPhoto` для Telegram media group.
    - `dumps`: Возвращает JSON-совместимый снимок объекта для storage или callback payload.
    - `get_image`: Открывает загруженные байты как PIL-изображение.
    - `save_as`: Сохраняет загруженное изображение в файл.
    - `load_from`: Читает изображение из локального файла в память.

    ### Жизненный цикл
    Экземпляры создаются из конфигурации транспорта, принимают события платформы и отдают app-layer унифицированные wrapper-объекты.

    ### Пример использования
    ```py
    photoAttachment: PhotoAttachment
    ```
    """
    ATTACHMENT_TYPE = BotTypes.ATTACHMENT_TYPE

    def from_filename(filename: str) -> Telebot.PhotoAttachment:
        """
        Создаёт вложение из локального файла.

        ### Аргументы:
        :param filename: имя файла

        :return: `PhotoAttachment` с установленным локальным filename

        ### Пример использования:
        ```py
        photoAttachment.from_filename(filename = filename)
        ```
        """
        class Sentinel():
            """
            Временный объект `Sentinel` повторяет поля ответа SDK, чтобы переиспользовать общий parser без настоящего API-объекта.
            Временный объект повторяет поля Telegram `PhotoSize`, чтобы
            использовать общий конструктор без настоящего ответа SDK.

            ### Поля
            - `file_id`: идентификатор объекта или связанной сущности, по которому runtime восстанавливает связь между слоями.
            - `file_size`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.
            - `width`: идентификатор объекта или связанной сущности, по которому runtime восстанавливает связь между слоями.
            - `height`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.

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

        attachment: Telebot.PhotoAttachment = Telebot.PhotoAttachment(Sentinel)
        attachment.set_filename(filename)
        logger_telegram.info("uploaded %s", filename)
        return attachment

    def from_bytes(data: BytesIO) -> Telebot.PhotoAttachment:
        """
        Создаёт вложение из байтового содержимого.

        ### Аргументы:
        :param data: сериализованный словарь

        :return: `PhotoAttachment` с байтами изображения в `data`

        ### Пример использования:
        ```py
        photoAttachment.from_bytes(data = data)
        ```
        """
        class Sentinel():
            """
            Временный объект `Sentinel` повторяет поля ответа SDK, чтобы переиспользовать общий parser без настоящего API-объекта.
            Временный объект повторяет поля Telegram `PhotoSize`, чтобы
            использовать общий конструктор без настоящего ответа SDK.

            ### Поля
            - `file_id`: идентификатор объекта или связанной сущности, по которому runtime восстанавливает связь между слоями.
            - `file_size`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.
            - `width`: идентификатор объекта или связанной сущности, по которому runtime восстанавливает связь между слоями.
            - `height`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.

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

        attachment: Telebot.PhotoAttachment = Telebot.PhotoAttachment(Sentinel)
        attachment.data = data
        return attachment

    def loads(data: ATTACHMENT_TYPE) -> Telebot.PhotoAttachment:
        """
        Восстанавливает объект из JSON-совместимого словаря.

        ### Аргументы:
        :param data: сериализованный словарь

        :return: восстановленный объект или загруженное состояние

        ### Пример использования:
        ```py
        photoAttachment.loads(data = data)
        ```
        """
        class Sentinel():

            """
            Временный объект `Sentinel` повторяет поля ответа SDK, чтобы переиспользовать общий parser без настоящего API-объекта.
            Временный объект повторяет поля Telegram `PhotoSize`, чтобы
            восстановить вложение из сериализованного словаря.

            ### Поля
            - `file_id`: идентификатор объекта или связанной сущности, по которому runtime восстанавливает связь между слоями.
            - `size`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.
            - `width`: идентификатор объекта или связанной сущности, по которому runtime восстанавливает связь между слоями.
            - `height`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.

            ### Методы
            - `__init__`: Создаёт объект и сохраняет данные, нужные transport-layer для отправки, сравнения или восстановления объекта.

            ### Жизненный цикл
            Экземпляры создаются из конфигурации транспорта, принимают события платформы и отдают app-layer унифицированные wrapper-объекты.

            ### Пример использования
            ```py
            sentinel: Sentinel
            ```
            """
            def __init__(self, data: dict[str, str | int]):
                """
                Создаёт `Sentinel` и сохраняет данные, нужные transport-layer для отправки, сравнения или восстановления объекта.

                ### Аргументы:
                :param data: JSON-совместимые данные для соответствующего repository

                ### Пример использования:
                ```py
                sentinel: Sentinel = Sentinel(data = data)
                ```
                """
                self.file_id: str = get_from(data, "id")
                self.size: int = get_int(data, -1, "size")
                self.width: int = get_int(data, -1, "width")
                self.height: int = get_int(data, -1, "height")

        filename: str = get_from(data, "filename")

        attachments_list: list[dict[str, str | int]] = get_from(data, "attachments")
        attachments: list[Sentinel] = [Sentinel(attachment) for attachment in attachments_list]

        sentinel = Sentinel(data)
        attachment: Telebot.PhotoAttachment = Telebot.PhotoAttachment(sentinel, attachments)
        if filename:
            attachment.set_filename(filename)
        return attachment

    def __init__(self, attachment: PhotoSize, sizes: Iterable[PhotoSize] = []):
        """
        Создаёт вложение `PhotoAttachment` и сохраняет transport-данные, нужные для отправки или восстановления сообщения.

        ### Аргументы:
        :param attachment: вложение
        :param sizes: варианты размеров изображения

        ### Пример использования:
        ```py
        photoAttachment = PhotoAttachment(attachment = attachment, sizes = sizes)
        ```
        """
        super().__init__(attachment)
        self.width: int = int(attachment.width)
        self.height: int = int(attachment.height)
        self.attachments: list[Telebot.PhotoAttachment] = []

        for photo in sizes:
            attachment: Telebot.PhotoAttachment = self.__class__(photo)
            self.attachments.append(attachment)

        """
        saved_files['photo']: int = file_id
        bot.send_photo(message.chat.id, saved_files['photo'], caption="Вот ваше сохраненное фот
        """

    def get_media_type(self) -> type[InputMediaPhoto]:
        """
        Возвращает media type для Telegram media group.

        :return: media type

        ### Пример использования:
        ```py
        photoAttachment.get_media_type()
        ```
        """
        return InputMediaPhoto

    def dumps(self) -> ATTACHMENT_TYPE:
        """
        Возвращает JSON-совместимый снимок объекта для storage или callback payload.

        :return: JSON-совместимый словарь для сохранения или передачи между слоями

        ### Пример использования:
        ```py
        photoAttachment.dumps()
        ```
        """
        result: "Telebot.PhotoAttachment.ATTACHMENT_TYPE" = super().dumps()

        result.update({
            "width": int(self.width),
            "height": int(self.height),
            "attachments": [attachment.dumps() for attachment in self.attachments]
        })

        return result

    def get_image(self) -> Image:
        """
        Открывает загруженное фото как PIL-изображение.

        :return: image

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        photoAttachment.get_image()
        ```
        """
        if not self.check():
            raise ValueError(f"Некорректное значение атрибута {self.data=}. Перед получением необходимо загрузить файл методом download.")

        self.data.seek(0)
        return Image.open(self.data)

    def save_as(self, filename: str, img_format: Literal["jpeg", "jpg", "png", "bmp", "gif"] = ""):
        """
        Сохраняет загруженное фото в файл.

        ### Аргументы:
        :param filename: имя файла
        :param img_format: img format

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        photoAttachment.save_as(filename = filename, img_format = img_format)
        ```
        """
        if not self.check():
            raise ValueError(f"Некорректное значение атрибута {self.data=}. Перед сохранением необходимо загрузить файл методом download.")

        if not img_format:
            extension: str = only_extension(filename).lower()

            if extension in (".jpeg", ".jpg", ".png", ".bmp", ".gif"):
                img_format = extension[1:]
            else:
                img_format = ".jpeg"

        if img_format not in ("jpeg", "jpg", "png", "bmp", "gif"):
            raise ValueError(f"Некорректное значение аргумента {img_format=}. Поддерживаются только форматы jpeg, jpg, png, bmp и gif.")

        self.data.seek(0)

        with Image.open(self.data) as img:
            img.save(filename, format = img_format)

    def load_from(self, filename: str):
        """
        Читает локальное изображение и сохраняет его байты в `self.data`.

        ### Аргументы:
        :param filename: имя файла

        ### Пример использования:
        ```py
        photoAttachment.load_from(filename = filename)
        ```
        """
        with Image.open(filename) as img:
            self.data = BytesIO()
            img.save(self.data, format = img.format)
            self.data.seek(0)
