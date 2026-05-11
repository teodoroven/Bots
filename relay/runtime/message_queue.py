"""
Описывает runtime-операции очереди wrapper-сообщений.
Модуль относится к архитектурной зоне: прикладной слой `relay`, который связывает пользователей, сессии, доменную модель, GPT, уведомления и runtime-логику приложения.

### Публичные классы
- `MessageQueueMixin`: runtime-логика очереди сообщений.

### Публичные функции
- Публичные функции отсутствуют.

### Связи
Используется app-layer сценариями, обработчиками, сессиями и runtime-миксинами для единого пользовательского потока между ботами, GPT и storage.
"""

from __future__ import annotations



from relay.common import BotTypes, Thread, sleep
from relay.config import MESSAGE_QUEUE_RETRY_INTERVAL, MESSAGE_QUEUE_SENT_LIMIT, logger_queue
from relay.queues import QueuedMessage
class MessageQueueMixin:
        """
        Добавляет `App` операции messagequeue без привязки к transport-layer.
        Mixin рассчитан на включение в `App` и работает с его registry, storage, пользователями, ботами и очередями.

        ### Методы
        - `load_message_queue`: Загружает message queue из storage.
        - `save_message_queue`: Сохраняет message queue в storage или во внутреннем состоянии объекта.
        - `enqueue_message`: Координирует runtime-состояние приложения между очередями, пользователями и transport-layer.
        - `send_message_now`: Отправляет message now через доступный transport-layer адаптер.
        - `catch_message_send`: Координирует runtime-состояние приложения между очередями, пользователями и transport-layer.
        - `process_queued_message`: Обрабатывает queued message в текущем пользовательском или transport-layer потоке.
        - `flush_message_queue`: Координирует runtime-состояние приложения между очередями, пользователями и transport-layer.
        - `message_queue_cycle`: Координирует runtime-состояние приложения между очередями, пользователями и transport-layer.
        - `start_message_queue`: Запускает message queue в runtime-потоке приложения.
        - `stop_message_queue`: Останавливает message queue и меняет флаг активности объекта.

        ### Жизненный цикл
        Создаётся app-layer кодом, участвует в обработке пользовательского события и сохраняет изменённое состояние через существующие runtime/storage механизмы.

        ### Пример использования
        ```py
        app: MessageQueueMixin
        ```
        """
        def load_message_queue(self):
            """
            Загружает message queue из storage.

            ### Примеры вызова:
            ```py
            app.load_message_queue()
            ```
            """
            data: BotTypes.MESSAGE_QUEUE_TYPE = self.storage.load_document("message_queue") or {}

            self.message_queue_id = int(data.get("last_id", 0) or 0)

            self.message_queue.clear()

            self.message_queue_unloaded_items.clear()

            items: list[BotTypes.QUEUE_ITEM_TYPE | dict[str, JSONABLE]] = list(data.get("items", []))

            for item_data in items:

                try:

                    item: QueuedMessage = QueuedMessage.loads(item_data, self.get_bot)

                except Exception as err:

                    logger_queue.exception("Не удалось загрузить элемент очереди сообщений: %s", err)

                    self.message_queue_unloaded_items.append(item_data)

                    continue

                if item.check_sent():

                    item.mark(QueuedMessage.STATUS_SENT)

                elif item.status == QueuedMessage.STATUS_SENDING:

                    item.mark(QueuedMessage.STATUS_PENDING)

                self.message_queue[item.id] = item

                self.message_queue_id = max(self.message_queue_id, item.id)

            self.save_message_queue()

        def save_message_queue(self):
            """
            Сохраняет message queue в storage или во внутреннем состоянии объекта.

            ### Примеры вызова:
            ```py
            app.save_message_queue()
            ```
            """
            items: list[QueuedMessage] = sorted(self.message_queue.values(), key = lambda item: item.id)

            sent_items: list[QueuedMessage] = [

                item for item in items

                if item.status == QueuedMessage.STATUS_SENT

            ]

            if len(sent_items) > MESSAGE_QUEUE_SENT_LIMIT:

                keep_sent_ids: set[int] = {item.id for item in sent_items[-MESSAGE_QUEUE_SENT_LIMIT:]}

                self.message_queue = {

                    item.id: item for item in items

                    if item.status != QueuedMessage.STATUS_SENT or item.id in keep_sent_ids

                }

                items = sorted(self.message_queue.values(), key = lambda item: item.id)

            data: BotTypes.MESSAGE_QUEUE_TYPE = {

                "last_id": int(self.message_queue_id),

                "items": [item.dumps() for item in items] + self.message_queue_unloaded_items,

            }

            self.storage.save_document("message_queue", data)

            self.storage.ensure_counters_at_least(message_queue = int(self.message_queue_id))

        def enqueue_message(

                self,

                message: Message,

                bot: BOT,

                chat_id: int,

                compression: bool = True,

                parse_mode: str = "",

                last_error: str = "",

                ) -> QueuedMessage:
            """
            Координирует runtime-состояние приложения между очередями, пользователями и transport-layer.

            ### Аргументы:
            :param message: сообщение проекта или сообщение конкретного транспорта
            :param bot: transport-адаптер
            :param chat_id: идентификатор чата
            :param compression: признак сжатия вложения
            :param parse_mode: режим разметки сообщения
            :param last_error: last error

            :return: значение, которое runtime использует для продолжения обработки события

            ### Пример использования:
            ```py
            messageQueueMixin.enqueue_message(message = message, bot = bot, chat_id = chat_id, compression = compression, parse_mode = parse_mode, last_error = last_error)
            ```
            """
            with self.message_queue_lock:

                self.message_queue_id += 1

                queue_id: int = int(self.message_queue_id)

                item: QueuedMessage = QueuedMessage(

                    queue_id,

                    message,

                    bot.get_bot_key(),

                    chat_id,

                    compression = compression,

                    parse_mode = parse_mode,

                    status = QueuedMessage.STATUS_PENDING,

                    attempts = 0,

                    last_error = last_error,

                )

                self.message_queue[queue_id] = item

                self.save_message_queue()

            logger_queue.warning("Сообщение добавлено в очередь отправки: id=%s bot=%s chat_id=%s", item.id, item.bot_key, item.chat_id)

            self.start_message_queue()

            return item

        def send_message_now(

                self,

                message: Message,

                bot: BOT,

                chat_id: int,

                compression: bool = True,

                parse_mode: str = "",

                ) -> Message:
            """
            Отправляет или переотправляет подготовленное сообщение через доступный transport/API.

            ### Аргументы:
            :param message: сообщение проекта или сообщение конкретного транспорта
            :param bot: transport-адаптер
            :param chat_id: идентификатор чата
            :param compression: признак сжатия вложения
            :param parse_mode: режим разметки сообщения

            :return: значение, которое runtime использует для продолжения обработки события

            :raises ConnectionError: если нижележащий слой сообщает об ошибке операции

            ### Пример использования:
            ```py
            messageQueueMixin.send_message_now(message = message, bot = bot, chat_id = chat_id, compression = compression, parse_mode = parse_mode)
            ```
            """
            bot_key: BOT_KEY = bot.get_bot_key()

            message.send(bot, chat_id, compression = compression, parse_mode = parse_mode)

            if not message.check_sent(bot_key, chat_id):

                raise ConnectionError(f"Сообщение не было подтверждено API: {bot_key=} {chat_id=}")

            return message

        def catch_message_send(

                self,

                message: Message,

                bot: BOT,

                chat_id: int,

                compression: bool = True,

                parse_mode: str = "",

                queue_on_error: bool = True,

                ) -> bool:
            """
            Координирует runtime-состояние приложения между очередями, пользователями и transport-layer.

            ### Аргументы:
            :param message: сообщение проекта или сообщение конкретного транспорта
            :param bot: transport-адаптер
            :param chat_id: идентификатор чата
            :param compression: признак сжатия вложения
            :param parse_mode: режим разметки сообщения
            :param queue_on_error: queue on error

            :return: значение, которое runtime использует для продолжения обработки события

            ### Пример использования:
            ```py
            messageQueueMixin.catch_message_send(message = message, bot = bot, chat_id = chat_id, compression = compression, parse_mode = parse_mode, queue_on_error = queue_on_error)
            ```
            """
            try:

                self.catch_bot(

                    lambda: self.send_message_now(message, bot, chat_id, compression = compression, parse_mode = parse_mode),

                    description = f"send_message {bot.get_bot_key()} {chat_id}",

                    raise_error = True,

                )

            except Exception as err:

                logger_queue.warning("Не удалось отправить сообщение сразу: %s", err, exc_info = True)

                if queue_on_error and self.check_retryable_bot_error(err):

                    self.enqueue_message(message, bot, chat_id, compression = compression, parse_mode = parse_mode, last_error = repr(err))

                return False

            return True

        def process_queued_message(self, item: QueuedMessage) -> bool:
            """
            Обрабатывает queued message в текущем runtime-контексте.

            ### Аргументы:
            :param item: элемент очереди или коллекции

            :return: значение, которое runtime использует для продолжения обработки события

            ### Пример использования:
            ```py
            messageQueueMixin.process_queued_message(item = item)
            ```
            """
            bot: BOT = self.get_bot(item.bot_key)

            item.mark(QueuedMessage.STATUS_SENDING)

            item.attempts += 1

            self.save_message_queue()

            try:

                self.catch_bot(

                    lambda: self.send_message_now(item.message, bot, item.chat_id, compression = item.compression, parse_mode = item.parse_mode),

                    description = f"queued_message {item.id} {item.bot_key} {item.chat_id}",

                    raise_error = True,

                )

            except Exception as err:

                item.mark(QueuedMessage.STATUS_FAILED, repr(err))

                self.save_message_queue()

                logger_queue.warning("Очередь не смогла отправить сообщение %s: %s", item.id, err, exc_info = True)

                return False

            item.mark(QueuedMessage.STATUS_SENT)

            self.save_message_queue()

            logger_queue.info("Очередь отправила сообщение %s", item.id)

            return True

        def flush_message_queue(self) -> bool:
            """
            Координирует runtime-состояние приложения между очередями, пользователями и transport-layer.

            :return: значение, которое runtime использует для продолжения обработки события

            ### Пример использования:
            ```py
            messageQueueMixin.flush_message_queue()
            ```
            """
            processed: bool = False

            items: list[QueuedMessage]

            with self.message_queue_lock:

                items = [

                    item for item in sorted(self.message_queue.values(), key = lambda item: item.id)

                    if item.check_pending() and not item.check_sent()

                ]

            for item in items:

                if not self.check_working():

                    break

                processed = self.process_queued_message(item) or processed

            return processed

        def message_queue_cycle(self):
            """
            Координирует runtime-состояние приложения между очередями, пользователями и transport-layer.

            ### Пример использования:
            ```py
            messageQueueMixin.message_queue_cycle()
            ```
            """
            while self.message_queue_working and self.check_working():

                self.flush_message_queue()

                sleep(MESSAGE_QUEUE_RETRY_INTERVAL)

        def start_message_queue(self):
            """
            Запускает message queue в runtime-потоке приложения.

            ### Примеры вызова:
            ```py
            app.start_message_queue()
            ```
            """
            if self.message_queue_thread is not None and self.message_queue_thread.is_alive():

                return

            self.message_queue_working = True

            self.message_queue_thread = Thread(target = self.message_queue_cycle, name = "message_queue", daemon = True)

            self.message_queue_thread.start()

            logger_queue.info("Запущена очередь отправки сообщений")

        def stop_message_queue(self):
            """
            Останавливает message queue и меняет флаг активности объекта.

            ### Примеры вызова:
            ```py
            app.stop_message_queue()
            ```
            """
            self.message_queue_working = False

            logger_queue.info("Остановка очереди отправки сообщений")
