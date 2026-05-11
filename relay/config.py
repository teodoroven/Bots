"""
Хранит лимиты сообщений, callback separator, permission keys, notification keys, logger-объекты и настройки очереди.
Модуль относится к архитектурной зоне: прикладной слой `relay`, который связывает пользователей, сессии, доменную модель, GPT, уведомления и runtime-логику приложения.

### Публичные классы
- Публичные классы отсутствуют.

### Публичные функции
- Публичные функции отсутствуют.

### Публичные константы и типы
- Модуль экспортирует лимиты сообщений, callback separator, permission keys, notification keys, logger-объекты и настройки очереди.

### Связи
Используется app-layer сценариями, обработчиками, сессиями и runtime-миксинами для единого пользовательского потока между ботами, GPT и storage.
"""

from __future__ import annotations




from modules import get_json_filenames
from bots import Bot
from bots import Telebot
from bots import Vkbot
from .common import BotTypes, Phrases, TypeVar, logging
T = TypeVar('T')
CALLBACK_SEPARATOR: str = ";;"
__phrases__: Phrases = Phrases(get_json_filenames("lang"), "ru")
get_phrase = __phrases__.get_phrase
get_phrase_list = __phrases__.get_phrase_list

BUTTON_LENGTH: int = Bot.Keyboard.MAX_BUTTON_LENGTH
MESSAGE_LENGTH: int = Bot.Message.MAX_LENGTH
MAX_REQUEST_LENGTH: int = MESSAGE_LENGTH * 2
MAX_RESPONSE_LENGTH: int = MESSAGE_LENGTH
INPUT_LENGTH: int = MESSAGE_LENGTH // 4
MAX_INPUT_LENGTH: int = MESSAGE_LENGTH * 4
MAX_PRINT_LENGTH: int = 100

MAX_USERS: int = 100
MAX_MESSAGES: int = 10
MAX_HISTORY: int = 100
MAX_REQUESTS: int = 100
MAX_RESPONSES: int = 100
MAX_USER_SESSIONS: int = 2
MAX_ADMIN_SESSIONS: int = 5
MAX_PROCESS_TASKS: int = 5
PROCESS_TASK_TIMEOUT: float = 0.2
CHATGPT_DEBOUNCE_WAIT_SECONDS: int = 3
CHATGPT_MAX_DEBOUNCE_MESSAGES: int = 10
CHATGPT_DEBOUNCE_POLL_SECONDS: float = 0.05

PERMISSION_KEY = BotTypes.PERMISSION_KEY
NOTIFICATION_KEY = BotTypes.NOTIFICATION_KEY

PERMISSION_KEYS: tuple[PERMISSION_KEY] = (
    "answer_users",
    "start_dialog",
)

NOTIFICATION_KEYS: tuple[NOTIFICATION_KEY] = (
    "call_admin",
    "new_appointment",
)

DEFAULT_PERMISSIONS: dict[PERMISSION_KEY, bool] = {
    "answer_users": True,
    "start_dialog": False,
}

DEFAULT_NOTIFICATIONS: dict[NOTIFICATION_KEY, bool] = {
    "call_admin": True,
    "new_appointment": True,
}

SYSTEM_ADMIN_ACCESS_LEVEL: int = 3

BOT_KEYS: dict[BOT_KEY, BOT] = {
    "vkbot": Vkbot,
    "telebot": Telebot
}

PERIODS: dict[int, str] = {
    1: "period_second",
    60: "period_minute",
    60*60: "period_hour",
    60*60*24: "period_day",
    60*60*24*7: "period_week",
    60*60*24*30: "period_month"
}

logger = logging.getLogger("bot.main")
logger_gpt = logging.getLogger("bot.gpt")
logger_sessions = logging.getLogger("bot.sessions")
logger_admin = logging.getLogger("bot.admin")
logger_queue = logging.getLogger("bot.message_queue")
logger_user_flow = logging.getLogger("bot.user_flow")

SKIP_POLLING: int = 10
MESSAGE_QUEUE_RETRY_INTERVAL: float = 5
MESSAGE_QUEUE_RETRIES: int = 3
MESSAGE_QUEUE_SENT_LIMIT: int = 500
MESSAGE_QUEUE_STATUS = BotTypes.MESSAGE_QUEUE_STATUS
