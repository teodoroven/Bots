"""
Собирает общие type aliases, лимиты и константы транспортного слоя `bots`.
Модуль относится к архитектурной зоне: слой унификации транспортов `bots`, который скрывает различия Telegram и VK за общими объектами сообщений, клавиатур, вложений и событий.

### Публичные классы
- Публичные классы отсутствуют.

### Публичные функции
- Публичные функции отсутствуют.

### Публичные константы и типы
- Модуль экспортирует type aliases, media limits, timeout values и extension sets транспортного слоя.

### Связи
Используется транспортным слоем и wrapper-логикой, чтобы app-layer работал с `Message`, `Keyboard`, `Button`, `Attachment` и `Event` без привязки к конкретной соцсети.
"""

from __future__ import annotations

import logging
from typing import Literal
from typing import Union

import bots.types as BotTypes

BOT = Union["Vkbot", "Telebot"]
BOT_KEY = BotTypes.BOT_KEY
CHANGED_PARTS = BotTypes.CHANGED_PARTS
JSONABLE = BotTypes.JSONABLE

MARKDOWN: Literal["MarkdownV2"] = "MarkdownV2"
DATE_FORMAT_1: str = "%d.%m.%Y %H:%M:%S"
EVENT_TIMEOUT: int = 1  # seconds

# Период между сообщениями для объединения
EVENT_PERIOD: float = 1  # seconds

# Период ожидания после неудачной попытки объединения для обработки необъединённых событий
EVENT_INTERVAL: int = 2  # seconds

PHOTO_EXTENSIONS: tuple[str, str, str] = (".jpeg", ".jpg", ".png")
VIDEO_EXTENSIONS: tuple[str] = (".mp4",)
AUDIO_EXTENSIONS: tuple[str, str, str, str] = (".wav", ".mp3", ".ogg", ".oga")
DOC_EXTENSIONS: tuple[str, str, str] = (".bin", ".txt", ".docx")

logger_vk = logging.getLogger("bot.vk")
logger_telegram = logging.getLogger("bot.telegram")
