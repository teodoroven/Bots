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
from bots.utils.files import change_extension, create_filename, only_extension
from bots.compat import (
    Audio,
    BotTypes,
    BytesIO,
    Document,
    File,
    InputMediaAudio,
    InputMediaDocument,
    InputMediaPhoto,
    InputMediaVideo,
    Never,
    PhotoSize,
    Response,
    Video,
    Voice,
    abstractmethod,
    isdir,
    makedirs,
    requests,
)
from bots.types import ATTACHMENT_TYPE

from bots.base.bindings import Bot
from bots.base.attachment import Attachment as BaseAttachment
from bots.base.button import Button as BaseButton
from bots.base.keyboard import Keyboard as BaseKeyboard
from bots.base.message import Message as BaseMessageClass
from bots.base.voice_message import VoiceMessage as BaseVoiceMessage

class Attachment(BaseAttachment):
    """
    Базовое Telegram-вложение с `file_id`, размером и локальными байтами файла.
    Класс хранит идентификатор Telegram, умеет скачать файл через `telebot` API,
    сохранить его локально и подготовить `BytesIO` для отправки media group.

    ### Поля
    - `ATTACHMENT_TYPE`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.
    - `DEFAULT_ATTACHMENT_TYPE`: значение, используемое конструктором при отсутствии явного аргумента.
    - `EXTENSIONS`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.
    - `id`: внутренний идентификатор записи или доменного объекта.
    - `size`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.

    ### Методы
    - `__init__`: Создаёт объект и сохраняет данные, нужные transport-layer для отправки, сравнения или восстановления объекта.
    - `get_media_type`: Возвращает media type из текущего состояния `Attachment`.
    - `dumps`: Возвращает JSON-совместимый снимок объекта для storage или callback payload.
    - `check`: Проверяет, есть ли у вложения Telegram id или локальный файл.
    - `get`: Возвращает `BytesIO` с уже загруженным содержимым.
    - `compare`: Сравнивает объект с другим вложением того же transport-типа.
    - `download`: Загружает файл вложения из API транспорта во временное хранилище.
    - `make_filename`: Формирует имя файла для локального сохранения transport-вложения.
    - `load_from`: Загружает локальный файл в память.
    - `check_id`: Проверяет id перед использованием.

    ### Жизненный цикл
    Экземпляры создаются из конфигурации транспорта, принимают события платформы и отдают app-layer унифицированные wrapper-объекты.

    ### Пример использования
    ```py
    attachment: Attachment
    ```
    """
    ATTACHMENT_TYPE = BotTypes.ATTACHMENT_TYPE
    DEFAULT_ATTACHMENT_TYPE: type[InputMediaDocument] = InputMediaDocument

    EXTENSIONS: dict[type[InputMediaPhoto] | type[InputMediaVideo] | type[InputMediaDocument], tuple[str]] = {
        InputMediaPhoto: PHOTO_EXTENSIONS,
        InputMediaVideo: VIDEO_EXTENSIONS,
        InputMediaAudio: AUDIO_EXTENSIONS,
        InputMediaDocument: DOC_EXTENSIONS
    }

    def __init__(self, attachment: PhotoSize | Video | Document | Audio | Voice):
        """
        Создаёт `Attachment` и сохраняет данные, нужные transport-layer для отправки, сравнения или восстановления объекта.

        ### Аргументы:
        :param attachment: вложение wrapper-сообщения

        ### Пример использования:
        ```py
        attachment: Attachment = Attachment(attachment = attachment)
        ```
        """
        super().__init__(attachment.file_id)
        self.id: str
        self.size: int = int((attachment.file_size if hasattr(attachment, "file_size") else None) or 0)

    @abstractmethod
    def get_media_type(self) -> Never:
        """
        Возвращает media type для Telegram media group.

        :return: media type

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        attachment.get_media_type()
        ```
        """
        raise NotImplementedError("Вместо Attachment используйте PhotoAttachment, VideoAttachment, AudioAttachment или DocumentAttachment")

    def dumps(self) -> ATTACHMENT_TYPE:
        """
        Возвращает JSON-совместимый снимок объекта для storage или callback payload.

        :return: JSON-совместимый словарь для сохранения или передачи между слоями

        ### Пример использования:
        ```py
        attachment.dumps()
        ```
        """
        result: "Telebot.Attachment.ATTACHMENT_TYPE" = super().dumps()

        result.update({
            "size": int(self.size)
        })

        return result

    def check(self) -> bool:
        """
        Проверяет, загружены ли байты файла в память.

        :return: `True`, если `self.data` уже содержит `BytesIO`; иначе `False`

        ### Пример использования:
        ```py
        attachment.check()
        ```
        """
        return self.data is not None

    def get(self) -> BytesIO:
        """
        Возвращает загруженные байты файла для отправки или сохранения.

        :return: `BytesIO`, установленный `download`, `load_from` или `from_bytes`

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        attachment.get()
        ```
        """
        if not self.check():
            raise ValueError(f"Некорректное значение атрибута {self.data=}. Перед получением необходимо загрузить файл методом download.")

        self.data.seek(0)
        return self.data

    def compare(self, attachment: Telebot.Attachment) -> bool:
        """
        Сравнивает Telegram-вложения по самому надёжному доступному признаку.

        ### Аргументы:
        :param attachment: вложение wrapper-сообщения

        :return: `True`, если совпали filename, Telegram id или загруженные байты

        ### Пример использования:
        ```py
        attachment.compare(attachment = attachment)
        ```
        """
        if self.filename or attachment.filename:
            return self.get_filename() == attachment.get_filename()
        elif self.id or attachment.id:
            return self.get_id() == attachment.get_id()
        elif self.data or attachment.data:
            return self.get() == attachment.get()
        else:
            # Два пустых вложения
            return True

    def download(self, telebot: Telebot) -> str:
        """
        Загружает файл из Telegram в `self.data`.

        ### Аргументы:
        :param telebot: Telegram transport-адаптер или API-клиент

        :return: путь файла, который вернул Telegram `get_file`

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        attachment.download(telebot = telebot)
        ```
        """
        if self.data is not None:
            raise ValueError(f"Некорректное значение атрибута {self.data=}. Скачивание уже выполнено, повторное скачивание невозможно.")

        file_info: File = telebot.bot.get_file(self.id)
        response: Response = requests.get(f"https://api.telegram.org/file/bot{telebot.token}/{file_info.file_path}")
        response.raise_for_status()
        self.data = BytesIO(response.content)
        return file_info.file_path

    def make_filename(self, telebot: Telebot, folder: str) -> str:
        """
        Сохраняет вложение в `folder` и запоминает локальный путь.

        ### Аргументы:
        :param telebot: Telegram transport-адаптер или API-клиент
        :param folder: директория для файлов вложений

        :return: локальный путь к сохранённому файлу

        ### Пример использования:
        ```py
        attachment.make_filename(telebot = telebot, folder = folder)
        ```
        """
        if self.filename:
            return self.get_filename()
        elif not self.data:
            filename: str = self.download(telebot)
            filename = create_filename(folder, filename)
        else:
            file_info: File = telebot.bot.get_file(self.id)
            filename = create_filename(folder, file_info.file_path)

        if not isdir(folder):
            makedirs(folder)

        # WARNING:
        if only_extension(filename).upper() in ".JPG":
            filename = change_extension(filename, ".jpeg")

        self.save_as(filename)
        self.set_filename(filename)
        return filename

    def load_from(self, filename: str):
        """
        Читает локальный файл в `self.data` без обращения к Telegram API.

        ### Аргументы:
        :param filename: имя файла

        ### Пример использования:
        ```py
        attachment.load_from(filename = filename)
        ```
        """
        with open(filename, "rb") as file:
            self.data = BytesIO(file.read())
            self.data.seek(0)


    def check_id(self, attachment_id: str) -> bool:
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
        return isinstance(attachment_id, str)

    def set_id(self, attachment_id: str):
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

    def get_id(self) -> str:
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


    def check(self) -> bool:
        """
        Проверяет, достаточно ли данных, чтобы считать вложение валидным.

        :return: `True`, если задан Telegram id или локальный filename

        ### Пример использования:
        ```py
        attachment.check()
        ```
        """
        return self.check_id(self.id) or self.check_filename(self.filename)
