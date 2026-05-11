"""
Содержит helper-функции для безопасного чтения значений из mapping-объектов.
Модуль относится к архитектурной зоне: слой унификации транспортов `bots`, который скрывает различия Telegram и VK за общими объектами сообщений, клавиатур, вложений и событий.

### Публичные классы
- Публичные классы отсутствуют.

### Публичные функции
- `get_from`: получает значение из `Mapping` с проверкой типа и default-значением.
- `get_int`: получает `int` из `Mapping` с default-значением.
- `is_iterable`: проверяет, что объект является `Iterable`.
- `is_int`: проверяет, что значение можно использовать как `int`.

### Связи
Используется транспортным слоем и wrapper-логикой, чтобы app-layer работал с `Message`, `Keyboard`, `Button`, `Attachment` и `Event` без привязки к конкретной соцсети.
"""

from __future__ import annotations

from bots.compat import (
    Any,
    Callable,
    DotDict,
    Iterable,
    Never,
)
from bots.types import Any

def get_from(dictionary: DotDict | dict, *keys, default: Any | None = None, types: Iterable[type] = None, check: Callable | None = None) -> Any | None:
    """
    Возвращает значение из `dict` или `DotDict` по вложенному пути ключей.
    Для каждого ключа сначала используется метод `get`, затем доступ к атрибуту.
    Если путь отсутствует, значение не проходит проверку `types` или `check`,
    возвращается `default`.

    ### Аргументы:
    :param dictionary: mapping-объект или `DotDict`, из которого читается значение
    :param keys: последовательность ключей вложенного пути
    :param default: значение для отсутствующего или неподходящего результата
    :param types: допустимые типы итогового значения
    :param check: дополнительная проверка итогового значения

    ### Примеры вызова:
    ```
    get_from({"key": {"value": 1}}, "key", "value") # 1
    get_from({"key": {}}, "key", "missing", default = 0) # 0
    get_from({"key": "1"}, "key", types = (int,), default = 0) # 0
    get_from(DotDict({"key": DotDict({"value": 1})}), "key", "value") # 1
    ```

    :return: найденное значение или `default`
    """
    sentinel: Never = object()

    for key in keys:
        if hasattr(dictionary, "get"):
            dictionary = dictionary.get(key, sentinel)

            if dictionary is not sentinel:
                continue

        if hasattr(dictionary, key):
            dictionary = getattr(dictionary, key)
            continue

        return default

    if types and not any(isinstance(dictionary, t) for t in types):
        return default

    if check is not None and not check(dictionary):
        return default

    return dictionary


def get_int(dictionary: DotDict | dict, default: int, *keys, check: Callable | None = None) -> int:
    """
    Возвращает `int` из `dict` или `DotDict` по вложенному пути ключей.
    Функция является обёрткой над `get_from` с `types = (int,)` и возвращает
    `default`, если значение отсутствует, не является `int` или не проходит
    дополнительную проверку `check`.

    ### Аргументы:
    :param dictionary: mapping-объект или `DotDict`, из которого читается значение
    :param default: значение для отсутствующего или неподходящего результата
    :param keys: последовательность ключей вложенного пути
    :param check: дополнительная проверка найденного `int`

    :return: найденное целое число или `default`
    """
    # if not isinstance(default, int):
    #     raise TypeError("default must be int")

    result: int = get_from(dictionary, *keys, default = default, types = (int,), check = check)

    if isinstance(result, int):
        return result
    else:
        return default
        raise TypeError("result must be int")
def is_iterable(obj) -> bool:
    """
    Проверяет, можно ли пройти по объекту в `for`.
    Строки, списки, tuple, dict, set и `range` считаются итерируемыми.
    `None`, `bool` и функции без протокола итерации возвращают `False`.

    ### Аргументы:
    :param obj: проверяемый объект

    ### Примеры вызова:
    ```
    is_iterable("123") # True
    is_iterable([1, 2, 3]) # True
    is_iterable((1, 2, 3)) # True
    is_iterable({"a": 1}) # True
    is_iterable({1, 2, 3}) # True
    is_iterable(range(3)) # True
    is_iterable(None) # False
    is_iterable(True) # False
    is_iterable(lambda: None) # False
    ```

    :return: `True`, если объект удалось начать итерировать; иначе `False`
    """
    try:
        for elem in obj:
            return True
    except TypeError:
        return False
    else:
        return True


def is_int(obj) -> bool:
    """
    Проверяет приводимость значения к `int`.
    Это не проверка `type(obj) is int`: строки с числами и другие значения,
    которые принимает `int(obj)`, тоже считаются подходящими.

    ### Аргументы:
    :param obj: проверяемый объект

    ### Примеры вызова:
    ```
    is_int(1) # True
    is_int("1") # True
    is_int("-1") # True
    is_int(1.0) # True
    is_int("1.2") # False
    is_int(None) # False
    ```

    :return: `True`, если `int(obj)` выполняется без исключения; иначе `False`
    """
    try:
        int(obj)
    except:
        return False
    else:
        return True
