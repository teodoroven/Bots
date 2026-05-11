"""
Связывает runtime-имена базовых классов ботов с конкретными Telegram и VK реализациями.
Модуль относится к архитектурной зоне: слой унификации транспортов `bots`, который скрывает различия Telegram и VK за общими объектами сообщений, клавиатур, вложений и событий.

### Публичные классы
- Публичные классы отсутствуют.

### Публичные функции
- `bind_runtime_names`: связывает базовые runtime-имена с конкретными реализациями транспорта.

### Связи
Используется транспортным слоем и wrapper-логикой, чтобы app-layer работал с `Message`, `Keyboard`, `Button`, `Attachment` и `Event` без привязки к конкретной соцсети.
"""

from __future__ import annotations

import sys

def bind_runtime_names(Bot, Vkbot, Telebot, Message):
    names = {
        "Bot": Bot,
        "Vkbot": Vkbot,
        "Telebot": Telebot,
        "Message": Message,
    }
    for module_name, module in list(sys.modules.items()):
        if module_name == "bots" or module_name.startswith("bots."):
            module.__dict__.update(names)
