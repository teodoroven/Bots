"""
Описывает пользовательские или GPT-настройки.
Модуль относится к архитектурной зоне: прикладной слой `relay`, который связывает пользователей, сессии, доменную модель, GPT, уведомления и runtime-логику приложения.

### Публичные классы
- `GptSettingsMixin`: runtime-логика GPT-настроек.

### Публичные функции
- Публичные функции отсутствуют.

### Связи
Используется app-layer сценариями, обработчиками, сессиями и runtime-миксинами для единого пользовательского потока между ботами, GPT и storage.
"""

from __future__ import annotations



from relay.common import BotTypes, Model
from relay.gpt import GPT
from relay.utils import catch_parsefiles
class GptSettingsMixin:
    """
    Добавляет `App` операции gptsettings без привязки к transport-layer.
    Mixin рассчитан на включение в `App` и работает с его registry, storage, пользователями, ботами и очередями.

    ### Методы
    - `get_apikey`: Возвращает apikey из текущего состояния `GptSettingsMixin`.
    - `set_apikey`: Проверяет и сохраняет значение `apikey` в `GptSettingsMixin`.
    - `check_apikey`: Проверяет apikey перед использованием.
    - `get_context`: Возвращает контекст обработки события из текущего состояния `GptSettingsMixin`.
    - `get_provider`: Возвращает провайдера GPT из текущего состояния `GptSettingsMixin`.
    - `find_model`: Ищет модель GPT по данным, которые пришли из вызывающего слоя.
    - `get_model`: Возвращает модель GPT из текущего состояния `GptSettingsMixin`.
    - `get_models`: Возвращает модели GPT из текущего состояния `GptSettingsMixin`.
    - `get_models_list`: Возвращает models list из текущего состояния `GptSettingsMixin`.
    - `get_providers_models`: Возвращает providers models из текущего состояния `GptSettingsMixin`.

    ### Жизненный цикл
    Создаётся app-layer кодом, участвует в обработке пользовательского события и сохраняет изменённое состояние через существующие runtime/storage механизмы.

    ### Пример использования
    ```py
    app: GptSettingsMixin
    ```
    """
    def get_apikey(self) -> str | Literal[""]:
        """
        Возвращает API key для выбранного GPT-провайдера.

        :return: apikey

        ### Пример использования:
        ```py
        gptSettingsMixin.get_apikey()
        ```
        """
        return self.apikey

    def set_apikey(self, apikey: str):
        """
        Проверяет и сохраняет значение `apikey`.

        ### Аргументы:
        :param apikey: API-ключ провайдера GPT

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        gptSettingsMixin.set_apikey(apikey = apikey)
        ```
        """
        if self.check_apikey(apikey):

            self.apikey = str(apikey)

            self.save_gpt()

            self.gpt = GPT(apikey)

        elif apikey == "":

            self.apikey = ""

            self.gpt = None

        else:
            raise ValueError(f"Некорректное значение аргумента apikey")

    def check_apikey(self, apikey: str) -> bool:
        """
        Проверяет значение `apikey` перед сохранением или использованием.

        ### Аргументы:
        :param apikey: API-ключ провайдера GPT

        :return: `True`, если значение `apikey` перед сохранением или использованием; иначе `False`

        ### Пример использования:
        ```py
        gptSettingsMixin.check_apikey(apikey = apikey)
        ```
        """
        return len(apikey) > 34 and apikey.count("-") == 1 and len(apikey[:apikey.find("-")]) == 2

    def get_context(self) -> SystemContext | None:
        """
        Возвращает GPT-контекст.

        :return: context

        ### Пример использования:
        ```py
        gptSettingsMixin.get_context()
        ```
        """
        return self.system_context

    def get_provider(self, model: str | Model) -> Literal["Anthropic", "DeepSeek", "Google", "OpenAI"] | None:
        """
        Возвращает выбранного GPT-провайдера.

        ### Аргументы:
        :param model: GPT-модель

        :return: GPT-провайдер

        ### Пример использования:
        ```py
        gptSettingsMixin.get_provider(model = model)
        ```
        """

        for provider in self.models:

            dictionary: dict[str, Model] = self.models[provider]

            if model in tuple(dictionary.keys()) or model in tuple(dictionary.values()):

                return provider

    def find_model(self, provider: Literal["Anthropic", "DeepSeek", "Google", "OpenAI"], model: str) -> Model:
        """
        Ищет GPT-модель в текущих данных объекта или storage.

        ### Аргументы:
        :param provider: GPT-провайдер
        :param model: GPT-модель

        :return: GPT-модель или None, если подходящей записи нет

        ### Пример использования:
        ```py
        gptSettingsMixin.find_model(provider = provider, model = model)
        ```
        """
        return self.models[provider][model]

    def get_model(self) -> Model | None:
        """
        Возвращает выбранную GPT-модель.

        :return: GPT-модель

        ### Пример использования:
        ```py
        gptSettingsMixin.get_model()
        ```
        """
        return self.model

    def get_models(self, provider: Literal["Anthropic", "DeepSeek", "Google", "OpenAI"]) -> dict[str, Model]:
        """
        Возвращает словарь моделей, доступных выбранному GPT-провайдеру.

        ### Аргументы:
        :param provider: GPT-провайдер

        :return: models

        ### Пример использования:
        ```py
        gptSettingsMixin.get_models(provider = provider)
        ```
        """
        return self.models[provider]

    def get_models_list(self, provider: Literal["Anthropic", "DeepSeek", "Google", "OpenAI"]) -> list[str]:
        """
        Возвращает список имён моделей для выбранного GPT-провайдера.

        ### Аргументы:
        :param provider: GPT-провайдер

        :return: models list

        ### Пример использования:
        ```py
        gptSettingsMixin.get_models_list(provider = provider)
        ```
        """

        return list(self.get_models(provider).keys())

    def get_providers_models(self) -> dict[str, dict[str, Model]]:
        """
        Возвращает mapping провайдеров на доступные модели.

        :return: providers models

        ### Пример использования:
        ```py
        gptSettingsMixin.get_providers_models()
        ```
        """
        return self.models

    def get_providers(self) -> Iterable[str]:
        """
        Возвращает список настроенных GPT-провайдеров.

        :return: providers

        ### Пример использования:
        ```py
        gptSettingsMixin.get_providers()
        ```
        """
        return self.models.keys()

    def set_model(self, provider: Literal["Anthropic", "DeepSeek", "Google", "OpenAI"], model: str):
        """
        Проверяет и сохраняет GPT-модель в объекте.

        ### Аргументы:
        :param provider: GPT-провайдер
        :param model: GPT-модель

        ### Пример использования:
        ```py
        gptSettingsMixin.set_model(provider = provider, model = model)
        ```
        """
        self.model = self.models[provider][model]

        self.save_gpt()

    def save_gpt(self):
        """
        Сохраняет gpt в storage или во внутреннем состоянии объекта.

        ### Примеры вызова:
        ```py
        app.save_gpt()
        ```
        """
        data: BotTypes.GPT_TYPE = {

            "contexts": [context.dumps() for context in self.contexts.values()],

            "context": None if self.system_context is None else self.system_context.id,

            "questions": [question.dumps() for question in self.questions.values()],

            "model": None if self.model is None else str(self.model.model),

            "clients": [client.dumps() for client in self.clients.values()],

            "limits": [limit.dumps() for limit in self.limits.values()],

            "shared_client": self.shared_client.dumps(),

            "user_client": self.user_client.dumps(),

            "apikey": str(self.apikey) if self.apikey else ""

        }

        self.storage.save_document("gpt", data)

        self.storage.ensure_counters_at_least(client = int(self.client_id), element = int(self.element_id))

    def load_client(self, client_data: BotTypes.CLIENT_TYPE) -> Client:
        """
        Загружает данные из storage или внешнего transport/API и приводит их к объектам проекта.

        ### Аргументы:
        :param client_data: client data

        :return: значение, которое runtime использует для продолжения обработки события

        ### Пример использования:
        ```py
        gptSettingsMixin.load_client(client_data = client_data)
        ```
        """
        if client_data:

            with catch_parsefiles(("gpt",), "load_client"):

                return Client.loads(client_data)

        return self.create_client()

    def load_gpt(self):
        """
        Загружает gpt из storage.

        ### Примеры вызова:
        ```py
        app.load_gpt()
        ```
        """
        data: BotTypes.GPT_TYPE = self.storage.load_document("gpt")

        self.apikey = data.get("apikey", "")

        if not self.check_apikey:

            self.apikey = ""

        if self.apikey:

            self.gpt = GPT(self.apikey)

        current_context: int = get_int(data, -1, "context")

        contexts_list: list[SystemContext] = []

        not_removed_contexts: list[int] = []

        for system_context in self.contexts_folder.elements:

            not_removed_contexts.append(system_context.id )

        for context_data in data.get("contexts", []):

            system_context: SystemContext = SystemContext.loads(context_data)

            self.contexts[system_context.id] = system_context

            if system_context.id == current_context:

                self.system_context = system_context

            if system_context.id in not_removed_contexts:

                contexts_list.append(system_context)

        self.contexts_folder.set_elements(contexts_list)

        questions_list: list[SystemContext] = []

        not_removed_questions: list[int] = []


        for question in self.questions_folder.elements:

            not_removed_questions.append(question.id)

        for question_data in data.get("questions", []):

            question: Question = Question.loads(question_data)


            self.questions[question.id] = question

            if question.id in not_removed_questions:

                questions_list.append(question)

        self.questions_folder.set_elements(questions_list)

        from models import MODELS

        current_model: str = data.get("model", "")

        for provider, models in MODELS.items():

            for model in models:

                if provider in self.models:

                    self.models[provider][model.model] = model

                else:

                    self.models[provider] = {model.model: model}

                if model.model == current_model:

                    self.model = model

        shared_client_data: BotTypes.CLIENT_TYPE = data.get("shared_client", {})

        self.shared_client = self.load_client(shared_client_data)

        user_client_data: BotTypes.CLIENT_TYPE = data.get("user_client", {})

        self.user_client = self.load_client(user_client_data)

        self.limits_folder.set_elements(self.shared_client.limits + self.user_client.limits)
