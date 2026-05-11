"""
Описывает JSON-форматы и type aliases, которыми обмениваются transport, wrapper и app-layer.
Модуль относится к архитектурной зоне: слой унификации транспортов `bots`, который скрывает различия Telegram и VK за общими объектами сообщений, клавиатур, вложений и событий.

### Публичные классы
- Публичные классы отсутствуют.

### Публичные функции
- Публичные функции отсутствуют.

### Публичные константы и типы
- Модуль экспортирует JSON type aliases для сообщений, пользователей, сессий, GPT, очередей и storage-документов.

### Связи
Используется транспортным слоем и wrapper-логикой, чтобы app-layer работал с `Message`, `Keyboard`, `Button`, `Attachment` и `Event` без привязки к конкретной соцсети.
"""

from __future__ import annotations

from typing import Any
from typing import Literal


JSONABLE = None | bool | int | float | str | list["JSONABLE"] | dict[str, "JSONABLE"]

BOT_KEY = Literal["vkbot", "telebot"]
USER_BOT_KEY = Literal["", "vkbot", "telebot"]
LEGACY_USER_BOT_KEY = Literal["", "Vkbot", "Telebot", "vkbot", "telebot"]

ACCESS_LEVEL = Literal[0, 1, 2, 3]

MESSAGE_EVENT_KEY = Literal["MESSAGE_NEW", "SENT", "EDIT", "DELETE"]
CHANGED_PARTS = Literal["text", "caption", "media", "reply_markup", "reply", "forward"]

BUTTON_KIND = Literal["text", "callback_data", "url"]
BUTTON_COLOR_INDEX = Literal[0, 1, 2, 3]
BUTTON_KEYS = Literal["text", "color", "type", "callback_data", "url", "min_width"]
BUTTON_TYPE = dict[BUTTON_KEYS, str | int | None]

KEYBOARD_KEYS = Literal["buttons", "max_width", "inline", "unused_buttons"]
KEYBOARD_TYPE = dict[KEYBOARD_KEYS, int | bool | list[BUTTON_TYPE]]

ATTACHMENT_CLASSNAME = Literal[
    "Attachment",
    "PhotoAttachment",
    "VideoAttachment",
    "AudioAttachment",
    "DocAttachment",
    "UrlAttachment",
]
ATTACHMENT_KEYS = Literal[
    "id",
    "filename",
    "classname",
    "type",
    "owner_id",
    "access_key",
    "url",
    "title",
    "description",
    "duration",
    "width",
    "height",
    "file_id",
    "file_size",
    "file_name",
    "attachment",
    "attachments",
    "thumb",
    "sizes",
    "image",
    "first_frame",
    "orig_photo",
    "response_type",
    "is_gif",
    "is_web",
]
ATTACHMENT_TYPE = dict[
    ATTACHMENT_KEYS,
    str | int | bool | None | list[int] | list[dict[str, Any]] | dict[str, Any],
]

EVENT_KEYS = Literal["owner_id", "chat_id", "date", "text", "reply", "forward", "attachments", "first_name", "last_name"]
EVENT_TYPE = dict[
    EVENT_KEYS,
    int | str | None | list[dict[str, Any]] | list[ATTACHMENT_TYPE] | dict[str, Any],
]

MESSAGE_KEYS = Literal[
    "events",
    "dates",
    "text",
    "owner_id",
    "reply",
    "chat_id",
    "id",
    "attachments",
    "keyboard",
    "forward",
    "audio_attachment",
]
MESSAGE_TYPE = dict[
    MESSAGE_KEYS,
    str
    | int
    | None
    | EVENT_TYPE
    | dict[MESSAGE_EVENT_KEY, list[EVENT_TYPE]]
    | dict[MESSAGE_EVENT_KEY, list[str]]
    | list[ATTACHMENT_TYPE]
    | KEYBOARD_TYPE
    | list[dict[str, Any]]
    | dict[str, Any]
    | ATTACHMENT_TYPE,
]

MESSAGE_GROUP_KEYS = Literal["bot_key", "messages", "username", "date", "compression"]
MESSAGE_GROUP_TYPE = dict[MESSAGE_GROUP_KEYS, str | int | bool | list[MESSAGE_TYPE]]

MESSAGE_WRAPPER_KEYS = Literal["id", "text", "buttons", "groups"]
MESSAGE_WRAPPER_TYPE = dict[
    MESSAGE_WRAPPER_KEYS,
    int | str | list[str] | list[BUTTON_TYPE] | dict[str, dict[int, list[MESSAGE_GROUP_TYPE]]],
]

SESSION_CONTAINER_TYPE = list[int | str]
SESSION_STORAGE_TYPE = dict[LEGACY_USER_BOT_KEY, list[SESSION_CONTAINER_TYPE]]
USER_MESSAGES_TYPE = dict[BOT_KEY, list[MESSAGE_WRAPPER_TYPE]]
USER_NAMES_TYPE = dict[BOT_KEY, str]
USER_TYPE_KEYS = Literal[
    "access_level",
    "sessions",
    "messages",
    "usernames",
    "names",
    "saved_messages",
    "client",
    "history",
    "requests",
    "responses",
]
USER_TYPE = dict[
    USER_TYPE_KEYS,
    int
    | SESSION_STORAGE_TYPE
    | USER_MESSAGES_TYPE
    | USER_NAMES_TYPE
    | list[int]
    | list[MESSAGE_GROUP_TYPE]
    | list[dict[str, Any]]
    | dict[str, int | list[dict[str, int | bool | str]]],
]

INPUT_KEYS = Literal[
    "question",
    "answers",
    "lang_answers",
    "actions",
    "lang_actions",
    "choosen",
    "default",
    "max_buttons",
    "min",
    "max",
    "required",
    "confirm",
    "cancel",
    "back",
    "skip",
    "actions_page",
    "answers_page",
    "finished",
]
INPUT_TYPE = dict[INPUT_KEYS, int | str | dict[str, JSONABLE] | bool | list[str] | JSONABLE]

STAGE_KEYS = Literal["asked", "confirming", "confirmed"]
STAGE_TYPE = dict[STAGE_KEYS, bool]
VALUE_KEYS = Literal["value", "stage"]
VALUE_TYPE = dict[VALUE_KEYS, str | STAGE_TYPE]
LEVEL_KEYS = Literal["value"]
LEVEL_TYPE = dict[LEVEL_KEYS, VALUE_TYPE]

SESSION_KEYS = Literal[
    "id",
    "input",
    "level",
    "levels",
    "element_id",
    "mode",
    "provider",
    "model",
    "admin_notifications",
]
SESSION_TYPE = dict[SESSION_KEYS, int | str | INPUT_TYPE | list[LEVEL_TYPE] | list[MESSAGE_WRAPPER_TYPE]]

ELEMENT_KEYS = Literal[
    "classname",
    "id",
    "parent_id",
    "removed_from",
    "enabled",
    "lang_name",
    "name",
    "elements",
    "date",
    "question",
    "answers",
    "content",
    "tokens",
    "period",
    "limit",
    "left",
    "shared",
]
ELEMENT_TYPE = dict[
    ELEMENT_KEYS,
    str | int | bool | None | list[str] | list[dict[str, Any]],
]

LIMIT_TYPE = dict[Literal["classname", "id", "parent_id", "removed_from", "period", "limit", "date", "left", "shared"], int | bool | None | str]
CLIENT_TYPE = dict[Literal["id", "limits"], int | list[LIMIT_TYPE]]
QUESTION_TYPE = dict[Literal["classname", "id", "parent_id", "removed_from", "question", "answers"], int | str | None | list[str]]
SYSTEM_CONTEXT_TYPE = dict[Literal["classname", "id", "parent_id", "removed_from", "content", "tokens"], int | str | None]

PARTICIPANT_TYPE = dict[Literal["user_id", "bot_key", "chat_id"], str | int]
CONVERSATION_KEYS = Literal["id", "message", "messages", "users", "admins", "admin_messages", "removable_messages"]
CONVERSATION_TYPE = dict[
    CONVERSATION_KEYS,
    int
    | MESSAGE_WRAPPER_TYPE
    | list[MESSAGE_GROUP_TYPE]
    | dict[str, dict[int, PARTICIPANT_TYPE]]
    | list[int]
    | dict[int, MESSAGE_WRAPPER_TYPE]
    | dict[str, MESSAGE_TYPE],
]

PERMISSION_KEY = Literal["answer_users", "start_dialog"]
NOTIFICATION_KEY = Literal["call_admin", "new_appointment"]
ADMIN_STORAGE_TYPE = dict[
    int,
    dict[Literal["access_level", "permissions", "notifications"], int | dict[PERMISSION_KEY, bool] | dict[NOTIFICATION_KEY, bool]],
]
ADMIN_FILE_TYPE = dict[
    str,
    dict[Literal["access_level", "permissions", "notifications"], int | dict[PERMISSION_KEY, bool] | dict[NOTIFICATION_KEY, bool]],
]

MESSAGE_QUEUE_STATUS = Literal["pending", "sending", "sent", "failed"]
QUEUE_ITEM_KEYS = Literal[
    "id",
    "message",
    "bot_key",
    "chat_id",
    "compression",
    "parse_mode",
    "status",
    "attempts",
    "last_error",
    "created_at",
    "updated_at",
]
QUEUE_ITEM_TYPE = dict[QUEUE_ITEM_KEYS, int | str | bool | MESSAGE_WRAPPER_TYPE]
MESSAGE_QUEUE_TYPE = dict[Literal["last_id", "items"], int | list[QUEUE_ITEM_TYPE | dict[str, JSONABLE]]]

REQUEST_TYPE = dict[
    Literal["classname", "id", "parent_id", "removed_from", "model", "context_id", "context", "messages", "tokens"],
    int | str | None | list[dict[str, str]],
]
RESPONSE_TYPE = dict[Literal["id", "request_id", "content", "tokens"], int | str]

AUTOCENTER_KEYS = Literal["message_id", "session_id", "event_id", "bot_enabled", "admins"]
AUTOCENTER_TYPE = dict[AUTOCENTER_KEYS, int | bool | list[int]]

BOTS_ITEM_KEYS = Literal["bot_key", "token", "name", "group_id"]
BOTS_ITEM_TYPE = dict[BOTS_ITEM_KEYS, str | int]
BOTS_TYPE = dict[Literal["bots"], list[BOTS_ITEM_TYPE]]

ROOT_TYPE = dict[Literal["root"], ELEMENT_TYPE]
GPT_TYPE = dict[
    Literal["contexts", "context", "questions", "model", "clients", "limits", "shared_client", "user_client", "apikey"],
    list[SYSTEM_CONTEXT_TYPE] | int | None | list[QUESTION_TYPE] | str | list[CLIENT_TYPE] | list[LIMIT_TYPE] | CLIENT_TYPE,
]

COMMANDS_TYPE = dict[str, dict[str, JSONABLE]]
UNKNOWN_JSON_OBJECT = dict[str, Any]

SAVING_ORDER_TYPE = dict[Literal["order", "in_progress"], list[dict[str, JSONABLE]]]
ADMIN_EVENT_KEYS = Literal["id", "next_process", "started", "finished", "admin_list"]
ADMIN_EVENT_TYPE = dict[ADMIN_EVENT_KEYS, int | str | bool | None | list[int]]
USERS_IDS_TYPE = dict[int | str, dict[BOT_KEY, list[int] | set[int]]]
