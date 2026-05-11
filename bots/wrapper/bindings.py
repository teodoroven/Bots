"""
Связывает wrapper-сообщение с группой транспортных сообщений.
Модуль относится к wrapper-слою `bots.wrapper` и добавляет `MessagesGroup` как вложенный тип для `Message`.

### Публичные классы
- Публичные классы не объявляются; используются импортированные `Message` и `MessagesGroup`.

### Публичные функции
- Публичные функции отсутствуют.

### Связи
Используется wrapper-логикой, чтобы единое сообщение могло хранить группы отправленных сообщений по разным ботам и чатам.
"""

from bots.wrapper.message_group import MessagesGroup
from bots.wrapper.message import Message

Message.MessagesGroup = MessagesGroup
