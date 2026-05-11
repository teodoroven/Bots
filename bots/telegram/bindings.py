"""
Связывает классы Telegram-адаптера через class-level aliases.
Модуль относится к транспортному слою `bots.telegram` и задаёт доступ к `Attachment`, `Keyboard`, `Button`, `Message` и `VoiceMessage` через `Telebot`.

### Публичные классы
- Публичные классы не объявляются; используются импортированные `Telebot`, `Attachment`, `PhotoAttachment`, `VideoAttachment`, `DocAttachment`, `AudioAttachment`, `Keyboard`, `Button`, `Message` и `VoiceMessage`.

### Публичные функции
- Публичные функции отсутствуют.

### Связи
Используется `bots.runtime` и wrapper-логикой, чтобы Telegram-объекты имели тот же вложенный API, что и базовый транспорт.
"""

from bots.telegram.bot import Telebot
from bots.telegram.attachments.base import Attachment
from bots.telegram.attachments.photo import PhotoAttachment
from bots.telegram.attachments.video import VideoAttachment
from bots.telegram.attachments.doc import DocAttachment
from bots.telegram.attachments.audio import AudioAttachment
from bots.telegram.button import Button
from bots.telegram.keyboard import Keyboard
from bots.telegram.message import Message
from bots.telegram.voice_message import VoiceMessage

Keyboard.Button = Button
Telebot.Attachment = Attachment
Telebot.PhotoAttachment = PhotoAttachment
Telebot.VideoAttachment = VideoAttachment
Telebot.DocAttachment = DocAttachment
Telebot.AudioAttachment = AudioAttachment
Telebot.Keyboard = Keyboard
Telebot.Keyboard.Button = Button
Telebot.Message = Message
Telebot.VoiceMessage = VoiceMessage
