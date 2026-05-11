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

class DocAttachment(Attachment):
    """
    VK-документ с исходным именем файла, расширением и ссылкой на скачивание.
    Класс хранит transport-id документа отдельно от локального `filename`, чтобы
    wrapper мог сравнивать входящее вложение и при необходимости сохранить файл.

    ### Поля
    - `ATTACHMENT_TYPE`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.
    - `owner_id`: владелец документа в VK.
    - `attachment_id`: id документа в VK.
    - `access_key`: ключ доступа к документу, если VK его вернул.
    - `date`: хранит доступную дату записи для операций этого объекта.
    - `title`: текстовое содержимое, которое показывается пользователю, отправляется в GPT или сохраняется в доменной модели.
    - `ext`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.
    - `url`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.
    - `can_manage`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.
    - `is_unsafe`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.

    ### Методы
    - `__init__`: Создаёт объект и сохраняет данные, нужные transport-layer для отправки, сравнения или восстановления объекта.
    - `dumps`: Возвращает JSON-совместимый снимок объекта для storage или callback payload.
    - `download_attachments`: Загружает файлы вложений из API транспорта.
    - `get_url`: Возвращает url из текущего состояния `DocAttachment`.

    ### Жизненный цикл
    Экземпляры создаются из конфигурации транспорта, принимают события платформы и отдают app-layer унифицированные wrapper-объекты.

    ### Пример использования
    ```py
    docAttachment: DocAttachment
    ```
    """
    ATTACHMENT_TYPE = BotTypes.ATTACHMENT_TYPE

    def __init__(self, attachment: dict | DotDict):
        """
        Создаёт `DocAttachment` и сохраняет данные, нужные transport-layer для отправки, сравнения или восстановления объекта.

        ### Аргументы:
        :param attachment: вложение wrapper-сообщения

        ### Пример использования:
        ```py
        docAttachment: DocAttachment = DocAttachment(attachment = attachment)
        ```
        """
        owner_id: str = get_from(attachment, "doc", "owner_id")
        attachment_id: str = get_from(attachment, "doc", "id")
        access_key: str = get_from(attachment, "doc", "access_key")

        super().__init__("doc", owner_id, attachment_id, access_key)

        self.date: datetime = get_date(attachment, "doc", "date")
        self.title: str = get_from(attachment, "doc", "title", types = (str,), default = None)
        self.ext: str = get_from(attachment, "doc", "ext", types = (str,), default = None)
        self.url: str = get_from(attachment, "doc", "url", types = (str,), default = "")

        self.can_manage: bool = get_from(attachment, "doc", "can_manage", types = (bool,), default = None)

        self.is_unsafe: bool = get_from(attachment, "doc", "is_unsafe", default = None)

        self.size: int = get_int(attachment, -1, "doc", "size")
        self.doc_type: int = get_int(attachment, -1, "doc", "type")

        if not isinstance(self.title, str):
            warn(f"Некорректное значение атрибута {self.title=}")
            self.title = ""

        if self.size < 0:
            warn(f"Некорректное значение атрибута {self.size=}")
            self.size = 0

        if not isinstance(self.ext, str):
            warn(f"Некорректное значение атрибута {self.ext=}")
            self.ext = ""

        if self.doc_type < 0:
            warn(f"Некорректное значение атрибута {self.doc_type=}")
            self.doc_type = 0

        if not self.url:
            warn(f"Некорректное значение атрибута {self.url=}")
            self.url = ""

        if self.is_unsafe is None:
            warn(f"Некорректное значение атрибута {self.is_unsafe=}")
            self.is_unsafe = False
        else:
            self.is_unsafe = bool(self.is_unsafe)

        if self.can_manage is None:
            warn(f"Некорректное значение атрибута {self.can_manage=}")
            self.can_manage = False

    def dumps(self) -> ATTACHMENT_TYPE:
        """
        Возвращает JSON-совместимый снимок объекта для storage или callback payload.

        :return: JSON-совместимый словарь для сохранения или передачи между слоями

        ### Пример использования:
        ```py
        docAttachment.dumps()
        ```
        """
        result: "Vkbot.DocAttachment.ATTACHMENT_TYPE" = super().dumps()

        result.update({
            "title": str(self.title),
            "ext": str(self.ext),
            "url": str(self.url),
            "can_manage": bool(self.can_manage),
            "is_unsafe": bool(self.is_unsafe),
            "size": int(self.size),
            "type": int(self.doc_type),
            "type": int(self.doc_type)
            # "date": int(self.date.timestamp()),
        })

        return result

    def download_attachments(self, vkbot: Vkbot) -> list[dict]:
        """
        Загружает файлы вложений из API транспорта.

        ### Аргументы:
        :param vkbot: VK transport-адаптер или API-клиент

        :return: список doc-словарей из VK `messages.getById`

        ### Пример использования:
        ```py
        docAttachment.download_attachments(vkbot = vkbot)
        ```
        """
        docs: list[dict] = vkbot.bot.method("docs.getById", {
            "docs": self.get_id()
        })

        return docs

    def get_url(self, attachment: dict) -> str:
        """
        Возвращает сохранённый URL вложения.

        ### Аргументы:
        :param attachment: вложение

        :return: url

        ### Пример использования:
        ```py
        docAttachment.get_url(attachment = attachment)
        ```
        """
        return attachment["url"]
