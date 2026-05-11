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


from bots.utils.mapping import get_from, get_int
from bots.compat import (
    AudioData,
    AudioFile,
    AudioSegment,
    BotTypes,
    BytesIO,
    DotDict,
    Literal,
    Recognizer,
    Response,
    UnknownValueError,
    datetime,
    requests,
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

class AudioAttachment(Attachment):
    """
    VK audio_message с WAV-данными и распознанным текстом.
    Класс получает URL голосового сообщения из VK payload, скачивает файл через
    базовый механизм вложений, конвертирует его через pydub и распознаёт речь.

    ### Поля
    - `ATTACHMENT_TYPE`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.
    - `owner_id`: владелец audio_message в VK.
    - `attachment_id`: id audio_message в VK.
    - `access_key`: ключ доступа к audio_message, если VK его вернул.
    - `date`: хранит доступную дату записи для операций этого объекта.
    - `duration`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.
    - `link_mp3`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.
    - `link_ogg`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.
    - `waveform`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.

    ### Методы
    - `__init__`: Создаёт объект и сохраняет данные, нужные transport-layer для отправки, сравнения или восстановления объекта.
    - `dumps`: Возвращает JSON-совместимый снимок объекта для storage или callback payload.
    - `recognize`: Распознаёт речь из аудио-вложения и возвращает текст.
    - `download_attachments`: Загружает файлы вложений из API транспорта.
    - `get_url`: Возвращает url из текущего состояния `AudioAttachment`.

    ### Жизненный цикл
    Экземпляры создаются из конфигурации транспорта, принимают события платформы и отдают app-layer унифицированные wrapper-объекты.

    ### Пример использования
    ```py
    audioAttachment: AudioAttachment
    ```
    """
    ATTACHMENT_TYPE = BotTypes.ATTACHMENT_TYPE

    def __init__(self, attachment: dict | DotDict):
        """
        Создаёт `AudioAttachment` и сохраняет данные, нужные transport-layer для отправки, сравнения или восстановления объекта.

        ### Аргументы:
        :param attachment: вложение wrapper-сообщения

        ### Пример использования:
        ```py
        audioAttachment: AudioAttachment = AudioAttachment(attachment = attachment)
        ```
        """
        owner_id: int = get_from(attachment, "audio_message", "owner_id")
        attachment_id: int = get_from(attachment, "audio_message", "id")
        access_key: str = get_from(attachment, "audio_message", "access_key")

        super().__init__("audio_message", owner_id, attachment_id, access_key)

        self.date: datetime = datetime.now()
        self.duration: int = get_int(attachment, -1, "audio_message", "duration")
        self.link_mp3: str = get_from(attachment, "audio_message", "link_mp3", types = (str,), default = "")
        self.link_ogg: str = get_from(attachment, "audio_message", "link_ogg", types = (str,), default = "")
        self.waveform: list[int] = get_from(attachment, "audio_message", "waveform", type = (list,), default = [])

        if self.duration < 0:
            warn(f"Некорректное значение атрибута {self.duration=}")
            self.duration = 0

        if not self.link_mp3:
            warn(f"Некорректное значение атрибута {self.link_mp3=}")
            self.link_mp3 = ""

        if not self.link_ogg:
            warn(f"Некорректное значение атрибута {self.link_ogg=}")
            self.link_ogg = ""

        if not isinstance(self.waveform, list) or not all(isinstance(x, int) for x in self.waveform):
            warn(f"Некорректное значение атрибута {self.waveform=}")
            self.waveform = []


    def dumps(self) -> ATTACHMENT_TYPE:
        """
        Возвращает JSON-совместимый снимок объекта для storage или callback payload.

        :return: JSON-совместимый словарь для сохранения или передачи между слоями

        ### Пример использования:
        ```py
        audioAttachment.dumps()
        ```
        """
        result: "Vkbot.AudioAttachment.ATTACHMENT_TYPE" = super().dumps()

        result.update({
            "duration": int(self.duration),
            "link_mp3": str(self.link_mp3),
            "link_ogg": str(self.link_ogg),
            "waveform": [int(elem) for elem in self.waveform]
        })

        return result

    def recognize(self) -> str | Literal[""]:
        """
        Распознаёт речь из аудио-вложения и возвращает текст.

        :return: распознанный текст в нижнем регистре или пустая строка

        ### Пример использования:
        ```py
        audioAttachment.recognize()
        ```
        """
        # Скачивание вложения, ответ в виде байтов
        response: Response = requests.get(self.link_mp3 or self.link_ogg)

        # Преобразование ответа в последовательность байтов
        audio_data: BytesIO = BytesIO(response.content)

        # Преобразование в аудио формат
        audio_segment: AudioSegment = AudioSegment.from_mp3(audio_data)

        # Преобразование mp3 в wav для распознавания
        audio_wav = audio_segment.export(format = "wav")

        # Распознавание текста голосового сообщения
        recognizer: Recognizer = Recognizer()

        with AudioFile(audio_wav) as source:
            audio: AudioData = recognizer.record(source)
            try:
                # language="ru" не мешает распознавать английскую речь
                recognized: str = recognizer.recognize_google(audio, language = "ru")
            except UnknownValueError as err:
                recognized: UnknownValueError = err

        if isinstance(recognized, str) and recognized:
            return recognized
        else:
            return ""

    def download_attachments(self, vkbot: Vkbot) -> list[dict]:
        """
        Загружает файлы вложений из API транспорта.

        ### Аргументы:
        :param vkbot: VK transport-адаптер или API-клиент

        :return: список audio_message-словарей из VK `messages.getById`

        ### Пример использования:
        ```py
        audioAttachment.download_attachments(vkbot = vkbot)
        ```
        """
        audios: list[dict] = vkbot.bot.method("audio.getById", {
            "audios": self.get_id()
        })

        return audios

    def get_url(self, attachment: dict) -> str:
        """
        Возвращает сохранённый URL вложения.

        ### Аргументы:
        :param attachment: вложение

        :return: url

        ### Пример использования:
        ```py
        audioAttachment.get_url(attachment = attachment)
        ```
        """
        return attachment["url"]
