"""
Описывает запуск, остановку и health-check runtime приложения.
Модуль относится к архитектурной зоне: прикладной слой `relay`, который связывает пользователей, сессии, доменную модель, GPT, уведомления и runtime-логику приложения.

### Публичные классы
- `LifecycleMixin`: runtime-логика запуска и остановки приложения.

### Публичные функции
- Публичные функции отсутствуют.

### Связи
Используется app-layer сценариями, обработчиками, сессиями и runtime-миксинами для единого пользовательского потока между ботами, GPT и storage.
"""

from __future__ import annotations



from relay.common import (
    BotTypes,
    Lock,
    Model,
    PriorityQueue,
    SqlAlchemyStorage,
    Storage,
    Thread,
    json,
    requests,
    sleep,
)
from relay.config import (
    MAX_MESSAGES,
    MAX_PROCESS_TASKS,
    MESSAGE_QUEUE_RETRIES,
    MESSAGE_QUEUE_RETRY_INTERVAL,
    SKIP_POLLING,
    get_phrase,
    logger,
)
from relay.conversations import Conversation
from relay.gpt import GPT
from relay.handlers import (
    ChatGPTHandler,
    CommonCommands,
    GeneralCommands,
    NoHandlers,
    SessionsHandler,
)
from relay.notifications import AdminEvent
from relay.queues import ProcessTask, QueuedMessage
from relay.users import Admin, Settings, User
from relay.utils import catch_parsefiles, is_int
class LifecycleMixin:
        """
        Добавляет `App` операции lifecycle без привязки к transport-layer.
        Mixin рассчитан на включение в `App` и работает с его registry, storage, пользователями, ботами и очередями.

        ### Поля
        - `working`: флаг, разрешающий обработку новых событий транспортом.
        - `bot_enabled`: флаги включения transport-ботов по ключам.
        - `threads`: активные фоновые потоки runtime.
        - `settings`: хранит настройки пользователя или GPT для операций этого объекта.
        - `storage`: storage API, через который диалог сохраняет состояние.
        - `admins`: хранит настройки администраторов для операций этого объекта.
        - `users`: хранит пользователей для операций этого объекта.
        - `users_ids`: идентификатор объекта или связанной сущности, по которому runtime восстанавливает связь между слоями.
        - `chats`: chat ids, для которых runtime уже загрузил пользователей.
        - `events`: очередь входящих событий по chat_id до объединения и обработки.

        ### Методы
        - `__init__`: Инициализирует `__init__` и подготавливает runtime-состояние приложения.
        - `check_working`: Проверяет флаг работы транспорта перед использованием.
        - `is_bot_enabled`: Проверяет, включён ли transport-бот в runtime-настройках.
        - `set_bot_enabled`: Проверяет и сохраняет значение `bot enabled` в `LifecycleMixin`.
        - `stop`: Останавливает transport-адаптер для новых событий и сбрасывает флаг `working`.
        - `start`: Запускает сценарий обработки и подготавливает первое сообщение или задачу.
        - `check_retryable_bot_error`: Проверяет retryable bot error перед использованием.
        - `catch_bot`: Координирует runtime-состояние приложения между очередями, пользователями и transport-layer.
        - `dumps`: Возвращает JSON-совместимый снимок объекта для storage или callback payload.
        - `load_data`: Загружает data из storage.

        ### Жизненный цикл
        Создаётся app-layer кодом, участвует в обработке пользовательского события и сохраняет изменённое состояние через существующие runtime/storage механизмы.

        ### Пример использования
        ```py
        app: LifecycleMixin
        ```
        """
        def __init__(self, enter_menu: bool = True):
            """
            Инициализирует runtime-mixin `LifecycleMixin` и подготавливает состояние, которое использует жизненный цикл приложения.

            ### Аргументы:
            :param enter_menu: enter menu

            ### Пример использования:
            ```py
            lifecycleMixin = LifecycleMixin(enter_menu = enter_menu)
            ```
            """
            self.working: bool = True

            self.bot_enabled: bool = True

            self.threads: list[Thread] = []

            self.settings: Settings = Settings()

            self.storage: Storage = SqlAlchemyStorage()

            self.storage.ensure_defaults()

            # list

            self.admins: dict[int, Admin] = {}

            self.users: dict[int, User] = {}

            self.users_ids: dict[int, dict[BOT_KEY, set[int]]] = {}  # user_id(int): { bot_key(str): chat_id(int)... }

            self.chats: dict[int, Conversation] = {}

            self.events: list[AdminEvent] = []

            self.users_lock: Lock = Lock()

            self.event_lock: Lock = Lock()

            # id

            self.event_id: int = 0

            self.user_id: int = 0

            self.message_id: int = 0

            self.session_id: int = 0

            self.conv_id: int = 0

            self.client_id: int = 0

            self.element_id: int = 0

            self.persist_ids: bool = False

            self.admins_storage: BotTypes.ADMIN_STORAGE_TYPE = {}

            self.message_queue: dict[int, QueuedMessage] = {}

            self.message_queue_id: int = 0

            self.message_queue_lock: Lock = Lock()

            self.message_queue_thread: Thread | None = None

            self.message_queue_working: bool = False

            self.message_queue_unloaded_items: list[BotTypes.QUEUE_ITEM_TYPE | dict[str, JSONABLE]] = []

            self.process_task_queue: PriorityQueue[tuple[int, int, ProcessTask]] = PriorityQueue()

            self.process_task_id: int = 0

            self.process_task_lock: Lock = Lock()

            self.process_task_workers: list[Thread] = []

            self.process_task_workers_working: bool = False

            self.process_task_key_locks: dict[tuple[str, int], Lock] = {}

            self.process_task_active_keys: dict[tuple[str, int], int] = {}

            self.max_process_tasks: int = MAX_PROCESS_TASKS

            self.chatgpt_state_lock: Lock = Lock()

            self.chatgpt_versions: dict[tuple[str, int], int] = {}

            self.chatgpt_request_statuses: dict[tuple[str, int], dict[int, str]] = {}

            # handlers

            general_handler: GeneralCommands = GeneralCommands()

            sessions_handler: SessionsHandler = SessionsHandler()

            common_handler: CommonCommands = CommonCommands()

            chatgpt_handler: ChatGPTHandler = ChatGPTHandler()

            calladmin_handler: NoHandlers = NoHandlers()

            # Порядок обработчиков

            self.process_handlers: tuple = (general_handler, sessions_handler, common_handler, chatgpt_handler, calladmin_handler)

            # bots

            self.bots: list[BOT] = []

            self.active_bots: list[BOT_KEY] = []

            # gpt

            self.gpt: GPT | None = None

            self.apikey: str = ""

            self.models: dict[str, dict[str, Model]] = {}

            self.model: Model | None = None

            self.contexts: dict[int, SystemContext] = {}

            self.system_context: SystemContext | None = None

            self.questions: dict[int, Question] = {}

            self.clients: dict[int, Client] = {}

            self.limits: dict[int, Limit] = {}

            self.shared_client: Client

            self.user_client: Client

            # root

            self.elements: dict[int, Element] = {}

            self.folders: dict[int, NamedFolder] = {}

            self.filials: dict[int, Filial] = {}

            self.dates: dict[int, Date | MonthDate] = {}

            self.root: Root[Folder] = Root()

            self.filials_folder: FilialsFolder[Filial] = FilialsFolder(self.create_id())

            self.theory_online: Filial = Filial(self.create_id(), "Теория онлайн")

            self.dates_folder: DatesFolder[MonthDate] = DatesFolder(self.create_id())

            self.contexts_folder: ContextsFolder[SystemContext] = ContextsFolder(self.create_id())

            self.questions_folder: QuestionsFolder[Question] = QuestionsFolder(self.create_id())

            self.limits_folder: LimitsFolder[Limit] = LimitsFolder(self.create_id())

            self.folders: dict[int, Folder] = {

                self.root.id: self.root,

                self.filials_folder.id: self.filials_folder,

                self.dates_folder.id: self.dates_folder,

                self.contexts_folder.id: self.contexts_folder,

                self.questions_folder.id: self.questions_folder,

                self.limits_folder.id: self.limits_folder

            }

            self.load_root()

            self.storage.ensure_counters_at_least(element = int(self.element_id))

            self.persist_ids = True

            # lock

            self.conv_lock: Lock = Lock()

            self.load_data()

            self.load_bots(enter_menu = enter_menu)

            self.load_message_queue()

            self.load_admins()

            self.load_gpt()

            self.user_id = self.load_ids()

            self.conv_id = self.load_conv()

        def __repr__(self) -> str:

            bots = len(self.bots)

            active_bots = self.active_bots

            try:

                users = list(self.users.keys())

            except Exception as err:

                users = err

            try:

                data = self.dumps()

            except Exception as err:

                data = err

            return f"{bots=} {active_bots=} users({len(users)})={repr(users)} {data=}"

        def check_working(self) -> bool:
            """
            Возвращает, разрешена ли обработка событий этим transport-адаптером.

            :return: `True`, если возвращает, разрешена ли обработка событий этим transport-адаптером; иначе `False`

            ### Пример использования:
            ```py
            lifecycleMixin.check_working()
            ```
            """
            return bool(self.working)

        def is_bot_enabled(self) -> bool:
            """
            Проверяет, включён ли transport-бот в runtime-настройках.

            :return: `True`, если включён ли transport-бот в runtime-настройках; иначе `False`

            ### Пример использования:
            ```py
            lifecycleMixin.is_bot_enabled()
            ```
            """
            return bool(self.bot_enabled)

        def set_bot_enabled(self, enabled: bool) -> bool:
            """
            Проверяет и сохраняет значение `bot enabled`.

            ### Аргументы:
            :param enabled: нужное состояние включения элемента

            :return: значение, которое runtime использует для продолжения обработки события

            ### Пример использования:
            ```py
            lifecycleMixin.set_bot_enabled(enabled = enabled)
            ```
            """
            enabled = bool(enabled)

            changed: bool = self.bot_enabled != enabled

            self.bot_enabled = enabled

            if changed:

                self.save_data()

            return changed

        def stop(self):
            """
            Останавливает transport-адаптер для новых событий и сбрасывает флаг `working`.

            ### Пример использования:
            ```py
            app.stop()
            ```
            """
            logger.info("Остановка бота")

            self.working = False

            self.stop_message_queue()

            self.stop_process_task_workers()

        def start(self):
            """
            Запускает сценарий обработки и подготавливает первое сообщение или задачу.

            ### Пример использования:
            ```py
            lifecycleMixin.start()
            ```
            """
            logger.info("Запуск рабочих потоков бота")

            self.start_process_task_workers()

            self.start_message_queue()

            self.start_polling_bots()

        def check_retryable_bot_error(self, err: Exception) -> bool:
            """
            Проверяет значение `retryable bot error` перед сохранением или использованием.

            ### Аргументы:
            :param err: исключение, которое нужно проверить или обработать

            :return: `True`, если значение `retryable bot error` перед сохранением или использованием; иначе `False`

            ### Пример использования:
            ```py
            lifecycleMixin.check_retryable_bot_error(err = err)
            ```
            """
            if isinstance(err, (ConnectionError, TimeoutError, OSError)):

                return True

            if isinstance(err, requests.exceptions.RequestException):

                return True

            if isinstance(err, ApiTelegramException):

                error_code: int = int(getattr(err, "error_code", 0) or 0)

                return error_code in (429, 500, 502, 503, 504)

            if isinstance(err, ApiError):

                error_code: int = int(getattr(err, "code", 0) or 0)

                return error_code in (1, 6, 9, 10, 29)

            text: str = str(err).lower()

            markers: tuple[str, ...] = (

                "connection",

                "timeout",

                "timed out",

                "temporarily",

                "network",

                "failed to establish",

                "remote end closed",

                "max retries exceeded",

            )

            return any(marker in text for marker in markers)

        def catch_bot(

                self,

                action: Callable,

                retries: int = MESSAGE_QUEUE_RETRIES,

                interval: float = MESSAGE_QUEUE_RETRY_INTERVAL,

                description: str = "bot action",

                raise_error: bool = False,

                ) -> Any | None:
            """
            Координирует runtime-состояние приложения между очередями, пользователями и transport-layer.

            ### Аргументы:
            :param action: действие меню
            :param retries: количество повторных попыток
            :param interval: пауза между повторными попытками
            :param description: описание операции для логов
            :param raise_error: raise error

            :return: значение, которое runtime использует для продолжения обработки события

            :raises last_error: если нижележащий слой сообщает об ошибке операции

            ### Пример использования:
            ```py
            lifecycleMixin.catch_bot(action = action, retries = retries, interval = interval, description = description, raise_error = raise_error)
            ```
            """
            last_error: Exception | None = None

            attempt: int

            for attempt in range(1, int(retries) + 1):

                try:

                    return action()

                except Exception as err:

                    last_error = err

                    if not self.check_retryable_bot_error(err):

                        logger.error(

                            "Не удалось выполнить %s: %s",

                            description,

                            err.__class__.__name__,

                        )

                        if raise_error:

                            raise

                        return None

                    logger.warning(

                        "Сетевая ошибка при выполнении %s, попытка %s/%s: %s",

                        description,

                        attempt,

                        retries,

                        err.__class__.__name__,

                    )

                    if attempt < retries and self.check_working():

                        sleep(interval)

            if raise_error and last_error is not None:

                raise last_error

            return None

        def dumps(self) -> AUTOCENTER_TYPE:
            """
            Возвращает JSON-совместимый снимок объекта для storage или callback payload.

            :return: JSON-совместимый словарь для сохранения или передачи между слоями

            ### Пример использования:
            ```py
            lifecycleMixin.dumps()
            ```
            """
            return {

                "message_id": int(self.message_id),

                "session_id": int(self.session_id),

                "event_id": int(self.event_id),

                "bot_enabled": bool(self.bot_enabled),

                "admins": [int(user_id) for user_id, admin in self.admins_storage.items() if int(admin.get("access_level") or 0) > 0]

            }

        def load_data(self):
            """
            Загружает data из storage.

            ### Примеры вызова:
            ```py
            app.load_data()
            ```
            """
            data: "App.AUTOCENTER_TYPE" = self.storage.load_app_state() or {}

            logger.info("Загрузка системных данных бота")

            with catch_parsefiles(("app_state",), "load_autocenter"):

                self.message_id = get_int(data, 0, "message_id")

            with catch_parsefiles(("app_state",), "load_autocenter"):

                self.session_id = get_int(data, 0, "session_id")

            with catch_parsefiles(("app_state",), "load_autocenter"):

                self.event_id = get_int(data, 0, "event_id")

            self.user_id = get_int(data, 0, "user_id")

            self.conv_id = get_int(data, 0, "conv_id")

            self.client_id = get_int(data, 0, "client_id")

            self.element_id = max(self.element_id, get_int(data, 0, "element_id"))

            self.message_queue_id = max(self.message_queue_id, get_int(data, 0, "message_queue_id"))

            with catch_parsefiles(("app_state",), "load_autocenter"):

                self.bot_enabled = get_from(data, "bot_enabled", default = True, types = (bool,))

            # with catch_parsefiles(("app_state",), "load_removable"):

            for key, message_data in data.get("removable_messages", {}).items():

                key: tuple[BOT_KEY, BOT_KEY, int, int] = json.loads(key)

                bot_key, from_bot_key, chat_id, message_id = key

                chat_id: int = int(chat_id)

                message_id: int = int(message_id)

                bot: BOT = self.get_bot(bot_key)

                message: Bot.Message = bot.__class__.Message.loads(message_data, type(bot), bot.bot)

                self.removable_messages[(bot_key, from_bot_key, chat_id, message_id)] = message

                while len(self.removable_messages) > MAX_MESSAGES:

                    self.removable_messages.popitem(last = False)

        def save_data(self):
            """
            Сохраняет data в storage или во внутреннем состоянии объекта.

            ### Примеры вызова:
            ```py
            app.save_data()
            ```
            """
            data: dict[str, JSONABLE] = self.dumps()

            data.update({

                "user_id": int(self.user_id),

                "conv_id": int(self.conv_id),

                "client_id": int(self.client_id),

                "element_id": int(self.element_id),

                "message_queue_id": int(self.message_queue_id),

            })

            self.storage.save_app_state(data)

            logger.info("Сохранены системные данные бота")

        def save(self):
            """
            Записывает текущее JSON-представление через storage API.

            ### Пример использования:
            ```py
            lifecycleMixin.save()
            ```
            """
            logger.info("Сохранение состояния бота")

            self.save_data()

            self.save_ids()

            self.save_admins()

            self.save_gpt()

            self.save_message_queue()

        def catch_polling(self, bot: BOT, polling: Callable):
            """
            Координирует runtime-состояние приложения между очередями, пользователями и transport-layer.

            ### Аргументы:
            :param bot: transport-адаптер
            :param polling: функция polling transport-адаптера

            ### Пример использования:
            ```py
            lifecycleMixin.catch_polling(bot = bot, polling = polling)
            ```
            """


            while self.check_working() and bot.get_bot_key() in self.active_bots:

                try:

                    self.catch_bot(

                        polling,

                        retries = 1,

                        description = f"polling {bot.get_bot_key()}",

                        raise_error = True,

                    )

                except Exception as err:

                    logger.error(

                        "Polling остановился с ошибкой: %s",

                        err.__class__.__name__,

                    )

                    sleep(MESSAGE_QUEUE_RETRY_INTERVAL)

                self.flush_message_queue()

        def start_polling(self, bot: BOT):
            """
            Запускает сценарий обработки и подготавливает первое сообщение или задачу.

            ### Аргументы:
            :param bot: transport-адаптер

            ### Пример использования:
            ```py
            lifecycleMixin.start_polling(bot = bot)
            ```
            """
            def polling():

                logger.info("Запуск polling: bot_key=%s class=%s", bot.get_bot_key(), bot.__class__.__name__)

                # Пропускаем события в первые 10 секунд

                bot.polling(skip = SKIP_POLLING)

                logger.warning("Polling остановлен: bot_key=%s class=%s", bot.get_bot_key(), bot.__class__.__name__)

            def catch_polling():

                self.catch_polling(bot, polling)

            thread = Thread(target = catch_polling, name = f"{bot.__class__.__name__}.polling", daemon = True)

            thread.start()

            self.threads.append(thread)

            logger.info("Запущен поток polling: bot_key=%s thread=%s", bot.get_bot_key(), thread.name)

        def start_polling_bots(self):
            """
            Запускает polling bots в runtime-потоке приложения.

            ### Примеры вызова:
            ```py
            app.start_polling_bots()
            ```
            """
            for b in self.bots:

                if isinstance(b, Vkbot):

                    def vkbot_listener(event: Bot.Event, bot: Vkbot = b):

                        self.vkbot_listener(bot, event)

                    b.process_event__ = vkbot_listener

                    logger.info("Настроен обработчик vkbot: bot_key=%s", b.get_bot_key())

                elif isinstance(b, Telebot):

                    def telebot_listener(event: Bot.Event, bot: Telebot = b):

                        self.telebot_listener(bot, event)

                    b.process_event__ = telebot_listener

                    logger.info("Настроен обработчик telebot: bot_key=%s", b.get_bot_key())

                self.start_polling(b)

        def get_settings(self, key: Literal["call_admin", "new_appointment", "gpt", "main", "buttons"]) -> dict[str, int]:
            """
            Возвращает настройки пользователя.

            ### Аргументы:
            :param key: ключ записи или настройки

            :return: settings

            ### Пример использования:
            ```py
            lifecycleMixin.get_settings(key = key)
            ```
            """
            return getattr(self.settings, key)

        def bots_menu(self):
            """
            Координирует runtime-состояние приложения между очередями, пользователями и transport-layer.

            :return: значение, которое runtime использует для продолжения обработки события

            ### Пример использования:
            ```py
            lifecycleMixin.bots_menu()
            ```
            """
            def ask_exit(phrase_key: str = "exit_question") -> bool:

                answer: str = input(f"{get_phrase(phrase_key)}\n>>>")

                if answer:

                    return True

                else:

                    return False

            question: str = "no_bots_question" if not self.bots else "bots_question"

            if ask_exit(question):

                self.stop()

            else:

                bots_was: int = len(self.bots)

                def ask_string(phrase_key: str, check: Callable[bool], wrong_key: str = "incorrect") -> str | None:

                    result: str = ""

                    while self.check_working() and not result:

                        result = input(f"{get_phrase(phrase_key)}\n>>>")

                        if not result:

                            if ask_exit():

                                return None

                            else:

                                continue

                        if not check(result):

                            logger.info("Некорректный ввод в меню добавления бота")

                            result = ""

                    return result

                name: str | None = ask_string("botname_question", check = lambda name: Bot.check_name(name))

                if not name:

                    return

                group_id: str | None = ask_string("groupid_question", check = lambda group_id: is_int(group_id) and Bot.check_group_id(int(group_id)))

                if not group_id:

                    return

                def get_bot_key(token: str) -> bool:

                    if Vkbot.check_token(token):

                        return Vkbot.BOT_KEY

                    elif Telebot.check_token(token):

                        return Telebot.BOT_KEY

                    else:

                        return False

                def check_bot(token: str) -> bool:

                    if Vkbot.check_token(token):

                        return True

                    elif Telebot.check_token(token):

                        return True

                    else:

                        return False

                token: str | None = ask_string("token_question", check = lambda token: check_bot(token))

                if not token:

                    return

                if name and group_id and token:

                    self.create_bot(get_bot_key(token), token, name, int(group_id))

                    if len(self.bots) > bots_was:

                        logger.info("Бот добавлен через интерактивное меню")

                    else:

                        logger.warning("Бот не был добавлен через интерактивное меню")

                else:

                    logger.warning("Бот не был добавлен через интерактивное меню")

        def admins_menu(self):
            """
            Выполняет консольное добавление первого администратора.

            ### Аргументы:

            ### Возвращаемое значение:

            ### Исключения:

            :raises ValueError: если введённый `chat_id` не прошёл проверку выбранного бота

            ### Примеры:

                >>> app.admins_menu()
            """

            answer: str = input(

                "Не добавлен ни один администратор. Вы хотите добавить администратора?\n"

                "Просто нажмите ENTER, чтобы добавить администратора.\n"

                "Введите что угодно и нажмите ENTER, чтобы выйти.\n"

                ">>>"

            )

            if answer:

                self.stop()

                return

            available_bot_keys: list[BOT_KEY] = [bot.get_bot_key() for bot in self.bots]

            if not available_bot_keys:

                logger.warning("Не удалось добавить администратора: нет загруженных ботов")

                self.stop()

                return

            bot_key: BOT_KEY | None = None

            if len(available_bot_keys) == 1:

                bot_key = available_bot_keys[0]

            else:

                while self.check_working() and bot_key is None:

                    bot_key_answer: str = input(f"Введите ключ бота ({', '.join(available_bot_keys)})\n>>>").strip()

                    if bot_key_answer in available_bot_keys:

                        bot_key = bot_key_answer

                    else:

                        logger.info("Некорректный ключ бота в меню администратора")

            if bot_key is None:

                return

            chat_id: int | None = None

            bot: BOT = self.get_bot(bot_key)

            while self.check_working() and chat_id is None:

                chat_id_answer: str = input("Введите chat_id администратора\n>>>").strip()

                if is_int(chat_id_answer):

                    current_chat_id: int = int(chat_id_answer)

                    if current_chat_id > 0 and bot.check_chat_id(current_chat_id):

                        chat_id = current_chat_id

                    else:

                        logger.info("Некорректный chat_id администратора")

                else:

                    logger.info("Некорректный chat_id администратора")

            if chat_id is None:

                return

            try:

                admin: User = self.create_first_admin(bot_key, chat_id)

            except ValueError:

                logger.warning("Не удалось создать первого администратора: некорректный chat_id")

                return

            logger.info("Администратор добавлен через интерактивное меню: user_id=%s", admin.id)
