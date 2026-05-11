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

from bots.compat import VkApi

from bots.base.bindings import Bot
from bots.base.attachment import Attachment as BaseAttachment
from bots.base.button import Button as BaseButton
from bots.base.keyboard import Keyboard as BaseKeyboard
from bots.base.message import Message as BaseMessageClass
from bots.base.voice_message import VoiceMessage as BaseVoiceMessage

class VoiceMessage(BaseVoiceMessage):

    """
    VK voice-сообщение transport-layer.
    Класс хранит audio_message attachment и отправляет его через VK
    `messages.send`, используя общий contract голосового сообщения.

    ### Поля
    - `vkbot`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.

    ### Методы
    - `__init__`: Создаёт объект и сохраняет данные, нужные transport-layer для отправки, сравнения или восстановления объекта.
    - `send`: Отправляет сообщение или вложение через transport-layer.
    - `check_vkbot`: Проверяет vkbot перед использованием.
    - `set_vkbot`: Проверяет и сохраняет значение `vkbot` в `VoiceMessage`.
    - `get_vkbot`: Возвращает vkbot из текущего состояния `VoiceMessage`.
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
    def __init__(self, vkbot: VkApi, owner_id: int, text: str, audio_attachment: Vkbot.AudioAttachment | None, reply: Bot.Message | None = None):
        """
        Создаёт голосовое сообщение `VoiceMessage` и сохраняет вложение с аудио для transport-layer.

        ### Аргументы:
        :param vkbot: VK transport-адаптер или API-клиент
        :param owner_id: идентификатор владельца сообщения
        :param text: текст
        :param audio_attachment: audio attachment
        :param reply: сообщение, на которое дан ответ

        ### Пример использования:
        ```py
        voiceMessage = VoiceMessage(vkbot = vkbot, owner_id = owner_id, text = text, audio_attachment = audio_attachment, reply = reply)
        ```
        """
        super().__init__(owner_id, text, audio_attachment, reply)
        self.vkbot : VkApi
        self.set_vkbot(vkbot)

    def send(self, chat_id: int):
        """
        Отправляет сообщение или вложение через transport-layer.

        ### Аргументы:
        :param chat_id: идентификатор чата

        :raises VkbotException: если нижележащий слой сообщает об ошибке операции

        ### Пример использования:
        ```py
        voiceMessage.send(chat_id = chat_id)
        ```
        """
        raise VkbotException("Vkbot не поддерживает загрузку вложений кроме PhotoAttachment")


    # Методы работы с полями


    def check_vkbot(self, vkbot: VkApi) -> bool:
        """
        Проверяет значение `vkbot` перед сохранением или использованием.

        ### Аргументы:
        :param vkbot: VK transport-адаптер или API-клиент

        :return: `True`, если значение `vkbot` перед сохранением или использованием; иначе `False`

        ### Пример использования:
        ```py
        voiceMessage.check_vkbot(vkbot = vkbot)
        ```
        """
        return isinstance(vkbot, VkApi)

    def set_vkbot(self, vkbot: VkApi):
        """
        Проверяет и сохраняет значение `vkbot`.

        ### Аргументы:
        :param vkbot: VK transport-адаптер или API-клиент

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        voiceMessage.set_vkbot(vkbot = vkbot)
        ```
        """
        if self.check_vkbot(vkbot):
            self.vkbot = vkbot
        else:
            raise ValueError(f"Некорректное значение аргумента {vkbot=}")

    def get_vkbot(self) -> VkApi:
        """
        Возвращает связанный VK transport-адаптер.

        :return: vkbot

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        voiceMessage.get_vkbot()
        ```
        """
        if self.check_vkbot(self.vkbot):
            return self.vkbot
        else:
            raise ValueError(f"Некорректное значение атрибута {self.vkbot=}")


    # Переопределённые методы работы с полями


    def check_audio_attachment(self, audio_attachment: Vkbot.AudioAttachment) -> bool:
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
        return isinstance(audio_attachment, Vkbot.AudioAttachment)

    def set_audio_attachment(self, audio_attachment: Vkbot.AudioAttachment | None):
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

    def get_audio_attachment(self) -> Vkbot.AudioAttachment | None:
        """
        Возвращает VK audio_message attachment для отправки voice.

        :return: audio attachment

        ### Пример использования:
        ```py
        voiceMessage.get_audio_attachment()
        ```
        """
        return super().set_audio_attachment()
