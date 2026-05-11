"""

from __future__ import annotations

from bots.wrapper.bindings import Message
from bots.wrapper.bindings import MessagesGroup

__all__: list[str] = [
    "Message",
    "MessagesGroup",
]
Открывает namespace wrapper-сообщений поверх конкретных транспортов.
Модуль относится к архитектурной зоне: слой унификации транспортов `bots`, который скрывает различия Telegram и VK за общими объектами сообщений, клавиатур, вложений и событий.

### Публичные классы
- Публичные классы отсутствуют.

### Публичные функции
- Публичные функции отсутствуют.

### Связи
Используется транспортным слоем и wrapper-логикой, чтобы app-layer работал с `Message`, `Keyboard`, `Button`, `Attachment` и `Event` без привязки к конкретной соцсети.
"""

