"""
Хранит строковые ключи callback data для кнопок, сессий и административных сценариев.
Модуль относится к архитектурной зоне: корневой слой проекта, который связывает запуск, compatibility exports и общие настройки приложения.

### Публичные классы
- Публичные классы отсутствуют.

### Публичные функции
- Публичные функции отсутствуют.

### Публичные константы и типы
- Модуль экспортирует callback keys `str` для кнопок, сессий, действий и административных сценариев.

### Связи
Используется соседними слоями проекта как корневой модуль запуска, compatibility exports или общий набор настроек.
"""

from typing import Literal

SESSION_CALLBACK: Literal["SID"] = "SID"
CONV_CALLBACK: Literal["CID"] = "CID"
ANSWER_CALLBACK: Literal["ANS"] = "ANS"
ACTION_CALLBACK: Literal["ACT"] = "ACT"
SELECT_ALL_CALLBACK: Literal["select_all_callback"] = "select_all_callback"
CONFIRM_CALLBACK: Literal["confirm_callback"] = "confirm_callback"
CANCEL_CALLBACK: Literal["cancel_callback"] = "cancel_callback"
SKIP_CALLBACK: Literal["skip_callback"] = "skip_callback"
BACK_CALLBACK: Literal["back_callback"] = "back_callback"
NEXT_CALLBACK: Literal["next_callback"] = "next_callback"
CREATE_CALLBACK: Literal["create_callback"] = "create_callback"
EMPTY_CALLBACK: Literal["empty_callback"] = "empty_callback"
REMOVE_CALLBACK: Literal["remove_callback"] = "remove_callback"
RESTORE_CALLBACK: Literal["restore_callback"] = "restore_callback"
CHOOSE_CALLBACK: Literal["choose_callback"] = "choose_callback"
QUESTIONS_CALLBACK: Literal["questions_callback"] = "questions_callback"
CHANGE_CALLBACK: Literal["change_callback"] = "change_callback"
ADD_CALLBACK: Literal["add_callback"] = "add_callback"
ENABLE_CALLBACK: Literal["enable_callback"] = "enable_callback"
DISABLE_CALLBACK: Literal["disable_callback"] = "disable_callback"
ACCEPT_CALLBACK: Literal["accept_callback"] = "accept_callback"
DECLINE_CALLBACK: Literal["decline_callback"] = "decline_callback"
CONFIGURE_CALLBACK: Literal["configure_callback"] = "configure_callback"
FINISH_CALLBACK: Literal["finish_callback"] = "finish_callback"
HELP_CALLBACK: Literal["help_callback"] = "help_callback"
MORE_CALLBACK: Literal["more_callback"] = "more_callback"
SAVE_CALLBACK: Literal["save_callback"] = "save_callback"
IGNORE_CALLBACK: Literal["ignore_callback"] = "ignore_callback"
DIALOG_CALLBACK: Literal["start_dialog"] = "start_dialog"
PREV_ACTIONS_CALLBACK: Literal["prev_actions_callback"] = "prev_actions_callback"
NEXT_ACTIONS_CALLBACK: Literal["next_actions_callback"] = "next_actions_callback"
MORE_ACTIONS_CALLBACK: Literal["more_actions_callback"] = "more_actions_callback"
BACK_ACTIONS_CALLBACK: Literal["back_actions_callback"] = "back_actions_callback"
PREV_ANSWERS_CALLBACK: Literal["prev_answers_callback"] = "prev_answers_callback"
NEXT_ANSWERS_CALLBACK: Literal["next_answers_callback"] = "next_answers_callback"

CALLBACK_MAIN: Literal["CALLBACKMAIN"] = "CALLBACKMAIN"
CALLBACK_CALLADMIN: Literal["CALLADMIN"] = "CALLADMIN"  # FIXME: -> STARTDIALOG
CALLBACK_CALL_ADMIN: Literal["CALL_ADMIN"] = "CALL_ADMIN"
CALLBACK_MODELS: Literal["MODELS"] = "MODELS"
CALLBACK_LIMITS: Literal["LIMITS"] = "LIMITS"
CALLBACK_CONTEXTS: Literal["CONTEXTS"] = "CONTEXTS"
CALLBACK_QUESTIONS: Literal["QUESTIONS"] = "QUESTIONS"
CALLBACK_FILIALS: Literal["FILIALS"] = "FILIALS"
CALLBACK_DATES: Literal["DATES"] = "DATES"
CALLBACK_SHOWDIALOG: Literal["SHOWDIALOG"] = "SHOWDIALOG"
CALLBACK_CLOSEDIALOG: Literal["CLOSEDIALOG"] = "CLOSEDIALOG"
CALLBACK_FINISHDIALOG: Literal["FINISHDIALOG"] = "FINISHDIALOG"
CALLBACK_USERS: Literal["USERS"] = "USERS"
CALLBACK_ADMINS: Literal["ADMINS"] = "ADMINS"
CALLBACK_BOTCON: Literal["BOTCON"] = "BOTCON"
CALLBACK_GPTCON: Literal["GPTCON"] = "GPTCON"
CALLBACK_REMOVE: Literal["REMOVE_MESSAGE"] = "RM_C"

SHARED_CALLBACK: Literal["shared_callback"] = "shared_callback"
NOTSHARED_CALLBACK: Literal["notshared_callback"] = "notshared_callback"
PERIOD_CALLBACK: Literal["period_callback"] = "period_callback"
NOTIFICATIONS_CALLBACK: Literal["notifications"] = "notifications"
PERMISSIONS_CALLBACK: Literal["permissions"] = "permissions"
ANSWER_USERS_CALLBACK: Literal["admin_permission_answer_users"] = "admin_permission_answer_users"
CALL_ADMIN_NOTIFICATION_CALLBACK: Literal["admin_notification_call_admin"] = "admin_notification_call_admin"
NEW_APPOINTMENT_NOTIFICATION_CALLBACK: Literal["admin_notification_new_appointment"] = "admin_notification_new_appointment"
PROMOTE_VKBOT_CALLBACK: Literal["promote_vkbot_callback"] = "promote_vkbot_callback"
PROMOTE_TELEBOT_CALLBACK: Literal["promote_telebot_callback"] = "promote_telebot_callback"

