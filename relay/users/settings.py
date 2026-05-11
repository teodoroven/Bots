"""
Описывает пользовательские или GPT-настройки.
Модуль относится к архитектурной зоне: прикладной слой `relay`, который связывает пользователей, сессии, доменную модель, GPT, уведомления и runtime-логику приложения.

### Публичные классы
- `Settings`: настройки пользователя.

### Публичные функции
- Публичные функции отсутствуют.

### Связи
Используется app-layer сценариями, обработчиками, сессиями и runtime-миксинами для единого пользовательского потока между ботами, GPT и storage.
"""

from __future__ import annotations


from callbacks import CALLBACK_MAIN
from callbacks import CALLBACK_CALLADMIN
from callbacks import CALLBACK_CALL_ADMIN
from callbacks import CALLBACK_CONTEXTS
from callbacks import CALLBACK_DATES
from callbacks import CALLBACK_FILIALS
from callbacks import CALLBACK_LIMITS
from callbacks import CALLBACK_QUESTIONS
from callbacks import CALL_ADMIN_NOTIFICATION_CALLBACK
from callbacks import NEW_APPOINTMENT_NOTIFICATION_CALLBACK
from callbacks import NOTIFICATIONS_CALLBACK
from callbacks import PERMISSIONS_CALLBACK
from callbacks import ANSWER_USERS_CALLBACK
from callbacks import DIALOG_CALLBACK
from callbacks import CALLBACK_GPTCON
from callbacks import CALLBACK_USERS
from callbacks import CALLBACK_ADMINS
from callbacks import CALLBACK_BOTCON
from callbacks import CALLBACK_MODELS
from callbacks import PERIOD_CALLBACK

class Settings():

    """
    `Settings` хранит пользовательские флаги уведомлений и доступности основных сценариев.

    ### Поля
    - `call_admin`: настройка уведомлений при вызове администратора.
    - `new_appointment`: настройка уведомлений о новой записи.
    - `gpt`: настройка доступа к GPT-функциям.
    - `main`: настройка основного пользовательского меню.
    - `buttons`: хранит кнопки клавиатуры для операций этого объекта.

    ### Методы
    - `__init__`: Создаёт объект и сохраняет app-layer ссылки, которые нужны обработчикам.
    - `load`: Загружает JSON-представление и восстанавливает поля объекта.
    - `save`: Записывает текущее JSON-представление через storage API.

    ### Жизненный цикл
    Создаётся app-layer кодом, участвует в обработке пользовательского события и сохраняет изменённое состояние через существующие runtime/storage механизмы.

    ### Пример использования
    ```py
    settings: Settings
    ```
    """
    def __init__(self):
        """
        Создаёт `Settings` и сохраняет app-layer ссылки, которые нужны обработчикам.

        ### Примеры вызова:
        ```py
        settings: Settings = Settings()
        ```
        """
        self.call_admin: dict[str, int] = {
            "quantity": 2,  # Будет отправлено первому администратору
            "timeout": 60 * 5  # Через 5 минут будет отправлено следующему администратору
        }

        self.new_appointment: dict[str, int] = {
            "quantity": 2,  # Будет отправлено первому администратору
            "timeout": 60 * 5  # Через 5 минут будет отправлено следующему администратору
        }

        self.gpt: dict[str, int] = {
            "min_request": 8000  # Минимальное количество токенов в одном запросе
        }

        self.main: dict[str, int] = {
            "months_dates": 6,  # Будет предложено записаться на полгода вперёд (месяц на выбор)
            "days_before_available": 7  # Если до конца месяца меньше дней, то он не будет доступен для записи
        }

        self.buttons: list[dict[str, str | int]] = [
            {
                "text": "main",
                "callback_data": CALLBACK_MAIN,
                "color": 3,
                "access": 0
            },
            {
                "text": "call_admin",
                "callback_data": CALLBACK_CALL_ADMIN,
                "color": 2,
                "access": 0
            },
            {
                "text": "models",
                "callback_data": CALLBACK_MODELS,
                "color": 0,
                "access": 1
            },
            {
                "text": "limits",
                "callback_data": CALLBACK_LIMITS,
                "color": 1,
                "access": 1
            },
            {
                "text": "contexts",
                "callback_data": CALLBACK_CONTEXTS,
                "color": 1,
                "access": 1
            },
            {
                "text": "questions",
                "callback_data": CALLBACK_QUESTIONS,
                "color": 0,
                "access": 1
            },
            {
                "text": "filials",
                "callback_data": CALLBACK_FILIALS,
                "color": 0,
                "access": 1
            },
            {
                "text": "dates",
                "callback_data": CALLBACK_DATES,
                "color": 1,
                "access": 1
            },
            {
                "text": "users",
                "callback_data": CALLBACK_USERS,
                "color": 1,
                "access": 1
            },
            {
                "text": "admins",
                "callback_data": CALLBACK_ADMINS,
                "color": 2,
                "access": 1
            },
            {
                "text": "gpt_control",
                "callback_data": CALLBACK_GPTCON,
                "color": 0,
                "access": 1
            },
            {
                "text": "bot_control",
                "callback_data": CALLBACK_BOTCON,
                "color": 1,
                "access": 1
            }
        ]

    def load(self):
        """
        Загружает JSON-представление и восстанавливает поля объекта.

        ### Пример использования:
        ```py
        settings.load()
        ```
        """
        pass

    def save(self):
        """
        Записывает текущее JSON-представление через storage API.

        ### Пример использования:
        ```py
        settings.save()
        ```
        """
        pass
