"""
Описывает runtime-операции для transport-ботов.
Модуль относится к архитектурной зоне: прикладной слой `relay`, который связывает пользователей, сессии, доменную модель, GPT, уведомления и runtime-логику приложения.

### Публичные классы
- `BotsMixin`: runtime-логика подключённых ботов.

### Публичные функции
- Публичные функции отсутствуют.

### Связи
Используется app-layer сценариями, обработчиками, сессиями и runtime-миксинами для единого пользовательского потока между ботами, GPT и storage.
"""

from __future__ import annotations



from relay.config import BOT_KEYS, logger
from relay.utils import catch_parsefiles
class BotsMixin:
        """
        Добавляет `App` операции конфигурации транспортных ботов без привязки к transport-layer.
        Mixin рассчитан на включение в `App` и работает с его registry, storage, пользователями, ботами и очередями.

        ### Методы
        - `get_bot`: Возвращает bot из текущего состояния `BotsMixin`.
        - `dumps_bots`: Нормализует конфигурации транспортных ботов к JSON-совместимому виду storage/API.
        - `save_bots`: Сохраняет конфигурации transport-ботов в storage.
        - `create_bot`: Создаёт bot и связывает результат с текущим app-layer состоянием.
        - `load_bots`: Загружает конфигурации транспортных ботов из storage.

        ### Жизненный цикл
        Создаётся app-layer кодом, участвует в обработке пользовательского события и сохраняет изменённое состояние через существующие runtime/storage механизмы.

        ### Пример использования
        ```py
        app: BotsMixin
        ```
        """
        def get_bot(self, bot_key: BOT_KEY) -> BOT:
            """
            Возвращает привязанный transport-адаптер.

            ### Аргументы:
            :param bot_key: ключ транспорта

            :return: transport-адаптер

            :raises Exception: если нижележащий слой сообщает об ошибке операции

            :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

            ### Пример использования:
            ```py
            botsMixin.get_bot(bot_key = bot_key)
            ```
            """
            if bot_key not in BOT_KEYS:

                raise ValueError(f"Некорректное значение аргумента {bot_key=}")

            for bot in self.bots:

                if bot.get_bot_key() == bot_key:

                    return bot

            raise Exception(f"Бот с {bot_key=} не найден")

        def dumps_bots(self) -> BOTS_TYPE:
            """
            Нормализует конфигурации транспортных ботов к JSON-совместимому виду storage/API.

            :return: JSON-совместимое представление для конфигурации транспортных ботов

            ### Примеры вызова:
            ```py
            app.dumps_bots()
            ```
            """
            return {

                "bots": [

                    {

                        "bot_key": bot.get_bot_key(),

                        "token": bot.get_token(),

                        "name": bot.get_name(),

                        "group_id": int(bot.get_group_id())

                    } for bot in self.bots

                ]

            }

        def save_bots(self):
            """
            Сохраняет конфигурации transport-ботов в storage.

            ### Примеры вызова:
            ```py
            app.save_bots()
            ```
            """
            self.storage.save_bots(self.dumps_bots())

            logger.info("Сохранены настройки ботов: count=%s", len(self.bots))

        def create_bot(self, bot_key: BOT_KEY, token: str, name: str, group_id: int, save: bool = True):
            """
            Создаёт bot и связывает результат с текущим app-layer состоянием.

            ### Аргументы:
            :param bot_key: ключ транспорта, например `vkbot` или `telebot`
            :param token: секретный token transport-бота из безопасной конфигурации или storage
            :param name: служебное имя бота, элемента, команды или настройки
            :param group_id: идентификатор группы или сообщества транспорта
            :param save: нужно ли сразу сохранить состояние пользователя после изменения

            ### Пример использования:
            ```py
            app.create_bot(bot_key = bot_key, token = token, name = name, group_id = group_id, save = save)
            ```
            """
            bot_class: type[BOT] = self.__class__.BOT_KEYS[bot_key]

            bot: BOT = bot_class(token, name, group_id = group_id)

            self.bots.append(bot)

            if save:

                self.save_bots()

            logger.info("Создан бот: bot_key=%s name=%s group_id=%s", bot_key, name, group_id)

        def load_bots(self, enter_menu: bool = True):
            """
            Загружает данные из storage или внешнего transport/API и приводит их к объектам проекта.

            ### Аргументы:
            :param enter_menu: enter menu

            :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

            ### Пример использования:
            ```py
            botsMixin.load_bots(enter_menu = enter_menu)
            ```
            """
            data: "App.BOTS_TYPE" = self.storage.load_bots()

            for bot_data in data.get("bots", []):

                with catch_parsefiles(("bot_configs",), "load_bots"):

                    bot_key: BOT_KEY = bot_data["bot_key"]

                    token: str = bot_data["token"]

                    name: str = bot_data["name"]

                    group_id: int = int(bot_data["group_id"])

                    if bot_key not in self.__class__.BOT_KEYS:

                        raise ValueError(f"Некорректное значение под ключом {bot_key=}")

                    if group_id < 0:

                        raise ValueError(f"Некорректное значение под ключом {group_id=}")

                    if (not token) or not isinstance(token, str):

                        raise ValueError("Некорректное значение под ключом token")

                    self.create_bot(bot_key, token, name, group_id, save = False)

                    self.active_bots.append(bot_key)

                    logger.info("Загружен бот: bot_key=%s name=%s group_id=%s", bot_key, name, group_id)

            if enter_menu and not self.bots:

                while self.check_working():

                    self.bots_menu()
