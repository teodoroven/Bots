"""
Описывает GPT-запросы, ответы и wrapper провайдера.
Модуль относится к архитектурной зоне: прикладной слой `relay`, который связывает пользователей, сессии, доменную модель, GPT, уведомления и runtime-логику приложения.

### Публичные классы
- `SessionProviders`: сессия выбора GPT-провайдера.
- `SessionModels`: сессия списка GPT-моделей.
- `ModelSession`: сессия выбора GPT-модели.
- `SessionContexts`: сессия списка GPT-контекстов.
- `ContextSession`: сессия управления GPT-контекстом.
- `SessionQuestions`: сессия списка GPT-вопросов.
- `QuestionSession`: сессия управления GPT-вопросом.
- `SessionLimits`: сессия списка GPT-лимитов.
- `CreateLimitSession`: сессия создания GPT-лимита.
- `LimitSession`: сессия управления GPT-лимитом.
- `GPTSession`: сессия настройки GPT.

### Публичные функции
- Публичные функции отсутствуют.

### Связи
Используется app-layer сценариями, обработчиками, сессиями и runtime-миксинами для единого пользовательского потока между ботами, GPT и storage.
"""

from __future__ import annotations




from relay.common import (
    Any,
    BotTypes,
    Literal,
    Model,
    abstractmethod,
)
from relay.config import MESSAGE_LENGTH, PERIODS, get_phrase
from relay.gpt import GPT, Request
from .level import Level, LevelSession
from .manage import ManageSession, ModeSession
from relay.users import User
from relay.utils import (
    is_float,
    is_int,
    join_callback,
    log_warn,
    parse_period,
)
class SessionProviders(ModeSession):
    """
    Описывает пользовательскую или административную сессию `SessionProviders`.
    Сессия хранит состояние текущего пользовательского сценария, обновляет сообщения и завершает себя через общий session lifecycle.

    ### Поля
    - `DESCRIPTION_KEY`: ключ сериализации или transport-события, по которому объект отличает один вариант данных от другого.
    - `get_model`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `get_provider`: идентификатор объекта или связанной сущности, по которому runtime восстанавливает связь между слоями.
    - `get_providers`: идентификатор объекта или связанной сущности, по которому runtime восстанавливает связь между слоями.
    - `element_class`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `next_session`: runtime-зависимость или поле, используемое текущим session-сценарием.

    ### Методы
    - `__init__`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `get_model`: Возвращает модель GPT из текущего состояния `SessionProviders`.
    - `get_provider`: Возвращает провайдера GPT из текущего состояния `SessionProviders`.
    - `get_providers`: Возвращает провайдеров GPT из текущего состояния `SessionProviders`.
    - `get_title`: Возвращает title из текущего состояния `SessionProviders`.
    - `get_question`: Возвращает вопрос анкеты или GPT-контекста из текущего состояния `SessionProviders`.
    - `get_answers`: Возвращает варианты ответа из текущего состояния `SessionProviders`.
    - `get_next_level`: Возвращает next level из текущего состояния `SessionProviders`.

    ### Жизненный цикл
    Создаётся app-layer кодом, участвует в обработке пользовательского события и сохраняет изменённое состояние через существующие runtime/storage механизмы.

    ### Пример использования
    ```py
    session: SessionProviders
    ```
    """
    DESCRIPTION_KEY: str = "provider_description"

    def __init__(self, session_id: int, context: Context, data: dict, message: Message):
        """
        Создаёт session-объект `SessionProviders` и сохраняет состояние пользовательского сценария между входящими событиями.

        ### Аргументы:
        :param session_id: идентификатор сессии
        :param context: контекст обработки события
        :param data: сериализованный словарь
        :param message: сообщение проекта или сообщение конкретного транспорта

        ### Пример использования:
        ```py
        sessionProviders = SessionProviders(session_id = session_id, context = context, data = data, message = message)
        ```
        """
        super().__init__(session_id, context, data, message)
        self.get_model = context.autocenter.get_model
        self.get_provider = context.autocenter.get_provider
        self.get_providers = context.autocenter.get_providers

        self.element_class = None
        self.next_session = SessionModels

        self.always_actions.clear()
        # self.choosing_actions.clear()
        self.removed_actions.clear()

        self.set_mode(data.get("mode", ""))

    @abstractmethod
    def get_model(self) -> Model | None:
        """
        Возвращает выбранную GPT-модель.

        :return: GPT-модель

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        sessionProviders.get_model()
        ```
        """
        raise NotImplementedError()

    @abstractmethod
    def get_provider(self, model: str | Model) -> str | None:
        """
        Возвращает выбранного GPT-провайдера.

        ### Аргументы:
        :param model: GPT-модель

        :return: GPT-провайдер

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        sessionProviders.get_provider(model = model)
        ```
        """
        raise NotImplementedError()

    @abstractmethod
    def get_providers(self) -> Iterable[str]:
        """
        Возвращает список настроенных GPT-провайдеров.

        :return: providers

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        sessionProviders.get_providers()
        ```
        """
        raise NotImplementedError()

    def get_title(self, answers: dict[str, JSONABLE]) -> str:
        """
        Возвращает заголовок элемента для меню и списков.

        ### Аргументы:
        :param answers: варианты ответа

        :return: заголовок элемента для пользовательского интерфейса

        ### Пример использования:
        ```py
        sessionProviders.get_title(answers = answers)
        ```
        """
        title: str = get_phrase("providers")
        return f"{title}: {len(answers)}"

    def get_question(self, answers: dict[str, JSONABLE] = {}) -> str:
        """
        Возвращает краткое описание элемента для вывода в чат.

        ### Аргументы:
        :param answers: варианты ответа

        :return: строка вида `Филиал «Название»` или `Элемент «id»`

        ### Пример использования:
        ```py
        sessionProviders.get_question(answers = answers)
        ```
        """
        description: str = self.get_description()

        if description:
            description = f"\n{description}"

        title: str = self.get_title(answers)
        return f"{title}{description}"

    def get_answers(self) -> dict[str, str]:
        """
        Возвращает варианты ответа для текущего меню.

        :return: варианты ответа

        ### Пример использования:
        ```py
        sessionProviders.get_answers()
        ```
        """
        model: Model | None = self.get_model()
        self.input.set_choosen([])

        if model:
            provider: Literal["Anthropic", "DeepSeek", "Google", "OpenAI"] | None = self.get_provider(model)

            if provider:
                self.input.choosen.append(provider)

        return {
            provider_name: provider_name for provider_name in self.get_providers()
        }

    def get_next_level(self, provider: Literal["Anthropic", "DeepSeek", "Google", "OpenAI"]) -> dict[str, int]:
        """
        Возвращает следующий шаг выбора GPT provider/model.

        ### Аргументы:
        :param provider: GPT-провайдер

        :return: next level

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        sessionProviders.get_next_level(provider = provider)
        ```
        """
        if not provider:
            raise ValueError(f"Некорректное значение аргумента {provider=}")

        return {
            "provider": str(provider).strip()
        }


class SessionModels(ModeSession):
    """
    Описывает пользовательскую или административную сессию `SessionModels`.
    Сессия хранит состояние текущего пользовательского сценария, обновляет сообщения и завершает себя через общий session lifecycle.

    ### Поля
    - `DESCRIPTION_KEY`: ключ сериализации или transport-события, по которому объект отличает один вариант данных от другого.
    - `get_model`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `get_models`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `get_models_list`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `get_provider`: идентификатор объекта или связанной сущности, по которому runtime восстанавливает связь между слоями.
    - `get_providers`: идентификатор объекта или связанной сущности, по которому runtime восстанавливает связь между слоями.
    - `get_providers_models`: идентификатор объекта или связанной сущности, по которому runtime восстанавливает связь между слоями.
    - `element_class`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `next_session`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `provider`: хранит провайдера GPT для операций этого объекта.

    ### Методы
    - `__init__`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `dumps`: Возвращает JSON-совместимый снимок объекта для storage или callback payload.
    - `validate_provider`: Проверяет ограничения для провайдера GPT и при необходимости завершает лишние объекты.
    - `update_data`: Обновляет data с учётом текущего состояния объекта.
    - `get_model`: Возвращает модель GPT из текущего состояния `SessionModels`.
    - `get_models`: Возвращает модели GPT из текущего состояния `SessionModels`.
    - `get_models_list`: Возвращает models list из текущего состояния `SessionModels`.
    - `get_provider`: Возвращает провайдера GPT из текущего состояния `SessionModels`.
    - `get_providers`: Возвращает провайдеров GPT из текущего состояния `SessionModels`.
    - `get_providers_models`: Возвращает providers models из текущего состояния `SessionModels`.

    ### Жизненный цикл
    Создаётся app-layer кодом, участвует в обработке пользовательского события и сохраняет изменённое состояние через существующие runtime/storage механизмы.

    ### Пример использования
    ```py
    session: SessionModels
    ```
    """
    DESCRIPTION_KEY: str = "models_description"

    def __init__(self, session_id: int, context: Context, data: dict, message: Message):
        """
        Создаёт session-объект `SessionModels` и сохраняет состояние пользовательского сценария между входящими событиями.

        ### Аргументы:
        :param session_id: идентификатор сессии
        :param context: контекст обработки события
        :param data: сериализованный словарь
        :param message: сообщение проекта или сообщение конкретного транспорта

        ### Пример использования:
        ```py
        sessionModels = SessionModels(session_id = session_id, context = context, data = data, message = message)
        ```
        """
        super().__init__(session_id, context, data, message)
        self.get_model = context.autocenter.get_model
        self.get_models = context.autocenter.get_models
        self.get_models_list = context.autocenter.get_models_list
        self.get_provider = context.autocenter.get_provider
        self.get_providers = context.autocenter.get_providers
        self.get_providers_models = context.autocenter.get_providers_models

        self.element_class = None
        self.next_session = ModelSession
        self.provider: Literal["Anthropic", "DeepSeek", "Google", "OpenAI"] = data.get("provider", "")

        self.always_actions.clear()
        # self.choosing_actions.clear()
        self.removed_actions.clear()


        self.validate_provider()

        self.set_mode(data.get("mode", ""))

    def dumps(self) -> BotTypes.SESSION_TYPE:
        """
        Возвращает JSON-совместимый снимок объекта для storage или callback payload.

        :return: JSON-совместимый словарь для сохранения или передачи между слоями

        ### Пример использования:
        ```py
        sessionModels.dumps()
        ```
        """
        result: BotTypes.SESSION_TYPE = super().dumps()

        result.update({
            "provider": self.provider
        })

        return result

    def validate_provider(self) -> bool:
        """
        Проверяет значение перед переходом к следующему шагу сценария.

        :return: результат шага сессии

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        sessionModels.validate_provider()
        ```
        """
        if self.provider in ("Anthropic", "DeepSeek", "Google", "OpenAI"):
            return True
        else:
            raise ValueError(f"Некорректное значение атрибута {self.provider=}")
            self.finish()
            return False

    def update_data(self, data: dict):
        """
        Обновляет data с учётом текущего состояния объекта.

        ### Аргументы:
        :param data: JSON-совместимые данные для соответствующего repository

        ### Пример использования:
        ```py
        session.update_data(data = data)
        ```
        """
        self.provider = data.get("provider", "")
        self.validate_provider()

    @abstractmethod
    def get_model(self) -> Model | None:
        """
        Возвращает выбранную GPT-модель.

        :return: GPT-модель

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        sessionModels.get_model()
        ```
        """
        raise NotImplementedError()

    @abstractmethod
    def get_models(self, provider: Literal["Anthropic", "DeepSeek", "Google", "OpenAI"]) -> dict[str, Model]:
        """
        Возвращает модели выбранного GPT-провайдера.

        ### Аргументы:
        :param provider: GPT-провайдер

        :return: models

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        sessionModels.get_models(provider = provider)
        ```
        """
        raise NotImplementedError()

    @abstractmethod
    def get_models_list(self, provider: Literal["Anthropic", "DeepSeek", "Google", "OpenAI"]) -> list[str]:
        """
        Возвращает список имён моделей выбранного провайдера.

        ### Аргументы:
        :param provider: GPT-провайдер

        :return: models list

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        sessionModels.get_models_list(provider = provider)
        ```
        """
        raise NotImplementedError()

    @abstractmethod
    def get_provider(self, model: str | Model) -> str | None:
        """
        Возвращает выбранного GPT-провайдера.

        ### Аргументы:
        :param model: GPT-модель

        :return: GPT-провайдер

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        sessionModels.get_provider(model = model)
        ```
        """
        raise NotImplementedError()

    @abstractmethod
    def get_providers(self) -> Iterable[str]:
        """
        Возвращает список доступных GPT-провайдеров.

        :return: providers

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        sessionModels.get_providers()
        ```
        """
        raise NotImplementedError()

    @abstractmethod
    def get_providers_models(self) -> dict[str, dict[str, Model]]:
        """
        Возвращает mapping провайдеров на модели.

        :return: providers models

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        sessionModels.get_providers_models()
        ```
        """
        raise NotImplementedError()


    def get_button_text(self, model: Model) -> str:
        """
        Возвращает текст кнопки выбора модели.

        ### Аргументы:
        :param model: GPT-модель

        :return: button text

        ### Пример использования:
        ```py
        sessionModels.get_button_text(model = model)
        ```
        """
        return f"{model.model} {model.economy_rating}₽"

    def get_title(self, answers: dict[str, JSONABLE]) -> str:
        """
        Возвращает заголовок элемента для меню и списков.

        ### Аргументы:
        :param answers: варианты ответа

        :return: заголовок элемента для пользовательского интерфейса

        ### Пример использования:
        ```py
        sessionModels.get_title(answers = answers)
        ```
        """
        title: str = get_phrase("models")
        return f"{title}: {len(answers)}"

    def get_question(self, answers: dict[str, JSONABLE] = {}) -> str:
        """
        Возвращает краткое описание элемента для вывода в чат.

        ### Аргументы:
        :param answers: варианты ответа

        :return: строка вида `Филиал «Название»` или `Элемент «id»`

        ### Пример использования:
        ```py
        sessionModels.get_question(answers = answers)
        ```
        """
        description: str = self.get_description()

        if description:
            description = f"\n{description}"

        title: str = self.get_title(answers)
        return f"{title}{description}"

    def get_answers(self) -> dict[str, str]:
        """
        Возвращает варианты ответа для текущего меню.

        :return: варианты ответа

        ### Пример использования:
        ```py
        sessionModels.get_answers()
        ```
        """
        model: Model | None = self.get_model()
        provider: Literal["Anthropic", "DeepSeek", "Google", "OpenAI"] | None = self.get_provider(model)
        self.input.set_choosen([])

        if model is not None and provider and provider == self.provider:
            model: Model = self.get_model()
            self.input.choosen.append(self.get_button_text(model))

        self.validate_provider()
        models_list: list[Model] = list(self.get_models(self.provider).values())
        models_list.sort(key = lambda model: model.economy_rating)
        return {
            self.get_button_text(model): model.model for model in models_list
        }

    def get_next_level(self, model: str) -> dict[str, int]:
        """
        Возвращает следующий шаг настройки модели.

        ### Аргументы:
        :param model: GPT-модель

        :return: next level

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        sessionModels.get_next_level(model = model)
        ```
        """
        self.validate_provider()

        if not model:
            raise ValueError(f"Некорректное значение аргумента {model=}")

        return {
            "provider": str(self.provider),
            "model": str(model)
        }


class ModelSession(ManageSession):
    """
    Описывает пользовательскую или административную сессию `ModelSession`.
    Сессия хранит состояние текущего пользовательского сценария, обновляет сообщения и завершает себя через общий session lifecycle.

    ### Поля
    - `DESCRIPTION_KEY`: ключ сериализации или transport-события, по которому объект отличает один вариант данных от другого.
    - `get_model`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `find_model`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `set_model`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `element_class`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `provider`: хранит провайдера GPT для операций этого объекта.
    - `model`: хранит модель GPT для операций этого объекта.

    ### Методы
    - `__init__`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `dumps`: Возвращает JSON-совместимый снимок объекта для storage или callback payload.
    - `update_data`: Обновляет data с учётом текущего состояния объекта.
    - `get_model`: Возвращает модель GPT из текущего состояния `ModelSession`.
    - `find_model`: Ищет модель GPT по данным, которые пришли из вызывающего слоя.
    - `set_model`: Проверяет и сохраняет модель GPT в состоянии `ModelSession`.
    - `get_element`: Возвращает элемент доменной модели из текущего состояния `ModelSession`.
    - `is_current`: Проверяет, относится ли объект к текущему выбранному GPT-элементу.
    - `get_description`: Возвращает description из текущего состояния `ModelSession`.
    - `get_question`: Возвращает вопрос анкеты или GPT-контекста из текущего состояния `ModelSession`.

    ### Жизненный цикл
    Создаётся app-layer кодом, участвует в обработке пользовательского события и сохраняет изменённое состояние через существующие runtime/storage механизмы.

    ### Пример использования
    ```py
    session: ModelSession
    ```
    """
    DESCRIPTION_KEY: str = "model_description"

    def __init__(self, session_id: int, context: Context, data: dict, message: Message):
        """
        Создаёт session-объект `ModelSession` и сохраняет состояние пользовательского сценария между входящими событиями.

        ### Аргументы:
        :param session_id: идентификатор сессии
        :param context: контекст обработки события
        :param data: сериализованный словарь
        :param message: сообщение проекта или сообщение конкретного транспорта

        ### Пример использования:
        ```py
        session = ModelSession(session_id = session_id, context = context, data = data, message = message)
        ```
        """
        super().__init__(session_id, context, data, message)
        self.get_model = context.autocenter.get_model
        self.find_model = context.autocenter.find_model
        self.set_model = context.autocenter.set_model

        self.element_class = Model
        self.provider: Literal["Anthropic", "DeepSeek", "Google", "OpenAI"] = data.get("provider", "")
        self.model: str = data.get("model", "")

        # self.always_actions.clear()
        self.removed_actions.clear()
        self.enabled_actions.clear()

    def dumps(self) -> BotTypes.SESSION_TYPE:
        """
        Возвращает JSON-совместимый снимок объекта для storage или callback payload.

        :return: JSON-совместимый словарь для сохранения или передачи между слоями

        ### Пример использования:
        ```py
        session.dumps()
        ```
        """
        result: BotTypes.SESSION_TYPE = super().dumps()

        result.update({
            "provider": self.provider,
            "model": self.model
        })

        return result

    def update_data(self, data: dict[str, str]):
        """
        Обновляет data с учётом текущего состояния объекта.

        ### Аргументы:
        :param data: JSON-совместимые данные для соответствующего repository

        ### Пример использования:
        ```py
        session.update_data(data = data)
        ```
        """
        self.provider: Literal["Anthropic", "DeepSeek", "Google", "OpenAI"] = data.get("provider", "")
        self.model: str = data.get("model", "")


    @abstractmethod
    def get_model(self) -> Model | None:
        """
        Возвращает выбранную GPT-модель.

        :return: GPT-модель

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        session.get_model()
        ```
        """
        raise NotImplementedError()

    @abstractmethod
    def find_model(self, provider: Literal["Anthropic", "DeepSeek", "Google", "OpenAI"], model: str) -> Model:
        """
        Ищет GPT-модель в текущих данных объекта или storage.

        ### Аргументы:
        :param provider: GPT-провайдер
        :param model: GPT-модель

        :return: GPT-модель или None, если подходящей записи нет

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        session.find_model(provider = provider, model = model)
        ```
        """
        raise NotImplementedError()

    @abstractmethod
    def set_model(self, provider: Literal["Anthropic", "DeepSeek", "Google", "OpenAI"], model: str):
        """
        Проверяет и сохраняет GPT-модель в объекте.

        ### Аргументы:
        :param provider: GPT-провайдер
        :param model: GPT-модель

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        session.set_model(provider = provider, model = model)
        ```
        """
        raise NotImplementedError()


    def get_element(self) -> Model:
        """
        Возвращает привязанный доменный элемент.

        :return: доменный элемент

        ### Пример использования:
        ```py
        session.get_element()
        ```
        """
        return self.find_model(self.provider, self.model)

    def is_current(self) -> bool:
        """
        Проверяет, относится ли объект к текущему выбранному GPT-элементу.

        :return: `True`, если относится ли объект к текущему выбранному GPT-элементу; иначе `False`

        ### Пример использования:
        ```py
        session.is_current()
        ```
        """
        model: Model | None = self.get_model()

        return model and model.model == self.model and self.model

    def get_description(self) -> str:
        """
        Возвращает описание GPT-контекста или вопроса для меню.

        :return: description

        ### Пример использования:
        ```py
        session.get_description()
        ```
        """
        self.validate_element()
        model: Model = self.get_element()

        # Формирование списка возможностей
        features: list[str] = []
        if model.reasoning:
            features.append(get_phrase("reasoning"))
        if model.search:
            features.append(get_phrase("search"))
        if model.audio:
            features.append(get_phrase("audio"))

        # Формирование текста возможностей
        features_text: str
        if features:
            features_text = ", ".join(features)
        else:
            features_text = get_phrase("basic_capabilities")

        # Подготовка переменных для f-строки
        model_label: str = get_phrase("model")
        context_label: str = get_phrase("context")
        tokens_label: str = get_phrase("n_tokens")
        price_request_label: str = get_phrase("price_request")
        price_response_label: str = get_phrase("price_response")
        per_1k_label: str = get_phrase("per_tokens")
        capabilities_label: str = get_phrase("capabilities")
        ratings_label: str = get_phrase("ratings")
        power_label: str = get_phrase("power")
        economy_label: str = get_phrase("economy")
        out_of_10_label: str = get_phrase("out_of_10")

        # Формирование итоговой строки с красивым форматированием
        description: str = (
            # f"• {model_label}: {model.model}\n"
            f"• {context_label}: {model.max_context:,} {tokens_label}\n"
            f"• {price_request_label}: {model.price_per_request}₽ {per_1k_label}\n"
            f"• {price_response_label}: {model.price_per_response}₽ {per_1k_label}\n"
            f"• {capabilities_label}: {features_text}\n"
            f"• {ratings_label}:\n"
            f"  - {power_label}: {model.power_rating} {out_of_10_label}\n"
            f"  - {economy_label}: {model.economy_rating} {out_of_10_label}"
        )

        return description

    def get_question(self, answers: Never = {}) -> str:
        """
        Возвращает краткое описание элемента для вывода в чат.

        ### Аргументы:
        :param answers: варианты ответа

        :return: строка вида `Филиал «Название»` или `Элемент «id»`

        ### Пример использования:
        ```py
        session.get_question(answers = answers)
        ```
        """
        description: str = self.get_description()

        if description:
            description = f"\n{description}"

        title: str = get_phrase("model_title").format(self.provider, self.model)
        current: str = get_phrase("model_current") if self.is_current() else ""
        return f"{title}{current}{description}"

    def get_actions(self, answers: Iterable[str] = {}) -> dict[str, str]:
        """
        Возвращает действия управления GPT-сущностью.

        ### Аргументы:
        :param answers: варианты ответа

        :return: actions

        ### Пример использования:
        ```py
        session.get_actions(answers = answers)
        ```
        """
        result: dict[str, JSONABLE] = {}  # super().get_actions(answers)

        if not self.is_current():
            result.update({
                "choose": CHOOSE_CALLBACK
            })

        return result

    def choose_element(self):
        """
        Выполняет следующий шаг текущей сессии.

        ### Пример использования:
        ```py
        session.choose_element()
        ```
        """
        self.set_model(self.provider, self.model)
        self.show_message(get_phrase("model_selected").format(self.model))
        self.input_default()


class SessionContexts(ModeSession):
    """
    Описывает пользовательскую или административную сессию `SessionContexts`.
    Сессия хранит состояние текущего пользовательского сценария, обновляет сообщения и завершает себя через общий session lifecycle.

    ### Поля
    - `DESCRIPTION_KEY`: ключ сериализации или transport-события, по которому объект отличает один вариант данных от другого.
    - `get_context`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `create_element`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `remove_element`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `folder_id`: идентификатор объекта или связанной сущности, по которому runtime восстанавливает связь между слоями.
    - `element_id`: идентификатор объекта или связанной сущности, по которому runtime восстанавливает связь между слоями.
    - `element_class`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `next_session`: runtime-зависимость или поле, используемое текущим session-сценарием.

    ### Методы
    - `__init__`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `get_context`: Возвращает контекст обработки события из текущего состояния `SessionContexts`.
    - `update_data`: Обновляет data с учётом текущего состояния объекта.
    - `check_choosen`: Проверяет choosen перед использованием.

    ### Жизненный цикл
    Создаётся app-layer кодом, участвует в обработке пользовательского события и сохраняет изменённое состояние через существующие runtime/storage механизмы.

    ### Пример использования
    ```py
    session: SessionContexts
    ```
    """
    DESCRIPTION_KEY: str = "contexts_description"

    def __init__(self, session_id: int, context: Context, data: dict, message: Message):
        """
        Создаёт session-объект `SessionContexts` и сохраняет состояние пользовательского сценария между входящими событиями.

        ### Аргументы:
        :param session_id: идентификатор сессии
        :param context: контекст обработки события
        :param data: сериализованный словарь
        :param message: сообщение проекта или сообщение конкретного транспорта

        ### Пример использования:
        ```py
        sessionContexts = SessionContexts(session_id = session_id, context = context, data = data, message = message)
        ```
        """
        super().__init__(session_id, context, data, message)
        self.get_context = context.autocenter.get_context
        self.create_element = context.autocenter.create_context
        self.remove_element = context.autocenter.remove_context

        self.folder_id: int = context.autocenter.contexts_folder.id
        self.element_id = context.autocenter.contexts_folder.id
        self.element_class = ContextsFolder
        self.next_session = ContextSession

        self.always_actions.update({
            "questions": QUESTIONS_CALLBACK,
        })

        self.set_mode(data.get("mode", ""))

    @abstractmethod
    def get_context(self) -> SystemContext | None:
        """
        Возвращает GPT-контекст.

        :return: context

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        sessionContexts.get_context()
        ```
        """
        raise NotImplementedError()

    def update_data(self, data: dict[str, str]):
        """
        Обновляет data с учётом текущего состояния объекта.

        ### Аргументы:
        :param data: JSON-совместимые данные для соответствующего repository

        ### Пример использования:
        ```py
        session.update_data(data = data)
        ```
        """
        super().update_data(data)
        self.element_id = self.folder_id

    def check_choosen(self, system_context: SystemContext) -> bool:
        """
        Проверяет значение `choosen` перед сохранением или использованием.

        ### Аргументы:
        :param system_context: system context

        :return: `True`, если значение `choosen` перед сохранением или использованием; иначе `False`

        ### Пример использования:
        ```py
        sessionContexts.check_choosen(system_context = system_context)
        ```
        """
        current_context: SystemContext | None = self.get_context()
        return current_context and current_context.id == system_context.id


class ContextSession(ManageSession):
    """
    Описывает пользовательскую или административную сессию `ContextSession`.
    Сессия хранит состояние текущего пользовательского сценария, обновляет сообщения и завершает себя через общий session lifecycle.

    ### Поля
    - `DESCRIPTION_KEY`: ключ сериализации или transport-события, по которому объект отличает один вариант данных от другого.
    - `CONTENT_DISPLAY_LENGTH`: ограничение размера, которое защищает transport/API от слишком длинного payload.
    - `get_context`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `set_context`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `remove_context`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `create_message_id`: идентификатор объекта или связанной сущности, по которому runtime восстанавливает связь между слоями.
    - `get_bot`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `catch_message_send`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `element_class`: runtime-зависимость или поле, используемое текущим session-сценарием.

    ### Методы
    - `__init__`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `get_context`: Возвращает контекст обработки события из текущего состояния `ContextSession`.
    - `set_context`: Проверяет и сохраняет контекст обработки события в состоянии `ContextSession`.
    - `remove_context`: Удаляет контекст обработки события из внутреннего состояния или storage.
    - `create_message_id`: Создаёт message id и связывает результат с текущим app-layer состоянием.
    - `get_bot`: Возвращает bot из текущего состояния `ContextSession`.
    - `is_current`: Проверяет, относится ли объект к текущему выбранному GPT-элементу.
    - `get_content`: Возвращает контент GPT-запроса из текущего состояния `ContextSession`.
    - `get_header`: Возвращает header из текущего состояния `ContextSession`.
    - `get_question`: Возвращает вопрос анкеты или GPT-контекста из текущего состояния `ContextSession`.

    ### Жизненный цикл
    Создаётся app-layer кодом, участвует в обработке пользовательского события и сохраняет изменённое состояние через существующие runtime/storage механизмы.

    ### Пример использования
    ```py
    session: ContextSession
    ```
    """
    DESCRIPTION_KEY: str = "context_description"
    CONTENT_DISPLAY_LENGTH: int = MESSAGE_LENGTH // 8

    def __init__(self, session_id: int, context: Context, data: dict, message: Message):
        """
        Создаёт session-объект `ContextSession` и сохраняет состояние пользовательского сценария между входящими событиями.

        ### Аргументы:
        :param session_id: идентификатор сессии
        :param context: контекст обработки события
        :param data: сериализованный словарь
        :param message: сообщение проекта или сообщение конкретного транспорта

        ### Пример использования:
        ```py
        session = ContextSession(session_id = session_id, context = context, data = data, message = message)
        ```
        """
        super().__init__(session_id, context, data, message)
        self.get_context = context.autocenter.get_context
        self.set_context = context.autocenter.set_context
        self.remove_context = context.autocenter.remove_context
        self.create_message_id = context.autocenter.create_message_id
        self.get_bot = context.autocenter.get_bot
        self.catch_message_send = context.autocenter.catch_message_send

        self.element_class = SystemContext
        self.always_actions.update({
            "questions": QUESTIONS_CALLBACK,
            "change": CHANGE_CALLBACK,
            "add": ADD_CALLBACK
        })
        self.get_actions()

        # self.removed_actions.clear()
        self.enabled_actions.clear()


    @abstractmethod
    def get_context(self) -> SystemContext | None:
        """
        Возвращает GPT-контекст.

        :return: context

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        session.get_context()
        ```
        """
        raise NotImplementedError()

    @abstractmethod
    def set_context(self, context_id: int) -> SystemContext | None:
        """
        Проверяет и сохраняет значение `context`.

        ### Аргументы:
        :param context_id: context id

        :return: результат шага сессии

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        session.set_context(context_id = context_id)
        ```
        """
        raise NotImplementedError()

    @abstractmethod
    def remove_context(self, context_id: int) -> bool:
        """
        Удаляет GPT-контекст из выбранного набора.

        ### Аргументы:
        :param context_id: context id

        :return: результат шага сессии

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        session.remove_context(context_id = context_id)
        ```
        """
        raise NotImplementedError()

    @abstractmethod
    def create_message_id(self) -> int:
        """
        Создаёт message id и связывает результат с текущим app-layer состоянием.

        :return: созданный объект для message id

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Примеры вызова:
        ```py
        session.create_message_id()
        ```
        """
        raise NotImplementedError()

    @abstractmethod
    def get_bot(self, bot_key: BOT_KEY) -> BOT:
        """
        Возвращает привязанный transport-адаптер.

        ### Аргументы:
        :param bot_key: ключ транспорта

        :return: transport-адаптер

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        session.get_bot(bot_key = bot_key)
        ```
        """
        raise NotImplementedError()


    def is_current(self) -> bool:
        """
        Проверяет, относится ли объект к текущему выбранному GPT-элементу.

        :return: `True`, если относится ли объект к текущему выбранному GPT-элементу; иначе `False`

        ### Пример использования:
        ```py
        session.is_current()
        ```
        """
        system_context: SystemContext = self.get_element()
        current_context: SystemContext | None = self.get_context()
        return current_context is not None and system_context is not None and system_context.id == current_context.id

    def get_content(self, max_length: int | None = None) -> str | None:
        """
        Возвращает сохранённый текст доменного элемента.

        ### Аргументы:
        :param max_length: максимальная длина проверяемого текста

        :return: содержимое доменного элемента

        ### Пример использования:
        ```py
        session.get_content(max_length = max_length)
        ```
        """
        system_context: SystemContext | None = self.get_element()

        if system_context:
            if max_length is None or len(system_context.content) <= max_length:
                return system_context.content
            else:
                first_part: str = cut(system_context.content, max_length//2, dots = False)
                second_part: str = system_context.content[(-max_length//2):]
                return f"{first_part}\n<...>\n{second_part}"
        else:
            self.validate_element()
            return None

    def get_header(self, answers: Never = {}) -> str:
        """
        Возвращает заголовок списка GPT-вопросов.

        ### Аргументы:
        :param answers: варианты ответа

        :return: header

        ### Пример использования:
        ```py
        session.get_header(answers = answers)
        ```
        """
        system_context: SystemContext | None = self.get_element()
        title: str = super().get_question(answers)
        current: str = get_phrase("context_current") if self.is_current() else ""

        symbols: str = get_phrase("symbols")
        tokens: str = get_phrase("n_tokens")
        length: str = f"{symbols}: {len(system_context.content)}" if system_context and system_context.content else ""
        length += f", {tokens}: {system_context.tokens}" if length and system_context.tokens else ""
        length = f", {length}" if length else ""
        return f"{title}{current}{length}\n"

    def get_question(self, answers: Never = {}) -> str:
        """
        Возвращает краткое описание элемента для вывода в чат.

        ### Аргументы:
        :param answers: варианты ответа

        :return: строка вида `Филиал «Название»` или `Элемент «id»`

        ### Пример использования:
        ```py
        session.get_question(answers = answers)
        ```
        """
        system_context: SystemContext | None = self.get_element()

        if system_context:
            result: str = self.get_header(answers)
            content: str = self.get_content(max_length = self.__class__.CONTENT_DISPLAY_LENGTH - len(result) - 3)
            content = f"«{content}»" if content else ""

            if not content.strip():
                no_context: str = get_phrase("empty_context")
                result = f"{result[:-1]}: {no_context}"

            return f"{result}{content}".strip()
        else:
            # -> element_removed permanently
            return super().get_question(answers)

    def get_actions(self, answers: Iterable[str] = {}) -> dict[str, str]:
        """
        Возвращает действия управления GPT-вопросом.

        ### Аргументы:
        :param answers: варианты ответа

        :return: actions

        ### Пример использования:
        ```py
        session.get_actions(answers = answers)
        ```
        """
        system_context: SystemContext | None = self.get_element()

        if not system_context:
            return super().get_actions(answers)

        result: dict[str, str] = super().get_actions(answers)

        if not self.is_current():
            result.update({
                "choose": CHOOSE_CALLBACK
            })

        system_context: SystemContext | None = self.get_element()
        content_length: int = len(system_context.content)
        header_length: int = len(self.get_header(answers))

        if content_length + header_length > self.__class__.CONTENT_DISPLAY_LENGTH:
            result.update({
                "more": MORE_CALLBACK
            })

        return result

    def choose_element(self):
        """
        Выполняет следующий шаг текущей сессии.

        ### Пример использования:
        ```py
        session.choose_element()
        ```
        """
        system_context: SystemContext | None = self.get_element()
        self.set_context(self.element_id)
        self.show_message(get_phrase("context_selected").format(system_context.get_answer(cut_string = False)))
        self.input_default()

    def remove_element(self):
        """
        Удаляет элемент доменной модели из внутреннего состояния или storage.

        ### Примеры вызова:
        ```py
        session.remove_element()
        ```
        """
        element: Element | None = self.get_element()

        if element:
            self.remove_context(element.id)
        else:
            self.validate_element()

    def process_action(self, bot_key: BOT_KEY, chat_id: int, action: str) -> bool:
        """
        Обрабатывает действие меню в текущем runtime-контексте.

        ### Аргументы:
        :param bot_key: ключ транспорта
        :param chat_id: идентификатор чата
        :param action: действие меню

        :return: результат шага сессии

        ### Пример использования:
        ```py
        session.process_action(bot_key = bot_key, chat_id = chat_id, action = action)
        ```
        """


        if action == MORE_CALLBACK:
            system_context: SystemContext = self.get_element()

            if not system_context:
                return

            content: str = self.get_content()
            self.show_message(content)

            if bot_key == "telebot":
                filename: str = create_filename(ATTACHMENTS_FOLDER, f"{system_context.get_answer(cut_string = True)}{DOC_EXTENSIONS[1]}")

                try:
                    if not isdir(ATTACHMENTS_FOLDER):
                        makedirs(ATTACHMENTS_FOLDER)

                    with open(filename, "w", encoding = "utf-8") as file:
                        file.write(content)
                except Exception as err:
                    log_warn(f"Ошибка при записи контекста {system_context=} в файл {filename=} {err=}")

                try:
                    file_message: Message = Message(self.create_message_id(), "", filenames = [filename])
                    self.catch_message_send(file_message, self.get_bot(bot_key), chat_id)
                except Exception as err:
                    log_warn(f"Ошибка при отправке файла контекста {filename=} пользователю {bot_key=} {chat_id=}")

            self.reset()
            return True
        else:
            return super().process_action(bot_key, chat_id, action)


class SessionQuestions(ModeSession):
    """
    Описывает пользовательскую или административную сессию `SessionQuestions`.
    Сессия хранит состояние текущего пользовательского сценария, обновляет сообщения и завершает себя через общий session lifecycle.

    ### Поля
    - `DESCRIPTION_KEY`: ключ сериализации или transport-события, по которому объект отличает один вариант данных от другого.
    - `create_element`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `remove_element`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `folder_id`: идентификатор объекта или связанной сущности, по которому runtime восстанавливает связь между слоями.
    - `element_id`: идентификатор объекта или связанной сущности, по которому runtime восстанавливает связь между слоями.
    - `element_class`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `next_session`: runtime-зависимость или поле, используемое текущим session-сценарием.

    ### Методы
    - `__init__`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `update_data`: Обновляет data с учётом текущего состояния объекта.

    ### Жизненный цикл
    Создаётся app-layer кодом, участвует в обработке пользовательского события и сохраняет изменённое состояние через существующие runtime/storage механизмы.

    ### Пример использования
    ```py
    session: SessionQuestions
    ```
    """
    DESCRIPTION_KEY: str = "questions_description"

    def __init__(self, session_id: int, context: Context, data: dict, message: Message):
        """
        Создаёт session-объект `SessionQuestions` и сохраняет состояние пользовательского сценария между входящими событиями.

        ### Аргументы:
        :param session_id: идентификатор сессии
        :param context: контекст обработки события
        :param data: сериализованный словарь
        :param message: сообщение проекта или сообщение конкретного транспорта

        ### Пример использования:
        ```py
        sessionQuestions = SessionQuestions(session_id = session_id, context = context, data = data, message = message)
        ```
        """
        super().__init__(session_id, context, data, message)
        self.create_element = context.autocenter.create_question
        self.remove_element = context.autocenter.remove_question

        self.folder_id: int = context.autocenter.questions_folder.id
        self.element_id = context.autocenter.questions_folder.id
        self.element_class = QuestionsFolder
        self.next_session = QuestionSession

        self.set_mode(data.get("mode", ""))

    def update_data(self, data: dict[str, str]):
        """
        Обновляет data с учётом текущего состояния объекта.

        ### Аргументы:
        :param data: JSON-совместимые данные для соответствующего repository

        ### Пример использования:
        ```py
        session.update_data(data = data)
        ```
        """
        super().update_data(data)
        self.element_id = self.folder_id


class QuestionSession(ManageSession):
    """
    Описывает пользовательскую или административную сессию `QuestionSession`.
    Сессия хранит состояние текущего пользовательского сценария, обновляет сообщения и завершает себя через общий session lifecycle.

    ### Поля
    - `DESCRIPTION_KEY`: ключ сериализации или transport-события, по которому объект отличает один вариант данных от другого.
    - `add_answer`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `remove_question`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `element_class`: runtime-зависимость или поле, используемое текущим session-сценарием.

    ### Методы
    - `__init__`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `add_answer`: Добавляет ответ пользователя в GPT batch.
    - `remove_question`: Удаляет вопрос анкеты или GPT-контекста из внутреннего состояния или storage.
    - `remove_element`: Удаляет элемент доменной модели из внутреннего состояния или storage.
    - `get_question`: Возвращает вопрос анкеты или GPT-контекста из текущего состояния `QuestionSession`.

    ### Жизненный цикл
    Создаётся app-layer кодом, участвует в обработке пользовательского события и сохраняет изменённое состояние через существующие runtime/storage механизмы.

    ### Пример использования
    ```py
    session: QuestionSession
    ```
    """
    DESCRIPTION_KEY: str = "question_description"

    def __init__(self, session_id: int, context: Context, data: dict, message: Message):
        """
        Создаёт session-объект `QuestionSession` и сохраняет состояние пользовательского сценария между входящими событиями.

        ### Аргументы:
        :param session_id: идентификатор сессии
        :param context: контекст обработки события
        :param data: сериализованный словарь
        :param message: сообщение проекта или сообщение конкретного транспорта

        ### Пример использования:
        ```py
        session = QuestionSession(session_id = session_id, context = context, data = data, message = message)
        ```
        """
        super().__init__(session_id, context, data, message)
        self.add_answer = context.autocenter.add_answer
        self.remove_question = context.autocenter.remove_question

        self.element_class = Question
        self.always_actions.update({
            "change": CHANGE_CALLBACK,
            "add": ADD_CALLBACK
        })

        # self.removed_actions.clear()
        self.enabled_actions.clear()


    @abstractmethod
    def add_answer(self, question_id: int, answer: str) -> bool:
        """
        Добавляет ответ пользователя в GPT batch.

        ### Аргументы:
        :param question_id: question id
        :param answer: ответ пользователя

        :return: результат шага сессии

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        session.add_answer(question_id = question_id, answer = answer)
        ```
        """
        raise NotImplementedError()

    @abstractmethod
    def remove_question(self, question_id: int) -> bool:
        """
        Удаляет GPT-вопрос из выбранного набора.

        ### Аргументы:
        :param question_id: question id

        :return: результат шага сессии

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        session.remove_question(question_id = question_id)
        ```
        """
        raise NotImplementedError()

    def remove_element(self):
        """
        Удаляет элемент доменной модели из внутреннего состояния или storage.

        ### Примеры вызова:
        ```py
        session.remove_element()
        ```
        """
        element: Element | None = self.get_element()

        if element:
            self.remove_question(element.id)
        else:
            self.validate_element()

    def get_question(self, answers: Never = {}) -> str:
        """
        Возвращает краткое описание элемента для вывода в чат.

        ### Аргументы:
        :param answers: варианты ответа

        :return: строка вида `Филиал «Название»` или `Элемент «id»`

        ### Пример использования:
        ```py
        session.get_question(answers = answers)
        ```
        """
        context_question: Question | None = self.get_element()

        if context_question:
            result: list[str] = [super().get_question(answers)]

            if context_question.question:
                question: str = get_phrase("question_single")
                result.append(f"{question}: «{context_question.question.strip()}»")

            for answer in context_question.answers:
                result.append(f"• {answer.strip()}")

            return "\n".join(result)
        else:
            # -> element_removed permanently
            return super().get_question(answers)


class SessionLimits(ModeSession):
    """
    Описывает пользовательскую или административную сессию `SessionLimits`.
    Сессия хранит состояние текущего пользовательского сценария, обновляет сообщения и завершает себя через общий session lifecycle.

    ### Поля
    - `DESCRIPTION_KEY`: ключ сериализации или transport-события, по которому объект отличает один вариант данных от другого.
    - `create_element`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `remove_element`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `folder_id`: идентификатор объекта или связанной сущности, по которому runtime восстанавливает связь между слоями.
    - `element_id`: идентификатор объекта или связанной сущности, по которому runtime восстанавливает связь между слоями.
    - `element_class`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `next_session`: runtime-зависимость или поле, используемое текущим session-сценарием.

    ### Методы
    - `__init__`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `dumps`: Возвращает JSON-совместимый снимок объекта для storage или callback payload.
    - `update_data`: Обновляет data с учётом текущего состояния объекта.
    - `process_action`: Обрабатывает действие меню в текущем пользовательском или transport-layer потоке.

    ### Жизненный цикл
    Создаётся app-layer кодом, участвует в обработке пользовательского события и сохраняет изменённое состояние через существующие runtime/storage механизмы.

    ### Пример использования
    ```py
    session: SessionLimits
    ```
    """
    DESCRIPTION_KEY: str = "limits_description"

    def __init__(self, session_id: int, context: Context, data: dict, message: Message):
        """
        Создаёт session-объект `SessionLimits` и сохраняет состояние пользовательского сценария между входящими событиями.

        ### Аргументы:
        :param session_id: идентификатор сессии
        :param context: контекст обработки события
        :param data: сериализованный словарь
        :param message: сообщение проекта или сообщение конкретного транспорта

        ### Пример использования:
        ```py
        sessionLimits = SessionLimits(session_id = session_id, context = context, data = data, message = message)
        ```
        """
        super().__init__(session_id, context, data, message)
        self.create_element = context.autocenter.create_limit
        self.remove_element = context.autocenter.remove_limit

        self.folder_id: int = context.autocenter.limits_folder.id
        self.element_id = context.autocenter.limits_folder.id
        self.element_class = LimitsFolder
        self.next_session = LimitSession

        self.set_mode(data.get("mode", ""))

    def dumps(self) -> BotTypes.SESSION_TYPE:
        """
        Возвращает JSON-совместимый снимок объекта для storage или callback payload.

        :return: JSON-совместимый словарь для сохранения или передачи между слоями

        ### Пример использования:
        ```py
        sessionLimits.dumps()
        ```
        """
        result: BotTypes.SESSION_TYPE = super().dumps()

        result.update({
            "element_id": int(self.element_id) if self.element_id > 0 else 5/0
        })

        return result

    def update_data(self, data: dict[str, str]):
        """
        Обновляет data с учётом текущего состояния объекта.

        ### Аргументы:
        :param data: JSON-совместимые данные для соответствующего repository

        ### Пример использования:
        ```py
        session.update_data(data = data)
        ```
        """
        super().update_data(data)
        self.element_id = self.folder_id

    def process_action(self, bot_key: BOT_KEY, chat_id: int, action: str) -> bool:
        """
        Обрабатывает действие меню в текущем runtime-контексте.

        ### Аргументы:
        :param bot_key: ключ транспорта
        :param chat_id: идентификатор чата
        :param action: действие меню

        :return: результат шага сессии

        ### Пример использования:
        ```py
        sessionLimits.process_action(bot_key = bot_key, chat_id = chat_id, action = action)
        ```
        """


        if action == CREATE_CALLBACK:
            self._next_level(bot_key, chat_id, CreateLimitSession, {
                "container_id": int(self.element_id)
            })#, message = self.get_message())
            return True

        return super().process_action(bot_key, chat_id, action)


class CreateLimitSession(LevelSession):

    """
    Описывает пользовательскую или административную сессию `CreateLimitSession`.
    Сессия хранит состояние текущего пользовательского сценария, обновляет сообщения и завершает себя через общий session lifecycle.

    ### Поля
    - `get_model`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `create_limits`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `element_class`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `levels`: runtime-зависимость или поле, используемое текущим session-сценарием.

    ### Методы
    - `__init__`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `create_limits`: Создаёт лимиты GPT и связывает результат с текущим app-layer состоянием.
    - `get_model`: Возвращает модель GPT из текущего состояния `CreateLimitSession`.
    - `update_data`: Обновляет data с учётом текущего состояния объекта.
    - `get_answer`: Возвращает ответ пользователя из текущего состояния `CreateLimitSession`.
    - `get_shared`: Возвращает shared из текущего состояния `CreateLimitSession`.
    - `get_period`: Возвращает period из текущего состояния `CreateLimitSession`.
    - `get_tokens`: Возвращает tokens из текущего состояния `CreateLimitSession`.
    - `prove_shared`: Проверяет введённое пользователем значение для шага `shared`.
    - `prove_period`: Проверяет введённое пользователем значение для шага `period`.

    ### Жизненный цикл
    Создаётся app-layer кодом, участвует в обработке пользовательского события и сохраняет изменённое состояние через существующие runtime/storage механизмы.

    ### Пример использования
    ```py
    session: CreateLimitSession
    ```
    """
    def __init__(self, session_id: int, context: Context, data: dict, message: Message):
        """
        Создаёт session-объект `CreateLimitSession` и сохраняет состояние пользовательского сценария между входящими событиями.

        ### Аргументы:
        :param session_id: идентификатор сессии
        :param context: контекст обработки события
        :param data: сериализованный словарь
        :param message: сообщение проекта или сообщение конкретного транспорта

        ### Пример использования:
        ```py
        session = CreateLimitSession(session_id = session_id, context = context, data = data, message = message)
        ```
        """
        super().__init__(session_id, context, data, message)
        self.get_model = context.autocenter.get_model
        self.create_limits = context.autocenter.create_limits

        self.element_class: type[Limit] = Limit

        self.levels: list[Level] = [
            Level(self.ask_shared),
            Level(self.ask_period),
            Level(self.ask_tokens)
        ]

        self.load_levels(data)


    @abstractmethod
    def create_limits(self, period: int, limit_tokens: int, shared: bool):
        """
        Создаёт limits и связывает результат с текущим объектом.

        ### Аргументы:
        :param period: период действия лимита или статистики
        :param limit_tokens: limit tokens
        :param shared: общий ли лимит для нескольких пользователей

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        session.create_limits(period = period, limit_tokens = limit_tokens, shared = shared)
        ```
        """
        raise NotImplementedError()

    @abstractmethod
    def get_model(self) -> Model | None:
        """
        Возвращает выбранную GPT-модель.

        :return: GPT-модель

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        session.get_model()
        ```
        """
        raise NotImplementedError()

    def update_data(self, data: dict[str, str]):
        """
        Обновляет data с учётом текущего состояния объекта.

        ### Аргументы:
        :param data: JSON-совместимые данные для соответствующего repository

        ### Пример использования:
        ```py
        session.update_data(data = data)
        ```
        """
        self.load_levels(data)


    def get_answer(self, limit_key: tuple[int, bool]) -> str:
        """
        Возвращает строку, показываемую пользователю как вариант ответа.

        ### Аргументы:
        :param limit_key: limit key

        :return: ответ пользователя

        ### Пример использования:
        ```py
        session.get_answer(limit_key = limit_key)
        ```
        """
        period, shared = limit_key
        period_string: str = parse_period(int(period))

        if shared:
            return get_phrase("shared_client").format(period_string)
        else:
            return get_phrase("user_client").format(period_string)


    def get_shared(self) -> bool | None:
        """
        Возвращает признак общего лимита.

        :return: shared

        ### Пример использования:
        ```py
        session.get_shared()
        ```
        """
        level: Level = self.levels[0]
        return self.get_value(level, bool)

    def get_period(self) -> bool | None:
        """
        Возвращает период действия GPT-лимита.

        :return: period

        ### Пример использования:
        ```py
        session.get_period()
        ```
        """
        level: Level = self.levels[1]
        return self.get_value(level, int)

    def get_tokens(self) -> bool | None:
        """
        Возвращает сохранённое количество GPT-токенов.

        :return: оставшийся лимит токенов

        ### Пример использования:
        ```py
        session.get_tokens()
        ```
        """
        level: Level = self.levels[2]
        return self.get_value(level, int)


    def prove_shared(self) -> bool:
        """
        Проверяет введённое пользователем значение для шага `shared`.

        :return: результат шага сессии

        ### Пример использования:
        ```py
        session.prove_shared()
        ```
        """
        shared: bool | None = self.get_shared()

        if shared is None:
            self.show_phrase("shared_required")
            self.change_level(0)

        return shared is not None

    def prove_period(self) -> bool:
        """
        Проверяет введённое пользователем значение для шага `period`.

        :return: результат шага сессии

        ### Пример использования:
        ```py
        session.prove_period()
        ```
        """
        period: int | None = self.get_period()

        if period is None:
            self.show_phrase("period_required")
            self.change_level(1)

        return period is not None

    def prove_tokens(self) -> bool:
        """
        Проверяет введённое пользователем значение для шага `tokens`.

        :return: результат шага сессии

        ### Пример использования:
        ```py
        session.prove_tokens()
        ```
        """
        tokens: int | None = self.get_tokens()

        if tokens is None:
            self.show_phrase("tokens_required")
            self.change_level(2)

        return tokens is not None


    def ask_shared(self, level: Level, context: Context | None):
        """
        Показывает пользователю вопрос для шага `shared`.

        ### Аргументы:
        :param level: уровень сценария
        :param context: контекст обработки события

        ### Пример использования:
        ```py
        session.ask_shared(level = level, context = context)
        ```
        """

        # Шаг 1 - общий или индивидуальный лимит

        shared: bool | None = self.get_shared()

        if isinstance(shared, bool) and self.check_confirmed(level):
            self.next_level(context)
        elif self.check_asked(level):
            self.set_asked(level, False)

            if context and context.has_event():
                if context.is_callback():
                    callback_data: str = context.get_callback_string(1)

                    if callback_data == SHARED_CALLBACK or callback_data == NOTSHARED_CALLBACK:
                        shared: bool = callback_data == SHARED_CALLBACK
                        self.set_value(level, shared)
                        self.set_confirmed(level, True)
                        self.next_level(None)
                        return

                context.remove_handler()
                return

        create_question: str = get_phrase(self.element_class.CREATING_KEY)

        actions: dict = {
            "shared_limit": SHARED_CALLBACK,
            "user_limit": NOTSHARED_CALLBACK
        }

        self.input.update(create_question, answers = [], choosen = [], actions = actions, cancel = True, back = True)
        self.set_asked(level, True)

    def ask_period(self, level: Level, context: Context | None):
        """
        Показывает пользователю вопрос для шага `period`.

        ### Аргументы:
        :param level: уровень сценария
        :param context: контекст обработки события

        ### Пример использования:
        ```py
        session.ask_period(level = level, context = context)
        ```
        """

        # Шаг 2 - Выбор периода

        period: int | None = self.get_period()

        if not self.prove_shared():
            return
        elif is_int(period) and int(period) > 0 and self.check_confirmed(level):
            self.next_level(context)
            return
        elif self.check_asked(level):
            self.set_asked(level, False)

            if context and context.has_event():
                content, is_callback = self.get_command(context)
                limit_period: int | None = None

                if is_callback:
                    args: list[str] = context.get_callback_data()
                    callback_data: str = context.get_callback_string(1)

                    if callback_data == PERIOD_CALLBACK:
                        limit_period = int(args[2])
                elif is_int(content):
                    limit_period: int = int(content)
                elif content:
                    pass

                if is_int(limit_period):
                    self.set_value(level, int(limit_period))
                    self.set_confirmed(level, True)
                    self.next_level(None)
                else:
                    context.remove_handler()

                return

        create_question: str = get_phrase("create_limit_period")
        shared: bool = self.get_shared()
        actions: dict = {}

        for period in PERIODS:
            if period > 1:
                action: str = self.get_answer((period, shared))
                actions[action] = join_callback(PERIOD_CALLBACK, period)

        self.input.update(create_question, answers = [], choosen = [], actions = actions, cancel = True, back = True)
        self.set_asked(level, True)

    def ask_tokens(self, level: Level, context: Context | None):
        """
        Показывает пользователю вопрос для шага `tokens`.

        ### Аргументы:
        :param level: уровень сценария
        :param context: контекст обработки события

        ### Пример использования:
        ```py
        session.ask_tokens(level = level, context = context)
        ```
        """

        # Шаг 3 - Ограничение по количеству токенов

        tokens: int | None = self.get_tokens()

        if not self.prove_shared():
            return
        elif not self.prove_period():
            return
        elif is_int(tokens) and int(tokens) >= 0 and self.check_confirmed(level):
            self.next_level(context)
            return
        elif self.check_asked(level):
            self.set_asked(level, False)

            if context and context.has_event():
                content, is_callback = self.get_command(context)
                content = str(content).strip() if content else ""

                if is_callback:
                    context.remove_handler()
                    return
                elif content.endswith("₽") and is_float(content.replace("₽", "")):
                    model: Model | None = self.get_model()

                    if model:
                        rubles: int = float(content.replace("₽", ""))
                        tokens: int = model.calc_tokens(rubles)

                        if tokens > 0:
                            self.set_value(level, int(tokens))
                            self.set_confirmed(level, True)
                            self.next_level(None)
                            return
                        else:
                            self.show_phrase("low_rubles")
                    else:
                        self.show_phrase("model_required")

                elif is_int(content):
                    self.set_value(level, int(content))
                    self.set_confirmed(level, True)
                    self.next_level(None)
                    return
                else:
                    context.remove_handler()
                    return

        shared: bool = self.get_shared()
        period: int = self.get_period()

        shared_string: str = get_phrase("create_shared_limit" if shared else "create_user_limit")
        period_string: str = parse_period(int(period))
        create_question: str = get_phrase("create_limit_tokens").format(shared_string, period_string)

        actions: dict = {}

        for period in PERIODS:
            pass
            # actions["9₽"] = 9 / self.autocenter.model.price

        self.input.update(create_question, answers = [], choosen = [], actions = actions, cancel = True, back = True)
        self.set_asked(level, True)

    def final_level(self):
        """
        Завершает текущий уровень сценария и передаёт управление дальше.

        ### Пример использования:
        ```py
        session.final_level()
        ```
        """

        # Шаг 4: Создание лимитов

        if not self.prove_shared():
            return
        elif not self.prove_period():
            return
        elif not self.prove_tokens():
            return

        shared: bool = self.get_shared()
        period: int = self.get_period()
        tokens: int = self.get_tokens()
        self.create_element(period, tokens, shared)

        answer: str = self.get_answer((period, shared))
        message: str = get_phrase("limit_created").format(answer, str(tokens))
        self.show_message(message)
        self.finish()
        # self.update_sessions(SessionLimits)


    def create_element(self, period: int, limit_tokens: int, shared: bool) -> Limit:
        """
        Создаёт доменный элемент и связывает результат с текущим объектом.

        ### Аргументы:
        :param period: период действия лимита или статистики
        :param limit_tokens: limit tokens
        :param shared: общий ли лимит для нескольких пользователей

        :return: созданный объект: доменный элемент

        ### Пример использования:
        ```py
        session.create_element(period = period, limit_tokens = limit_tokens, shared = shared)
        ```
        """
        self.create_limits(period, limit_tokens, shared)
        return self.get_answer((period, shared))


class LimitSession(ManageSession):
    """
    Описывает пользовательскую или административную сессию `LimitSession`.
    Сессия хранит состояние текущего пользовательского сценария, обновляет сообщения и завершает себя через общий session lifecycle.

    ### Поля
    - `DESCRIPTION_KEY`: ключ сериализации или transport-события, по которому объект отличает один вариант данных от другого.
    - `add_answer`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `remove_limit`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `element_class`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `users`: хранит пользователей для операций этого объекта.

    ### Методы
    - `__init__`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `add_answer`: Добавляет ответ пользователя в GPT batch.
    - `add_content`: Добавляет текстовый блок в GPT-контекст или вопрос.
    - `remove_element`: Удаляет элемент доменной модели из внутреннего состояния или storage.
    - `get_answer`: Возвращает ответ пользователя из текущего состояния `LimitSession`.
    - `get_question`: Возвращает вопрос анкеты или GPT-контекста из текущего состояния `LimitSession`.

    ### Жизненный цикл
    Создаётся app-layer кодом, участвует в обработке пользовательского события и сохраняет изменённое состояние через существующие runtime/storage механизмы.

    ### Пример использования
    ```py
    session: LimitSession
    ```
    """
    DESCRIPTION_KEY: str = "limit_description"

    def __init__(self, session_id: int, context: Context, data: dict, message: Message):
        """
        Создаёт session-объект `LimitSession` и сохраняет состояние пользовательского сценария между входящими событиями.

        ### Аргументы:
        :param session_id: идентификатор сессии
        :param context: контекст обработки события
        :param data: сериализованный словарь
        :param message: сообщение проекта или сообщение конкретного транспорта

        ### Пример использования:
        ```py
        session = LimitSession(session_id = session_id, context = context, data = data, message = message)
        ```
        """
        super().__init__(session_id, context, data, message)
        self.add_answer = context.autocenter.add_answer
        self.remove_limit = context.autocenter.remove_limit

        self.element_class = Limit
        self.always_actions.update({
            "change": CHANGE_CALLBACK
        })

        # self.removed_actions.clear()
        self.enabled_actions.clear()

        # del
        self.users = context.autocenter.users


    @abstractmethod
    def add_answer(self, question_id: int, answer: str) -> bool:
        """
        Добавляет ответ пользователя в GPT batch.

        ### Аргументы:
        :param question_id: question id
        :param answer: ответ пользователя

        :return: результат шага сессии

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        session.add_answer(question_id = question_id, answer = answer)
        ```
        """
        raise NotImplementedError()

    def add_content(self, addition: str):
        """
        Добавляет текстовое содержимое к доменному элементу.

        ### Аргументы:
        :param addition: дополнительное значение для расчёта

        ### Пример использования:
        ```py
        session.add_content(addition = addition)
        ```
        """
        if str(addition).strip():
            self.add_answer(addition)

    def remove_element(self):
        """
        Удаляет элемент доменной модели из внутреннего состояния или storage.

        :return: результат шага сессии

        ### Примеры вызова:
        ```py
        session.remove_element()
        ```
        """
        return self.remove_limit(self.element_id)


    def get_answer(self, limit_key: tuple[int, bool]) -> str:
        """
        Возвращает строку, показываемую пользователю как вариант ответа.

        ### Аргументы:
        :param limit_key: limit key

        :return: ответ пользователя

        ### Пример использования:
        ```py
        session.get_answer(limit_key = limit_key)
        ```
        """
        period, shared = limit_key
        period_string: str = parse_period(int(period))

        if shared:
            return get_phrase("shared_client").format(period_string)
        else:
            return get_phrase("user_client").format(period_string)

    def get_question(self, answers: Never = {}) -> str:
        """
        Возвращает краткое описание элемента для вывода в чат.

        ### Аргументы:
        :param answers: варианты ответа

        :return: строка вида `Филиал «Название»` или `Элемент «id»`

        ### Пример использования:
        ```py
        session.get_question(answers = answers)
        ```
        """
        limit: Limit | None = self.get_element()

        if not limit:
            return super().get_question(answers)

        period: int = limit.period
        shared: bool = limit.shared
        limit_tokens: int = int(limit.limit)
        users_limits: str = ""

        class Result():

            """
            `Result` хранит состояние многошагового пользовательского сценария между входящими событиями.
            Сессия хранит состояние текущего пользовательского сценария, обновляет сообщения и завершает себя через общий session lifecycle.

            ### Поля
            - `left`: runtime-зависимость или поле, используемое текущим session-сценарием.
            - `string`: текстовое содержимое, которое показывается пользователю, отправляется в GPT или сохраняется в доменной модели.

            ### Методы
            - `__init__`: runtime-зависимость или поле, используемое текущим session-сценарием.

            ### Жизненный цикл
            Создаётся app-layer кодом, участвует в обработке пользовательского события и сохраняет изменённое состояние через существующие runtime/storage механизмы.

            ### Пример использования
            ```py
            result: Result
            ```
            """
            def __init__(self, left: int, string: str):
                """
                Создаёт session-объект `Result` и сохраняет состояние пользовательского сценария между входящими событиями.

                ### Аргументы:
                :param left: оставшийся объём лимита
                :param string: строковый payload, который нужно разобрать или отформатировать

                ### Пример использования:
                ```py
                result = Result(left = left, string = string)
                ```
                """
                self.left: int = int(left)
                self.string: str = str(string)

        results: list[Result] = []

        def get_results(max_results: int = 100):
            for user in self.users.values():
                for client in user.clients:
                    client_limit: Limit | None = client.find_limit(period)

                    if client_limit:
                        id: int = user.id
                        username: str = user.get_username(Any)
                        left: int = client_limit.left
                        results.append(Result(left, f"• Пользователь {username} {id=}, осталось токенов: {left}"))

                        if len(results) >= max_results:
                            return

        get_results()
        results.sort(key = lambda result: result.left)

        if results:
            users_limits = f"\nПользователи с этим лимитом:{users_limits}"
            string: str = "\n".join(result.string for result in results)
            users_limits = f"{users_limits}\n{string}"

        return f"{self.get_answer((period, shared))}, лимит токенов: {limit_tokens}{users_limits}"


class GPTSession(LevelSession):
    """
    Описывает пользовательскую или административную сессию `GPTSession`.
    Сессия хранит состояние текущего пользовательского сценария, обновляет сообщения и завершает себя через общий session lifecycle.

    ### Поля
    - `ACTION_MODEL`: callback-действие, которое session/handler использует при разборе нажатой кнопки.
    - `ACTION_LIMITS`: callback-действие, которое session/handler использует при разборе нажатой кнопки.
    - `ACTION_CONTEXT`: callback-действие, которое session/handler использует при разборе нажатой кнопки.
    - `ACTION_QUESTIONS`: callback-действие, которое session/handler использует при разборе нажатой кнопки.
    - `ACTION_TEST`: callback-действие, которое session/handler использует при разборе нажатой кнопки.
    - `autocenter`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `get_apikey`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `set_apikey`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `check_apikey`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `get_model`: runtime-зависимость или поле, используемое текущим session-сценарием.

    ### Методы
    - `__init__`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `get_apikey`: Возвращает apikey из текущего состояния `GPTSession`.
    - `set_apikey`: Проверяет и сохраняет значение `apikey` в `GPTSession`.
    - `check_apikey`: Проверяет apikey перед использованием.
    - `get_model`: Возвращает модель GPT из текущего состояния `GPTSession`.
    - `get_provider`: Возвращает провайдера GPT из текущего состояния `GPTSession`.
    - `get_context`: Возвращает контекст обработки события из текущего состояния `GPTSession`.
    - `get_questions`: Возвращает вопросы анкеты или GPT-контекста из текущего состояния `GPTSession`.
    - `get_ready_mark`: Возвращает ready mark из текущего состояния `GPTSession`.
    - `format_rubles`: Форматирует rubles для вывода пользователю.

    ### Жизненный цикл
    Создаётся app-layer кодом, участвует в обработке пользовательского события и сохраняет изменённое состояние через существующие runtime/storage механизмы.

    ### Пример использования
    ```py
    session: GPTSession
    ```
    """
    ACTION_MODEL: str = "gpt_model_callback"
    ACTION_LIMITS: str = "gpt_limits_callback"
    ACTION_CONTEXT: str = "gpt_context_callback"
    ACTION_QUESTIONS: str = "gpt_questions_callback"
    ACTION_TEST: str = "gpt_test_callback"

    def __init__(self, session_id: int, context: Context, data: dict, message: Message):
        """
        Создаёт session-объект `GPTSession` и сохраняет состояние пользовательского сценария между входящими событиями.

        ### Аргументы:
        :param session_id: идентификатор сессии
        :param context: контекст обработки события
        :param data: сериализованный словарь
        :param message: сообщение проекта или сообщение конкретного транспорта

        ### Пример использования:
        ```py
        session = GPTSession(session_id = session_id, context = context, data = data, message = message)
        ```
        """
        super().__init__(session_id, context, data, message)
        self.autocenter: App = context.autocenter
        self.get_apikey = context.autocenter.get_apikey
        self.set_apikey = context.autocenter.set_apikey
        self.check_apikey = context.autocenter.check_apikey
        self.get_model = context.autocenter.get_model
        self.get_provider = context.autocenter.get_provider
        self.get_context = context.autocenter.get_context
        self.get_questions = context.autocenter.get_questions
        self.shared_client: Client = context.autocenter.shared_client
        self.user_client: Client = context.autocenter.user_client
        self.users: dict[int, User] = context.autocenter.users
        self.min_request: int = context.autocenter.settings.gpt.get("min_request", 8000)
        self.input.lang_actions = True

        self.levels = [
            Level(self.summary),
            Level(self.ask_apikey),
            Level(self.ask_test_request)
        ]

        self.load_levels(data)


    @abstractmethod
    def get_apikey(self) -> str | Literal[""]:
        """
        Возвращает API key выбранного GPT-провайдера.

        :return: apikey

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        session.get_apikey()
        ```
        """
        raise NotImplementedError()

    @abstractmethod
    def set_apikey(self, apikey: str):
        """
        Проверяет и сохраняет значение `apikey`.

        ### Аргументы:
        :param apikey: API-ключ провайдера GPT

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        session.set_apikey(apikey = apikey)
        ```
        """
        raise NotImplementedError()

    @abstractmethod
    def check_apikey(self, apikey: str) -> bool:
        """
        Проверяет значение `apikey` перед сохранением или использованием.

        ### Аргументы:
        :param apikey: API-ключ провайдера GPT

        :return: `True`, если значение `apikey` перед сохранением или использованием; иначе `False`

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        session.check_apikey(apikey = apikey)
        ```
        """
        raise NotImplementedError()

    @abstractmethod
    def get_model(self) -> Model | None:
        """
        Возвращает выбранную GPT-модель.

        :return: GPT-модель

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        session.get_model()
        ```
        """
        raise NotImplementedError()

    @abstractmethod
    def get_provider(self, model: str | Model) -> str | None:
        """
        Возвращает выбранного GPT-провайдера.

        ### Аргументы:
        :param model: GPT-модель

        :return: GPT-провайдер

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        session.get_provider(model = model)
        ```
        """
        raise NotImplementedError()

    @abstractmethod
    def get_context(self) -> SystemContext | None:
        """
        Возвращает GPT-контекст.

        :return: context

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        session.get_context()
        ```
        """
        raise NotImplementedError()

    @abstractmethod
    def get_questions(self) -> list[Question]:
        """
        Возвращает вопросы, доступные для GPT-сессии.

        :return: строка вида `Филиал «Название»` или `Элемент «id»`s

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        session.get_questions()
        ```
        """
        raise NotImplementedError()

    def get_ready_mark(self, ready: bool) -> str:
        """
        Возвращает отметку готовности GPT-настроек.

        ### Аргументы:
        :param ready: готово ли состояние к следующему шагу

        :return: ready mark

        ### Пример использования:
        ```py
        session.get_ready_mark(ready = ready)
        ```
        """
        return "\u2705" if ready else "\u274c"

    def format_rubles(self, rubles: float) -> str:
        """
        Форматирует rubles для вывода пользователю.

        ### Аргументы:
        :param rubles: сумма в рублях

        :return: результат шага сессии

        ### Пример использования:
        ```py
        session.format_rubles(rubles = rubles)
        ```
        """
        if rubles >= 10:
            return f"{round(rubles)}\u20bd"
        else:
            return f"{rubles:.2f}".rstrip("0").rstrip(".") + "\u20bd"

    def get_proxyapi_balance_text(self, apikey: str) -> str:
        """
        Возвращает текст с балансом ProxyAPI для admin-интерфейса.

        ### Аргументы:
        :param apikey: API-ключ провайдера GPT

        :return: proxyapi balance text

        ### Пример использования:
        ```py
        session.get_proxyapi_balance_text(apikey = apikey)
        ```
        """
        if not apikey:
            return "неизвестен"

        gpt: GPT = self.autocenter.gpt if self.autocenter.gpt else GPT(apikey)
        balance: float = gpt.get_tokens()

        if balance < 0:
            return "не удалось получить"

        return self.format_rubles(balance)

    def estimate_limit_rubles(self, tokens: float, model: Model) -> float:
        """
        Оценивает limit rubles по текущим настройкам GPT.

        ### Аргументы:
        :param tokens: количество токенов
        :param model: GPT-модель

        :return: результат шага сессии

        ### Пример использования:
        ```py
        session.estimate_limit_rubles(tokens = tokens, model = model)
        ```
        """
        prompt_ratio: int = 4
        response_ratio: int = 1
        price: float = (
            model.price_per_request * prompt_ratio + model.price_per_response * response_ratio
        ) / ((prompt_ratio + response_ratio) * 1_000_000)
        return max(0.0, float(tokens) * price)

    def get_limit_title(self, limit: Limit, shared: bool) -> str:
        """
        Возвращает заголовок GPT-лимита.

        ### Аргументы:
        :param limit: лимит GPT
        :param shared: общий ли лимит для нескольких пользователей

        :return: limit title

        ### Пример использования:
        ```py
        session.get_limit_title(limit = limit, shared = shared)
        ```
        """
        period_string: str = parse_period(int(limit.period))
        phrase_key: str = "shared_client" if shared else "user_client"
        return get_phrase(phrase_key).format(period_string)

    def get_exhausted_user_limit(self) -> str:
        """
        Возвращает текст о потраченном пользовательском лимите.

        :return: exhausted user limit

        ### Пример использования:
        ```py
        session.get_exhausted_user_limit()
        ```
        """
        users: list[User] = list(self.users.values())

        if not users:
            return ""

        for limit in self.user_client.limits:
            exhausted: int = 0

            for user in users:
                try:
                    client_limit: Limit | None = user.get_client().find_limit(limit.period)
                except Exception:
                    client_limit = None

                if client_limit and client_limit.left < self.min_request:
                    exhausted += 1

            if exhausted:
                percent: int = round(exhausted * 100 / len(users))
                limit_title: str = self.get_limit_title(limit, False)
                return f"у {percent}% пользователей исчерпан лимит \"{limit_title}\""

        return ""

    def get_limits_text(self, model: Model | None) -> tuple[str, bool]:
        """
        Возвращает текстовое описание доступных GPT-лимитов.

        ### Аргументы:
        :param model: GPT-модель

        :return: limits text

        ### Пример использования:
        ```py
        session.get_limits_text(model = model)
        ```
        """
        for limit in self.shared_client.limits:
            if limit.left < self.min_request:
                limit_title: str = self.get_limit_title(limit, True)
                return f"общий лимит \"{limit_title}\" исчерпан", False

        exhausted_user_limit: str = self.get_exhausted_user_limit()

        if exhausted_user_limit:
            return exhausted_user_limit, False

        tokens_left: float = self.user.get_tokens()

        if tokens_left == float("inf"):
            return "без ограничений", True
        elif model:
            rubles: str = self.format_rubles(self.estimate_limit_rubles(tokens_left, model))
            return f"{rubles} осталось, нужно от {self.min_request} токенов", tokens_left >= self.min_request
        else:
            return f"{int(tokens_left)} доступно, нужно от {self.min_request}", tokens_left >= self.min_request

    def get_context_text(self, model: Model | None) -> tuple[str, bool]:
        """
        Возвращает текст выбранного GPT-контекста.

        ### Аргументы:
        :param model: GPT-модель

        :return: context text

        ### Пример использования:
        ```py
        session.get_context_text(model = model)
        ```
        """
        system_context: SystemContext | None = self.get_context()

        if not system_context:
            return "не выбран", False
        elif not model:
            return system_context.get_answer(), True

        context_tokens: int = system_context.get_tokens(model)
        ready: bool = context_tokens < model.max_context
        return f"{system_context.get_answer()}, {context_tokens}/{model.max_context} токенов", ready

    def get_status(self) -> tuple[list[str], bool, list[str]]:
        """
        Возвращает статус GPT-настроек или лимита.

        :return: status

        ### Пример использования:
        ```py
        session.get_status()
        ```
        """
        lines: list[str] = ["Настройка нейросетей"]
        reasons: list[str] = []

        apikey: str = self.get_apikey()
        apikey_ready: bool = bool(apikey)
        lines.append(f"• API-ключ: {'установлен' if apikey_ready else 'не установлен'} {self.get_ready_mark(apikey_ready)}")

        if not apikey_ready:
            reasons.append("установить API-ключ")
        else:
            balance_text: str = self.get_proxyapi_balance_text(apikey)
            lines.append(f"• Баланс ProxyAPI: {balance_text}")

        model: Model | None = self.get_model()
        provider: str | None = self.get_provider(model) if model else None
        model_ready: bool = model is not None

        if model:
            model_price: str = f"{model.economy_rating}\u20bd"
            lines.append(f"• Модель: {provider} {model.model} {model_price} {self.get_ready_mark(model_ready)}")
        else:
            lines.append(f"• Модель: не выбрана {self.get_ready_mark(False)}")
            reasons.append("выбрать модель")

        context_text, context_ready = self.get_context_text(model)
        lines.append(f"• Контекст: {context_text} {self.get_ready_mark(context_ready)}")

        if not context_ready:
            reasons.append("выбрать контекст")

        questions_count: int = len(self.get_questions())
        lines.append(f"• Вопросы и ответы: {questions_count}")

        limits_text, limits_ready = self.get_limits_text(model)
        lines.append(f"• Лимиты: {limits_text} {self.get_ready_mark(limits_ready)}")

        if not limits_ready:
            reasons.append("пополнить или настроить лимиты")

        ready: bool = apikey_ready and model_ready and context_ready and limits_ready
        return lines, ready, reasons


    def summary(self, level: Level, context: Context | None):
        """
        Выполняет следующий шаг текущей сессии.

        ### Аргументы:
        :param level: уровень сценария
        :param context: контекст обработки события

        ### Пример использования:
        ```py
        session.summary(level = level, context = context)
        ```
        """
        if context and context.has_event() and context.is_callback():
            callback_data: str = context.get_callback_string(1)

            if callback_data == CONFIGURE_CALLBACK:
                self.change_level(1)
                return
            elif callback_data == FINISH_CALLBACK:
                self.finish()
                return
            elif callback_data == self.__class__.ACTION_MODEL:
                context.user.go_session(SessionProviders, context)
                return
            elif callback_data == self.__class__.ACTION_LIMITS:
                context.user.go_session(SessionLimits, context)
                return
            elif callback_data == self.__class__.ACTION_CONTEXT:
                context.user.go_session(SessionContexts, context)
                return
            elif callback_data == self.__class__.ACTION_QUESTIONS:
                context.user.go_session(SessionQuestions, context)
                return
            elif callback_data == self.__class__.ACTION_TEST:
                self.change_level(2)
                return
            else:
                context.remove_handler()
                return

        question, ready, reasons = self.get_status()

        if ready:
            question.append("Текстовые сообщения пользователей будут отправляться в ChatGPT. \u2705")
        else:
            question.append(f"Текстовые сообщения пользователей не будут отправляться в ChatGPT: нужно {', '.join(reasons)}.")

        actions: dict[str, str] = {
            "gpt_api_key": CONFIGURE_CALLBACK,
            "gpt_model": self.__class__.ACTION_MODEL,
            "gpt_limits": self.__class__.ACTION_LIMITS,
            "gpt_context": self.__class__.ACTION_CONTEXT,
            "gpt_questions": self.__class__.ACTION_QUESTIONS,
            "gpt_test_request": self.__class__.ACTION_TEST
        }

        self.input.update("\n".join(question), answers = [], choosen = [], actions = actions, cancel = True, back = True)

    def ask_apikey(self, level: Level, context: Context | None):
        """
        Показывает пользователю вопрос для шага `apikey`.

        ### Аргументы:
        :param level: уровень сценария
        :param context: контекст обработки события

        ### Пример использования:
        ```py
        session.ask_apikey(level = level, context = context)
        ```
        """
        if context and context.has_event():
            content, is_callback = self.get_command(context)

            if is_callback:
                callback_data: str = context.get_callback_string(1)

                if callback_data == HELP_CALLBACK:
                    return
                else:
                    context.remove_handler()
                    return
            elif self.check_apikey(content):
                self.set_apikey(content)
                self.change_level(0)
                return
            elif content:
                self.incorrect()

        apikey: str = self.get_apikey()
        question: list[str] = [get_phrase("apikey_valid") if apikey else get_phrase("apikey_invalid")]
        question.append(get_phrase("apikey_question"))

        actions: dict[str, str] = {
            "help": HELP_CALLBACK
        }

        self.input.update("\n".join(question), answers = [], choosen = [], actions = actions, cancel = True, back = True)

    def ask_test_request(self, level: Level, context: Context | None):
        """
        Показывает пользователю вопрос для шага `test_request`.

        ### Аргументы:
        :param level: уровень сценария
        :param context: контекст обработки события

        ### Пример использования:
        ```py
        session.ask_test_request(level = level, context = context)
        ```
        """
        if context and context.has_event():
            content, is_callback = self.get_command(context)

            if is_callback:
                context.remove_handler()
                return
            elif content:
                status_lines, ready, reasons = self.get_status()

                if not ready:
                    self.show_message(f"Тестовый запрос не отправлен: нужно {', '.join(reasons)}.")
                    self.change_level(0)
                    return

                self.autocenter.prove_request(context)

                if isinstance(context.handler, Request):
                    self.autocenter.process_request(context)
                    self.menu.reset_message()
                else:
                    self.show_message("Тестовый запрос не отправлен.")

                self.change_level(0)
                return

        self.input.update("Введите текст тестового запроса для ChatGPT.", answers = [], choosen = [], actions = {}, cancel = True, back = True)
