"""
Описывает транспортный бот и операции отправки или получения событий.
Модуль относится к архитектурной зоне: слой унификации транспортов `bots`, который скрывает различия Telegram и VK за общими объектами сообщений, клавиатур, вложений и событий.

### Публичные классы
- `Bot`: базовый контракт транспорта бота.

### Публичные функции
- Публичные функции отсутствуют.

### Связи
Используется транспортным слоем и wrapper-логикой, чтобы app-layer работал с `Message`, `Keyboard`, `Button`, `Attachment` и `Event` без привязки к конкретной соцсети.
"""

from __future__ import annotations


from bots.constants import EVENT_INTERVAL, EVENT_TIMEOUT
from bots.compat import Iterable, Thread, chain, sleep
from bots.types import BOT_KEY

class Bot():
    """
    Задаёт общий контракт transport-layer для Telegram и VK ботов.
    Базовый класс хранит конфигурацию транспортного адаптера, очередь входящих событий и общие операции разбиения сообщений. Конкретные Telegram/VK классы реализуют отправку и polling.

    ### Поля
    - `BOT_KEY`: строковый ключ транспорта, по которому app-layer различает Telegram и VK.
    - `URL`: базовый адрес API или служебного endpoint конкретного транспорта.
    - `MAX_SPLIT`: дистанция поиска безопасной границы при разбиении длинного текста.
    - `name`: человекочитаемое имя бота в конфигурации и логах.
    - `token`: секретный token transport-бота. Используется для инициализации Telegram/VK SDK и не должен попадать в логи или публичные примеры.
    - `group_id`: идентификатор группы или сообщества, от имени которого работает transport-бот.
    - `working`: флаг, разрешающий обработку новых событий транспортом.
    - `events`: очередь входящих событий по chat_id до объединения и обработки.

    ### Методы
    - `check_chat_id`: Проверяет chat id перед использованием.
    - `check_attachment`: Проверяет вложение сообщения перед использованием.
    - `__init__`: Создаёт объект и сохраняет данные, нужные transport-layer для отправки, сравнения или восстановления объекта.
    - `get_bot_key`: Возвращает ключ транспорта текущего бота.
    - `check_working`: Возвращает, разрешена ли обработка событий этим transport-адаптером.
    - `stop`: Останавливает transport-адаптер для новых событий и сбрасывает флаг `working`.
    - `get_matches`: Находит уже совпадающий префикс сообщений перед обновлением чата.
    - `check_group_id`: Проверяет идентификатор группы или сообщества перед использованием.
    - `set_group_id`: Проверяет и сохраняет идентификатор группы или сообщества в состоянии `Bot`.
    - `get_group_id`: Возвращает идентификатор группы или сообщества из текущего состояния `Bot`.

    ### Жизненный цикл
    Экземпляры создаются из конфигурации транспорта, принимают события платформы и отдают app-layer унифицированные объекты событий и сообщений.

    ### Пример использования
    ```py
    bot: Bot
    ```
    """
    BOT_KEY: str = ""
    URL: str = "http://google.com/"

    """
    Максимальная дистанция на которой разделение слишком длинного сообщения на части будет искать пробелы или сносы строк.
    Если среди последних 100 символов таковых нет, то срез будет ровно по max_length.
    """
    MAX_SPLIT: int = 100

    @staticmethod
    def check_chat_id(chat_id: int) -> bool:
        """
        Проверяет, подходит ли chat id для transport-сообщения или события.

        ### Аргументы:
        :param chat_id: идентификатор чата

        :return: `True`, если подходит ли chat id для transport-сообщения или события; иначе `False`

        ### Пример использования:
        ```py
        Bot.check_chat_id(chat_id = chat_id)
        ```
        """
        return isinstance(chat_id, int) and chat_id >= 0



    @classmethod
    def check_attachment(cls, attachment: Bot.Attachment) -> bool:
        """
        Проверяет, поддерживается ли переданное вложение transport-адаптером.

        ### Аргументы:
        :param attachment: вложение

        :return: `True`, если поддерживается ли переданное вложение transport-адаптером; иначе `False`

        ### Пример использования:
        ```py
        Bot.check_attachment(attachment = attachment)
        ```
        """
        return type(attachment) in cls.__dict__.values()

    def __init__(self, token: str, name: str, group_id: int):
        """
        Сохраняет базовую конфигурацию transport-бота.

        Конструктор валидирует имя, group_id и token через setter-методы,
        включает обработку событий и создаёт пустую очередь входящих событий.

        ### Аргументы:
        :param token: секретный token transport-бота из безопасной конфигурации или storage
        :param name: публичное имя transport-бота в формате `@name`
        :param group_id: идентификатор группы или сообщества транспорта

        ### Пример использования:
        ```py
        bot = Telebot(token = token, name = "@school_bot", group_id = group_id)
        ```
        """
        self.name: str = ""
        self.token: str = ""
        self.group_id: int = -1

        self.set_name(name)
        self.set_group_id(group_id)
        self.set_token(token)

        self.working: bool = True
        self.events: dict[int, list[Bot.Event]] = {}

    def __repr__(self) -> str:
        name = self.name
        group_id = self.group_id
        working = self.working
        bot_key: BOT_KEY = self.get_bot_key()
        return f"{self.__class__.__name__}({bot_key=} {name=} {group_id=} {working=} events={len(self.events)})"

    def get_bot_key(self) -> BOT_KEY:
        """
        Возвращает ключ транспорта текущего бота.

        :return: строковый ключ транспорта, например `telebot` или `vkbot`

        ### Примеры вызова:
        ```py
        bot.get_bot_key()
        ```
        """
        return self.__class__.BOT_KEY

    def check_working(self) -> bool:
        """
        Возвращает, разрешена ли обработка событий этим transport-адаптером.

        :return: `True`, если возвращает, разрешена ли обработка событий этим transport-адаптером; иначе `False`

        ### Пример использования:
        ```py
        bot.check_working()
        ```
        """
        return not not self.working

    def stop(self):
        """
        Останавливает transport-адаптер для новых событий и сбрасывает флаг `working`.

        ### Пример использования:
        ```py
        bot.stop()
        ```
        """
        self.working = False

    def get_matches(self, old_messages: Iterable[Bot.Message], new_messages: Iterable[Bot.Message]) -> list[Bot.Message]:
        """
        Находит уже совпадающий префикс сообщений перед обновлением чата.

        ### Аргументы:
        :param old_messages: сообщения, уже находящиеся в чате
        :param new_messages: сообщения, которые приложение собирается показать

        :return: сообщения, которые можно оставить без переотправки

        ### Пример использования:
        ```py
        bot.get_matches(old_messages = old_messages, new_messages = new_messages)
        ```
        """
        common_prefix_len: int = 0
        min_len: int = min(len(old_messages), len(new_messages))

        while common_prefix_len < min_len:
            old_message: Bot.Message = old_messages[common_prefix_len]
            new_message: Bot.Message = new_messages[common_prefix_len]

            if old_message.compare(new_message) and old_message.owner_id == new_message.owner_id:
                common_prefix_len += 1
            else:
                break

        return old_messages[:common_prefix_len]

    # Методы работы с полями


    @classmethod
    def check_group_id(cls, group_id: int) -> bool:
        """
        Проверяет, что group_id транспорта является неотрицательным целым числом.

        ### Аргументы:
        :param group_id: идентификатор группы или сообщества транспорта

        :return: `True`, если что group_id транспорта является неотрицательным целым числом; иначе `False`

        ### Пример использования:
        ```py
        Bot.check_group_id(group_id = group_id)
        ```
        """
        return isinstance(group_id, int) and group_id >= 0

    def set_group_id(self, group_id: int):
        """
        Проверяет и сохраняет идентификатор группы или сообщества в состоянии `Bot`.

        ### Аргументы:
        :param group_id: идентификатор группы или сообщества транспорта

        :raises ValueError: если значение не проходит локальную проверку перед сохранением

        ### Пример использования:
        ```py
        bot.set_group_id(group_id = group_id)
        ```
        """
        if self.__class__.check_group_id(group_id):
            self.group_id = group_id
        else:
            raise ValueError(f"Некорректное значение аргумента {group_id=}")

    def get_group_id(self) -> int:
        """
        Возвращает сохранённый идентификатор группы или сообщества транспорта.

        :return: идентификатор группы или сообщества транспорта

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        bot.get_group_id()
        ```
        """
        if self.__class__.check_group_id(self.group_id):
            return self.group_id
        raise ValueError(f"Некорректное значение атрибута {self.group_id=}")

    @classmethod
    def check_token(cls, token: str) -> bool:
        """
        Проверяет минимальный формат token транспортного бота.

        Базовый класс проверяет только форму значения. Валидность token во
        внешнем API проверяют конкретные Telegram/VK-адаптеры при подключении.

        ### Аргументы:
        :param token: секретный token, полученный из конфигурации или storage

        :return: `True`, если минимальный формат token транспортного бота; иначе `False`

        ### Пример использования:
        ```py
        Bot.check_token(token = token)
        ```
        """
        return isinstance(token, str) and len(token) >= 46

    def set_token(self, token: str):
        """
        Проверяет и сохраняет token транспортного адаптера в состоянии `Bot`.

        Метод меняет только поле `self.token`; подключение к внешнему API
        остаётся ответственностью конкретного transport-класса.

        ### Аргументы:
        :param token: секретный token transport-бота из безопасной конфигурации или storage

        :raises ValueError: если token не проходит проверку `check_token`

        ### Пример использования:
        ```py
        bot.set_token(token = token)
        ```
        """
        if self.__class__.check_token(token):
            self.token = token
        else:
            raise ValueError("Некорректное значение аргумента token")

    def get_token(self) -> str:
        """
        Возвращает сохранённый token transport-бота после проверки формата.

        :return: секретный token transport-бота

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        bot.get_token()
        ```
        """
        if self.__class__.check_token(self.token):
            return str(self.token).strip()
        else:
            raise ValueError("Некорректное значение атрибута token")

    @classmethod
    def check_name(cls, name: str) -> bool:
        """
        Проверяет, можно ли использовать строку как имя transport-бота.

        ### Аргументы:
        :param name: имя

        :return: `True`, если строку можно использовать как имя transport-бота; иначе `False`

        ### Пример использования:
        ```py
        Bot.check_name(name = name)
        ```
        """
        return isinstance(name, str) and name.startswith("@") and len(name) >= 5

    def set_name(self, name: str):
        """
        Проверяет и сохраняет служебное имя в состоянии `Bot`.

        ### Аргументы:
        :param name: служебное имя бота, элемента, команды или настройки

        :raises ValueError: если значение не проходит локальную проверку перед сохранением

        ### Пример использования:
        ```py
        bot.set_name(name = name)
        ```
        """
        if self.__class__.check_name(name):
            self.name = name
        else:
            raise ValueError(f"Некорректное значение аргумента {name=}")

    def get_name(self) -> str:
        """
        Возвращает сохранённое имя.

        :return: служебное имя

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        bot.get_name()
        ```
        """
        if self.__class__.check_name(self.name):
            return str(self.name).strip()
        else:
            raise ValueError(f"Некорректное значение атрибута {self.name=}")


    # Методы работы с событиями


    def add_id(self, event_id: int):
        """
        Добавляет id события в список обработанных событий transport-адаптера.

        ### Аргументы:
        :param event_id: id события или чата в очереди транспорта

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        bot.add_id(event_id = event_id)
        ```
        """
        if event_id not in self.events:
            if isinstance(event_id, int) and event_id > 0:
                self.events[event_id] = []
            else:
                raise ValueError(f"Некорректное значение аргумента {event_id=}")

    def add_event(self, event: Event):
        """
        Добавляет transport-событие в очередь `self.events[event.chat_id]`.
        Перед вызовом для этого chat id должен быть создан ключ через `add_id`; иначе обращение к `self.events[event.chat_id]` приведёт к `KeyError`.

        ### Аргументы:
        :param event: wrapper-событие, полученное из транспортного слоя

        :raises ValueError: если `event.chat_id` не проходит проверку `Event.check_chat_id`
        :raises KeyError: если очередь для `event.chat_id` ещё не создана в `self.events`

        ### Пример использования:
        ```py
        bot.add_event(event = event)
        ```
        """
        if event.check_chat_id(event.chat_id):
            self.events[event.chat_id].append(event)
        else:
            raise ValueError(f"Некорректное значение атрибута {event.chat_id=}")

    def remove_event(self, event: Event):
        """
        Удаляет событие транспорта из внутреннего состояния или storage.

        ### Аргументы:
        :param event: wrapper-событие, полученное из транспортного слоя

        :raises ValueError: если значение не проходит локальную проверку перед сохранением

        ### Пример использования:
        ```py
        bot.remove_event(event = event)
        ```
        """
        if event.check_chat_id(event.chat_id):
            if event in self.events[event.chat_id]:
                self.events[event.chat_id].remove(event)
        else:
            raise ValueError(f"Некорректное значение атрибута {event.chat_id=}")

    def wait_events(self):
        """
        Даёт соседним событиям одного чата короткое окно для объединения перед обработкой.

        ### Пример использования:
        ```py
        bot.wait_events()
        ```
        """
        sleep(EVENT_TIMEOUT)

    def get_events(self, event_id: int) -> list[Event]:
        """
        Возвращает события указанного chat/event id, отсортированные по дате.

        ### Аргументы:
        :param event_id: идентификатор чата или события в очереди transport-адаптера

        :return: список событий с подходящим id в хронологическом порядке

        ### Пример использования:
        ```py
        bot.get_events(event_id = event_id)
        ```
        """
        return sorted(self.events[event_id] if event_id in self.events else [], key = lambda event: event.date)

    def get_prev_events(self, last_event: Event) -> list[Event]:
        """
        Возвращает цепочку предыдущих событий, если текущее событие последнее в очереди.
        Если после `last_event` уже есть более новые события, возвращается пустой список.

        ### Аргументы:
        :param last_event: событие, для которого нужно найти предыдущие события той же очереди

        :return: предыдущие события той же цепочки или пустой список

        ### Пример использования:
        ```py
        bot.get_prev_events(last_event = last_event)
        ```
        """
        events: list[Bot.Event] = self.get_events(last_event.chat_id)

        # Вся цепочка событий, предыдущих для last_event
        prev_events: list[Bot.Event] = []

        def check_previous(prev_event: Bot.Event) -> bool:
            """
            Возвращает истину, если указанное событие является предыдущим хотя бы для одного из цепочки событий
            """
            return prev_event.prev_for(last_event)

        # Если текущее событие последнее в очереди
        if last_event in events and events.index(last_event) == len(events) - 1:

            for event in events:
                # Проверяем является ли событие предыдущим для last_event
                if check_previous(event):
                    # Удаляем его из очереди
                    self.remove_event(event)

                    # Добавляем его в цепочку
                    prev_events.append(event)

            return prev_events + [last_event]

        return prev_events

    def combine_events(self, events: Iterable[Event]) -> Event:
        """
        Объединяет несколько событий одного чата в последнее событие цепочки.
        Метод переносит в него список вложенных events, склеивает текст через пробел и объединяет вложения.

        ### Аргументы:
        :param events: последовательность wrapper-событий одного чата

        :return: последнее событие из `events`, изменённое на месте

        ### Пример использования:
        ```py
        bot.combine_events(events = events)
        ```
        """
        event: Bot.Event = events[-1]

        # Объединяем события
        event.set_events(list(chain.from_iterable(ev.events for ev in events)))

        # Объединяем текст через пробел
        event.set_text(" ".join([ev.get_text() for ev in events]))

        # Объединяем вложения
        event.set_attachments(list(chain.from_iterable(ev.attachments for ev in events)))

        # Возвращаем последнее событие, в которое были объединены все остальные события
        return event

    def check_callback(self, event: Event) -> bool:
        """
        Проверяет, считается ли событие callback-кнопкой в базовой реализации.
        Базовый класс признаёт callback только через `DEBUG_CALLBACK`; реальные transport-адаптеры могут переопределять этот метод.

        ### Аргументы:
        :param event: transport-событие для проверки

        :return: `True`, если включён `DEBUG_CALLBACK`; иначе `False`

        ### Пример использования:
        ```py
        bot.check_callback(event = event)
        ```
        """
        if event.DEBUG_CALLBACK:
            return True
        return False


    # Методы обработчики


    def listener(self, chat_id: int, text: str):
        """
        Базовый hook для обработки текста входящего события; наследники могут переопределить его.

        ### Аргументы:
        :param chat_id: идентификатор чата
        :param text: текст

        ### Пример использования:
        ```py
        bot.listener(chat_id = chat_id, text = text)
        ```
        """
        # logger.debug(text)
        pass

    def process_message(self, event: Event):
        """
        Обрабатывает wrapper-сообщение в текущем пользовательском или transport-layer потоке.

        ### Аргументы:
        :param event: wrapper-событие, полученное из транспортного слоя

        :return: результат обработки, если нижележащий handler его возвращает

        ### Пример использования:
        ```py
        bot.process_message(event = event)
        ```
        """
        return self.listener(event.chat_id, event.get_text())

    def process_callback(self, event: Event):
        """
        Обрабатывает callback-событие в текущем пользовательском или transport-layer потоке.

        ### Аргументы:
        :param event: wrapper-событие, полученное из транспортного слоя

        :return: результат обработки, если нижележащий handler его возвращает

        ### Пример использования:
        ```py
        bot.process_callback(event = event)
        ```
        """
        return self.listener(event.chat_id, event.get_text())

    def process_event__(self, event: Event):
        """
        Обрабатывает событие транспорта в текущем пользовательском или transport-layer потоке.

        ### Аргументы:
        :param event: wrapper-событие, полученное из транспортного слоя

        :return: результат обработки, если нижележащий handler его возвращает

        ### Пример использования:
        ```py
        bot.process_event__(event = event)
        ```
        """
        if self.check_callback(event):
            return self.process_callback(event)
        else:
            return self.process_message(event)

    def process_event_(self, event: Event):
        """
        Ставит событие в очередь, ждёт соседние события и обрабатывает объединённую цепочку.
        Если за время ожидания появились более поздние события того же чата,
        текущее событие оставляется в очереди: последующее событие соберёт всю
        цепочку через `get_prev_events`. Если объединение не произошло, метод
        повторно проверяет очередь и обрабатывает одиночное событие.

        ### Аргументы:
        :param event: wrapper-событие, полученное из транспортного слоя

        ### Пример использования:
        ```py
        bot.process_event_(event = event)
        ```
        """

        # Добавляем событие в очередь событий
        self.add_event(event)

        # Ожидаем возможного появления следующих событий
        self.wait_events()

        # Получаем предыдущие события
        events: list[Bot.Event] = self.get_prev_events(
            event)  # Если есть последующие события, вернётся [], иначе вернётся список событий, включающий текущее событие

        # Объединяем события
        ev: Bot.Event | None = self.combine_events(events) if events else None

        # Удаляем событие из очереди
        self.remove_event(ev) if ev else None

        # Обрабатываем событие
        self.process_event__(ev) if ev else None

        """
        ### Если событие не было обработано
        Предыдущие события возвращают get_prev_events=[] если есть последующие события
        Но если событие не было обработано с последующими, оно обрабатывается здесь
        """

        # Ожидание возможной обработки события
        sleep(EVENT_INTERVAL)

        # Если событие не было обработано с последующими
        if event and event in self.events[event.chat_id]:
            # Удаляем событие из очереди
            self.remove_event(event)

            # Обрабатываем событие
            self.process_event__(event)

    def process_event(self, event: Event, combine_events: bool = True):
        """
        Запускает обработку события в отдельном `Thread` и не возвращает результат обработчика.
        Если `combine_events=True`, поток вызывает `process_event_`; иначе сразу вызывает `process_event__`.

        ### Аргументы:
        :param event: transport-событие, которое нужно передать в обработчик
        :param combine_events: нужно ли перед обработкой объединять связанные события

        :return: `None`

        ### Пример использования:
        ```py
        bot.process_event(event = event, combine_events = combine_events)
        ```
        """
        def process_event():
            if combine_events:
                return self.process_event_(event)
            else:
                return self.process_event__(event)

        Thread(target = process_event).start()

    # Родительские методы


    def split_text(self, text: str) -> list[str]:
        """
        Разбивает текст на части, которые не превышают лимит транспорта.
        Метод ищет перевод строки или пробел среди последних `MAX_SPLIT`
        символов допустимого блока. Если подходящей границы рядом нет, срез
        выполняется ровно по `Message.MAX_LENGTH`.

        ### Аргументы:
        :param text: исходный текст сообщения

        :return: список текстовых частей, каждая не длиннее лимита транспорта

        ### Пример использования:
        ```py
        bot.split_text(text = text)
        ```
        """
        max_length: int = self.__class__.Message.MAX_LENGTH
        texts: list[str] = []
        text: str = str(text).strip()

        while text:
            part: str = text[:max_length].rstrip()
            last_space: int = part.rfind(" ")
            last_demolition: int = part.rfind("\n")

            last_splitter = max(last_space, last_demolition)
            last_splitter = max_length if last_splitter == -1 else last_splitter
            last_splitter = last_splitter if max_length - last_splitter < self.__class__.MAX_SPLIT else max_length

            part = text[:last_splitter]

            if part.strip():
                texts.append(part)

            text = text[last_splitter:].strip()

        return texts

    def split_attachments(self, attachments: Iterable[Bot.Attachment]) -> list[tuple[Bot.Attachment]]:
        """
        Разбивает вложения на группы, допустимые для одного transport-сообщения.

        ### Аргументы:
        :param attachments: вложения, которые нужно отправить

        :return: список кортежей вложений, разбитых по `Message.MAX_ATTACHMENTS`

        ### Пример использования:
        ```py
        bot.split_attachments(attachments = attachments)
        ```
        """
        max_attachments: int = self.__class__.Message.MAX_ATTACHMENTS
        return [tuple(attachments[i:i + max_attachments]) for i in range(0, len(attachments), max_attachments)]
