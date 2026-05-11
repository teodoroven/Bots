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


from bots.utils.dates import get_date
from bots.utils.mapping import get_from, get_int
from bots.compat import (
    BotTypes,
    DotDict,
    Literal,
    datetime,
    warn,
)
from bots.types import ATTACHMENT_TYPE, Literal

from bots.base.bindings import Bot
from bots.base.attachment import Attachment as BaseAttachment
from bots.base.button import Button as BaseButton
from bots.base.keyboard import Keyboard as BaseKeyboard
from bots.base.message import Message as BaseMessageClass
from bots.base.voice_message import VoiceMessage as BaseVoiceMessage

from bots.vk.attachments.base import Attachment
from bots.vk.attachments.url import UrlAttachment

class VideoAttachment(Attachment):
    """
    VK-видео с metadata, превью и ссылками на mp4-файлы разных размеров.
    Класс хранит VK transport-id отдельно от локального файла и выбирает
    подходящий URL из payload при скачивании.

    ### Поля
    - `ATTACHMENT_TYPE`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.
    - `owner_id`: владелец видео в VK.
    - `attachment_id`: id видео в VK.
    - `access_key`: ключ доступа к видео, если VK его вернул.
    - `date`: хранит доступную дату записи для операций этого объекта.
    - `can_edit`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.
    - `can_delete`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.
    - `can_add`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.
    - `can_attach_link`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.
    - `can_edit_privacy`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.

    ### Методы
    - `__init__`: Создаёт объект и сохраняет данные, нужные transport-layer для отправки, сравнения или восстановления объекта.
    - `dumps`: Возвращает JSON-совместимый снимок объекта для storage или callback payload.
    - `download_attachments`: Загружает файлы вложений из API транспорта.
    - `get_url`: Возвращает url из текущего состояния `VideoAttachment`.

    ### Жизненный цикл
    Экземпляры создаются из конфигурации транспорта, принимают события платформы и отдают app-layer унифицированные wrapper-объекты.

    ### Пример использования
    ```py
    videoAttachment: VideoAttachment
    ```
    """
    ATTACHMENT_TYPE = BotTypes.ATTACHMENT_TYPE

    def __init__(self, attachment: dict | DotDict):
        """
        Создаёт `VideoAttachment` и сохраняет данные, нужные transport-layer для отправки, сравнения или восстановления объекта.

        ### Аргументы:
        :param attachment: вложение wrapper-сообщения

        ### Пример использования:
        ```py
        videoAttachment: VideoAttachment = VideoAttachment(attachment = attachment)
        ```
        """
        owner_id: str = get_from(attachment, "video", "owner_id")
        attachment_id: str = get_from(attachment, "video", "id")
        access_key: str = get_from(attachment, "video", "access_key")

        super().__init__("video", owner_id, attachment_id, access_key)

        self.date: datetime = get_date(attachment, "video", "date")
        self.can_edit: bool = get_from(attachment, "video", "can_edit", default = None)
        self.can_delete: bool = get_from(attachment, "video", "can_delete", default = None)
        self.can_add: bool = get_from(attachment, "video", "can_add", default = None)
        self.can_attach_link: bool = get_from(attachment, "video", "can_attach_link", default = None)
        self.can_edit_privacy: bool = get_from(attachment, "video", "can_edit_privacy", default = None)
        self.is_private: bool = get_from(attachment, "video", "is_private", default = None)
        self.processing: bool = get_from(attachment, "video", "processing", default = None)
        self.can_dislike: bool = get_from(attachment, "video", "can_dislike", default = None)

        self.is_author: bool = get_from(attachment, "video", "is_author", types = (bool,), default = None)
        self.is_favorite: bool = get_from(attachment, "video", "is_favorite", types = (bool,), default = None)

        self.response_type: Literal["min"] | str = get_from(attachment, "video", "response_type", types = (str,), default = None)
        self.description: str = get_from(attachment, "video", "description", types = (str,), default = None)
        self.title: str = get_from(attachment, "video", "title", types = (str,), default = None)
        self.track_code: str = get_from(attachment, "video", "track_code", types = (str,), default = None)

        # В секундах
        self.duration: int = get_int(attachment, -1, "video", "duration")
        self.width: int = get_int(attachment, -1, "video", "width")
        self.height: int = get_int(attachment, -1, "video", "height")
        self.views: int = get_int(attachment, -1, "video", "views")
        self.local_views: int = get_int(attachment, -1, "video", "local_views")

        self.image: list[Vkbot.UrlAttachment] = []
        self.first_frame: list[Vkbot.UrlAttachment] = []

        for image_dict in get_from(attachment, "video", "image", types = (list,), default = []):
            if isinstance(image_dict, dict) or isinstance(image_dict, DotDict):
                image_attachment: Vkbot.UrlAttachment = Vkbot.UrlAttachment(image_dict)
                self.image.append(image_attachment)
            else:
                warn(f"Некорректное значение словаря с ключом image пропущено")

        for image_dict in get_from(attachment, "video", "first_frame", types = (list,), default = []):
            if isinstance(image_dict, dict) or isinstance(image_dict, DotDict):
                image_attachment: Vkbot.UrlAttachment = Vkbot.UrlAttachment(image_dict)
                self.first_frame.append(image_attachment)
            else:
                warn(f"Некорректное значение словаря с ключом image пропущено")

        for key in ("can_edit", "can_delete", "can_add", "can_attach_link", "can_edit_privacy", "is_private", "processing", "can_dislike"):
            value: int | None = getattr(self, key)

            if value is None:
                warn(f"Некорректное значение словаря с ключом {key}={repr(value)}")
                setattr(self, key, False)
            else:
                setattr(self, key, bool(value))

        if not isinstance(self.response_type, str):
            warn(f"Некорректное значение атрибута {self.response_type=}")
            self.response_type = ""

        if not isinstance(self.description, str):
            warn(f"Некорректное значение атрибута {self.description=}")
            self.description = ""

        if not isinstance(self.title, str):
            warn(f"Некорректное значение атрибута {self.title=}")
            self.title = ""

        if (not isinstance(self.track_code, str)) or not self.track_code.startswith("video_"):
            warn(f"Некорректное значение атрибута {self.track_code=}")
            self.track_code = ""

        if not isinstance(self.is_author, bool):
            warn(f"Некорректное значение атрибута {self.is_author=}")
            self.is_author = False

        if not isinstance(self.is_favorite, bool):
            warn(f"Некорректное значение атрибута {self.is_favorite=}")
            self.is_favorite = False

        if self.duration < 0:
            warn(f"Некорректное значение атрибута {self.duration=}")
            self.duration = 0

        if self.width < 0:
            warn(f"Некорректное значение атрибута {self.width=}")
            self.width = 0

        if self.height < 0:
            warn(f"Некорректное значение атрибута {self.height=}")
            self.height = 0

        if self.views < 0:
            warn(f"Некорректное значение атрибута {self.views=}")
            self.views = -1

        if self.local_views < 0:
            warn(f"Некорректное значение атрибута {self.local_views=}")
            self.local_views = -1

    def dumps(self) -> ATTACHMENT_TYPE:
        """
        Возвращает JSON-совместимый снимок объекта для storage или callback payload.

        :return: JSON-совместимый словарь для сохранения или передачи между слоями

        ### Пример использования:
        ```py
        videoAttachment.dumps()
        ```
        """
        result: "Vkbot.VideoAttachment.ATTACHMENT_TYPE" = super().dumps()

        result.update({
            "can_edit": bool(self.can_edit),
            "can_delete": bool(self.can_delete),
            "can_add": bool(self.can_add),
            "can_attach_link": bool(self.can_attach_link),
            "can_edit_privacy": bool(self.can_edit_privacy),
            "is_private": bool(self.is_private),
            "processing": bool(self.processing),
            "can_dislike": bool(self.can_dislike),
            "is_author": bool(self.is_author),
            "is_favorite": bool(self.is_favorite),
            "response_type": str(self.response_type),
            "description": str(self.description),
            "title": str(self.title),
            "track_code": str(self.track_code),
            "duration": int(self.duration),
            "width": int(self.width),
            "height": int(self.height),
            "views": int(self.views),
            "local_views": int(self.local_views),
            "image": [img.dumps() for img in self.image],
            "first_frame": [frame.dumps() for frame in self.first_frame]
            # "date": int(self.date.timestamp()),
        })

        return result

    def download_attachments(self, vkbot: Vkbot) -> list[dict]:
        """
        Загружает файлы вложений из API транспорта.

        ### Аргументы:
        :param vkbot: VK transport-адаптер или API-клиент

        :return: список video-словарей из VK `messages.getById`

        ### Пример использования:
        ```py
        videoAttachment.download_attachments(vkbot = vkbot)
        ```
        """
        video: dict = vkbot.bot.method("video.get", {
            "videos": self.get_id(),
            "extended": 0
        })

        return video.get("items")

    def get_url(self, attachment: dict, size_key: Literal["mp4_1080", "mp4_720", "mp4_480", "mp4_360", "mp4_240"] | None = None) -> str:
        """
        Возвращает сохранённый URL вложения.

        ### Аргументы:
        :param attachment: вложение
        :param size_key: size key

        :return: url

        ### Пример использования:
        ```py
        videoAttachment.get_url(attachment = attachment, size_key = size_key)
        ```
        """
        files: dict = attachment["files"]

        for key in ("mp4_1080", "mp4_720", "mp4_480", "mp4_360", "mp4_240"):
            if key == size_key:
                return files[key]
            elif size_key is None and key in files:
                return files[key]

        return list(files.values())[0]
