"""
Описывает очереди сохранения, отправки и фоновой обработки.
Модуль относится к архитектурной зоне: прикладной слой `relay`, который связывает пользователей, сессии, доменную модель, GPT, уведомления и runtime-логику приложения.

### Публичные классы
- `SavingOrder`: очередь последовательного сохранения.
- `QueuedMessage`: элемент очереди отправки сообщений.
- `ProcessTask`: задача фоновой обработки события.

### Публичные функции
- Публичные функции отсутствуют.

### Связи
Используется app-layer сценариями, обработчиками, сессиями и runtime-миксинами для единого пользовательского потока между ботами, GPT и storage.
"""

from __future__ import annotations




from .common import Literal, Thread, abstractmethod, datetime
from bots.types import JSONABLE
from .config import MESSAGE_QUEUE_STATUS
class SavingOrder(list[dict[str, JSONABLE]]):
    """
    `SavingOrder` управляет очередью фонового сохранения и не запускает несколько обработок одного элемента одновременно.

    ### Поля
    - `ITEM_TYPE`: тип элементов, которые принимает очередь.
    - `process`: callable, выполняющий элемент очереди или события.
    - `working`: флаг, разрешающий обработку новых событий транспортом.
    - `in_progress`: элементы очереди, которые уже взяты в обработку.
    - `cycle_thread`: фоновый поток цикла обработки очереди.
    - `threads`: активные фоновые потоки runtime.
    - `max_parallel`: ограничение размера, которое защищает transport/API от слишком длинного payload.

    ### Методы
    - `__init__`: Создаёт объект и сохраняет app-layer ссылки, которые нужны обработчикам.
    - `dumps`: Возвращает JSON-совместимый снимок объекта для storage или callback payload.
    - `process`: Передаёт текущий `Context` выбранному обработчику и обновляет `context.handler` по результату.
    - `check_working`: Проверяет флаг работы транспорта перед использованием.
    - `start`: Запускает сценарий обработки и подготавливает первое сообщение или задачу.
    - `stop`: Останавливает transport-адаптер для новых событий и сбрасывает флаг `working`.
    - `add`: Добавляет элемент в очередь и запускает обработку, если она ещё не идёт.
    - `get_next`: Возвращает next из текущего состояния `SavingOrder`.
    - `start_process`: Запускает process в runtime-потоке приложения.
    - `cycle`: Берёт элементы из очереди и запускает их обработку с учётом лимита параллельности.

    ### Жизненный цикл
    Создаётся app-layer кодом, участвует в обработке пользовательского события и сохраняет изменённое состояние через существующие runtime/storage механизмы.

    ### Пример использования
    ```py
    savingOrder: SavingOrder
    ```
    """
    ITEM_TYPE = dict[str, JSONABLE]

    def __init__(self, process: Callable, max_parallel: int = 5):
        """
        Создаёт объект очереди `SavingOrder` и сохраняет payload, который runtime обработает асинхронно или при следующем проходе.

        ### Аргументы:
        :param process: callable, который выполняет элемент очереди
        :param max_parallel: max parallel

        ### Пример использования:
        ```py
        savingOrder = SavingOrder(process = process, max_parallel = max_parallel)
        ```
        """
        self.process = process
        self.working: bool = False
        self.in_progress: list[SavingOrder.ITEM_TYPE] = []
        self.cycle_thread: Thread | None = None
        self.threads: list[Thread] = []
        self.max_parallel: int = int(max_parallel)

    def dumps(self) -> BotTypes.SAVING_ORDER_TYPE:
        """
        Возвращает JSON-совместимый снимок объекта для storage или callback payload.

        :return: JSON-совместимый словарь для сохранения или передачи между слоями

        ### Пример использования:
        ```py
        savingOrder.dumps()
        ```
        """
        return {
            "order": [
                dict(item) for item in self
            ],
            "in_progress": [
                dict(item) for item in self.in_progress
            ]
        }

    @abstractmethod
    def process(self, item: ITEM_TYPE):
        """
        Передаёт текущий `Context` выбранному обработчику и обновляет `context.handler` по результату.

        ### Аргументы:
        :param item: элемент очереди или коллекции

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        savingOrder.process(item = item)
        ```
        """
        raise NotImplementedError()

    def check_working(self) -> bool:
        """
        Возвращает, разрешена ли обработка событий этим transport-адаптером.

        :return: `True`, если возвращает, разрешена ли обработка событий этим transport-адаптером; иначе `False`

        ### Пример использования:
        ```py
        savingOrder.check_working()
        ```
        """
        return self.working

    def start(self):
        """
        Запускает сценарий обработки и подготавливает первое сообщение или задачу.

        :raises RuntimeError: если объект ещё не связан с необходимым runtime-состоянием

        ### Пример использования:
        ```py
        savingOrder.start()
        ```
        """
        if self.check_working():
            raise RuntimeError(f"SavingOrder уже запущена")

        self.working = True
        self.start_cycle()

    def stop(self):
        """
        Останавливает transport-адаптер для новых событий и сбрасывает флаг `working`.

        ### Пример использования:
        ```py
        savingOrder.stop()
        ```
        """
        self.working = False

    def add(self, data: ITEM_TYPE):
        """
        Добавляет элемент в очередь и запускает обработку, если она ещё не идёт.

        ### Аргументы:
        :param data: сериализованный словарь

        ### Пример использования:
        ```py
        savingOrder.add(data = data)
        ```
        """
        self.append(data)
        self.prove_started()

    def get_next(self) -> ITEM_TYPE | None:
        """
        Возвращает следующий элемент очереди.

        :return: next

        ### Пример использования:
        ```py
        savingOrder.get_next()
        ```
        """
        for item in self:
            if item not in self.in_progress:
                self.remove(item)
                return item

    def start_process(self, item: ITEM_TYPE):
        """
        Запускает сценарий обработки и подготавливает первое сообщение или задачу.

        ### Аргументы:
        :param item: элемент очереди или коллекции

        ### Пример использования:
        ```py
        savingOrder.start_process(item = item)
        ```
        """
        def process_item():
            # try catch finally
            self.process(item)
            self.in_progress.remove(item)
            self.prove_started()

        thread: Thread = Thread(target = process_item)
        self.threads.append(thread)
        self.in_progress.append(item)
        thread.start()

    def cycle(self):
        """
        Берёт элементы из очереди и запускает их обработку с учётом лимита параллельности.

        ### Пример использования:
        ```py
        savingOrder.cycle()
        ```
        """
        while self.check_working():
            if len(self.in_progress) < self.max_parallel:
                item: SavingOrder.ITEM_TYPE | None = self.get_next()

                if item is None:
                    self.stop()
                else:
                    self.start_process(item)
            else:
                self.stop()

        self.cycle_thread = None

    def start_cycle(self):
        """
        Запускает cycle в runtime-потоке приложения.

        :raises RuntimeError: если объект ещё не связан с необходимым runtime-состоянием

        ### Примеры вызова:
        ```py
        savingOrder.start_cycle()
        ```
        """
        if self.cycle_thread:
            raise RuntimeError(f"SavingOrder уже запущена")

        self.cycle_thread = Thread(target = self.cycle)
        self.cycle_thread.start()

    def prove_started(self):
        """
        Проверяет введённое пользователем значение для шага `started`.

        ### Пример использования:
        ```py
        savingOrder.prove_started()
        ```
        """
        if not self.check_working() and len(self) > 0:
            self.start()


class QueuedMessage():
    """
    Описывает wrapper-сообщение transport-layer `QueuedMessage`.

    ### Поля
    - `STATUS_PENDING`: статус сообщения, ожидающего отправки.
    - `STATUS_SENDING`: статус сообщения, которое сейчас отправляется.
    - `STATUS_SENT`: статус успешно отправленного сообщения.
    - `STATUS_FAILED`: статус сообщения, отправка которого завершилась ошибкой.
    - `STATUSES`: допустимые статусы очереди сообщений.
    - `id`: внутренний идентификатор записи или доменного объекта.
    - `message`: хранит wrapper-сообщение для операций этого объекта.
    - `bot_key`: хранит ключ транспорта для операций этого объекта.
    - `chat_id`: идентификатор объекта или связанной сущности, по которому runtime восстанавливает связь между слоями.
    - `compression`: флаг сжатия групп сообщений перед отправкой.

    ### Методы
    - `__init__`: Создаёт объект и сохраняет app-layer ссылки, которые нужны обработчикам.
    - `loads`: Восстанавливает объект из JSON-совместимого словаря.
    - `dumps`: Возвращает JSON-совместимый снимок объекта для storage или callback payload.
    - `mark`: Обновляет статус queued-сообщения и последнюю ошибку отправки.
    - `check_pending`: Проверяет pending перед использованием.
    - `check_sent`: Проверяет sent перед использованием.

    ### Жизненный цикл
    Создаётся app-layer кодом, участвует в обработке пользовательского события и сохраняет изменённое состояние через существующие runtime/storage механизмы.

    ### Пример использования
    ```py
    queuedMessage: QueuedMessage
    ```
    """
    STATUS_PENDING: Literal["pending"] = "pending"
    STATUS_SENDING: Literal["sending"] = "sending"
    STATUS_SENT: Literal["sent"] = "sent"
    STATUS_FAILED: Literal["failed"] = "failed"
    STATUSES: tuple[str, str, str, str] = (
        STATUS_PENDING,
        STATUS_SENDING,
        STATUS_SENT,
        STATUS_FAILED,
    )

    def __init__(
            self,
            queue_id: int,
            message: Message,
            bot_key: BOT_KEY,
            chat_id: int,
            compression: bool = True,
            parse_mode: str = "",
            status: MESSAGE_QUEUE_STATUS = STATUS_PENDING,
            attempts: int = 0,
            last_error: str = "",
            created_at: str | None = None,
            updated_at: str | None = None,
            ):
        """
        Создаёт объект очереди `QueuedMessage` и сохраняет payload, который runtime обработает асинхронно или при следующем проходе.

        ### Аргументы:
        :param queue_id: queue id
        :param message: сообщение проекта или сообщение конкретного транспорта
        :param bot_key: ключ транспорта
        :param chat_id: идентификатор чата
        :param compression: признак сжатия вложения
        :param parse_mode: режим разметки сообщения
        :param status: статус runtime-задачи
        :param attempts: число уже выполненных попыток
        :param last_error: last error
        :param created_at: created at
        :param updated_at: updated at

        ### Пример использования:
        ```py
        queuedMessage = QueuedMessage(queue_id = queue_id, message = message, bot_key = bot_key, chat_id = chat_id, compression = compression, parse_mode = parse_mode, status = status, attempts = attempts, last_error = last_error, created_at = created_at, updated_at = updated_at)
        ```
        """
        self.id: int = int(queue_id)
        self.message: Message = message
        self.bot_key: BOT_KEY = bot_key
        self.chat_id: int = int(chat_id)
        self.compression: bool = bool(compression)
        self.parse_mode: str = str(parse_mode or "")
        self.status: MESSAGE_QUEUE_STATUS = status if status in self.__class__.STATUSES else self.__class__.STATUS_PENDING
        self.attempts: int = int(attempts)
        self.last_error: str = str(last_error or "")
        self.created_at: str = str(created_at or datetime.now().isoformat())
        self.updated_at: str = str(updated_at or self.created_at)

    @classmethod
    def loads(cls, data: BotTypes.QUEUE_ITEM_TYPE | dict[str, JSONABLE], get_bot: Callable[[BOT_KEY], BOT]) -> QueuedMessage:
        """
        Восстанавливает объект из JSON-совместимого словаря.

        ### Аргументы:
        :param data: сериализованный словарь
        :param get_bot: get bot

        :return: восстановленный объект или загруженное состояние

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        QueuedMessage.loads(data = data, get_bot = get_bot)
        ```
        """
        bot_key_value: str = str(data.get("bot_key", ""))

        if bot_key_value not in ("vkbot", "telebot"):
            raise ValueError(f"Некорректное значение очереди отправки {bot_key_value=}")

        bot_key: BOT_KEY = bot_key_value
        message_data: dict[str, JSONABLE] = dict(data.get("message", {}))
        message: Message = Message.loads(message_data, get_bot)
        status: str = str(data.get("status", cls.STATUS_PENDING))

        return cls(
            int(data.get("id", 0)),
            message,
            bot_key,
            int(data.get("chat_id", 0)),
            compression = bool(data.get("compression", True)),
            parse_mode = str(data.get("parse_mode", "")),
            status = status if status in cls.STATUSES else cls.STATUS_PENDING,
            attempts = int(data.get("attempts", 0)),
            last_error = str(data.get("last_error", "")),
            created_at = str(data.get("created_at", "")),
            updated_at = str(data.get("updated_at", "")),
        )

    def dumps(self) -> BotTypes.QUEUE_ITEM_TYPE:
        """
        Возвращает JSON-совместимый снимок объекта для storage или callback payload.

        :return: JSON-совместимый словарь для сохранения или передачи между слоями

        ### Пример использования:
        ```py
        queuedMessage.dumps()
        ```
        """
        return {
            "id": int(self.id),
            "message": self.message.dumps(),
            "bot_key": str(self.bot_key),
            "chat_id": int(self.chat_id),
            "compression": bool(self.compression),
            "parse_mode": str(self.parse_mode),
            "status": str(self.status),
            "attempts": int(self.attempts),
            "last_error": str(self.last_error),
            "created_at": str(self.created_at),
            "updated_at": str(self.updated_at),
        }

    def mark(self, status: MESSAGE_QUEUE_STATUS, last_error: str = ""):
        """
        Обновляет статус queued-сообщения и последнюю ошибку отправки.

        ### Аргументы:
        :param status: статус runtime-задачи
        :param last_error: last error

        ### Пример использования:
        ```py
        queuedMessage.mark(status = status, last_error = last_error)
        ```
        """
        self.status = status if status in self.__class__.STATUSES else self.__class__.STATUS_PENDING
        self.last_error = str(last_error or "")
        self.updated_at = datetime.now().isoformat()

    def check_pending(self) -> bool:
        """
        Проверяет значение `pending` перед сохранением или использованием.

        :return: `True`, если значение `pending` перед сохранением или использованием; иначе `False`

        ### Пример использования:
        ```py
        queuedMessage.check_pending()
        ```
        """
        return self.status in (self.__class__.STATUS_PENDING, self.__class__.STATUS_SENDING, self.__class__.STATUS_FAILED)

    def check_sent(self) -> bool:
        """
        Проверяет значение `sent` перед сохранением или использованием.

        :return: `True`, если значение `sent` перед сохранением или использованием; иначе `False`

        ### Пример использования:
        ```py
        queuedMessage.check_sent()
        ```
        """
        return self.message.check_sent(self.bot_key, self.chat_id)


class ProcessTask():

    """
    `ProcessTask` описывает отложенную runtime-задачу: transport-событие, bot, пользователя и приоритет обработки.

    ### Поля
    - `id`: внутренний идентификатор записи или доменного объекта.
    - `bot`: transport-адаптер, с которым работает объект.
    - `event`: хранит событие транспорта для операций этого объекта.
    - `admin_priority`: флаг приоритетной обработки задачи администратора.

    ### Методы
    - `__init__`: Создаёт объект и сохраняет app-layer ссылки, которые нужны обработчикам.
    - `get_queue_item`: Возвращает queue item из текущего состояния `ProcessTask`.

    ### Жизненный цикл
    Создаётся app-layer кодом, участвует в обработке пользовательского события и сохраняет изменённое состояние через существующие runtime/storage механизмы.

    ### Пример использования
    ```py
    processTask: ProcessTask
    ```
    """
    def __init__(self, task_id: int, bot: BOT, event: Bot.Event, admin_priority: bool):
        """
        Создаёт объект очереди `ProcessTask` и сохраняет payload, который runtime обработает асинхронно или при следующем проходе.

        ### Аргументы:
        :param task_id: task id
        :param bot: transport-адаптер
        :param event: transport-событие для обработки
        :param admin_priority: admin priority

        ### Пример использования:
        ```py
        processTask = ProcessTask(task_id = task_id, bot = bot, event = event, admin_priority = admin_priority)
        ```
        """
        self.id: int = int(task_id)
        self.bot: BOT = bot
        self.event: Bot.Event = event
        self.admin_priority: bool = bool(admin_priority)

    def get_queue_item(self) -> tuple[int, int, ProcessTask]:
        """
        Возвращает объект очереди для фоновой обработки.

        :return: queue item

        ### Пример использования:
        ```py
        processTask.get_queue_item()
        ```
        """
        priority: int = 0 if self.admin_priority else 1
        return priority, int(self.id), self
