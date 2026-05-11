"""
Открывает публичный namespace базовых классов transport-layer.
Модуль относится к слою `bots` и экспортирует общие классы `Bot`,
`BaseMessage`, `Message`, `Event`, `Keyboard`, `Button`, `Attachment`
и `VoiceMessage`, через которые `relay` работает с Telegram и VK без
прямой зависимости от SDK конкретного транспорта.
"""

from __future__ import annotations

from bots.base.bindings import Attachment
from bots.base.bindings import BaseMessage
from bots.base.bindings import Bot
from bots.base.bindings import Button
from bots.base.bindings import Event
from bots.base.bindings import Keyboard
from bots.base.bindings import Message
from bots.base.bindings import VoiceMessage

__all__: list[str] = [
    "Attachment",
    "BaseMessage",
    "Bot",
    "Button",
    "Event",
    "Keyboard",
    "Message",
    "VoiceMessage",
]

