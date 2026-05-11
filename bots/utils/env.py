"""
Содержит helper-функции для чтения числовых значений из переменных окружения.
Модуль относится к архитектурной зоне: слой унификации транспортов `bots`, который скрывает различия Telegram и VK за общими объектами сообщений, клавиатур, вложений и событий.

### Публичные классы
- Публичные классы отсутствуют.

### Публичные функции
- `get_env_int_set`: получает множество `int` из переменной окружения.
- `get_env_int`: получает `int` из переменной окружения.

### Связи
Используется транспортным слоем и wrapper-логикой, чтобы app-layer работал с `Message`, `Keyboard`, `Button`, `Attachment` и `Event` без привязки к конкретной соцсети.
"""

from __future__ import annotations

from bots.compat import Iterable, getenv

def get_env_int_set(key: str, default: Iterable[int] = ()) -> set[int]:
    """
    Возвращает множество `int` из переменной окружения `key`.
    Пустая или отсутствующая переменная возвращает `default`, приведённый к
    `set[int]`. Непустое значение разбивается по запятым, пробелы вокруг
    элементов отбрасываются, каждый элемент приводится к `int`.

    ### Аргументы:
    :param key: имя переменной окружения
    :param default: значения по умолчанию

    ### Примеры вызова:
    ```
    get_env_int_set("UNKNOWN_ENV_KEY") # set()
    get_env_int_set("UNKNOWN_ENV_KEY", default = (1, 2)) # {1, 2}
    ```

    ### Вызываемые исключения:
    :raises ValueError: если значение переменной или `default` нельзя привести к `int`.

    :return: множество целых чисел
    """
    value: str = getenv(key, "")

    if not value:
        return {int(item) for item in default}

    return {int(item.strip()) for item in value.split(",") if item.strip()}


def get_env_int(key: str, default: int = 0) -> int:
    """
    Возвращает `int` из переменной окружения `key`.
    Пустая или отсутствующая переменная возвращает `default`, приведённый к
    `int`; непустое значение переменной приводится к `int`.

    ### Аргументы:
    :param key: имя переменной окружения
    :param default: значение по умолчанию

    ### Примеры вызова:
    ```
    get_env_int("UNKNOWN_ENV_KEY") # 0
    get_env_int("UNKNOWN_ENV_KEY", default = 5) # 5
    ```

    ### Вызываемые исключения:
    :raises ValueError: если значение переменной или `default` нельзя привести к `int`.

    :return: целое число из окружения или `default`
    """
    value: str = getenv(key, "")

    if not value:
        return int(default)

    return int(value)

