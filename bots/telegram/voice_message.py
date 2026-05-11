"""
Описывает голосовое сообщение конкретного транспорта.
Модуль относится к архитектурной зоне: слой унификации транспортов `bots`, который скрывает различия Telegram и VK за общими объектами сообщений, клавиатур, вложений и событий.

### Публичные классы
- `VoiceMessage`: модель голосового сообщения.

### Публичные функции
- Публичные функции отсутствуют.

### Связи
Используется транспортным слоем и wrapper-логикой, чтобы app-layer работал с `Message`, `Keyboard`, `Button`, `Attachment` и `Event` без привязки к конкретной соцсети.
"""

from __future__ import annotations

from bots.compat import (
    BufferedReader,
    BytesIO,
    TeleBot,
    TelebotMessage,
    Voice,
    datetime,
)

from bots.base.bindings import Bot
from bots.base.attachment import Attachment as BaseAttachment
from bots.base.button import Button as BaseButton
from bots.base.keyboard import Keyboard as BaseKeyboard
from bots.base.message import Message as BaseMessageClass
from bots.base.voice_message import VoiceMessage as BaseVoiceMessage

class VoiceMessage(BaseVoiceMessage):

    """
    Telegram voice-сообщение transport-layer.
    Класс синтезирует audio attachment при необходимости, отправляет voice через
    `telebot.send_voice` и умеет распознать загруженное аудио.

    ### Поля
    - `telebot`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.

    ### Методы
    - `__init__`: Создаёт объект и сохраняет данные, нужные transport-layer для отправки, сравнения или восстановления объекта.
    - `send`: Отправляет сообщение или вложение через transport-layer.
    - `synthesize`: Создаёт голосовое сообщение из текста.
    - `recognize`: Распознаёт речь из аудио-вложения и возвращает текст.
    - `check_telebot`: Проверяет telebot перед использованием.
    - `set_telebot`: Проверяет и сохраняет значение `telebot` в `VoiceMessage`.
    - `get_telebot`: Возвращает telebot из текущего состояния `VoiceMessage`.
    - `check_audio_attachment`: Проверяет audio attachment перед использованием.
    - `set_audio_attachment`: Проверяет и сохраняет значение `audio attachment` в `VoiceMessage`.
    - `get_audio_attachment`: Возвращает audio attachment из текущего состояния `VoiceMessage`.

    ### Жизненный цикл
    Экземпляры создаются из конфигурации транспорта, принимают события платформы и отдают app-layer унифицированные wrapper-объекты.

    ### Пример использования
    ```py
    voice_message: VoiceMessage
    ```
    """
    def __init__(self, telebot: TeleBot, owner_id: int, text: str, audio_attachment: Telebot.AudioAttachment | None, event: Bot.Event = None, reply: Bot.Message | None = None):
        """
        Создаёт голосовое сообщение `VoiceMessage` и сохраняет вложение с аудио для transport-layer.

        ### Аргументы:
        :param telebot: Telegram transport-адаптер или API-клиент
        :param owner_id: идентификатор владельца сообщения
        :param text: текст
        :param audio_attachment: audio attachment
        :param event: transport-событие для обработки
        :param reply: сообщение, на которое дан ответ

        ### Пример использования:
        ```py
        voiceMessage = VoiceMessage(telebot = telebot, owner_id = owner_id, text = text, audio_attachment = audio_attachment, event = event, reply = reply)
        ```
        """
        super().__init__(owner_id, text, audio_attachment, event, reply)
        self.telebot: TeleBot
        self.set_telebot(telebot)

    def send(self, chat_id: int) -> Telebot.Event:
        """
        Отправляет сообщение или вложение через transport-layer.

        ### Аргументы:
        :param chat_id: идентификатор чата

        :return: `Bot.Event`, созданный из ответа Telegram `send_voice`

        ### Пример использования:
        ```py
        voiceMessage.send(chat_id = chat_id)
        ```
        """
        audio_attachment: Telebot.AudioAttachment | None = self.get_audio_attachment()
        telebot: TeleBot = self.get_telebot()
        content: str | BufferedReader | BytesIO
        files: list[BufferedReader] = []

        if not audio_attachment:
            self.synthesize()

        file_id: str = audio_attachment.get_id()
        if file_id:
            content = file_id
        elif audio_attachment.check_filename(audio_attachment.filename):
            filename: str = audio_attachment.get_filename()
            content = open(filename, "rb")
            files.append(content)
        else:
            content = audio_attachment.get()

        response: TelebotMessage = telebot.send_voice(chat_id, content)
        message_id: int = int(response.message_id)
        event: Bot.Event = self.__class__.Event(chat_id, "", datetime.now(), [audio_attachment])
        event.set_events([response])
        self.add_event(event, datetime.fromtimestamp(response.date), self.__class__.SENT_KEY)
        self.set_id(message_id)
        self.set_chat_id(chat_id)

        for file in files:
            file.close()

        return event

    def synthesize(self):
        """
        Создаёт голосовое сообщение из текста.

        ### Пример использования:
        ```py
        voiceMessage.synthesize()
        ```
        """
        text: str = self.get_text()
        audio: BytesIO = Voice().synthesize(text)
        audio_attachment: Telebot.AudioAttachment = Telebot.AudioAttachment.from_bytes(audio)
        self.set_audio_attachment(audio_attachment)

    def recognize(self):
        """
        Распознаёт речь из аудио-вложения и возвращает текст.

        ### Пример использования:
        ```py
        voiceMessage.recognize()
        ```
        """
        audio_attachment: Telebot.AudioAttachment | None = self.get_audio_attachment()

        if audio_attachment:
            text: str = audio_attachment.recognize()
            self.set_text(text)


    # Методы работы с полями


    def check_telebot(self, telebot: TeleBot) -> bool:
        """
        Проверяет значение `telebot` перед сохранением или использованием.

        ### Аргументы:
        :param telebot: Telegram transport-адаптер или API-клиент

        :return: `True`, если значение `telebot` перед сохранением или использованием; иначе `False`

        ### Пример использования:
        ```py
        voiceMessage.check_telebot(telebot = telebot)
        ```
        """
        return isinstance(telebot, TeleBot)

    def set_telebot(self, telebot: TeleBot):
        """
        Проверяет и сохраняет значение `telebot`.

        ### Аргументы:
        :param telebot: Telegram transport-адаптер или API-клиент

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        voiceMessage.set_telebot(telebot = telebot)
        ```
        """
        if self.check_telebot(telebot):
            self.telebot = telebot
        else:
            raise ValueError(f"Некорректное значение аргумента {telebot=}")

    def get_telebot(self) -> TeleBot:
        """
        Возвращает SDK-клиент `TeleBot`, используемый для отправки voice.

        :return: telebot

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        voiceMessage.get_telebot()
        ```
        """
        if self.check_telebot(self.telebot):
            return self.telebot
        else:
            raise ValueError(f"Некорректное значение атрибута {self.telebot=}")


    # Переопределённые методы работы с полями


    def check_audio_attachment(self, audio_attachment: Telebot.AudioAttachment) -> bool:
        """
        Проверяет значение `audio attachment` перед сохранением или использованием.

        ### Аргументы:
        :param audio_attachment: audio attachment

        :return: `True`, если значение `audio attachment` перед сохранением или использованием; иначе `False`

        ### Пример использования:
        ```py
        voiceMessage.check_audio_attachment(audio_attachment = audio_attachment)
        ```
        """
        return isinstance(audio_attachment, Telebot.AudioAttachment)

    def set_audio_attachment(self, audio_attachment: Telebot.AudioAttachment | None):
        """
        Проверяет и сохраняет значение `audio attachment`.

        ### Аргументы:
        :param audio_attachment: audio attachment

        :return: результат базового `set_audio_attachment`; метод сохраняет audio attachment

        ### Пример использования:
        ```py
        voiceMessage.set_audio_attachment(audio_attachment = audio_attachment)
        ```
        """
        return super().set_audio_attachment(audio_attachment)

    def get_audio_attachment(self) -> Telebot.AudioAttachment | None:
        """
        Возвращает audio attachment, подготовленное для `send_voice`.

        :return: audio attachment

        ### Пример использования:
        ```py
        voiceMessage.get_audio_attachment()
        ```
        """
        return super().set_audio_attachment()
