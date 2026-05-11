"""
Открывает namespace VK-вложений.
Модуль относится к архитектурной зоне: слой унификации транспортов `bots`, который скрывает различия Telegram и VK за общими объектами сообщений, клавиатур, вложений и событий.

### Публичные классы
- Публичные классы отсутствуют.

### Публичные функции
- Публичные функции отсутствуют.

### Связи
Используется транспортным слоем и wrapper-логикой, чтобы app-layer работал с `Message`, `Keyboard`, `Button`, `Attachment` и `Event` без привязки к конкретной соцсети.
"""

from bots.vk.attachments.base import Attachment
from bots.vk.attachments.url import UrlAttachment
from bots.vk.attachments.photo import PhotoAttachment
from bots.vk.attachments.video import VideoAttachment
from bots.vk.attachments.doc import DocAttachment
from bots.vk.attachments.audio import AudioAttachment
