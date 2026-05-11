"""

from __future__ import annotations

from bots.telegram.bindings import Attachment
from bots.telegram.bindings import AudioAttachment
from bots.telegram.bindings import Button
from bots.telegram.bindings import DocAttachment
from bots.telegram.bindings import Keyboard
from bots.telegram.bindings import Message
from bots.telegram.bindings import PhotoAttachment
from bots.telegram.bindings import Telebot
from bots.telegram.bindings import VideoAttachment
from bots.telegram.bindings import VoiceMessage

__all__: list[str] = [
    "Attachment",
    "AudioAttachment",
    "Button",
    "DocAttachment",
    "Keyboard",
    "Message",
    "PhotoAttachment",
    "Telebot",
    "VideoAttachment",
    "VoiceMessage",
]
Открывает namespace Telegram-адаптера `bots.telegram`.
Модуль относится к архитектурной зоне: слой унификации транспортов `bots`, который скрывает различия Telegram и VK за общими объектами сообщений, клавиатур, вложений и событий.

### Публичные классы
- Публичные классы отсутствуют.

### Публичные функции
- Публичные функции отсутствуют.

### Связи
Используется транспортным слоем и wrapper-логикой, чтобы app-layer работал с `Message`, `Keyboard`, `Button`, `Attachment` и `Event` без привязки к конкретной соцсети.
"""

