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


from bots.constants import logger_vk
from bots.utils.dates import get_date
from bots.utils.mapping import get_from, get_int
from bots.compat import BotTypes, DotDict, datetime, warn
from bots.types import ATTACHMENT_TYPE

from bots.base.bindings import Bot
from bots.base.attachment import Attachment as BaseAttachment
from bots.base.button import Button as BaseButton
from bots.base.keyboard import Keyboard as BaseKeyboard
from bots.base.message import Message as BaseMessageClass
from bots.base.voice_message import VoiceMessage as BaseVoiceMessage

from bots.vk.attachments.base import Attachment
from bots.vk.attachments.url import UrlAttachment

class PhotoAttachment(Attachment):
    """
    VK-фото с размерами и набором ссылок на разные варианты изображения.
    Для локального файла использует VK upload `photo_messages`, а для входящих
    событий хранит `owner_id/id/access_key` отдельно от `filename`.

    ### Поля
    - `ATTACHMENT_TYPE`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.
    - `owner_id`: владелец фотографии в VK.
    - `attachment_id`: id фотографии в VK.
    - `access_key`: ключ доступа к фотографии, если VK его вернул.
    - `date`: хранит доступную дату записи для операций этого объекта.
    - `sizes`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.
    - `text`: текстовое содержимое, которое показывается пользователю, отправляется в GPT или сохраняется в доменной модели.
    - `web_view_token`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.
    - `has_tags`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.
    - `orig_photo`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.

    ### Методы
    - `from_filename`: Создаёт вложение из локального файла.
    - `__init__`: Создаёт объект и сохраняет данные, нужные transport-layer для отправки, сравнения или восстановления объекта.
    - `dumps`: Возвращает JSON-совместимый снимок объекта для storage или callback payload.
    - `download_attachments`: Загружает файлы вложений из API транспорта.
    - `get_url`: Возвращает url из текущего состояния `PhotoAttachment`.

    ### Жизненный цикл
    Экземпляры создаются из конфигурации транспорта, принимают события платформы и отдают app-layer унифицированные wrapper-объекты.

    ### Пример использования
    ```py
    photoAttachment: PhotoAttachment
    ```
    """
    ATTACHMENT_TYPE = BotTypes.ATTACHMENT_TYPE

    def from_filename(filename: str, vkbot: Vkbot) -> Vkbot.Attachment:
        """
        Создаёт вложение из локального файла.

        ### Аргументы:
        :param filename: имя файла
        :param vkbot: VK transport-адаптер или API-клиент

        :return: VK `Attachment` с `photo{owner_id}_{id}_{access_key}` и локальным filename

        ### Пример использования:
        ```py
        photoAttachment.from_filename(filename = filename, vkbot = vkbot)
        ```
        """
        responses: list = vkbot.upload.photo_messages(filename)
        response: dict = responses[0]

        owner_id: int = get_int(response, -1, "owner_id")
        attachment_id = get_int(response, -1, "id")
        access_key: str = get_from(response, "access_key", types = (str,), default = "")

        attachment: Vkbot.Attachment = vkbot.__class__.Attachment("photo", owner_id, attachment_id, access_key)
        attachment.set_filename(filename)
        logger_vk.info("uploaded %s to %s", filename, attachment)
        return attachment

    def __init__(self, attachment: dict | DotDict):
        """
        Создаёт `PhotoAttachment` и сохраняет данные, нужные transport-layer для отправки, сравнения или восстановления объекта.

        ### Аргументы:
        :param attachment: вложение wrapper-сообщения

        ### Пример использования:
        ```py
        photoAttachment: PhotoAttachment = PhotoAttachment(attachment = attachment)
        ```
        """
        owner_id: str = get_from(attachment, "photo", "owner_id")
        attachment_id: str = get_from(attachment, "photo", "id")
        access_key: str = get_from(attachment, "photo", "access_key")

        super().__init__("photo", owner_id, attachment_id, access_key)

        self.date: datetime = get_date(attachment, "photo", "date")
        self.sizes: list[Vkbot.UrlAttachment] = []
        self.text: str = get_from(attachment, "photo", "text", types = (str,), default = None)
        self.web_view_token: str = get_from(attachment, "photo", "web_view_token", types = (str,), default = None)
        self.has_tags: bool = get_from(attachment, "photo", "has_tags", default = None)
        orig_photo: dict = get_from(attachment, "photo", "orig_photo", types = (dict,), default = {})
        self.orig_photo: Vkbot.UrlAttachment = Vkbot.UrlAttachment(orig_photo)

        album_id: int | None = get_from(attachment, "photo", "album_id", types = (int,), default = None)
        self.album_id: int = album_id if isinstance(album_id, int) else 0

        if album_id is None:
            warn(f"Некорректное значение атрибута {self.album_id=}")

        for size_dict in get_from(attachment, "photo", "sizes", types = (list,), default = []):
            size_attachment: Vkbot.UrlAttachment = Vkbot.UrlAttachment(size_dict)
            self.sizes.append(size_attachment)

        if not isinstance(self.text, str):
            warn(f"Некорректное значение атрибута {self.text=}")
            self.text = ""

        if not isinstance(self.web_view_token, str):
            warn(f"Некорректное значение атрибута {self.web_view_token=}")
            self.web_view_token = ""

        if self.has_tags is None:
            warn(f"Некорректное значение атрибута {self.has_tags=}")
            self.has_tags = False
        else:
            self.has_tags = bool(self.has_tags)

        if (not orig_photo) or not isinstance(orig_photo, dict):
            warn(f"Некорректное значение атрибута {self.orig_photo=}")

    def dumps(self) -> ATTACHMENT_TYPE:
        """
        Возвращает JSON-совместимый снимок объекта для storage или callback payload.

        :return: JSON-совместимый словарь для сохранения или передачи между слоями

        ### Пример использования:
        ```py
        photoAttachment.dumps()
        ```
        """
        result: "Vkbot.PhotoAttachment.ATTACHMENT_TYPE" = super().dumps()

        result.update({
            "album_id": int(self.album_id),
            "text": str(self.text),
            "web_view_token": str(self.web_view_token),
            "has_tags": bool(self.has_tags),
            "orig_photo": self.orig_photo.dumps(),
            "sizes": [size.dumps() for size in self.sizes]
        })

        return result

    def download_attachments(self, vkbot: Vkbot) -> list[dict]:
        """
        Загружает файлы вложений из API транспорта.

        ### Аргументы:
        :param vkbot: VK transport-адаптер или API-клиент

        :return: список photo-словарей из VK `messages.getById`

        ### Пример использования:
        ```py
        photoAttachment.download_attachments(vkbot = vkbot)
        ```
        """
        photos: list[dict] = vkbot.bot.method("photos.getById", {
            "photos": self.get_id(),
            "extended": 0
        })

        return photos

    def get_url(self, attachment: dict) -> str:
        """
        Возвращает сохранённый URL вложения.

        ### Аргументы:
        :param attachment: вложение

        :return: url

        ### Пример использования:
        ```py
        photoAttachment.get_url(attachment = attachment)
        ```
        """
        sizes: list[dict] = attachment.get("sizes", [])

        # Ищем максимальный размер
        max_size: dict = max(sizes, key=lambda x: x.get("width", 0) * x.get("height", 0))
        url = max_size["url"]
        return url
