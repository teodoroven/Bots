"""
Собирает app-layer объект и его runtime-миксины.
Модуль относится к архитектурной зоне: прикладной слой `relay`, который связывает пользователей, сессии, доменную модель, GPT, уведомления и runtime-логику приложения.

### Публичные классы
- `App`: главный app-layer класс, который объединяет runtime-миксины и настройки приложения.

### Публичные функции
- Публичные функции отсутствуют.

### Связи
Используется app-layer сценариями, обработчиками, сессиями и runtime-миксинами для единого пользовательского потока между ботами, GPT и storage.
"""

from __future__ import annotations


from bots import Telebot
from bots import Vkbot
from bots.constants import BOT
from bots.types import BOT_KEY
from relay.domain import ContextsFolder
from relay.domain import Date
from relay.domain import DatesFolder
from relay.domain import Element
from relay.domain import Filial
from relay.domain import FilialsFolder
from relay.domain import Folder
from relay.domain import Limit
from relay.domain import LimitsFolder
from relay.domain import MonthDate
from relay.domain import NamedElement
from relay.domain import NamedFolder
from relay.domain import Question
from relay.domain import QuestionsFolder
from relay.domain import Root
from relay.domain import SystemContext
from relay.sessions import AdminSession
from relay.sessions import BotControlSession
from relay.sessions import ChangeContentSession
from relay.sessions import ConfigureDateSession
from relay.sessions import ContextSession
from relay.sessions import ConvSession
from relay.sessions import CreateLimitSession
from relay.sessions import DateSession
from relay.sessions import FilialSession
from relay.sessions import GPTSession
from relay.sessions import LimitSession
from relay.sessions import MainSession
from relay.sessions import ModelSession
from relay.sessions import NoHandlersSession
from relay.sessions import QuestionSession
from relay.sessions import Session
from relay.sessions import SessionAdmins
from relay.sessions import SessionContexts
from relay.sessions import SessionDates
from relay.sessions import SessionFilials
from relay.sessions import SessionLimits
from relay.sessions import SessionModels
from relay.sessions import SessionProviders
from relay.sessions import SessionQuestions
from relay.sessions import SessionUsers
from relay.sessions import UserSession
from .common import BotTypes
from .runtime import AdminsMixin
from .runtime import BotsMixin
from .runtime import ConversationsMixin
from .runtime import DomainMixin
from .runtime import GptRuntimeMixin
from .runtime import LifecycleMixin
from .runtime import MessageQueueMixin
from .runtime import MessagingMixin
from .runtime import ProcessTaskMixin
from .runtime import UsersMixin


class App(
        LifecycleMixin,
        MessageQueueMixin,
        ProcessTaskMixin,
        AdminsMixin,
        UsersMixin,
        MessagingMixin,
        GptRuntimeMixin,
        ConversationsMixin,
        DomainMixin,
        BotsMixin
):
        """
        Собирает основной app-layer объект приложения.
        `App` объединяет runtime-миксины, registry транспортов, сессий и доменных типов. Экземпляр создаётся bootstrap-слоем, загружает состояние из storage и маршрутизирует входящие события через handlers и sessions.

        ### Поля
        - `AUTOCENTER_TYPE`: публичный тип сериализованного состояния app-layer.
        - `BOTS_TYPE`: публичный тип конфигурации транспортных ботов.
        - `BOT_KEYS`: registry классов транспортных ботов по ключам `vkbot` и `telebot`.
        - `SESSIONS`: registry классов сессий для восстановления сохранённых сценариев из storage.
        - `PERIODS`: подписи периодов для отображения лимитов и интервалов.
        - `ELEMENTS`: registry доменных элементов для десериализации каталога автошколы.
        - `FOLDERS`: типы доменных элементов, которые считаются папками дерева каталога.

        ### Жизненный цикл
        Экземпляр создаётся bootstrap-слоем, загружает состояние из storage, подключает транспорты и дальше маршрутизирует события через handlers и sessions.

        ### Пример использования
        ```py
        app: App = App()
        ```
        """
        AUTOCENTER_TYPE = BotTypes.AUTOCENTER_TYPE

        BOTS_TYPE = BotTypes.BOTS_TYPE

        BOT_KEYS: dict[BOT_KEY, BOT] = {
            "vkbot": Vkbot,
            "telebot": Telebot
        }

        SESSIONS: dict[str, type[Session]] = {
            "MainSession": MainSession,
            "GPTSession": GPTSession,
            "SessionUsers": SessionUsers,
            "UserSession": UserSession,
            "SessionAdmins": SessionAdmins,
            "AdminSession": AdminSession,
            "BotControlSession": BotControlSession,
            "SessionProviders": SessionProviders,
            "SessionModels": SessionModels,
            "ModelSession": ModelSession,
            "SessionContexts": SessionContexts,
            "ContextSession": ContextSession,
            "SessionQuestions": SessionQuestions,
            "QuestionSession": QuestionSession,
            "SessionLimits": SessionLimits,
            "LimitSession": LimitSession,
            "CreateLimitSession": CreateLimitSession,
            "SessionFilials": SessionFilials,
            "FilialSession": FilialSession,
            "DateSession": DateSession,
            "SessionDates": SessionDates,
            "ConfigureDateSession": ConfigureDateSession,
            "ConvSession": ConvSession,
            "ChangeContentSession": ChangeContentSession,
            "NoHandlersSession": NoHandlersSession
        }

        PERIODS: dict[int, str] = {
            1: "period_second",
            60: "period_minute",
            60*60: "period_hour",
            60*60*24: "period_day",
            60*60*24*7: "period_week",
            60*60*24*30: "period_month"
        }

        ELEMENTS: dict[str, type[Element | NamedElement | Folder | NamedFolder | Filial | Date]] = {
            "Element": Element,
            "NamedElement": NamedElement,
            "Folder": Folder,
            "NamedFolder": NamedFolder,
            "Filial": Filial,
            "Date": Date,
            "MonthDate": MonthDate,
            "FilialsFolder": FilialsFolder,
            "DatesFolder": DatesFolder,
            "ContextsFolder": ContextsFolder,
            "QuestionsFolder": QuestionsFolder,
            "LimitsFolder": LimitsFolder,
            "SystemContext": SystemContext,
            "Question": Question,
            "Limit": Limit
        }

        FOLDERS: tuple[type[Folder | NamedFolder]] = (Folder, NamedFolder, Root, Filial, FilialsFolder, DatesFolder, ContextsFolder, QuestionsFolder, LimitsFolder)


# Compatibility alias for old imports and tests.
Autocenter = App
