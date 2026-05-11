"""
Описывает runtime-обработку GPT-лимитов.
Модуль относится к архитектурной зоне: прикладной слой `relay`, который связывает пользователей, сессии, доменную модель, GPT, уведомления и runtime-логику приложения.

### Публичные классы
- `GptLimitsMixin`: runtime-логика GPT-лимитов.

### Публичные функции
- Публичные функции отсутствуют.

### Связи
Используется app-layer сценариями, обработчиками, сессиями и runtime-миксинами для единого пользовательского потока между ботами, GPT и storage.
"""

from __future__ import annotations



from relay.common import datetime
from relay.users import User
class GptLimitsMixin:
    """
    Добавляет `App` операции gptlimits без привязки к transport-layer.
    Mixin рассчитан на включение в `App` и работает с его registry, storage, пользователями, ботами и очередями.

    ### Методы
    - `create_client_id`: Создаёт client id и связывает результат с текущим app-layer состоянием.
    - `create_client`: Создаёт GPT-клиента и связывает результат с текущим app-layer состоянием.
    - `prove_shared`: Проверяет введённое пользователем значение для шага `shared`.
    - `create_limit`: Создаёт лимит GPT и связывает результат с текущим app-layer состоянием.
    - `create_limits`: Создаёт лимиты GPT и связывает результат с текущим app-layer состоянием.
    - `remove_limit`: Удаляет лимит GPT из внутреннего состояния или storage.
    - `update_limits`: Обновляет лимиты GPT с учётом текущего состояния объекта.
    - `find_limit`: Ищет лимит GPT по данным, которые пришли из вызывающего слоя.
    - `get_limits`: Возвращает лимиты GPT из текущего состояния `GptLimitsMixin`.

    ### Жизненный цикл
    Создаётся app-layer кодом, участвует в обработке пользовательского события и сохраняет изменённое состояние через существующие runtime/storage механизмы.

    ### Пример использования
    ```py
    app: GptLimitsMixin
    ```
    """
    def create_client_id(self) -> int:
        """
        Создаёт client id и связывает результат с текущим app-layer состоянием.

        :return: созданный объект для client id

        ### Примеры вызова:
        ```py
        app.create_client_id()
        ```
        """
        if hasattr(self, "storage") and getattr(self, "persist_ids", True):

            self.client_id = self.storage.next_id("client")

        else:

            self.client_id += 1

        return self.client_id

    def create_client(self) -> Client:
        """
        Создаёт GPT-клиента и связывает результат с текущим app-layer состоянием.

        :return: созданный объект для GPT-клиента

        ### Примеры вызова:
        ```py
        app.create_client()
        ```
        """
        client_id: int = self.create_client_id()

        client: Client = Client(client_id)

        self.clients[client_id] = client

        return client

    def prove_shared(self, client_id: int) -> bool:
        """
        Проверяет введённое пользователем значение для шага `shared`.

        ### Аргументы:
        :param client_id: client id

        :return: значение, которое runtime использует для продолжения обработки события

        ### Пример использования:
        ```py
        gptLimitsMixin.prove_shared(client_id = client_id)
        ```
        """
        return int(client_id) not in self.user_clients

    def create_limit(self, period: int, limit_tokens: int, shared: bool, user_only: bool = False) -> Limit:
        """
        Создаёт лимит GPT и связывает результат с текущим объектом.

        ### Аргументы:
        :param period: период действия лимита или статистики
        :param limit_tokens: limit tokens
        :param shared: общий ли лимит для нескольких пользователей
        :param user_only: user only

        :return: созданный объект: лимит GPT

        ### Пример использования:
        ```py
        gptLimitsMixin.create_limit(period = period, limit_tokens = limit_tokens, shared = shared, user_only = user_only)
        ```
        """
        limit_id: int = self.create_id()

        limit: Limit = Limit(limit_id, period, limit_tokens, datetime.now(), limit_tokens, shared)

        self.limits[limit_id] = limit

        if not user_only:

            self.add_element(limit, self.limits_folder.id)

        return limit

    def create_limits(self, period: int, limit_tokens: int, shared: bool):
        """
        Создаёт limits и связывает результат с текущим объектом.

        ### Аргументы:
        :param period: период действия лимита или статистики
        :param limit_tokens: limit tokens
        :param shared: общий ли лимит для нескольких пользователей

        ### Пример использования:
        ```py
        gptLimitsMixin.create_limits(period = period, limit_tokens = limit_tokens, shared = shared)
        ```
        """
        client: Client = self.shared_client if shared else self.user_client

        limit: Limit = self.create_limit(period, limit_tokens, shared)

        client.add_limit(limit)

        self.save_gpt()

        self.save_root()

        self.update_limits()

    def remove_limit(self, limit_id: int) -> bool:
        """
        Удаляет GPT-лимит из настроек клиента.

        ### Аргументы:
        :param limit_id: limit id

        :return: значение, которое runtime использует для продолжения обработки события

        ### Пример использования:
        ```py
        gptLimitsMixin.remove_limit(limit_id = limit_id)
        ```
        """
        if self.remove_element(limit_id, from_id = self.limits_folder.id):

            self.shared_client.remove_id(limit_id)

            self.user_client.remove_id(limit_id)

            self.save_gpt()

            self.save_root()

            self.update_limits()

            return True

        return False

    def update_limits(self):
        """
        Обновляет лимиты GPT с учётом текущего состояния объекта.

        ### Примеры вызова:
        ```py
        app.update_limits()
        ```
        """
        for user_id in self.users.keys():

            if user_id in self.users:

                user: User = self.users[user_id]

                if user.clients:

                    user.get_client().update_limits(self.user_client, self.create_limit)

                    user.save()

    def find_limit(self, period: int, shared: bool) -> Limit | None:
        """
        Ищет лимит GPT в текущих данных объекта или storage.

        ### Аргументы:
        :param period: период действия лимита или статистики
        :param shared: общий ли лимит для нескольких пользователей

        :return: лимит GPT или None, если подходящей записи нет

        ### Пример использования:
        ```py
        gptLimitsMixin.find_limit(period = period, shared = shared)
        ```
        """
        client: Client = self.shared_client if shared else self.user_client

        period = int(period)

        for limit in client.limits:

            if limit.period == period:

                return limit

        return None

    def get_limits(self) -> dict[tuple[int, bool], list[int]]:
        """
        Возвращает все лимиты всех пользователей, отсортированные по period, shared

        period: int - период лимита в секундах

        shared: bool - входит ли лимит в Client, который является общим для всех пользователей (не входит в user_clients)
        """

        result: dict[tuple[int, bool], list[int]] = {}

        def add(limit: Limit, shared: bool):

            limit_id: int = int(limit.id)

            key: tuple[int, bool] = (int(limit.period), bool(shared))

            if key in result:

                result[key].append(limit_id)

            else:

                result[key] = [limit_id]

        def add_limits(client: Client, shared: bool):

            for limit in client.limits:

                add(limit, shared)

        add_limits(self.shared_client, True)

        add_limits(self.user_client, False)

        return result

        result: dict[tuple[int, bool], list[int]] = {}

        def add(shared: bool, limit: Limit):

            limit_id: int = int(limit.id)

            key: tuple[int, bool] = (int(limit.period), bool(shared))

            if key in result:

                result[key].append(limit_id)

            else:

                result[key] = [limit_id]

        for client_id, client in self.clients.items():

            shared: bool = self.prove_shared(client_id)

            for limit in client.limits:

                add(limit, shared)

        return result
