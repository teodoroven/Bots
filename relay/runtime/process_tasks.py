"""
Описывает runtime-операции фоновых задач обработки событий.
Модуль относится к архитектурной зоне: прикладной слой `relay`, который связывает пользователей, сессии, доменную модель, GPT, уведомления и runtime-логику приложения.

### Публичные классы
- `ProcessTaskMixin`: runtime-логика фоновых задач.

### Публичные функции
- Публичные функции отсутствуют.

### Связи
Используется app-layer сценариями, обработчиками, сессиями и runtime-миксинами для единого пользовательского потока между ботами, GPT и storage.
"""

from __future__ import annotations



from relay.common import (
    Empty,
    Lock,
    Thread,
    sys,
    traceback,
)
from relay.config import PROCESS_TASK_TIMEOUT, logger_admin, logger_queue
from relay.queues import ProcessTask
class ProcessTaskMixin:
        """
        Добавляет `App` операции processtask без привязки к transport-layer.
        Mixin рассчитан на включение в `App` и работает с его registry, storage, пользователями, ботами и очередями.

        ### Методы
        - `get_event_access_level`: Возвращает event access level из текущего состояния `ProcessTaskMixin`.
        - `check_admin_event`: Проверяет admin event перед использованием.
        - `enqueue_process_task`: Координирует runtime-состояние приложения между очередями, пользователями и transport-layer.
        - `start_process_task_workers`: Запускает process task workers в runtime-потоке приложения.
        - `stop_process_task_workers`: Останавливает process task workers и меняет флаг активности объекта.
        - `get_process_task_key`: Возвращает process task key из текущего состояния `ProcessTaskMixin`.
        - `get_process_task_lock`: Возвращает process task lock из текущего состояния `ProcessTaskMixin`.
        - `get_chatgpt_key`: Возвращает chatgpt key из текущего состояния `ProcessTaskMixin`.
        - `mark_process_task_active`: Координирует runtime-состояние приложения между очередями, пользователями и transport-layer.
        - `has_pending_chatgpt_task`: Проверяет наличие pending chatgpt task.

        ### Жизненный цикл
        Создаётся app-layer кодом, участвует в обработке пользовательского события и сохраняет изменённое состояние через существующие runtime/storage механизмы.

        ### Пример использования
        ```py
        app: ProcessTaskMixin
        ```
        """
        def get_event_access_level(self, bot_key: BOT_KEY, chat_id: int) -> int:
            """
            Возвращает уровень доступа, требуемый для события.

            ### Аргументы:
            :param bot_key: ключ транспорта
            :param chat_id: идентификатор чата

            :return: event access level

            ### Пример использования:
            ```py
            processTaskMixin.get_event_access_level(bot_key = bot_key, chat_id = chat_id)
            ```
            """
            user_id: int | None = self.find_user(bot_key, chat_id)

            if user_id is None:

                return 0

            admin_data: dict[str, JSONABLE] = self.admins_storage.get(user_id, {})

            return int(admin_data.get("access_level") or 0)

        def check_admin_event(self, bot: BOT, event: Bot.Event) -> bool:
            """
            Проверяет значение `admin event` перед сохранением или использованием.

            ### Аргументы:
            :param bot: transport-адаптер
            :param event: transport-событие для обработки

            :return: `True`, если значение `admin event` перед сохранением или использованием; иначе `False`

            ### Пример использования:
            ```py
            processTaskMixin.check_admin_event(bot = bot, event = event)
            ```
            """
            bot_key: BOT_KEY = bot.get_bot_key()

            chat_id: int = int(event.chat_id)

            return self.get_event_access_level(bot_key, chat_id) > 0

        def enqueue_process_task(self, bot: BOT, event: Bot.Event) -> ProcessTask:
            """
            Координирует runtime-состояние приложения между очередями, пользователями и transport-layer.

            ### Аргументы:
            :param bot: transport-адаптер
            :param event: transport-событие для обработки

            :return: значение, которое runtime использует для продолжения обработки события

            ### Пример использования:
            ```py
            processTaskMixin.enqueue_process_task(bot = bot, event = event)
            ```
            """
            with self.process_task_lock:

                self.process_task_id += 1

                task_id: int = int(self.process_task_id)

            admin_priority: bool = self.check_admin_event(bot, event)

            task: ProcessTask = ProcessTask(task_id, bot, event, admin_priority)

            self.process_task_queue.put(task.get_queue_item())

            self.start_process_task_workers()

            return task

        def start_process_task_workers(self):
            """
            Запускает process task workers в runtime-потоке приложения.

            ### Примеры вызова:
            ```py
            app.start_process_task_workers()
            ```
            """
            with self.process_task_lock:

                max_process_tasks: int = max(1, int(self.max_process_tasks))

                alive_workers: list[Thread] = [

                    thread for thread in self.process_task_workers

                    if thread.is_alive()

                ]

                self.process_task_workers = alive_workers

                self.process_task_workers_working = True

                while len(self.process_task_workers) < max_process_tasks:

                    worker_index: int = len(self.process_task_workers) + 1

                    thread: Thread = Thread(target = self.process_task_worker, name = f"process_queue_{worker_index}", daemon = True)

                    self.process_task_workers.append(thread)

                    thread.start()

                    logger_queue.info("Запущен обработчик очереди событий: index=%s", worker_index)

        def stop_process_task_workers(self):
            """
            Останавливает process task workers и меняет флаг активности объекта.

            ### Примеры вызова:
            ```py
            app.stop_process_task_workers()
            ```
            """
            self.process_task_workers_working = False

            logger_queue.info("Остановка обработчиков очереди событий")

        def get_process_task_key(self, bot: BOT, event: Bot.Event) -> tuple[str, int]:
            """
            Возвращает ключ фоновой задачи обработки.

            ### Аргументы:
            :param bot: transport-адаптер
            :param event: transport-событие для обработки

            :return: process task key

            ### Пример использования:
            ```py
            processTaskMixin.get_process_task_key(bot = bot, event = event)
            ```
            """
            bot_key: BOT_KEY = bot.get_bot_key()

            chat_id: int = int(event.chat_id)

            user_id: int | None = self.find_user(bot_key, chat_id)

            if user_id is None:

                return bot_key, chat_id

            else:

                return "user", int(user_id)

        def get_process_task_lock(self, task_key: tuple[str, int]) -> Lock:
            """
            Возвращает lock фоновой задачи обработки.

            ### Аргументы:
            :param task_key: ключ runtime-задачи в очереди

            :return: process task lock

            ### Пример использования:
            ```py
            processTaskMixin.get_process_task_lock(task_key = task_key)
            ```
            """
            with self.process_task_lock:

                if task_key not in self.process_task_key_locks:

                    self.process_task_key_locks[task_key] = Lock()

                return self.process_task_key_locks[task_key]

        def get_chatgpt_key(self, bot_key: BOT_KEY, chat_id: int) -> tuple[str, int]:
            """
            Возвращает ключ GPT-задачи пользователя.

            ### Аргументы:
            :param bot_key: ключ транспорта
            :param chat_id: идентификатор чата

            :return: ключ GPT-задачи пользователя

            ### Пример использования:
            ```py
            processTaskMixin.get_chatgpt_key(bot_key = bot_key, chat_id = chat_id)
            ```
            """
            return str(bot_key), int(chat_id)

        def mark_process_task_active(self, bot: BOT, event: Bot.Event, active: bool):
            """
            Координирует runtime-состояние приложения между очередями, пользователями и transport-layer.

            ### Аргументы:
            :param bot: transport-адаптер
            :param event: transport-событие для обработки
            :param active: новое состояние активности задачи

            ### Пример использования:
            ```py
            processTaskMixin.mark_process_task_active(bot = bot, event = event, active = active)
            ```
            """
            bot_key: BOT_KEY = bot.get_bot_key()

            chat_id: int = int(event.chat_id)

            key: tuple[str, int] = self.get_chatgpt_key(bot_key, chat_id)

            with self.process_task_lock:

                current: int = int(self.process_task_active_keys.get(key, 0))

                if active:

                    self.process_task_active_keys[key] = current + 1

                elif current <= 1:

                    self.process_task_active_keys.pop(key, None)

                else:

                    self.process_task_active_keys[key] = current - 1

        def has_pending_chatgpt_task(self, bot_key: BOT_KEY, chat_id: int) -> bool:
            """
            Проверяет наличие pending chatgpt task.

            ### Аргументы:
            :param bot_key: ключ транспорта
            :param chat_id: идентификатор чата

            :return: `True`, если наличие pending chatgpt task; иначе `False`

            ### Пример использования:
            ```py
            processTaskMixin.has_pending_chatgpt_task(bot_key = bot_key, chat_id = chat_id)
            ```
            """
            key: tuple[str, int] = self.get_chatgpt_key(bot_key, chat_id)

            with self.process_task_lock:

                if self.process_task_active_keys.get(key, 0) > 0:

                    return True

            with self.process_task_queue.mutex:

                queue_items: list[tuple[int, int, ProcessTask]] = list(self.process_task_queue.queue)

            for queue_item in queue_items:

                task: ProcessTask = queue_item[2]

                task_bot_key: BOT_KEY = task.bot.get_bot_key()

                task_chat_id: int = int(task.event.chat_id)

                if self.get_chatgpt_key(task_bot_key, task_chat_id) == key:

                    return True

            return False

        def create_chatgpt_version(self, bot_key: BOT_KEY, chat_id: int) -> int:
            """
            Создаёт chatgpt version и связывает результат с текущим app-layer состоянием.

            ### Аргументы:
            :param bot_key: ключ транспорта, например `vkbot` или `telebot`
            :param chat_id: идентификатор чата в конкретной платформе

            :return: созданный объект для chatgpt version

            ### Пример использования:
            ```py
            app.create_chatgpt_version(bot_key = bot_key, chat_id = chat_id)
            ```
            """
            key: tuple[str, int] = self.get_chatgpt_key(bot_key, chat_id)

            with self.chatgpt_state_lock:

                version: int = int(self.chatgpt_versions.get(key, 0)) + 1

                self.chatgpt_versions[key] = version

                self.chatgpt_request_statuses.setdefault(key, {})[version] = "waiting"

                return version

        def check_chatgpt_version(self, bot_key: BOT_KEY, chat_id: int, version: int) -> bool:
            """
            Проверяет значение `chatgpt version` перед сохранением или использованием.

            ### Аргументы:
            :param bot_key: ключ транспорта
            :param chat_id: идентификатор чата
            :param version: версия GPT-запроса для защиты от устаревших ответов

            :return: `True`, если значение `chatgpt version` перед сохранением или использованием; иначе `False`

            ### Пример использования:
            ```py
            processTaskMixin.check_chatgpt_version(bot_key = bot_key, chat_id = chat_id, version = version)
            ```
            """
            key: tuple[str, int] = self.get_chatgpt_key(bot_key, chat_id)

            with self.chatgpt_state_lock:

                return int(self.chatgpt_versions.get(key, 0)) == int(version)

        def set_chatgpt_request_status(self, bot_key: BOT_KEY, chat_id: int, version: int, status: str):
            """
            Проверяет и сохраняет значение `chatgpt request status`.

            ### Аргументы:
            :param bot_key: ключ транспорта
            :param chat_id: идентификатор чата
            :param version: версия GPT-запроса для защиты от устаревших ответов
            :param status: статус runtime-задачи

            ### Пример использования:
            ```py
            processTaskMixin.set_chatgpt_request_status(bot_key = bot_key, chat_id = chat_id, version = version, status = status)
            ```
            """
            key: tuple[str, int] = self.get_chatgpt_key(bot_key, chat_id)

            with self.chatgpt_state_lock:

                self.chatgpt_request_statuses.setdefault(key, {})[int(version)] = str(status)

        def cleanup_chatgpt_request_status(self, bot_key: BOT_KEY, chat_id: int, version: int):
            """
            Координирует runtime-состояние приложения между очередями, пользователями и transport-layer.

            ### Аргументы:
            :param bot_key: ключ транспорта
            :param chat_id: идентификатор чата
            :param version: версия GPT-запроса для защиты от устаревших ответов

            ### Пример использования:
            ```py
            processTaskMixin.cleanup_chatgpt_request_status(bot_key = bot_key, chat_id = chat_id, version = version)
            ```
            """
            key: tuple[str, int] = self.get_chatgpt_key(bot_key, chat_id)

            with self.chatgpt_state_lock:

                statuses: dict[int, str] = self.chatgpt_request_statuses.get(key, {})

                statuses.pop(int(version), None)

                if not statuses:

                    self.chatgpt_request_statuses.pop(key, None)

        def process_task_worker(self):
            """
            Обрабатывает task worker в текущем пользовательском или transport-layer потоке.

            ### Примеры вызова:
            ```py
            app.process_task_worker()
            ```
            """
            while self.process_task_workers_working and self.check_working():

                try:

                    queue_item: tuple[int, int, ProcessTask] = self.process_task_queue.get(timeout = PROCESS_TASK_TIMEOUT)

                except Empty:

                    continue

                task: ProcessTask = queue_item[2]

                try:

                    self.process_task(task)

                finally:

                    self.process_task_queue.task_done()

        def process_task(self, task: ProcessTask):
            """
            Обрабатывает task в текущем runtime-контексте.

            ### Аргументы:
            :param task: runtime-задача

            ### Пример использования:
            ```py
            processTaskMixin.process_task(task = task)
            ```
            """
            bot: BOT = task.bot

            event: Bot.Event = task.event

            task_key: tuple[str, int] = self.get_process_task_key(bot, event)

            task_lock: Lock = self.get_process_task_lock(task_key)

            self.mark_process_task_active(bot, event, True)

            try:

                with task_lock:

                    self.process_task_locked(bot, event)

            finally:

                self.mark_process_task_active(bot, event, False)

        def process_task_locked(self, bot: BOT, event: Bot.Event):
            """
            Обрабатывает task locked в текущем runtime-контексте.

            ### Аргументы:
            :param bot: transport-адаптер
            :param event: transport-событие для обработки

            ### Пример использования:
            ```py
            processTaskMixin.process_task_locked(bot = bot, event = event)
            ```
            """
            try:

                self._process(bot, event)

            except Exception as err:

                exc_type, exc_value, exc_traceback = sys.exc_info()

                formatted_traceback: list[str] = traceback.format_exception(exc_type, exc_value, exc_traceback)

                bot_key: BOT_KEY | None = None

                chat_id: int | None = None

                content: str | None = None

                try:

                    bot_key = bot.get_bot_key()

                except Exception as err:

                    bot_key = err

                try:

                    chat_id = event.chat_id

                except Exception as err:

                    chat_id = err

                try:

                    content = event.get_text()

                except Exception as err:

                    content = err

                logger_admin.error(

                    "\n".join([

                        f"Возникла ошибка при вызове process: {bot_key=} {chat_id=} {content=} {event=}",

                        *formatted_traceback,

                        f"{type(err)} {err=}",

                    ])

                )
