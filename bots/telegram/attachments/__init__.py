"""
Открывает namespace Telegram-вложений.
Модуль относится к архитектурной зоне: слой унификации транспортов `bots`, который скрывает различия Telegram и VK за общими объектами сообщений, клавиатур, вложений и событий.

### Публичные классы
- Публичные классы отсутствуют.

### Публичные функции
- Публичные функции отсутствуют.

### Связи
Используется транспортным слоем и wrapper-логикой, чтобы app-layer работал с `Message`, `Keyboard`, `Button`, `Attachment` и `Event` без привязки к конкретной соцсети.
"""

from bots.telegram.attachments.base import Attachment
from bots.telegram.attachments.photo import PhotoAttachment
from bots.telegram.attachments.video import VideoAttachment
from bots.telegram.attachments.doc import DocAttachment
from bots.telegram.attachments.audio import AudioAttachment
