"""
Описывает административные модели или сессии.
Модуль относится к архитектурной зоне: прикладной слой `relay`, который связывает пользователей, сессии, доменную модель, GPT, уведомления и runtime-логику приложения.

### Публичные классы
- `Admin`: модель администратора.

### Публичные функции
- Публичные функции отсутствуют.

### Связи
Используется app-layer сценариями, обработчиками, сессиями и runtime-миксинами для единого пользовательского потока между ботами, GPT и storage.
"""

from __future__ import annotations


from relay.common import Literal
from .user import User


class Admin(User):
    """
    `Admin` расширяет пользователя правами администратора и настройками уведомлений.

    ### Поля
    - `DEFAULT_SINGLE_KEY`: ключ сериализации или transport-события, по которому объект отличает один вариант данных от другого.
    - `permissions`: права администратора или пользователя.
    - `notifications`: хранит уведомления администраторов для операций этого объекта.

    ### Методы
    - `__init__`: Создаёт объект и сохраняет app-layer ссылки, которые нужны обработчикам.
    - `check_permissions`: Проверяет permissions перед использованием.
    - `check_notifications`: Проверяет уведомления администраторов перед использованием.

    ### Жизненный цикл
    Создаётся app-layer кодом, участвует в обработке пользовательского события и сохраняет изменённое состояние через существующие runtime/storage механизмы.

    ### Пример использования
    ```py
    admin: Admin
    ```
    """
    DEFAULT_SINGLE_KEY: Literal["user_single"] = "admin_single"

    def __init__(self, user_id: int, chat_ids: dict[str, list[int]], access_level: int = 1):
        """
        Создаёт `Admin` и сохраняет app-layer ссылки, которые нужны обработчикам.

        ### Аргументы:
        :param user_id: внутренний идентификатор пользователя в app-layer
        :param chat_ids: существующее соответствие transport key и chat id; объект хранит ссылку на этот словарь
        :param access_level: уровень доступа пользователя или администратора

        ### Пример использования:
        ```py
        admin: Admin = Admin(user_id = user_id, chat_ids = chat_ids, access_level = access_level)
        ```
        """
        super().__init__(user_id, chat_ids, access_level)

        self.permissions: dict[str, bool] = {
            "answer_users": True,
            "start_dialog": False
        }

        self.notifications: dict[str] = {
            "call_admin": True,
            "new_appointment": True
        }

    def check_permissions(self, permissions: Iterable[str]) -> bool:
        """
        Проверяет, есть ли у администратора нужные права.

        ### Аргументы:
        :param permissions: права администратора

        :return: `True`, если есть ли у администратора нужные права; иначе `False`

        ### Пример использования:
        ```py
        admin.check_permissions(permissions = permissions)
        ```
        """
        for key in permissions:
            if key not in self.permissions:
                return False
            elif self.permissions[key] == False:
                return False
        return True

    def check_notifications(self, notifications: Iterable[str]) -> bool:
        """
        Проверяет, включены ли нужные уведомления администратора.

        ### Аргументы:
        :param notifications: настройки уведомлений

        :return: `True`, если включены ли нужные уведомления администратора; иначе `False`

        ### Пример использования:
        ```py
        admin.check_notifications(notifications = notifications)
        ```
        """
        for key in notifications:
            if key not in self.notifications:
                return False
            elif self.notifications[key] == False:
                return False
        return True
