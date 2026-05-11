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

from bots.compat import BotTypes
from bots.types import MESSAGE_TYPE

from bots.base.base_message import BaseMessage

class VoiceMessage(BaseMessage):
    """
    Базовое transport-сообщение для voice/audio-вложения.
    Хранит ссылку на audio attachment, а platform-наследники выполняют
    конкретный сетевой вызов отправки.

    ### Поля
    - `MESSAGE_TYPE`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.
    - `audio_attachment`: связанные сообщения или вложения, которые transport-layer использует при отправке, сравнении или редактировании.

    ### Методы
    - `__init__`: Создаёт объект и сохраняет данные, нужные transport-layer для отправки, сравнения или восстановления объекта.
    - `dumps`: Возвращает JSON-совместимый снимок объекта для storage или callback payload.
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
    MESSAGE_TYPE = BotTypes.MESSAGE_TYPE

    def __init__(self, owner_id: int, text: str, audio_attachment: Vkbot.AudioAttachment | Telebot.AudioAttachment | None, reply: Bot.Message | None = None):
        """
        Создаёт голосовое сообщение `VoiceMessage` и сохраняет вложение с аудио для transport-layer.

        ### Аргументы:
        :param owner_id: идентификатор владельца сообщения
        :param text: текст
        :param audio_attachment: audio attachment
        :param reply: сообщение, на которое дан ответ

        ### Пример использования:
        ```py
        voiceMessage = VoiceMessage(owner_id = owner_id, text = text, audio_attachment = audio_attachment, reply = reply)
        ```
        """
        super().__init__(owner_id, text, reply)

        self.audio_attachment: Bot.AudioAttachment | None
        self.set_audio_attachment(audio_attachment)

    def dumps(self) -> MESSAGE_TYPE:
        """
        Возвращает JSON-совместимый снимок объекта для storage или callback payload.

        :return: JSON-совместимый словарь для сохранения или передачи между слоями

        ### Пример использования:
        ```py
        voiceMessage.dumps()
        ```
        """
        result: "Bot.VoiceMessage.MESSAGE_TYPE" = super().dumps()

        result.update({
            "text": self.get_text(),
            "audio_attachment": self.get_audio_attachment().dumps() if self.audio_attachment is not None else None
        })

        return result


    def check_audio_attachment(self, audio_attachment: Bot.AudioAttachment) -> bool:
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
        return isinstance(audio_attachment, Bot.AudioAttachment)

    def set_audio_attachment(self, audio_attachment: Bot.AudioAttachment | None):
        """
        Проверяет и сохраняет значение `audio attachment`.

        ### Аргументы:
        :param audio_attachment: audio attachment

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        voiceMessage.set_audio_attachment(audio_attachment = audio_attachment)
        ```
        """
        if audio_attachment is None:
            self.audio_attachment = None
        elif self.check_audio_attachment(audio_attachment):
            self.audio_attachment = audio_attachment
        else:
            raise ValueError(f"Некорректное значение аргумента {audio_attachment=}")

    def get_audio_attachment(self) -> Bot.AudioAttachment | None:
        """
        Возвращает audio attachment, которое будет отправлено как voice-сообщение.

        :return: audio attachment

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        voiceMessage.get_audio_attachment()
        ```
        """
        if self.audio_attachment is None:
            return None
        elif self.check_audio_attachment(self.audio_attachment):
            return self.audio_attachment
        else:
            raise ValueError(f"Некорректное значение атрибута {self.audio_attachment=}")
