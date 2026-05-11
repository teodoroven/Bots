"""

from __future__ import annotations

from bots.vk.bindings import Attachment
from bots.vk.bindings import AudioAttachment
from bots.vk.bindings import Button
from bots.vk.bindings import DocAttachment
from bots.vk.bindings import Keyboard
from bots.vk.bindings import Message
from bots.vk.bindings import PhotoAttachment
from bots.vk.bindings import UrlAttachment
from bots.vk.bindings import VideoAttachment
from bots.vk.bindings import Vkbot
from bots.vk.bindings import VoiceMessage

__all__: list[str] = [
    "Attachment",
    "AudioAttachment",
    "Button",
    "DocAttachment",
    "Keyboard",
    "Message",
    "PhotoAttachment",
    "UrlAttachment",
    "VideoAttachment",
    "Vkbot",
    "VoiceMessage",
]
Открывает namespace VK-адаптера `bots.vk`.
Модуль относится к архитектурной зоне: слой унификации транспортов `bots`, который скрывает различия Telegram и VK за общими объектами сообщений, клавиатур, вложений и событий.

### Публичные классы
- Публичные классы отсутствуют.

### Публичные функции
- Публичные функции отсутствуют.

### Связи
Используется транспортным слоем и wrapper-логикой, чтобы app-layer работал с `Message`, `Keyboard`, `Button`, `Attachment` и `Event` без привязки к конкретной соцсети.
"""

