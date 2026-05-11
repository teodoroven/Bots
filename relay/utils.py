"""
Содержит прикладные helper-функции для callback data, токенов, дат и startup-настроек.
Модуль относится к архитектурной зоне: прикладной слой `relay`, который связывает пользователей, сессии, доменную модель, GPT, уведомления и runtime-логику приложения.

### Публичные классы
- Публичные классы отсутствуют.

### Публичные функции
- `print_level`: форматирует уровень вложенности для диагностического вывода.
- `join_callback`: собирает callback data из частей.
- `split_callback`: разбирает callback data на части.
- `get_answer`: получает ответ из callback payload.
- `get_action`: получает действие из callback payload.
- `is_int`: проверяет, что значение можно использовать как `int`.
- `is_float`: проверяет, что значение можно использовать как `float`.
- `log_warn`: записывает warning в общий logger приложения.
- `parse_startup_args`: разбирает параметры запуска приложения.
- `parse_debug_flag`: получает debug-флаг из CLI-аргументов.
- `catch_parsefiles`: создаёт context manager для ошибок разбора файлов.
- `catch_json`: создаёт context manager для ошибок JSON.
- `count_tokens`: считает токены GPT-сообщений.
- `count_group_tokens`: считает токены группы сообщений.
- `parse_period`: форматирует период в секундах через крупнейшую подходящую единицу.
- `get_month_date`: возвращает конец месяца для расписания.
- `get_month_string`: возвращает строку `месяц.год`.

### Связи
Используется app-layer сценариями, обработчиками, сессиями и runtime-миксинами для единого пользовательского потока между ботами, GPT и storage.
"""

from __future__ import annotations




from .common import (
    argparse,
    contextmanager,
    datetime,
    json,
    tiktoken,
)
from .config import CALLBACK_SEPARATOR, PERIODS, get_phrase, logger
def print_level(string: str, level: int = 0) -> list[str]:
    """
    Разбивает диагностический текст на строки с отступом для заданного уровня вложенности.

    ### Аргументы:
    :param string: исходный текст, который нужно подготовить для вывода
    :param level: уровень вложенности; каждый уровень добавляет два пробела и уменьшает ширину строки

    :return: список строк с применённым отступом
    """
    max_length: int = 133 - level*2
    lines: list[str] = []

    for line in string.split("\n"):
        while len(line) > max_length:
            lines.append(line[:max_length])
            line = line[max_length:]

        lines.append(line)

    tab: str = "  " * level
    return [f"{tab}{line}" for line in lines]


def join_callback(*args: Iterable[JSONABLE]):
    """
    Объединяет аргументы в одну строку для `Bot.Keyboard.Button.callback_data` (`payload`).
    - WARNING: Использует разделитель `CALLBACK_SEPARATOR`, функция не вызовет исключение, но в аргументах не должен встречаться разделитель.

    :param args: Аргументы для объединения будут приведены к строковому типу, не должны содержать `CALLBACK_SEPARATOR`.
    :return: Объединённая строка для `Bot.Keyboard.Button.callback_data` (`payload`).
    """
    return CALLBACK_SEPARATOR.join(map(str, args))


def split_callback(string: str) -> list[str]:
    """
    Разделяет полученный из API `payload` (`Bot.Keyboard.Button.callback_data`) на аргументы.

    :param string: Строка для разделения, может содержать `CALLBACK_SEPARATOR`.
    :return: Строковые аргументы.
    """
    return string.split(CALLBACK_SEPARATOR)


def get_answer(callback_data: str):
    """
    Удаляет из `callback_data` начальный `ANSWER_CALLBACK` и возвращает остаток.
    """
    return callback_data[callback_data.find(ANSWER_CALLBACK) + len(ANSWER_CALLBACK):]


def get_action(callback_data: str):
    """
    Удаляет из `callback_data` начальный `ACTION_CALLBACK` и возвращает остаток.
    """
    return callback_data[callback_data.find(ACTION_CALLBACK) + len(ACTION_CALLBACK):]


def is_int(value: Any) -> bool:
    """
    Пытается привести аргумент к целочисленному типу `int`, и если получилось возвращает `True`, иначе - `False`.

    :param value: Аргумент для проверки.
    :return: `True` если можно привести к int, иначе `False`.
    """
    try:
        int(value)
    except OverflowError:
        return False
    except ValueError:
        return False
    except TypeError:
        return False
    else:
        return True


def is_float(value: Any) -> bool:
    """
    Пытается привести аргумент к типу `float`, и если получилось возвращает `True`, иначе - `False`.

    :param value: Аргумент для проверки.
    :return: `True` если можно привести к float, иначе `False`.
    """
    try:
        float(value)
    except ValueError:
        return False
    except TypeError:
        return False
    else:
        return True


def log_warn(message: str):
    """
    Записывает сообщение с уровнем warning в общий logger приложения.

    ### Аргументы:
    :param message: текст предупреждения
    """
    logger.warning(message)


def parse_startup_args(argv: list[str] | None = None) -> argparse.Namespace:
    """
    Разбирает CLI-аргументы запуска приложения через `argparse`.
    Поддерживает `--debug` для debug-логирования и `--check-startup` для проверки загрузки без polling.

    ### Аргументы:
    :param argv: список CLI-аргументов без имени программы; если `None`, `argparse` читает `sys.argv`

    :return: `argparse.Namespace` с полями `debug` и `check_startup`
    """
    parser: argparse.ArgumentParser = argparse.ArgumentParser(add_help = True)
    parser.add_argument(
        "--debug",
        action = "store_true",
        help = "Включает debug-режим логирования.",
    )
    parser.add_argument(
        "--check-startup",
        action = "store_true",
        help = "Проверяет загрузку конфигурации без запуска polling.",
    )
    return parser.parse_args(argv)


def parse_debug_flag(argv: list[str] | None = None) -> bool:
    """
    Возвращает значение CLI-флага `--debug`.
    Метод вызывает `parse_startup_args(argv)` и не читает переменные окружения.

    ### Аргументы:
    :param argv: список CLI-аргументов без имени программы; если `None`, `argparse` читает `sys.argv`

    :return: `True`, если в CLI-аргументах есть `--debug`; иначе `False`
    """
    args: argparse.Namespace = parse_startup_args(argv)
    return bool(args.debug)


@contextmanager
def catch_parsefiles(filenames: tuple[str] = tuple(), phrase_key: str = ""):
    def show_err(err: Exception):
        phrase: str = get_phrase(phrase_key) if phrase_key else ""
        mes: str = f"{phrase}\n" if phrase else ""

        if filenames:
            mes += f"Возникла ошибка при обработке содержимого одного из файлов {filenames}\n{err.__class__.__name__}: {err}"
        else:
            mes += f"Возникла ошибка при обработке словаря - {err.__class__.__name__}: {err}"

        log_warn(mes)

    try:
        yield
    except TypeError as err:
        show_err(err)
    except KeyError as err:
        show_err(err)
    except ValueError as err:
        show_err(err)
    except OverflowError as err:
        show_err(err)
    except AssertionError as err:
        show_err(err)


@contextmanager
def catch_json(filenames: tuple[str] = tuple()):
    def show_err(err: Exception):
        message: str

        if filenames:
            message = f"Возникла ошибка при парсинге json содержимого одного из файлов {filenames}\n{err.__class__.__name__}: {err}"
        else:
            message = f"Возникла ошибка при парсинге json - {err.__class__.__name__}: {err}"

        log_warn(message)

    try:
        yield
    except json.decoder.JSONDecodeError as err:
        show_err(err)


def count_tokens(messages: list[dict[Literal["role", "content", "name"], str]], model: Model) -> int:
    """
    Оценивает количество токенов в списке GPT chat messages для выбранной модели.
    Если модель неизвестна `tiktoken`, используется кодировка `cl100k_base`.

    ### Аргументы:
    :param messages: сообщения в формате chat completion с ключами `role`, `content` и опционально `name`
    :param model: модель, по имени которой выбирается tokenizer

    :return: примерное количество токенов с учётом служебных токенов chat-формата
    """
    if not messages:
        return 0

    try:
        encoding = tiktoken.encoding_for_model(model.model)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")

    num_tokens: int = 0

    for message in messages:
        num_tokens += 4  # every message follows <im_start>{role/name}\n{content}<im_end>\n

        for key, value in message.items():
            num_tokens += len(encoding.encode(value))

            if key == "name":  # if exists name, the role is omitted
                num_tokens += -1  # role is always required and always 1 token

    num_tokens += 2  # every reply is primed with <im_start>assistant
    return num_tokens


def count_group_tokens(group: Message.MessagesGroup) -> int:
    """
    Быстро оценивает токены группы wrapper-сообщений по длине объединённого текста.

    ### Аргументы:
    :param group: группа сообщений, для которой нужно оценить объём текста

    :return: приблизительное количество токенов
    """
    return len(group.get_text()) // 2


def parse_period(period: int) -> str:
    """
    Форматирует период в секундах через крупнейшую единицу из `PERIODS`.
    Если значение не делится на выбранную единицу без остатка, округляет результат до одного знака после запятой.

    ### Аргументы:
    :param period: длительность периода в секундах

    :return: строка с числом и локализованной единицей периода, например `60 -> 1 мин`
    """
    periods: list[int] = sorted(list(PERIODS), reverse = True)

    for unit_period in periods:
        unit_key: str = PERIODS[unit_period]
        unit_string: str = get_phrase(unit_key)

        if period / unit_period >= 1:
            if period % unit_period == 0:
                return f"{period // unit_period} {unit_string}"
            else:
                return f"{round(period / unit_period, 1)} {unit_string}"

    unit_string: str = get_phrase("period_second")
    return f"{period} {unit_string}"


def get_month_date(available_threshold: datetime, month_index: int) -> datetime:
    """
    Возвращает последний момент месяца, заданного индексом относительно начала года.
    Индексы больше 11 переносятся на следующие годы.

    ### Аргументы:
    :param available_threshold: дата, из которой берётся базовый год
    :param month_index: индекс месяца с нуля

    :return: `datetime` последнего дня месяца в `23:59:59.999999`
    """
    year: int = available_threshold.year
    month: int = month_index + 1
    last_day: int = 31

    # Корректируем год и месяц если месяц > 12
    year += (month - 1) // 12
    month = (month - 1) % 12 + 1

    # Получаем последний день месяца
    if month != 12:
        next_month: datetime = datetime(year, month + 1, 1)
        last_day = (next_month - timedelta(days=1)).day

    return datetime(year, month, last_day, 23, 59, 59, 999999)


def get_month_string(date: datetime) -> str:
    """
    Форматирует дату как строковый ключ месяца.

    ### Аргументы:
    :param date: дата, из которой берутся месяц и год

    :return: строка вида `M.YYYY`
    """
    return f"{date.month}.{date.year}"
