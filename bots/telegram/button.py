"""
Описывает кнопку клавиатуры конкретного слоя.
Модуль относится к архитектурной зоне: слой унификации транспортов `bots`, который скрывает различия Telegram и VK за общими объектами сообщений, клавиатур, вложений и событий.

### Публичные классы
- `Button`: модель кнопки клавиатуры бота.

### Публичные функции
- Публичные функции отсутствуют.

### Связи
Используется транспортным слоем и wrapper-логикой, чтобы app-layer работал с `Message`, `Keyboard`, `Button`, `Attachment` и `Event` без привязки к конкретной соцсети.
"""

from __future__ import annotations


from bots.utils.mapping import get_from
from bots.compat import BotTypes, Literal, VkKeyboardColor
from bots.types import BUTTON_TYPE, Literal

from bots.base.bindings import Bot
from bots.base.attachment import Attachment as BaseAttachment
from bots.base.button import Button as BaseButton
from bots.base.keyboard import Keyboard as BaseKeyboard
from bots.base.message import Message as BaseMessageClass
from bots.base.voice_message import VoiceMessage as BaseVoiceMessage

class Button(BaseButton):
    """
    Хранит Telegram-кнопку и сериализует её в общий transport-формат.

    Кнопка может быть callback-кнопкой, URL-кнопкой или обычной кнопкой,
    где текст используется как callback payload.
    """
    BUTTON_TYPE = BotTypes.BUTTON_TYPE

    @staticmethod
    def loads(data: BUTTON_TYPE) -> Telebot.Keyboard.Button:
        """
        Восстанавливает Telegram-кнопку из словаря, сохранённого `dumps`.
        """
        text: str = get_from(data, "text")
        callback_data: str = get_from(data, "callback_data")
        url: str = get_from(data, "url")
        return Telebot.Keyboard.Button(text, callback_data = callback_data, url = url)

    def __init__(self, text: str, callback_data: str | None = None, url: str | None = None):
        """
        Создаёт кнопку `Button` для transport-layer и сохраняет данные, из которых конкретный адаптер собирает клавиатуру.
        """
        super().__init__(text, callback_data = callback_data, url = url)

    def dumps(self) -> BUTTON_TYPE:
        """
        Возвращает JSON-совместимый словарь для сохранения кнопки в сообщении.
        """
        return {
            "text": self.get_text(),
            "type": self.get_type(),
            **self.get_kwarg()
        }

    def get_kwarg(self) -> dict[str, str]:
        """
        Возвращает аргумент Telegram-кнопки: `url` или `callback_data`.
        """
        match self.get_type():
            case "url":
                return {"url": self.url}
            case "callback_data":
                return {"callback_data": self.callback_data}
            case _:
                return {"callback_data": self.get_text()}

    def set_color(self, color: Literal[0, 1, 2, 3] | str | VkKeyboardColor):
        """
        Игнорирует цвет, потому что Telegram inline-кнопки не поддерживают palette API.
        """
        pass
