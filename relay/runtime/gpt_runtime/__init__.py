"""
Открывает namespace GPT runtime-миксинов.
Модуль относится к архитектурной зоне: прикладной слой `relay`, который связывает пользователей, сессии, доменную модель, GPT, уведомления и runtime-логику приложения.

### Публичные классы
- `GptRuntimeMixin`: агрегатор runtime-логики GPT.

### Публичные функции
- Публичные функции отсутствуют.

### Связи
Используется app-layer сценариями, обработчиками, сессиями и runtime-миксинами для единого пользовательского потока между ботами, GPT и storage.
"""

from __future__ import annotations

from .requests import GptRequestsMixin
from .limits import GptLimitsMixin
from .settings import GptSettingsMixin
from .content import GptContentMixin


class GptRuntimeMixin(
        GptRequestsMixin,
        GptLimitsMixin,
        GptSettingsMixin,
        GptContentMixin
):
    """
    Добавляет `App` операции gptruntime без привязки к transport-layer.
    Mixin рассчитан на включение в `App` и работает с его registry, storage, пользователями, ботами и очередями.

    ### Жизненный цикл
    Создаётся app-layer кодом, участвует в обработке пользовательского события и сохраняет изменённое состояние через существующие runtime/storage механизмы.

    ### Пример использования
    ```py
    app: GptRuntimeMixin
    ```
    """
    pass
