"""
Связывает базовые классы транспорта `bots.base` через class-level aliases.
Модуль относится к слою унификации транспортов `bots` и задаёт доступ к `Attachment`, `Event`, `Keyboard`, `Button`, `Message` и `VoiceMessage` через базовый `Bot`.

### Публичные классы
- Публичные классы не объявляются; используются импортированные `Bot`, `Attachment`, `Event`, `Keyboard`, `Button`, `BaseMessage`, `Message` и `VoiceMessage`.

### Публичные функции
- Публичные функции отсутствуют.

### Связи
Используется runtime-сборкой транспорта, чтобы app-layer мог обращаться к вложенным типам вроде `Bot.Keyboard.Button` и `Bot.Message` единообразно.
"""

from bots.base.bot import Bot
from bots.base.attachment import Attachment
from bots.base.event import Event
from bots.base.button import Button
from bots.base.keyboard import Keyboard
from bots.base.base_message import BaseMessage
from bots.base.message import Message
from bots.base.voice_message import VoiceMessage

Keyboard.Button = Button
Bot.Attachment = Attachment
Bot.Event = Event
Bot.Keyboard = Keyboard
Bot.Keyboard.Button = Button
Bot.BaseMessage = BaseMessage
Bot.Message = Message
Bot.VoiceMessage = VoiceMessage
