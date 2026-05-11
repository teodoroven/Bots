"""
Связывает классы VK-адаптера через class-level aliases.
Модуль относится к транспортному слою `bots.vk` и задаёт доступ к `Attachment`, `Keyboard`, `Button`, `Message` и `VoiceMessage` через `Vkbot`.

### Публичные классы
- Публичные классы не объявляются; используются импортированные `Vkbot`, `Attachment`, `UrlAttachment`, `PhotoAttachment`, `VideoAttachment`, `DocAttachment`, `AudioAttachment`, `Keyboard`, `Button`, `Message` и `VoiceMessage`.

### Публичные функции
- Публичные функции отсутствуют.

### Связи
Используется `bots.runtime` и wrapper-логикой, чтобы VK-объекты имели тот же вложенный API, что и базовый транспорт.
"""

from bots.vk.bot import Vkbot
from bots.vk.attachments.base import Attachment
from bots.vk.attachments.url import UrlAttachment
from bots.vk.attachments.photo import PhotoAttachment
from bots.vk.attachments.video import VideoAttachment
from bots.vk.attachments.doc import DocAttachment
from bots.vk.attachments.audio import AudioAttachment
from bots.vk.button import Button
from bots.vk.keyboard import Keyboard
from bots.vk.message import Message
from bots.vk.voice_message import VoiceMessage

Keyboard.Button = Button
Vkbot.Attachment = Attachment
Vkbot.UrlAttachment = UrlAttachment
Vkbot.PhotoAttachment = PhotoAttachment
Vkbot.VideoAttachment = VideoAttachment
Vkbot.DocAttachment = DocAttachment
Vkbot.AudioAttachment = AudioAttachment
Vkbot.Keyboard = Keyboard
Vkbot.Keyboard.Button = Button
Vkbot.Message = Message
Vkbot.VoiceMessage = VoiceMessage
