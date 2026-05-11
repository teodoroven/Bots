"""
Настраивает логирование приложения в файл и консоль.
Модуль относится к архитектурной зоне: корневой слой проекта, который связывает запуск, compatibility exports и общие настройки приложения.

### Публичные классы
- `ExcludeConsoleFilter`: filter для отсечения шумных console-логов.
- `ExcludeUserFlowFilter`: filter для отделения пользовательского потока от общих логов.

### Публичные функции
- `setup_logging`: настраивает root logger, файл логов и console output.

### Публичные константы и типы
- Ключевые публичные значения отсутствуют.

### Связи
Используется соседними слоями проекта как корневой модуль запуска, compatibility exports или общий набор настроек.
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


class ExcludeConsoleFilter(logging.Filter):
    """
    Фильтр шумных console-логов.
    Класс находится в архитектуре проекта и используется как часть актуальной модульной архитектуры проекта.
    Фильтр используется logging-конфигурацией и решает, какие записи попадут в конкретный handler.

    ### Методы
    - `filter`: отбрасывает шумные записи логгера.

    ### Жизненный цикл
    Создаётся в своём слое приложения и передаётся дальше как объект состояния или поведения без скрытых внешних зависимостей.

    ### Пример использования
    ```py
        exclude_console_filter_type = ExcludeConsoleFilter
    ```
    """
    def filter(self, record: logging.LogRecord) -> bool:
        """
        Проверяет, нужно ли оставить запись в console-логе.

        ### Аргументы:
        :param record: запись логгера перед выводом в console

        :return: `True`, если запись нужно оставить в потоке логов

        ### Пример использования:
        ```py
        result = filter.filter(record = record)
        ```
        """
        return not record.name.startswith(("httpx", "httpcore"))


class ExcludeUserFlowFilter(logging.Filter):
    """
    Фильтр пользовательского потока для общих логов.
    Класс находится в архитектуре проекта и используется как часть актуальной модульной архитектуры проекта.
    Фильтр используется logging-конфигурацией и решает, какие записи попадут в конкретный handler.

    ### Методы
    - `filter`: отбрасывает шумные записи логгера.

    ### Жизненный цикл
    Создаётся в своём слое приложения и передаётся дальше как объект состояния или поведения без скрытых внешних зависимостей.

    ### Пример использования
    ```py
        exclude_user_flow_filter_type = ExcludeUserFlowFilter
    ```
    """
    def filter(self, record: logging.LogRecord) -> bool:
        """
        Проверяет, нужно ли оставить запись в console-логе.

        ### Аргументы:
        :param record: запись логгера перед выводом в console

        :return: `True`, если запись нужно оставить в потоке логов

        ### Пример использования:
        ```py
        result = filter.filter(record = record)
        ```
        """
        return not record.name.startswith("bot.user_flow")


def setup_logging(debug: bool = False):
    logs_dir: Path = Path("logs")
    logs_dir.mkdir(parents = True, exist_ok = True)

    formatter: logging.Formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")

    file_handler: RotatingFileHandler = RotatingFileHandler(
        logs_dir / "bot.log",
        maxBytes = 10 * 1024 * 1024,
        backupCount = 5,
        encoding = "utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.addFilter(ExcludeUserFlowFilter())

    console_handler: logging.StreamHandler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(ExcludeConsoleFilter())
    console_handler.addFilter(ExcludeUserFlowFilter())

    root_logger: logging.Logger = logging.getLogger()
    handler: logging.Handler

    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)
        handler.close()

    root_logger.setLevel(logging.DEBUG if debug else logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    logging.disable(logging.NOTSET)

    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("bot.user_flow").setLevel(logging.WARNING)
