"""
Содержит helper-функции для форматирования дат, timestamp и расчёта разницы в секундах.
Модуль относится к архитектурной зоне: слой унификации транспортов `bots`, который скрывает различия Telegram и VK за общими объектами сообщений, клавиатур, вложений и событий.

### Публичные классы
- Публичные классы отсутствуют.

### Публичные функции
- `strftime`: форматирует `datetime` в строку проекта.
- `get_date`: получает `datetime` из строки или timestamp-значения.
- `get_timestamp`: возвращает timestamp для `datetime`.
- `diff_sec`: вычисляет разницу дат в секундах.

### Связи
Используется транспортным слоем и wrapper-логикой, чтобы app-layer работал с `Message`, `Keyboard`, `Button`, `Attachment` и `Event` без привязки к конкретной соцсети.
"""

from __future__ import annotations


from bots.constants import DATE_FORMAT_1
from .mapping import get_from, get_int
from bots.compat import Any, DotDict, datetime, warn
from bots.types import Any

def strftime(date: datetime) -> str:
    """
    Форматирует дату в строку проекта для отправки в JavaScript.
    Результат не является полноценным обратимым форматом для `strptime`;
    для разбора дат нужно использовать формат, предназначенный для парсинга.

    ### Аргументы:
    :param date: дата для форматирования

    :return: строка в формате `DATE_FORMAT_1`
    """
    return date.strftime(DATE_FORMAT_1)
def get_date(dictionary: DotDict | dict, *keys, default: datetime = datetime.fromtimestamp(0), warning: bool = True) -> datetime:
    """
    Читает timestamp из `dict` или `DotDict` и возвращает `datetime`.
    Если значение отсутствует или меньше нуля, возвращает `default` и при
    `warning=True` пишет предупреждение с исходным значением.

    ### Аргументы:
    :param dictionary: mapping-объект или `DotDict`, из которого читается timestamp
    :param keys: последовательность ключей вложенного пути
    :param default: дата для некорректного timestamp
    :param warning: нужно ли предупреждать о некорректном значении

    :return: дата из timestamp или `default`
    """
    timestamp: int = get_int(dictionary, -1, *keys)

    if timestamp < 0:
        if warning:
            value: Any | None = get_from(dictionary, *keys)
            warn(f"Некорректное значение поля {repr(value)}")

        return default

    return datetime.fromtimestamp(timestamp)

def get_timestamp(date: datetime) -> int:
    """
    Возвращает Unix timestamp для `datetime`.
    Для дат до Unix epoch на платформах, где `datetime.timestamp()` вызывает
    `OSError`, разница относительно `1970-01-01` вычисляется вручную.

    ### Аргументы:
    :param date: дата для преобразования

    ### Вызываемые исключения:
    :raises ValueError: если передан `None`.

    :return: timestamp в секундах
    """
    if date is not None:
        try:
            return int(date.timestamp())
        except OSError:
            # Если дата до 1970-01-01 UTC, вычисляем разницу вручную
            epoch = datetime(1970, 1, 1)
            delta = date - epoch
            return int(delta.total_seconds())

    raise ValueError(f"Некорректный аргумент {date=}")
def diff_sec(date1: datetime, date2: datetime) -> float:
    """
    Возвращает разницу между датами в секундах как `date2 - date1`.
    Результат положительный, если `date1 < date2`, и отрицательный, если
    `date1 > date2`.

    ### Аргументы:
    :param date1: первая дата
    :param date2: вторая дата

    :return: разница в секундах
    """
    return (date2 - date1).total_seconds()
