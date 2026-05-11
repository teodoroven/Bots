"""
Открывает публичный namespace пользовательских и административных сессий.
Модуль относится к app-layer и явно реэкспортирует session-классы без
wildcard-импортов.
"""

from __future__ import annotations

from .admin import AdminSession
from .admin import BotControlSession
from .admin import NoHandlersSession
from .admin import SessionAdmins
from .admin import SessionUsers
from .admin import UserSession
from .appointment import ConfigureDateSession
from .appointment import DateSession
from .appointment import FilialSession
from .appointment import MainSession
from .appointment import SessionDates
from .appointment import SessionFilials
from .base import Input
from .base import Menu
from .base import MenuInput
from .base import MenuSession
from .base import Session
from .conversation import ConvSession
from .gpt import ContextSession
from .gpt import CreateLimitSession
from .gpt import GPTSession
from .gpt import LimitSession
from .gpt import ModelSession
from .gpt import QuestionSession
from .gpt import SessionContexts
from .gpt import SessionLimits
from .gpt import SessionModels
from .gpt import SessionProviders
from .gpt import SessionQuestions
from .level import Level
from .level import LevelSession
from .level import Stage
from .level import Value
from .manage import ChangeContentSession
from .manage import ManageSession
from .manage import Mode
from .manage import ModeSession

import relay.users as _users_module
import relay.users.user as _user_module

_users_module.Session = Session
_users_module.ConvSession = ConvSession
_users_module.NoHandlersSession = NoHandlersSession
_user_module.Session = Session
_user_module.ConvSession = ConvSession
_user_module.NoHandlersSession = NoHandlersSession

__all__: list[str] = [
    "AdminSession",
    "BotControlSession",
    "ChangeContentSession",
    "ConfigureDateSession",
    "ContextSession",
    "ConvSession",
    "CreateLimitSession",
    "DateSession",
    "FilialSession",
    "GPTSession",
    "Input",
    "Level",
    "LevelSession",
    "LimitSession",
    "MainSession",
    "ManageSession",
    "Menu",
    "MenuInput",
    "MenuSession",
    "Mode",
    "ModeSession",
    "ModelSession",
    "NoHandlersSession",
    "QuestionSession",
    "Session",
    "SessionAdmins",
    "SessionContexts",
    "SessionDates",
    "SessionFilials",
    "SessionLimits",
    "SessionModels",
    "SessionProviders",
    "SessionQuestions",
    "SessionUsers",
    "Stage",
    "UserSession",
    "Value",
]
