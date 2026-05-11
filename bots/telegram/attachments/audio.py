"""
Описывает аудиовложение для конкретного транспорта.
Модуль относится к архитектурной зоне: слой унификации транспортов `bots`, который скрывает различия Telegram и VK за общими объектами сообщений, клавиатур, вложений и событий.

### Публичные классы
- `AudioAttachment`: модель аудиовложения сообщения.

### Публичные функции
- Публичные функции отсутствуют.

### Связи
Используется транспортным слоем и wrapper-логикой, чтобы app-layer работал с `Message`, `Keyboard`, `Button`, `Attachment` и `Event` без привязки к конкретной соцсети.
"""

from __future__ import annotations


from bots.utils.files import only_extension
from bots.utils.mapping import get_from, get_int
from bots.compat import (
    Any,
    Audio,
    AudioSegment,
    BotTypes,
    BytesIO,
    File,
    InputMediaAudio,
    Literal,
    PhotoSize,
    Recognizer,
    Response,
    Voice,
    WavFile,
    requests,
)
from bots.types import ATTACHMENT_TYPE, Any, Literal

from bots.base.bindings import Bot
from bots.base.attachment import Attachment as BaseAttachment
from bots.base.button import Button as BaseButton
from bots.base.keyboard import Keyboard as BaseKeyboard
from bots.base.message import Message as BaseMessageClass
from bots.base.voice_message import VoiceMessage as BaseVoiceMessage

from bots.telegram.attachments.base import Attachment

class AudioAttachment(Attachment):
    """
    Telegram voice/audio-вложение с нормализацией в WAV.
    Класс хранит длительность, распознанный текст, поля обычного audio-файла
    и thumbnail, скачивает файл через Telegram API и конвертирует его через pydub.

    ### Поля
    - `ATTACHMENT_TYPE`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.
    - `text`: результат распознавания речи или вручную установленный текст.
    - `duration`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.
    - `title`: заголовок audio-файла из Telegram, если он был передан.
    - `original_filename`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.
    - `attachment`: хранит вложение сообщения для операций этого объекта.
    - `thumbnail`: связанные сообщения или вложения, которые transport-layer использует при отправке, сравнении или редактировании.

    ### Методы
    - `from_filename`: Создаёт вложение из локального файла.
    - `from_bytes`: Создаёт вложение из байтового содержимого.
    - `loads`: Восстанавливает объект из JSON-совместимого словаря.
    - `__init__`: Создаёт объект и сохраняет данные, нужные transport-layer для отправки, сравнения или восстановления объекта.
    - `get_media_type`: Возвращает `InputMediaAudio` для Telegram media group.
    - `dumps`: Возвращает JSON-совместимый снимок объекта для storage или callback payload.
    - `download`: Загружает файл вложения из API транспорта во временное хранилище.
    - `recognize`: Распознаёт речь из аудио-вложения и возвращает текст.
    - `save_as`: Экспортирует загруженное WAV-аудио в файл.
    - `load_from`: Загружает локальный wav/mp3/ogg и нормализует в WAV.

    ### Жизненный цикл
    Экземпляры создаются из конфигурации транспорта, принимают события платформы и отдают app-layer унифицированные wrapper-объекты.

    ### Пример использования
    ```py
    audioAttachment: AudioAttachment
    ```
    """
    ATTACHMENT_TYPE = BotTypes.ATTACHMENT_TYPE

    def from_filename(filename: str) -> Telebot.AudioAttachment:
        """
        Создаёт вложение из локального файла.

        ### Аргументы:
        :param filename: имя файла

        :return: `AudioAttachment` с установленным локальным filename

        ### Пример использования:
        ```py
        audioAttachment.from_filename(filename = filename)
        ```
        """
        class Sentinel():
            """
            Временный объект `Sentinel` повторяет поля ответа SDK, чтобы переиспользовать общий parser без настоящего API-объекта.
            Временный объект повторяет поля Telegram voice/audio, чтобы
            использовать общий конструктор без настоящего ответа SDK.

            ### Поля
            - `file_id`: идентификатор объекта или связанной сущности, по которому runtime восстанавливает связь между слоями.
            - `file_size`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.
            - `duration`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.

            ### Жизненный цикл
            Экземпляры создаются из конфигурации транспорта, принимают события платформы и отдают app-layer унифицированные wrapper-объекты.

            ### Пример использования
            ```py
            sentinel: Sentinel
            ```
            """
            file_id: Literal[""] = ""
            file_size: Literal[0] = 0
            duration: Literal[0] = 0

        attachment: Telebot.AudioAttachment = Telebot.AudioAttachment(Sentinel)
        attachment.set_filename(filename)
        return attachment

    def from_bytes(data: BytesIO) -> Telebot.AudioAttachment:
        """
        Создаёт вложение из байтового содержимого.

        ### Аргументы:
        :param data: сериализованный словарь

        :return: `AudioAttachment` с байтами аудио в `data`

        ### Пример использования:
        ```py
        audioAttachment.from_bytes(data = data)
        ```
        """
        class Sentinel():
            """
            Временный объект `Sentinel` повторяет поля ответа SDK, чтобы переиспользовать общий parser без настоящего API-объекта.
            Временный объект повторяет поля Telegram voice/audio, чтобы
            использовать общий конструктор без настоящего ответа SDK.

            ### Поля
            - `file_id`: идентификатор объекта или связанной сущности, по которому runtime восстанавливает связь между слоями.
            - `file_size`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.
            - `duration`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.

            ### Жизненный цикл
            Экземпляры создаются из конфигурации транспорта, принимают события платформы и отдают app-layer унифицированные wrapper-объекты.

            ### Пример использования
            ```py
            sentinel: Sentinel
            ```
            """
            file_id: Literal[""] = ""
            file_size: Literal[0] = 0
            duration: Literal[0] = 0

        attachment: Telebot.AudioAttachment = Telebot.AudioAttachment(Sentinel)
        attachment.data = data
        return attachment

    def loads(data: ATTACHMENT_TYPE) -> Telebot.AudioAttachment:
        """
        Восстанавливает объект из JSON-совместимого словаря.

        ### Аргументы:
        :param data: сериализованный словарь

        :return: восстановленный объект или загруженное состояние

        ### Пример использования:
        ```py
        audioAttachment.loads(data = data)
        ```
        """
        attachment: "Telebot.AudioAttachment.ATTACHMENT_TYPE" = get_from(data, "attachment", default = None)

        if attachment:
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
        else:
            SentinelThumb = None

        class Sentinel():
            """
            Временный объект `Sentinel` повторяет поля ответа SDK, чтобы переиспользовать общий parser без настоящего API-объекта.
            Временный объект повторяет поля Telegram voice/audio, сохранённые
            в JSON-снимке вложения.

            ### Поля
            - `file_id`: идентификатор объекта или связанной сущности, по которому runtime восстанавливает связь между слоями.
            - `size`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.
            - `text`: текстовое содержимое, которое показывается пользователю, отправляется в GPT или сохраняется в доменной модели.
            - `duration`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.
            - `title`: текстовое содержимое, которое показывается пользователю, отправляется в GPT или сохраняется в доменной модели.
            - `file_name`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.
            - `thumbnail`: связанные сообщения или вложения, которые transport-layer использует при отправке, сравнении или редактировании.

            ### Жизненный цикл
            Экземпляры создаются из конфигурации транспорта, принимают события платформы и отдают app-layer унифицированные wrapper-объекты.

            ### Пример использования
            ```py
            sentinel: Sentinel
            ```
            """
            file_id: str = get_from(data, "id")
            size: int = get_int(data, -1, "size")
            text: str = get_from(data, "text")
            duration: int = get_int(data, -1, "height")
            title: str = get_from(data, "title", default = "")
            file_name: str = get_from(data, "original_filename", default = "")
            thumbnail: SentinelThumb | None = SentinelThumb

        filename: str = get_from(data, "filename")

        attachment: Telebot.AudioAttachment = Telebot.AudioAttachment(Sentinel)
        if filename:
            attachment.set_filename(filename)
        return attachment

    def __init__(self, attachment: Voice | Audio):
        """
        Создаёт `AudioAttachment` и сохраняет данные, нужные transport-layer для отправки, сравнения или восстановления объекта.

        ### Аргументы:
        :param attachment: вложение wrapper-сообщения

        ### Пример использования:
        ```py
        audioAttachment: AudioAttachment = AudioAttachment(attachment = attachment)
        ```
        """
        super().__init__(attachment)
        self.text: str = ""
        self.duration: int = int(attachment.duration)

        # Уникальные поля Audio

        self.title: str = getattr(attachment, "title", "")
        self.original_filename: str = getattr(attachment, "file_name", "")
        self.attachment: Telebot.PhotoAttachment | None = None

        thumbnail: PhotoSize | None = getattr(attachment, "thumbnail", None)
        if thumbnail is None or isinstance(thumbnail, PhotoSize):
            if thumbnail:
                self.attachment = Telebot.PhotoAttachment(thumbnail)

    def get_media_type(self) -> type[InputMediaAudio]:
        """
        Возвращает media type для Telegram media group.

        :return: media type

        ### Пример использования:
        ```py
        audioAttachment.get_media_type()
        ```
        """
        return InputMediaAudio

    def dumps(self) -> ATTACHMENT_TYPE:
        """
        Возвращает JSON-совместимый снимок объекта для storage или callback payload.

        :return: JSON-совместимый словарь для сохранения или передачи между слоями

        ### Пример использования:
        ```py
        audioAttachment.dumps()
        ```
        """
        result: "Telebot.AudioAttachment.ATTACHMENT_TYPE" = super().dumps()

        # Voice | Audio
        result.update({
            "text": str(self.text),
            "duration": int(self.duration)
        })

        # Audio
        if self.title or self.original_filename or self.attachment:
            result.update({
                "original_filename": str(self.original_filename),
                "title": str(self.title),
                "attachment": self.attachment.dumps() if self.attachment is not None else None
            })

        return result

    def download(self, telebot: Telebot) -> str:
        """
        Скачивает voice/audio из Telegram и конвертирует его в WAV в памяти.

        ### Аргументы:
        :param telebot: Telegram transport-адаптер или API-клиент

        :return: путь файла, который вернул Telegram `get_file`

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        audioAttachment.download(telebot = telebot)
        ```
        """
        if self.check():
            raise ValueError(f"Некорректное значение атрибута {self.data=}. Скачивание уже выполнено, повторное скачивание невозможно.")

        file_info: File = telebot.bot.get_file(self.id)
        response: Response = requests.get(f"https://api.telegram.org/file/bot{telebot.token}/{file_info.file_path}")
        response.raise_for_status()

        extension: Literal[".wav", ".mp3", ".ogg", ".oga"] = only_extension(file_info.file_path).lower()

        if extension == "." or not extension:
            extension = ".ogg"

        audio_format: Literal["wav", "mp3", "ogg"] = "ogg"

        if extension in (".wav", ".mp3", ".ogg"):
            audio_format = extension[1:]

        sound = AudioSegment.from_file(BytesIO(response.content), format = audio_format)
        self.data = BytesIO()
        sound.export(self.data, format = "wav")
        self.data.seek(0)
        return file_info.file_path

    def recognize(self) -> str | Literal[""]:
        """
        Распознаёт загруженное WAV-аудио через `speech_recognition`.

        :return: распознанный текст в нижнем регистре или пустая строка

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        audioAttachment.recognize()
        ```
        """
        if not self.check():
            raise ValueError(f"Некорректное значение атрибута {self.data=}. Перед сохранением необходимо загрузить файл методом download.")

        self.data.seek(0)  # Перемещаем указатель в начало файла
        recognized: Any | str = ""
        rec: Recognizer = Recognizer()

        with WavFile(self.data) as source:
            audio = rec.record(source)
            try:
                # language="ru" не мешает распознавать английскую речь
                recognized = rec.recognize_google(audio, language = "ru-RU").lower()
            except LookupError as err:
                recognized = err

        if isinstance(recognized, str) and recognized:
            return recognized
        else:
            return ""


    def save_as(self, filename: str, audio_format: Literal["wav", "mp3", "ogg"] = ""):
        """
        Экспортирует загруженное WAV-аудио в локальный файл.

        ### Аргументы:
        :param filename: имя файла
        :param audio_format: audio format

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        audioAttachment.save_as(filename = filename, audio_format = audio_format)
        ```
        """
        if not self.check():
            raise ValueError(f"Некорректное значение атрибута {self.data=}. Перед сохранением необходимо загрузить файл методом download.")

        self.data.seek(0)
        sound = AudioSegment.from_wav(self.data)

        if not audio_format:
            extension: Literal[".wav", ".mp3", ".ogg"] = only_extension(filename).lower()

            if extension == "." or not extension:
                extension = ".mp3"
            elif extension not in (".wav", ".mp3", ".ogg"):
                extension = ".mp3"

            audio_format = extension[1:]

        sound = AudioSegment.from_wav(self.data)
        sound.export(filename, format = audio_format)

    def load_from(self, filename: str):
        """
        Загружает локальный wav/mp3/ogg и сохраняет в памяти WAV-версию.

        ### Аргументы:
        :param filename: имя файла

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        audioAttachment.load_from(filename = filename)
        ```
        """
        if not self.check():
            raise ValueError(f"Некорректное значение атрибута {self.data=}. Поле уже содержит данные, повторная загрузка невозможна.")

        extension: Literal[".wav", ".mp3", ".ogg"] = only_extension(filename).lower()

        if extension == "." or not extension:
            extension = ".mp3"

        if extension not in (".wav", ".mp3", ".ogg"):
            raise ValueError(f"Некорректное значение аргумента {filename=}. Поддерживаются только форматы wav, mp3 и ogg.")

        sound = AudioSegment.from_file(filename, format = extension[1:])
        self.data = BytesIO()
        sound.export(self.data, format = "wav")
        self.data.seek(0)  # Перемещаем указатель в начало файла


    def check_text(self, text: str) -> bool:
        """
        Проверяет допустимость текста сообщения.

        ### Аргументы:
        :param text: текст

        :return: `True`, если допустимость текста сообщения; иначе `False`

        ### Пример использования:
        ```py
        audioAttachment.check_text(text = text)
        ```
        """
        return isinstance(text, str)

    def set_text(self, text: str):
        """
        Проверяет и сохраняет значение `text` в `AudioAttachment`.

        ### Аргументы:
        :param text: текст сообщения или пользовательского ввода

        :raises ValueError: если значение не проходит локальную проверку перед сохранением

        ### Пример использования:
        ```py
        audioAttachment.set_text(text = text)
        ```
        """
        if self.check_text(text):
            self.text = text
        else:
            raise ValueError(f"Некорректное значение аргумента {text=}")

    def get_text(self) -> str:
        """
        Возвращает сохранённый текст сообщения.

        :return: текст текущего сообщения

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        audioAttachment.get_text()
        ```
        """
        if self.check_text(self.text):
            return self.text
        else:
            raise ValueError(f"Некорректное значение атрибута {self.text=}")
