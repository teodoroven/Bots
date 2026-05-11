"""
Описывает базовые сущности модуля.
Модуль относится к архитектурной зоне: слой унификации транспортов `bots`, который скрывает различия Telegram и VK за общими объектами сообщений, клавиатур, вложений и событий.

### Публичные классы
- `Attachment`: базовая модель вложения сообщения.

### Публичные функции
- Публичные функции отсутствуют.

### Связи
Используется транспортным слоем и wrapper-логикой, чтобы app-layer работал с `Message`, `Keyboard`, `Button`, `Attachment` и `Event` без привязки к конкретной соцсети.
"""

from __future__ import annotations


from bots.constants import AUDIO_EXTENSIONS, DOC_EXTENSIONS, PHOTO_EXTENSIONS, VIDEO_EXTENSIONS
from bots.utils.files import change_extension, only_extension
from bots.utils.mapping import get_from, get_int, is_int
from bots.compat import (
    BotTypes,
    BytesIO,
    Literal,
    NoReturn,
    VkApi,
    abstractmethod,
    isdir,
    makedirs,
    requests,
)
from bots.types import ATTACHMENT_TYPE, Literal

from bots.base.bindings import Bot
from bots.base.attachment import Attachment as BaseAttachment
from bots.base.button import Button as BaseButton
from bots.base.keyboard import Keyboard as BaseKeyboard
from bots.base.message import Message as BaseMessageClass
from bots.base.voice_message import VoiceMessage as BaseVoiceMessage

class Attachment(BaseAttachment):
    """
    Базовое VK-вложение с transport-id и локальным файлом.
    VK хранит вложение как связку `type`, `owner_id`, `id` и `access_key`;
    локальный `filename` нужен только для повторной отправки или сохранения файла.

    ### Поля
    - `ATTACHMENT_TYPE`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.
    - `DEFAULT_ATTACHMENT_TYPE`: значение, используемое конструктором при отсутствии явного аргумента.
    - `EXTENSIONS`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.
    - `id`: внутренний идентификатор записи или доменного объекта.
    - `type`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.
    - `owner_id`: владелец VK-вложения.
    - `access_key`: ключ доступа к VK-вложению, если API его вернул.

    ### Методы
    - `loads`: Восстанавливает объект из JSON-совместимого словаря.
    - `from_filename`: Создаёт вложение из локального файла.
    - `get_extension`: Возвращает extension из текущего состояния `Attachment`.
    - `create_filename`: Подбирает локальное имя файла для скачанного вложения.
    - `__init__`: Создаёт объект и сохраняет данные, нужные transport-layer для отправки, сравнения или восстановления объекта.
    - `dumps`: Возвращает JSON-совместимый снимок объекта для storage или callback payload.
    - `check`: Проверяет значение по правилам текущего класса и не изменяет состояние.
    - `compare`: Сравнивает объект с другим вложением того же transport-типа.
    - `download_attachments`: Загружает файлы вложений из API транспорта.
    - `get_max_size`: Возвращает max size из текущего состояния `Attachment`.

    ### Жизненный цикл
    Экземпляры создаются из конфигурации транспорта, принимают события платформы и отдают app-layer унифицированные wrapper-объекты.

    ### Пример использования
    ```py
    attachment: Attachment
    ```
    """
    ATTACHMENT_TYPE = BotTypes.ATTACHMENT_TYPE
    DEFAULT_ATTACHMENT_TYPE: Literal["doc"] = "doc"

    EXTENSIONS: dict[str, tuple[str]] = {
        "photo": PHOTO_EXTENSIONS,
        "video": VIDEO_EXTENSIONS,
        "doc": DOC_EXTENSIONS,
        "audio_message": AUDIO_EXTENSIONS
    }

    @classmethod
    def loads(cls: type[Vkbot.Attachment | Vkbot.PhotoAttachment | Vkbot.VideoAttachment | Vkbot.AudioAttachment | Vkbot.DocAttachment], data: ATTACHMENT_TYPE) -> Vkbot.Attachment | Vkbot.PhotoAttachment | Vkbot.VideoAttachment | Vkbot.AudioAttachment | Vkbot.DocAttachment:
        """
        Восстанавливает объект из JSON-совместимого словаря.

        ### Аргументы:
        :param data: сериализованный словарь

        :return: восстановленный объект или загруженное состояние

        ### Пример использования:
        ```py
        Attachment.loads(data = data)
        ```
        """
        attachment_type: str | int = get_from(data, "type")
        owner_id: int = get_int(data, -1, "owner_id")
        attachment_id: int = get_int(data, -1, "id")
        access_key: str = get_from(data, "access_key")
        filename: str = get_from(data, "filename")

        type_key: str = attachment_type

        if is_int(type_key):
            type_key = "doc"

        attachment: Vkbot.Attachment | Vkbot.PhotoAttachment | Vkbot.VideoAttachment | Vkbot.AudioAttachment | Vkbot.DocAttachment = cls(
            {
                type_key: {
                    "owner_id": owner_id,
                    "id": attachment_id,
                    "access_key": access_key,
                    "type": attachment_type
                }
            }
        )

        if filename:
            attachment.set_filename(filename)

        return attachment

    def from_filename(filename: str, vkbot: VkApi) -> NoReturn:
        """
        Создаёт вложение из локального файла.

        ### Аргументы:
        :param filename: имя файла
        :param vkbot: VK transport-адаптер или API-клиент

        :raises NotImplementedError: базовый класс не знает, какой VK upload-метод использовать

        :raises VkbotException: если нижележащий слой сообщает об ошибке операции

        ### Пример использования:
        ```py
        attachment.from_filename(filename = filename, vkbot = vkbot)
        ```
        """
        raise VkbotException("Vkbot не поддерживает загрузку вложений кроме PhotoAttachment")

    @classmethod
    def get_extension(cls, attachment_type: Literal["photo", "video", "doc", "audio_message"]) -> str:
        """
        Возвращает расширение файла по типу VK-вложения.

        ### Аргументы:
        :param attachment_type: attachment type

        :return: extension

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        Attachment.get_extension(attachment_type = attachment_type)
        ```
        """
        match attachment_type:
            case "photo":
                return PHOTO_EXTENSIONS[0]
            case "video":
                return VIDEO_EXTENSIONS[0]
            case "audio_message":
                return AUDIO_EXTENSIONS[0]
            case "doc":
                return DOC_EXTENSIONS[0]  # .bin
            case _:
                raise ValueError(f"Некорректное значение аргумента {attachment_type=}")

    @classmethod
    def create_filename(cls, folder: str, attachment_type: Literal["photo", "video", "doc", "audio_message"], attachment_id: int):
        """
        Создаёт имя файла и связывает результат с текущим объектом.

        ### Аргументы:
        :param folder: директория для файлов вложений
        :param attachment_type: attachment type
        :param attachment_id: attachment id

        :return: созданный объект: имя файла

        ### Пример использования:
        ```py
        Attachment.create_filename(folder = folder, attachment_type = attachment_type, attachment_id = attachment_id)
        ```
        """
        ext: str = cls.get_extension(attachment_type)
        return create_filename(folder, f"{attachment_type}_{attachment_id}{ext}")

    def __init__(self, attachment_type: Literal["photo", "video", "doc", "audio_message"], owner_id: int, attachment_id: int, access_key: str):
        """
        Создаёт вложение `Attachment` и сохраняет transport-данные, нужные для отправки или восстановления сообщения.

        ### Аргументы:
        :param attachment_type: attachment type
        :param owner_id: идентификатор владельца сообщения
        :param attachment_id: attachment id
        :param access_key: access key

        ### Пример использования:
        ```py
        attachment = Attachment(attachment_type = attachment_type, owner_id = owner_id, attachment_id = attachment_id, access_key = access_key)
        ```
        """
        super().__init__(attachment_id)
        self.id: int
        self.type: Literal["photo", "video", "doc", "audio_message"] = self.__class__.DEFAULT_ATTACHMENT_TYPE
        self.owner_id: int = -1
        self.access_key: str = ""

        self.set_type(attachment_type)
        self.set_owner_id(owner_id)
        self.set_access_key(access_key)

    def dumps(self) -> ATTACHMENT_TYPE:
        """
        Возвращает JSON-совместимый снимок объекта для storage или callback payload.

        :return: JSON-совместимый словарь для сохранения или передачи между слоями

        ### Пример использования:
        ```py
        attachment.dumps()
        ```
        """
        result: "Vkbot.Attachment.ATTACHMENT_TYPE" = super().dumps()

        result.update({
            "owner_id": self.get_owner_id(),
            "access_key": self.get_access_key(),
            "type": self.get_type()
        })


        return result

    def __str__(self) -> str:
        """
        type-ownerId_attachmentId_accessKey
        photo-225421698_457239018_009eebb3138c0e130b
        """
        return f"{self.type}{self.owner_id}_{self.id}_{self.access_key}"

    def check(self) -> bool:
        """
        Проверяет значение по правилам текущего класса и не изменяет состояние.

        :return: `True`, если тип, `owner_id`, `id` и `access_key` проходят локальную проверку

        ### Пример использования:
        ```py
        attachment.check()
        ```
        """
        return self.check_type(self.type) and self.check_owner_id(self.owner_id) and self.check_id(self.id) and self.check_access_key(self.access_key)

    def compare(self, attachment: Vkbot.Attachment) -> bool:
        """
        Сравнивает объект с другим вложением того же transport-типа.

        ### Аргументы:
        :param attachment: вложение wrapper-сообщения

        :return: `True`, если совпали filename или VK-связка `type/owner_id/id/access_key`

        ### Пример использования:
        ```py
        attachment.compare(attachment = attachment)
        ```
        """
        if self.filename or attachment.filename:
            return self.get_filename() == attachment.get_filename()
        elif attachment.get_id() != self.get_id():
            return False
        elif attachment.get_access_key() != self.get_access_key():
            return False
        elif attachment.get_owner_id() != self.get_owner_id():
            return False
        else:
            return True

    @abstractmethod
    def download_attachments(self, vkbot: Vkbot) -> list[dict]:
        """
        Загружает файлы вложений из API транспорта.

        ### Аргументы:
        :param vkbot: VK transport-адаптер или API-клиент

        :return: список словарей вложений из VK `messages.getById`

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        attachment.download_attachments(vkbot = vkbot)
        ```
        """
        raise NotImplementedError()

    def get_max_size(self, attachments: list[dict]) -> dict:
        """
        Возвращает словарь с самым крупным вариантом файла из VK payload.

        ### Аргументы:
        :param attachments: вложения

        :return: max size

        ### Пример использования:
        ```py
        attachment.get_max_size(attachments = attachments)
        ```
        """
        return attachments[0]

    @abstractmethod
    def get_url(self, attachment: dict) -> str:
        """
        Возвращает сохранённый URL вложения.

        ### Аргументы:
        :param attachment: вложение

        :return: url

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        attachment.get_url(attachment = attachment)
        ```
        """
        raise NotImplementedError()

    def download(self, vkbot: Vkbot) -> str:
        """
        Загружает файл вложения из API транспорта во временное хранилище.

        ### Аргументы:
        :param vkbot: VK transport-адаптер или API-клиент

        :return: URL файла, выбранный из VK attachment payload

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        attachment.download(vkbot = vkbot)
        ```
        """
        if self.data is not None:
            raise ValueError(f"Некорректное значение атрибута {self.data=}. Скачивание уже выполнено, повторное скачивание невозможно.")

        attachments: list[dict] = self.download_attachments(vkbot)
        attachment: dict = self.get_max_size(attachments)
        url: str = self.get_url(attachment)
        # Скачиваем файл
        response = requests.get(url)
        response.raise_for_status()
        self.data = BytesIO(response.content)
        return attachment.get("title", "")

    def make_filename(self, vkbot: Vkbot, folder: str) -> str:
        """
        Формирует имя файла для локального сохранения transport-вложения.

        ### Аргументы:
        :param vkbot: VK transport-адаптер или API-клиент
        :param folder: директория для файлов вложений

        :return: локальный путь к сохранённому файлу

        ### Пример использования:
        ```py
        attachment.make_filename(vkbot = vkbot, folder = folder)
        ```
        """
        filename: str = self.filename

        if self.filename:
            return self.get_filename()
        elif not self.data:
            filename = self.download(vkbot)

        if not isdir(folder):
            makedirs(folder)

        attachment_filename: str = self.__class__.create_filename(folder, self.get_type(), self.get_id())

        if filename:
            if len(only_extension(filename)) < 2:
                filename = change_extension(filename, only_extension(attachment_filename))

            filename = create_filename(filename)
        else:
            filename = attachment_filename

        # WARNING:
        if only_extension(filename).upper() in ".JPG":
            filename = change_extension(filename, ".jpeg")

        self.save_as(filename)
        self.set_filename(filename)
        return filename


    # Методы, связанные с полями класса


    def check_type(self, type: Literal["photo", "video", "doc", "audio_message"]) -> bool:
        """
        Проверяет допустимость transport-типа.

        ### Аргументы:
        :param type: тип

        :return: `True`, если допустимость transport-типа; иначе `False`

        ### Пример использования:
        ```py
        attachment.check_type(type = type)
        ```
        """
        return type in Vkbot.Attachment.EXTENSIONS

    def set_type(self, attachment_type: Literal["photo", "video", "doc", "audio_message"]):
        """
        Проверяет и сохраняет тип в объекте.

        ### Аргументы:
        :param attachment_type: attachment type

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        attachment.set_type(attachment_type = attachment_type)
        ```
        """
        if self.check_type(attachment_type):
            self.type = attachment_type
        else:
            raise ValueError(f"Некорректное значение аргумента {attachment_type=}")

    def get_type(self) -> Literal["photo", "video", "doc", "audio_message"]:
        """
        Возвращает сохранённый тип объекта.

        :return: тип текущего объекта

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        attachment.get_type()
        ```
        """
        if self.check_type(self.type):
            return self.type
        else:
            raise ValueError(f"Некорректное значение атрибута {self.type=}")


    def check_id(self, attachment_id: int) -> bool:
        """
        Проверяет допустимость идентификатора.

        ### Аргументы:
        :param attachment_id: attachment id

        :return: `True`, если допустимость идентификатора; иначе `False`

        ### Пример использования:
        ```py
        attachment.check_id(attachment_id = attachment_id)
        ```
        """
        return isinstance(attachment_id, int) and attachment_id > 0

    def set_id(self, attachment_id: int):
        """
        Проверяет и сохраняет идентификатор в объекте.

        ### Аргументы:
        :param attachment_id: attachment id

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        attachment.set_id(attachment_id = attachment_id)
        ```
        """
        if self.check_id(attachment_id):
            self.id = attachment_id
        else:
            raise ValueError(f"Некорректное значение аргумента {attachment_id=}")

    def get_id(self) -> int:
        """
        Возвращает сохранённый идентификатор объекта.

        :return: идентификатор текущего объекта

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        attachment.get_id()
        ```
        """
        if self.check_id(self.id):
            return self.id
        else:
            raise ValueError(f"Некорректное значение атрибута {self.id=}")


    def check_owner_id(self, owner_id: int) -> bool:
        """
        Проверяет допустимость owner id transport-сообщения.

        ### Аргументы:
        :param owner_id: идентификатор владельца сообщения

        :return: `True`, если допустимость owner id transport-сообщения; иначе `False`

        ### Пример использования:
        ```py
        attachment.check_owner_id(owner_id = owner_id)
        ```
        """
        return isinstance(owner_id, int)

    def set_owner_id(self, owner_id: int):
        """
        Проверяет и сохраняет идентификатор владельца сообщения в объекте.

        ### Аргументы:
        :param owner_id: идентификатор владельца сообщения

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        attachment.set_owner_id(owner_id = owner_id)
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
        attachment.get_owner_id()
        ```
        """
        if self.check_owner_id(self.owner_id):
            return self.owner_id
        else:
            raise ValueError(f"Некорректное значение атрибута {self.owner_id=}")


    def check_access_key(self, key: str) -> bool:
        """
        Проверяет значение `access key` перед сохранением или использованием.

        ### Аргументы:
        :param key: ключ записи или настройки

        :return: `True`, если значение `access key` перед сохранением или использованием; иначе `False`

        ### Пример использования:
        ```py
        attachment.check_access_key(key = key)
        ```
        """
        return isinstance(key, str) and key.strip()

    def set_access_key(self, key: str):
        """
        Проверяет и сохраняет значение `access key` в `Attachment`.

        ### Аргументы:
        :param key: ключ служебного документа или набора команд

        :raises ValueError: если значение не проходит локальную проверку перед сохранением

        ### Пример использования:
        ```py
        attachment.set_access_key(key = key)
        ```
        """
        if self.check_access_key(key):
            self.access_key = key.strip()
        else:
            raise ValueError(f"Некорректное значение аргумента {key=}")

    def get_access_key(self) -> str:
        """
        Возвращает VK access key вложения.

        :return: access key

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        attachment.get_access_key()
        ```
        """
        if self.check_access_key(self.access_key):
            return self.access_key
        else:
            raise ValueError(f"Некорректное значение атрибута {self.access_key=}")
