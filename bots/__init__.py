"""
Открывает публичный namespace транспортного слоя `bots`.
Модуль явно реэкспортирует project API для базового, Telegram, VK и wrapper
транспортов без wildcard-импортов и без stdlib/SDK имён.
"""

from __future__ import annotations

import bots.constants as _constants
import bots.types as BotTypes
import bots.types as _types
from bots.base.bindings import Bot
from bots.runtime import bind_runtime_names
from bots.telegram.bindings import Telebot
from bots.utils.audio import AudioSegment_directory
from bots.utils.audio import converter_filename
from bots.utils.audio import ffmpeg_filename
from bots.utils.audio import ffmpeg_program_name
from bots.utils.audio import ffprobe_filename
from bots.utils.audio import ffprobe_program_name
from bots.utils.audio import local_converter_filename
from bots.utils.audio import local_ffprobe_filename
from bots.utils.dates import diff_sec
from bots.utils.dates import get_date
from bots.utils.dates import get_timestamp
from bots.utils.dates import strftime
from bots.utils.env import get_env_int
from bots.utils.env import get_env_int_set
from bots.utils.files import change_extension
from bots.utils.files import create_filename
from bots.utils.files import only_extension
from bots.utils.files import only_filename
from bots.utils.mapping import get_from
from bots.utils.mapping import get_int
from bots.utils.mapping import is_int
from bots.utils.mapping import is_iterable
from bots.utils.text import cut
from bots.utils.text import preceding
from bots.vk.bindings import Vkbot
from bots.wrapper.bindings import Message

bind_runtime_names(Bot, Vkbot, Telebot, Message)

_TYPE_EXPORTS: list[str] = [
    "ACCESS_LEVEL",
    "ADMIN_EVENT_KEYS",
    "ADMIN_EVENT_TYPE",
    "ADMIN_FILE_TYPE",
    "ADMIN_STORAGE_TYPE",
    "ATTACHMENT_CLASSNAME",
    "ATTACHMENT_KEYS",
    "ATTACHMENT_TYPE",
    "AUTOCENTER_KEYS",
    "AUTOCENTER_TYPE",
    "BOTS_ITEM_KEYS",
    "BOTS_ITEM_TYPE",
    "BOTS_TYPE",
    "BOT_KEY",
    "BUTTON_COLOR_INDEX",
    "BUTTON_KEYS",
    "BUTTON_KIND",
    "BUTTON_TYPE",
    "CHANGED_PARTS",
    "CLIENT_TYPE",
    "COMMANDS_TYPE",
    "CONVERSATION_KEYS",
    "CONVERSATION_TYPE",
    "ELEMENT_KEYS",
    "ELEMENT_TYPE",
    "EVENT_KEYS",
    "EVENT_TYPE",
    "GPT_TYPE",
    "INPUT_KEYS",
    "INPUT_TYPE",
    "JSONABLE",
    "KEYBOARD_KEYS",
    "KEYBOARD_TYPE",
    "LEGACY_USER_BOT_KEY",
    "LEVEL_KEYS",
    "LEVEL_TYPE",
    "LIMIT_TYPE",
    "MESSAGE_EVENT_KEY",
    "MESSAGE_GROUP_KEYS",
    "MESSAGE_GROUP_TYPE",
    "MESSAGE_KEYS",
    "MESSAGE_QUEUE_STATUS",
    "MESSAGE_QUEUE_TYPE",
    "MESSAGE_TYPE",
    "MESSAGE_WRAPPER_KEYS",
    "MESSAGE_WRAPPER_TYPE",
    "NOTIFICATION_KEY",
    "PARTICIPANT_TYPE",
    "PERMISSION_KEY",
    "QUESTION_TYPE",
    "QUEUE_ITEM_KEYS",
    "QUEUE_ITEM_TYPE",
    "REQUEST_TYPE",
    "RESPONSE_TYPE",
    "ROOT_TYPE",
    "SAVING_ORDER_TYPE",
    "SESSION_CONTAINER_TYPE",
    "SESSION_KEYS",
    "SESSION_STORAGE_TYPE",
    "SESSION_TYPE",
    "STAGE_KEYS",
    "STAGE_TYPE",
    "SYSTEM_CONTEXT_TYPE",
    "UNKNOWN_JSON_OBJECT",
    "USERS_IDS_TYPE",
    "USER_BOT_KEY",
    "USER_MESSAGES_TYPE",
    "USER_NAMES_TYPE",
    "USER_TYPE",
    "USER_TYPE_KEYS",
    "VALUE_KEYS",
    "VALUE_TYPE",
]

_CONSTANT_EXPORTS: list[str] = [
    "AUDIO_EXTENSIONS",
    "BOT",
    "DATE_FORMAT_1",
    "DOC_EXTENSIONS",
    "EVENT_INTERVAL",
    "EVENT_PERIOD",
    "EVENT_TIMEOUT",
    "MARKDOWN",
    "PHOTO_EXTENSIONS",
    "VIDEO_EXTENSIONS",
    "logger_telegram",
    "logger_vk",
]

_UTIL_EXPORTS: list[str] = [
    "AudioSegment_directory",
    "change_extension",
    "converter_filename",
    "create_filename",
    "cut",
    "diff_sec",
    "ffmpeg_filename",
    "ffmpeg_program_name",
    "ffprobe_filename",
    "ffprobe_program_name",
    "get_date",
    "get_env_int",
    "get_env_int_set",
    "get_from",
    "get_int",
    "get_timestamp",
    "is_int",
    "is_iterable",
    "local_converter_filename",
    "local_ffprobe_filename",
    "only_extension",
    "only_filename",
    "preceding",
    "strftime",
]

for _name in _TYPE_EXPORTS:
    globals()[_name] = getattr(_types, _name)

for _name in _CONSTANT_EXPORTS:
    globals()[_name] = getattr(_constants, _name)

__all__: list[str] = [
    "Bot",
    "BotTypes",
    "Message",
    "Telebot",
    "Vkbot",
    *_TYPE_EXPORTS,
    *_CONSTANT_EXPORTS,
    *_UTIL_EXPORTS,
]

del _constants
del _name
del _types
