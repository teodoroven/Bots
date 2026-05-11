"""
Открывает публичный namespace доменной модели `relay.domain`.
Модуль относится к app-layer и явно реэкспортирует классы каталога,
GPT-настроек и базовой доменной иерархии без wildcard-импортов.
"""

from __future__ import annotations

from .base import Element
from .base import Folder
from .base import NamedElement
from .base import NamedFolder
from .base import Root
from .catalog import Date
from .catalog import Filial
from .catalog import InteractiveMixin
from .catalog import MonthDate
from .folders import ContextsFolder
from .folders import DatesFolder
from .folders import FilialsFolder
from .folders import LimitsFolder
from .folders import QuestionsFolder
from .folders import RootFolder
from .gpt import Client
from .gpt import Limit
from .gpt import Question
from .gpt import SystemContext

import relay.domain.base as _base_module

_base_module.InteractiveMixin = InteractiveMixin

__all__: list[str] = [
    "Client",
    "ContextsFolder",
    "Date",
    "DatesFolder",
    "Element",
    "Filial",
    "FilialsFolder",
    "Folder",
    "InteractiveMixin",
    "Limit",
    "LimitsFolder",
    "MonthDate",
    "NamedElement",
    "NamedFolder",
    "Question",
    "QuestionsFolder",
    "Root",
    "RootFolder",
    "SystemContext",
]
