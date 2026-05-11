"""
Запускает приложение через новый app-layer `relay`.
Модуль относится к архитектурной зоне: прикладной слой `relay`, который связывает пользователей, сессии, доменную модель, GPT, уведомления и runtime-логику приложения.

### Публичные классы
- Публичные классы отсутствуют.

### Публичные функции
- `run_bot`: запускает приложение с текущими настройками runtime.

### Связи
Используется app-layer сценариями, обработчиками, сессиями и runtime-миксинами для единого пользовательского потока между ботами, GPT и storage.
"""

from __future__ import annotations


from .common import argparse, setup_logging, sleep, sys
from .config import SKIP_POLLING, logger
from .utils import parse_startup_args
from .app import App


def run_bot(argv: list[str] | None = None, app_class: type[App] = App) -> int:
    """
    Разбирает CLI-аргументы, настраивает logging, создаёт `App` и запускает runtime loop.
    В режиме `--check-startup` проверяет загрузку ботов без запуска polling.

    :return: код завершения: `0` при успешной проверке или штатном завершении, `1` если не загружены боты
    """
    startup_args: argparse.Namespace = parse_startup_args(argv)
    check_startup: bool = bool(startup_args.check_startup)
    enter_menu: bool = sys.stdin.isatty() and not check_startup
    debug: bool = bool(startup_args.debug)
    setup_logging(debug)

    autocenter: App = app_class(enter_menu = enter_menu)

    if not autocenter.bots:
        logger.error(
            "Не загружены боты. Проверьте `bot_configs` "
            "или запустите бота интерактивно для первичной настройки."
        )
        autocenter.stop()
        return 1

    if not autocenter.has_active_admins():
        logger.warning(
            "Активные администраторы не найдены. Бот продолжит запуск без административных пользователей."
        )

    if check_startup:
        logger.info(
            "Проверка запуска успешна. Загружены боты: %s",
            ", ".join(bot.get_bot_key() for bot in autocenter.bots),
        )
        autocenter.stop()
        return 0

    autocenter.start()
    logger.info("Запуск бота...")
    sleep(SKIP_POLLING)
    logger.info("Запущены боты: %s", ", ".join(bot.get_bot_key() for bot in autocenter.bots))
    while autocenter.check_working():
        sleep(1)
    return 0
