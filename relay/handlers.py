"""
Описывает контекст и обработчики команд, сессий и GPT-запросов.
Модуль относится к архитектурной зоне: прикладной слой `relay`, который связывает пользователей, сессии, доменную модель, GPT, уведомления и runtime-логику приложения.

### Публичные классы
- `Context`: контекст обработки события.
- `Command`: описание команды приложения.
- `AcceptedCommand`: результат успешного распознавания команды.
- `CommandsHandler`: обработчик набора команд.
- `GeneralCommands`: общие команды приложения.
- `CommonCommands`: пользовательские команды приложения.
- `SessionsHandler`: обработчик активных сессий.
- `ChatGPTHandler`: обработчик GPT-запросов.
- `NoHandlers`: fallback-обработчик события.

### Публичные функции
- Публичные функции отсутствуют.

### Связи
Используется app-layer сценариями, обработчиками, сессиями и runtime-миксинами для единого пользовательского потока между ботами, GPT и storage.
"""

from __future__ import annotations


from .common import (
    BotTypes,
    Callable,
    Union,
    abstractmethod,
    json,
)
from bots import Bot
from bots import Telebot
from bots import Vkbot
from .config import MESSAGE_LENGTH, get_phrase, logger_admin
from .conversations import Conversation
from .gpt import Request
from .sessions import NoHandlersSession
from .sessions import Session
from .users import Admin, User
from .utils import catch_parsefiles, split_callback
from .callback_data import Callback


class Context():
    """
    `Context` передаёт зависимости между обработчиками, сессиями и runtime-слоем.
    Обработчики читают из него текущее событие и пользователя, а найденный обработчик сохраняют обратно в `handler`.

    ### Поля
    - `HANDLER_TYPE`: допустимые типы обработчика текущего события: распознанная команда, сессия, GPT-запрос или `None`.
    - `autocenter`: экземпляр `App`, через который обработчики вызывают runtime-операции.
    - `bot`: активный transport-адаптер, из которого пришло событие.
    - `user`: пользователь, связанный с текущим `chat_id`.
    - `handler`: найденная команда, активная сессия или GPT-запрос, который должен обработать событие.
    - `event`: унифицированное событие transport-layer.
    - `DEBUG_CALLBACK`: отладочный флаг, заставляющий считать событие callback-кнопкой.
    - `order`: цепочка обработчиков и сессий, через которую прошло событие.

    ### Методы
    - `__init__`: Проверяет типы зависимостей и сохраняет контекст обработки события.
    - `copy`: Создаёт новый `Context` с теми же ссылками на app, bot, user, handler и event.
    - `set_handler`: Проверяет тип обработчика и записывает его в `context.handler`.
    - `remove_handler`: Очищает `context.handler`.
    - `has_handler`: Проверяет, выбран ли обработчик события.
    - `has_event`: Проверяет, есть ли transport-событие.
    - `get_chat_id`: Возвращает chat id пользователя для текущего транспорта.
    - `is_callback`: Проверяет событие через transport-адаптер или отладочный флаг.
    - `get_callback`: Разбирает callback payload текущего события.
    - `get_callback_data`: Возвращает аргументы callback payload текущего события.

    ### Жизненный цикл
    Создаётся на входе обработки transport-события и передаётся по цепочке command/session/GPT handlers.

    ### Пример использования
    ```py
    context: Context
    ```
    """
    HANDLER_TYPE = Union["AcceptedCommand", Session, "Request", None]

    def __init__(self, autocenter: App, bot: BOT, user: User, handler: HANDLER_TYPE, event: Bot.Event| None):
        """
        Создаёт `Context`, проверяет типы app, transport-адаптера, пользователя, обработчика и события.

        ### Аргументы:
        :param autocenter: экземпляр `App`, управляющий runtime-операциями приложения
        :param bot: transport-адаптер Telegram или VK, из которого пришло событие
        :param user: пользователь, найденный по chat id текущего транспорта
        :param handler: уже выбранный обработчик события или `None`
        :param event: унифицированное событие transport-layer или `None`

        :raises ValueError: если одна из зависимостей не относится к ожидаемому типу

        ### Пример использования:
        ```py
        context = Context(autocenter = autocenter, bot = bot, user = user, handler = handler, event = event)
        ```
        """
        from .app import App as AppClass

        self.autocenter: App = autocenter
        self.bot: BOT = bot
        self.user: User = user
        self.handler: "Context.HANDLER_TYPE" = handler
        self.event: Bot.Event | None = event
        self.DEBUG_CALLBACK: bool = False  # FIXME: del
        self.HANDLER_TYPE = AcceptedCommand | Session | Request | None

        # У пользователя есть порядок сессий, а в order хранится порядок внутри сессии (меню, подменю)
        self.order: list["Context.HANDLER_TYPE" | str] = []

        if not isinstance(autocenter, AppClass):
            raise ValueError(f"Некорректное значение аргумента {autocenter=}")

        if isinstance(bot, Vkbot) or isinstance(bot, Telebot):
            pass
        else:
            raise ValueError(f"Некорректное значение аргумента {bot=}")

        if not isinstance(user, User):
            raise ValueError(f"Некорректное значение аргумента {user=}")

        if not isinstance(handler, self.HANDLER_TYPE):
            raise ValueError(f"Некорректное значение аргумента {handler=}")

        if event is None or isinstance(event, Bot.Event):
            pass
        else:
            raise ValueError(f"Некорректное значение аргумента {event=}")


    def copy(self):
        """
        Создаёт новый `Context` с теми же app, bot, user, handler и event.

        :return: копия контекста без переноса цепочки `order`

        ### Пример использования:
        ```py
        context.copy()
        ```
        """
        return Context(autocenter = self.autocenter, bot = self.bot, user = self.user, handler = self.handler, event = self.event)

    def set_handler(self, handler: HANDLER_TYPE):
        """
        Проверяет тип обработчика и сохраняет его в `context.handler`.

        ### Аргументы:
        :param handler: команда, сессия, GPT-запрос или `None`, выбранные для текущего события

        :raises ValueError: если обработчик не входит в допустимые типы `HANDLER_TYPE`

        ### Пример использования:
        ```py
        context.set_handler(handler = handler)
        ```
        """
        if isinstance(handler, self.HANDLER_TYPE):
            self.handler = handler
        else:
            raise ValueError(f"Некорректное значение аргумента {handler=}")

    def remove_handler(self):
        """
        Очищает выбранный обработчик текущего события.

        ### Примеры вызова:
        ```py
        context.remove_handler()
        ```
        """
        self.handler = None

    def has_handler(self) -> bool:
        """
        Проверяет, выбран ли обработчик текущего события.

        :return: `True`, если `context.handler` не пустой; иначе `False`

        ### Пример использования:
        ```py
        context.has_handler()
        ```
        """
        return bool(self.handler)

    def has_event(self) -> bool:
        """
        Проверяет, привязано ли к контексту transport-событие.

        :return: `True`, если `context.event` не равен `None`; иначе `False`

        ### Пример использования:
        ```py
        context.has_event()
        ```
        """
        return self.event is not None

    def get_chat_id(self) -> int:
        """
        Возвращает сохранённый chat id.

        :return: идентификатор чата

        ### Пример использования:
        ```py
        context.get_chat_id()
        ```
        """
        return self.user.get_chat_id(self.bot.get_bot_key())

    def is_callback(self) -> bool:
        """
        Проверяет, должно ли текущее событие обрабатываться как callback-кнопка.

        :return: `True` при включённом `DEBUG_CALLBACK` или если transport-адаптер распознал callback

        ### Пример использования:
        ```py
        context.is_callback()
        ```
        """
        if self.DEBUG_CALLBACK:
            return True

        return self.event and self.bot.check_callback(self.event)

    def get_callback(self) -> Callback:
        """
        Возвращает callback payload для текущего объекта.

        :return: callback

        ### Пример использования:
        ```py
        context.get_callback()
        ```
        """
        return Callback.loads(self.event.get_text())

    def get_callback_data(self) -> list[str]:
        """
        Возвращает аргументы callback payload текущей кнопки.

        :return: payload callback-кнопки

        ### Пример использования:
        ```py
        context.get_callback_data()
        ```
        """
        return Callback.loads(self.event.get_text()).args

    def get_callback_string(self, index: int = 0) -> str:
        """
        Возвращает строковый аргумент callback payload по индексу.

        ### Аргументы:
        :param index: позиция аргумента в callback payload

        :return: аргумент callback payload или пустая строка, если индекса нет

        ### Пример использования:
        ```py
        context.get_callback_string(index = index)
        ```
        """
        args: list[str] = Callback.loads(self.event.get_text()).args
        return args[index] if index < len(args) else ""


class Command():
    """
    `Command` описывает правило распознавания пользовательской команды.
    Команда хранит ключевые слова, ограничения распознавания, минимальный access level и callable-обработчик, который вызывает `CommandsHandler` после успешной проверки текста или callback payload.

    ### Поля
    - `name`: имя команды из JSON-конфигурации.
    - `words`: ключевые слова, по которым команда распознаётся в пользовательском тексте.
    - `quantity`: минимальное количество совпадений, необходимое для активации команды.
    - `min_words`: минимальное количество слов, которое должно остаться после удаления слов команды.
    - `max_length`: максимальная длина текста, который можно проверять как команду.
    - `method`: callable-обработчик команды.
    - `access_level`: минимальный уровень доступа пользователя.

    ### Методы
    - `__init__`: Нормализует параметры распознавания и сохраняет callable-обработчик.
    - `method`: Контракт обработчика команды.
    - `check`: Проверяет частичное совпадение команды с текстом.
    - `check_exact`: Проверяет полное совпадение текста с одним из ключевых слов.
    - `process`: Проверяет access level и вызывает callable-обработчик команды.

    ### Жизненный цикл
    Создаётся из конфигурации `CommandsHandler` и используется при проверке входящих сообщений.

    ### Пример использования
    ```py
    command: Command
    ```
    """

    def __init__(self, name: str, words: Iterable[str], quantity: int, min_words: int, max_length: int, method: Callable, access_level: int = 0):
        """
        Создаёт правило распознавания команды из конфигурации.

        ### Аргументы:
        :param name: имя команды в конфигурации
        :param words: ключевые слова, по которым команда распознаётся в пользовательском тексте
        :param quantity: минимальное количество совпадений, необходимое для активации команды
        :param min_words: минимальное количество слов, которое должно остаться после удаления слов команды
        :param max_length: максимальная длина текста, который можно проверять как команду
        :param method: обработчик, вызываемый после успешного распознавания команды
        :param access_level: минимальный уровень доступа пользователя

        :raises ValueError: если `max_length` меньше 1 или `access_level` отрицательный

        ### Пример использования:
        ```py
        command = Command(name = name, words = words, quantity = quantity, min_words = min_words, max_length = max_length, method = method, access_level = access_level)
        ```
        """
        self.name: str = str(name)
        self.words: tuple[str] = tuple(str(word).upper() for word in words)
        self.quantity: int = int(quantity)
        self.min_words: int = int(min_words or 0)
        self.max_length: int = int(max_length or MESSAGE_LENGTH)

        if self.max_length < 1:
            raise ValueError(f"Некорректное значение аргумента {max_length=}.")

        self.method = method
        self.access_level: int = int(access_level)

        if self.access_level < 0:
            raise ValueError(f"Некорректное значение аргумента {access_level=}.")

    def __repr__(self) -> str:
        words: str = ",".join(map(repr, self.words))
        return f"Command({repr(self.name)} -> {self.method.__name__} access={self.access_level})[({self.quantity}) {words}]"

    @abstractmethod
    def method(self):
        """
        Вызывает сохранённый обработчик режима или уровня.

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        command.method()
        ```
        """
        raise NotImplementedError()

    def check(self, text: str) -> AcceptedCommand | None:
        """
        Проверяет условия для активации команды.
        - Длина проверяемой строки (`text`) не должна превышать `self.max_length`.
        - Как минимум `self.quantity` слов из `self.words` должны входить в проверяемую строку вне зависимости от регистра.
        - После проверки вхождений должно остаться не меньше `self.min_words` слов, например, если `self.quantity=2`, а в проверяемой строке 3 слова, разделённых пробелами, то после проверки останется 1 слово.

        :param text: Проверяемая строка в любом регистре.
        :return: `None`, если хотя бы одно условие не выполнено, иначе копия `self@Command` с оставшимися словами в атрибуте `words`.
        """
        command: str = text.upper()
        result: list[str] = command.split()

        if len(text) > self.max_length:
            return None

        for s in tuple(result):
            for w in self.words:
                if w in s:
                    if s in result:
                        result.remove(s)

                    words: tuple[str] = tuple(result)
                    return AcceptedCommand(self.name, words, self.quantity, self.min_words, self.max_length, self.method, self.access_level)

        return None

    def check_exact(self, text: str) -> AcceptedCommand | None:
        """
        Проверяет полное совпадение текста с одним из ключевых слов команды.

        ### Аргументы:
        :param text: текст входящего сообщения или callback payload

        :return: `AcceptedCommand`, если текст полностью совпал с командой; иначе `None`

        ### Пример использования:
        ```py
        command.check_exact(text = text)
        ```
        """
        command: str = text.upper()

        if len(text) > self.max_length:
            return None

        for word in self.words:
            if command == word:
                words: tuple[str] = tuple()
                return AcceptedCommand(self.name, words, self.quantity, self.min_words, self.max_length, self.method, self.access_level)

        return None

    def process(self, context: Context):
        """
        Передаёт текущий `Context` выбранному обработчику и обновляет `context.handler` по результату.

        ### Аргументы:
        :param context: контекст обработки события

        ### Пример использования:
        ```py
        command.process(context = context)
        ```
        """
        self.method(context)


class AcceptedCommand(Command):
    """
    `AcceptedCommand` хранит результат распознавания команды и оставшиеся слова пользовательского текста.

    ### Методы
    - `__init__`: Создаёт объект и сохраняет app-layer ссылки, которые нужны обработчикам.

    ### Жизненный цикл
    Создаётся app-layer кодом, участвует в обработке пользовательского события и сохраняет изменённое состояние через существующие runtime/storage механизмы.

    ### Пример использования
    ```py
    acceptedCommand: AcceptedCommand
    ```
    """

    def __init__(self, name: str, words: Iterable[str], quantity: int, min_words: int, max_length: int, method: Callable, access_level: int):
        """
        Создаёт handler-объект `AcceptedCommand` и сохраняет контекст, команду или ссылки на app-layer для последующей обработки события.

        ### Аргументы:
        :param name: имя
        :param words: ключевые слова или остаток пользовательского текста
        :param quantity: минимальное количество совпадений
        :param min_words: минимальное число слов после распознавания команды
        :param max_length: максимальная длина проверяемого текста
        :param method: callable-обработчик
        :param access_level: уровень доступа

        ### Пример использования:
        ```py
        acceptedCommand = AcceptedCommand(name = name, words = words, quantity = quantity, min_words = min_words, max_length = max_length, method = method, access_level = access_level)
        ```
        """
        super().__init__(name, words, quantity = quantity, min_words = min_words, max_length = max_length, method = method, access_level = access_level)


class CommandsHandler():
    """
    `CommandsHandler` загружает конфигурацию команд из словаря или JSON-файла и создаёт `Command`.
    При проверке текущего `Context` он читает текст события или callback payload, ищет подходящую команду, проверяет access level и кладёт найденную команду в `context.handler`.

    ### Поля
    - `commands`: список команд, созданных из конфигурации.

    ### Методы
    - `__init__`: Загружает конфигурацию и создаёт список `Command`.
    - `load_commands`: Читает команды из словаря или файла.
    - `init_commands`: Преобразует элементы конфигурации в `Command`.
    - `add_command`: Добавляет команду в список проверяемых правил.
    - `check`: Ищет команду для текущего текста или callback payload и записывает её в `context.handler`.
    - `process`: Запускает обработчик найденной команды.

    ### Жизненный цикл
    Создаётся при инициализации runtime и переиспользуется для обработки входящих событий.

    ### Пример использования
    ```py
    handler: CommandsHandler
    ```
    """

    class Methods:
        """
        `Methods` является namespace callable-обработчиков, на которые ссылается JSON-конфигурация команд.

        ### Пример использования
        ```py
        methods: Methods
        ```
        """
        pass

    def __init__(self, commands: BotTypes.COMMANDS_TYPE | str | None = None):
        """
        Создаёт handler-объект `CommandsHandler` и сохраняет контекст, команду или ссылки на app-layer для последующей обработки события.

        ### Аргументы:
        :param commands: конфигурация команд

        ### Пример использования:
        ```py
        commandsHandler = CommandsHandler(commands = commands)
        ```
        """
        self.source_name: str = self.__class__.__name__
        self.commands: list[Command] = []
        loaded_commands: BotTypes.COMMANDS_TYPE = {}

        if isinstance(commands, str):
            content: str | None = readfiles((commands,))

            if content:
                loaded_commands = json.loads(content)
        elif commands:
            loaded_commands = commands

        self.init_commands(loaded_commands)

    def init_commands(self, commands: dict[str, dict[str, str | int]]):
        """
        Создаёт `Command` для каждого элемента конфигурации и добавляет его в обработчик.

        ### Аргументы:
        :param commands: словарь команд, загруженный из JSON или переданный напрямую

        ### Пример использования:
        ```py
        commandsHandler.init_commands(commands = commands)
        ```
        """
        for commandname, d in commands.items():
            key: str = "methodname"

            if key in d and d[key]:
                with catch_parsefiles((self.source_name,), "load_commands"):
                    method: Callable | None = self.get_methodname(d[key]) or self.get_cannot()
                    command = Command(commandname, d["words"], d["quantity"], get_int(d, 0, "min_words"), get_int(d, MESSAGE_LENGTH, "max_length"), method, d["access"])
                    self.commands.append(command)


    def get_methodname(self, methodname: str) -> Callable | None:
        """
        Возвращает имя метода, указанное в конфигурации команды.

        ### Аргументы:
        :param methodname: имя вызываемого метода

        :return: methodname

        ### Пример использования:
        ```py
        commandsHandler.get_methodname(methodname = methodname)
        ```
        """
        if hasattr(self.__class__.Methods, methodname):
            return getattr(self.__class__.Methods, methodname)
        else:
            return None

    def get_cannot(self) -> Callable:
        """
        Возвращает текст отказа при недостаточном доступе к команде.

        :return: cannot

        ### Пример использования:
        ```py
        commandsHandler.get_cannot()
        ```
        """
        def cannot(context: Context):
            context.autocenter.send_phrase(context, "cannot")
            return None

        return cannot

    def check(self, context: Context):
        """
        Проверяет строку из переданного контекста (события) на соответствие любой из команд по порядку.

        :param context: Объект контекста обязательно с командой.

        - Если проверка не пройдена, то в `context.handler` останется `None`.
        - Иначе в атрибут добавится копия команды `AcceptedCommand`.
        """
        access_level: int = context.user.get_access_level()
        command_text: str = context.event.text
        is_callback: bool = context.is_callback()

        if is_callback:
            callback_args: list[str] = split_callback(command_text)
            command_text = callback_args[0] if callback_args else ""

        for c in self.commands:
            command: AcceptedCommand | None = c.check_exact(command_text) if is_callback else c.check(command_text)

            if command is not None:
                access_required: int = command.access_level

                if access_level >= access_required:
                    context.set_handler(command)
                else:
                    logger_admin.warning(
                        "Недостаточно прав для команды: user_id=%s access_level=%s required=%s command=%s",
                        context.user.id,
                        access_level,
                        access_required,
                        command.name,
                    )

        return None

    def process(self, context: Context):
        """
        Передаёт текущий `Context` выбранному обработчику и обновляет `context.handler` по результату.

        ### Аргументы:
        :param context: контекст обработки события

        ### Пример использования:
        ```py
        commandsHandler.process(context = context)
        ```
        """
        context.handler.process(context)


class GeneralCommands(CommandsHandler):

    """
    `GeneralCommands` загружает общий набор команд приложения.
    Вложенный `Methods` содержит callable-обработчики, имена которых используются в JSON-конфигурации.

    ### Методы
    - `__init__`: Загружает переданную конфигурацию или файл общих команд.

    ### Жизненный цикл
    Создаётся runtime-слоем как один из command handlers приложения.

    ### Пример использования
    ```py
    generalCommands: GeneralCommands
    ```
    """
    class Methods:

        """
        `Methods` является namespace callable-обработчиков общих команд из JSON-конфигурации.

        ### Пример использования
        ```py
        methods: Methods
        ```
        """
        def start(context: Context):
            """
            Запускает сценарий обработки и подготавливает первое сообщение или задачу.

            ### Аргументы:
            :param context: контекст обработки события

            ### Пример использования:
            ```py
            methods.start(context = context)
            ```
            """
            context.autocenter.send(context, get_phrase("greeting"))

        def call_admin(context: Context):
            """
            Создаёт обращение к администратору, если у пользователя ещё нет активного диалога.

            ### Аргументы:
            :param context: контекст обработки события

            ### Пример использования:
            ```py
            methods.call_admin(context = context)
            ```
            """
            user: User = context.user
            bot_key: BOT_KEY = context.bot.get_bot_key()
            if user.find_conv_session(bot_key):
                return


            context.autocenter.call_admin(context)
            context.autocenter.send(context, get_phrase("admin_called"))

        def finish_dialog(context: Context):
            """
            Завершает dialog и очищает связанные runtime-данные.

            ### Аргументы:
            :param context: контекст обработки события с app, bot, user, handler и message

            ### Пример использования:
            ```py
            methods.finish_dialog(context = context)
            ```
            """
            autocenter: App = context.autocenter
            autocenter.check_access(context)
            text: str = context.event.get_text()
            args: list[str] = split_callback(text)
            bot_key: BOT_KEY = args[1]
            chat_id: int = int(args[2])
            autocenter.finish_dialog(bot_key, chat_id)

        def show_dialog(context: Context):
            """
            Переотправляет администратору уведомления по выбранному пользовательскому диалогу.

            ### Аргументы:
            :param context: контекст обработки события

            ### Пример использования:
            ```py
            methods.show_dialog(context = context)
            ```
            """
            autocenter: App = context.autocenter
            autocenter.check_access(context)

            admin: Admin = context.user
            text: str = context.event.get_text()
            args: list[str] = split_callback(text)
            bot_key: BOT_KEY = args[1]
            chat_id: int = int(args[2])

            user: User = autocenter.get_user(bot_key, chat_id)
            session: ConvSession | None = user.find_conv_session(bot_key)

            if session:
                session.resend_notifications(context.bot.get_bot_key(), context.get_chat_id())
                user.save()

        def start_dialog(admin_context: Context):
            """
            Запускает сценарий обработки и подготавливает первое сообщение или задачу.

            ### Аргументы:
            :param admin_context: admin context

            ### Пример использования:
            ```py
            methods.start_dialog(admin_context = admin_context)
            ```
            """
            autocenter: App = admin_context.autocenter
            autocenter.check_access(admin_context)

            admin: Admin = admin_context.user
            text: str = admin_context.event.get_text()
            args: list[str] = split_callback(text)
            bot_key: BOT_KEY = args[1]
            chat_id: int = int(args[2])

            user: User = autocenter.get_user(bot_key, chat_id)
            user_bot: BOT = autocenter.get_bot(bot_key)
            username: str = user.get_username(bot_key)

            conv: Conversation = autocenter.start_conv(Context(autocenter, user_bot, user, None, None))


            admin.start_session(ConvSession, admin_context, {
                "conv_id": conv.id,
                "admin_role": True
            }, process_context = False)
            conv.join_admin(admin_context, username, bot_key)

        def main(context: Context):
            """
            Обрабатывает обычное входящее событие пользователя и выбирает подходящий сценарий.

            ### Аргументы:
            :param context: контекст обработки события

            ### Пример использования:
            ```py
            methods.main(context = context)
            ```
            """
            user: User = context.user
            user.start_session(MainSession, context)

        def edit_models(context: Context):
            """
            Обновляет уже отправленное модели GPT через transport-layer.

            ### Аргументы:
            :param context: контекст обработки события с app, bot, user, handler и message

            ### Пример использования:
            ```py
            methods.edit_models(context = context)
            ```
            """
            context.autocenter.check_access(context)
            context.user.go_session(SessionProviders, context)

        def edit_limits(context: Context):
            """
            Обновляет уже отправленное лимиты GPT через transport-layer.

            ### Аргументы:
            :param context: контекст обработки события с app, bot, user, handler и message

            ### Пример использования:
            ```py
            methods.edit_limits(context = context)
            ```
            """
            context.autocenter.check_access(context)
            context.user.go_session(SessionLimits, context)

        def edit_context(context: Context):
            """
            Обновляет уже отправленное контекст обработки события через transport-layer.

            ### Аргументы:
            :param context: контекст обработки события с app, bot, user, handler и message

            ### Пример использования:
            ```py
            methods.edit_context(context = context)
            ```
            """
            context.autocenter.check_access(context)
            context.user.go_session(SessionContexts, context)

        def edit_questions(context: Context):
            """
            Обновляет уже отправленное вопросы анкеты или GPT-контекста через transport-layer.

            ### Аргументы:
            :param context: контекст обработки события с app, bot, user, handler и message

            ### Пример использования:
            ```py
            methods.edit_questions(context = context)
            ```
            """
            context.autocenter.check_access(context)
            context.user.go_session(SessionQuestions, context)

        def edit_filials(context: Context):
            """
            Обновляет уже отправленное филиалы автошколы через transport-layer.

            ### Аргументы:
            :param context: контекст обработки события с app, bot, user, handler и message

            ### Пример использования:
            ```py
            methods.edit_filials(context = context)
            ```
            """
            context.autocenter.check_access(context)
            context.user.go_session(SessionFilials, context)

        def edit_dates(context: Context):
            """
            Обновляет уже отправленное доступные даты записи через transport-layer.

            ### Аргументы:
            :param context: контекст обработки события с app, bot, user, handler и message

            ### Пример использования:
            ```py
            methods.edit_dates(context = context)
            ```
            """
            context.autocenter.check_access(context)
            context.user.go_session(SessionDates, context)

        def edit_gpt(context: Context):
            """
            Обновляет уже отправленное gpt через transport-layer.

            ### Аргументы:
            :param context: контекст обработки события с app, bot, user, handler и message

            ### Пример использования:
            ```py
            methods.edit_gpt(context = context)
            ```
            """
            context.autocenter.check_access(context)
            context.user.go_session(GPTSession, context)

        def edit_users(context: Context):
            """
            Обновляет уже отправленное пользователей через transport-layer.

            ### Аргументы:
            :param context: контекст обработки события с app, bot, user, handler и message

            ### Пример использования:
            ```py
            methods.edit_users(context = context)
            ```
            """
            context.autocenter.check_access(context)
            context.user.go_session(SessionUsers, context)

        def edit_admins(context: Context):
            """
            Обновляет уже отправленное настройки администраторов через transport-layer.

            ### Аргументы:
            :param context: контекст обработки события с app, bot, user, handler и message

            ### Пример использования:
            ```py
            methods.edit_admins(context = context)
            ```
            """
            context.autocenter.check_access(context)
            context.user.go_session(SessionAdmins, context, {"mode": "admins"})

        def edit_bot_control(context: Context):
            """
            Обновляет уже отправленное bot control через transport-layer.

            ### Аргументы:
            :param context: контекст обработки события с app, bot, user, handler и message

            ### Пример использования:
            ```py
            methods.edit_bot_control(context = context)
            ```
            """
            context.autocenter.check_access(context)
            context.user.go_session(BotControlSession, context)

    def __init__(self, commands: BotTypes.COMMANDS_TYPE | str | None = None):
        """
        Создаёт обработчик общих команд из переданной конфигурации или стандартного JSON-файла.

        ### Аргументы:
        :param commands: словарь команд или путь к JSON-файлу; если не передан, используется файл общих команд

        ### Пример использования:
        ```py
        generalCommands = GeneralCommands(commands = commands)
        ```
        """
        super().__init__(commands or join(JSON_FOLDER, GENERAL_COMMANDS_FILENAME))


class CommonCommands(CommandsHandler):

    """
    `CommonCommands` загружает пользовательский набор команд приложения.
    Вложенный `Methods` оставлен как namespace callable-обработчиков, на которые может ссылаться JSON-конфигурация.

    ### Методы
    - `__init__`: Загружает переданную конфигурацию или файл пользовательских команд.

    ### Жизненный цикл
    Создаётся runtime-слоем как один из command handlers приложения.

    ### Пример использования
    ```py
    commonCommands: CommonCommands
    ```
    """
    class Methods:
        """
        `Methods` является namespace callable-обработчиков пользовательских команд из JSON-конфигурации.

        ### Пример использования
        ```py
        methods: Methods
        ```
        """
        pass


    def __init__(self, commands: BotTypes.COMMANDS_TYPE | str | None = None):
        """
        Создаёт обработчик пользовательских команд из переданной конфигурации или стандартного JSON-файла.

        ### Аргументы:
        :param commands: словарь команд или путь к JSON-файлу; если не передан, используется файл пользовательских команд

        ### Пример использования:
        ```py
        commonCommands = CommonCommands(commands = commands)
        ```
        """
        super().__init__(commands or join(JSON_FOLDER, COMMON_COMMANDS_FILENAME))


class SessionsHandler():

    """
    Описывает пользовательскую или административную сессию `SessionsHandler`.

    ### Методы
    - `__init__`: Создаёт объект и сохраняет app-layer ссылки, которые нужны обработчикам.
    - `check`: Проверяет значение по правилам текущего класса и не изменяет состояние.
    - `process`: Передаёт текущий `Context` выбранному обработчику и обновляет `context.handler` по результату.

    ### Жизненный цикл
    Создаётся app-layer кодом, участвует в обработке пользовательского события и сохраняет изменённое состояние через существующие runtime/storage механизмы.

    ### Пример использования
    ```py
    session: SessionsHandler
    ```
    """
    def __init__(self):
        """
        Создаёт `SessionsHandler` и сохраняет app-layer ссылки, которые нужны обработчикам.

        ### Примеры вызова:
        ```py
        session: SessionsHandler = SessionsHandler()
        ```
        """
        pass

    def check(self, context: Context):
        """
        Проверяет значение по правилам текущего класса и не изменяет состояние.

        ### Аргументы:
        :param context: контекст обработки события

        ### Пример использования:
        ```py
        sessionsHandler.check(context = context)
        ```
        """
        user: User = context.user
        bot_key: str = context.bot.get_bot_key()

        if bot_key in user.sessions:
            if user.sessions[bot_key]:
                sessions: list[Session] = user.sessions[bot_key]

                for session in reversed(sessions):
                    if session.check(context):
                        context.set_handler(session)
                        return
        return None

    def process(self, context: Context):
        """
        Передаёт текущий `Context` выбранному обработчику и обновляет `context.handler` по результату.

        ### Аргументы:
        :param context: контекст обработки события

        ### Пример использования:
        ```py
        sessionsHandler.process(context = context)
        ```
        """
        user: User = context.user
        bot_key: str = context.bot.get_bot_key()

        if bot_key in user.sessions:
            if user.sessions[bot_key]:
                sessions: list[Session] = user.sessions[bot_key]

                for session in reversed(sessions):
                    if session.check(context):
                        context.set_handler(session)
                        user.process(context)

                        if context.has_handler():
                            # success
                            return
                        else:
                            # Переходим к следующей сессии, может она сможет обработать запрос
                            pass
        return None


class ChatGPTHandler():

    """
    Описывает handler app-layer для выбора и запуска нужной сессии.

    ### Методы
    - `__init__`: Создаёт объект и сохраняет app-layer ссылки, которые нужны обработчикам.
    - `check`: Проверяет значение по правилам текущего класса и не изменяет состояние.
    - `process`: Передаёт текущий `Context` выбранному обработчику и обновляет `context.handler` по результату.

    ### Жизненный цикл
    Создаётся app-layer кодом, участвует в обработке пользовательского события и сохраняет изменённое состояние через существующие runtime/storage механизмы.

    ### Пример использования
    ```py
    chatGPTHandler: ChatGPTHandler
    ```
    """
    def __init__(self):
        """
        Создаёт `ChatGPTHandler` и сохраняет app-layer ссылки, которые нужны обработчикам.

        ### Примеры вызова:
        ```py
        chatGPTHandler: ChatGPTHandler = ChatGPTHandler()
        ```
        """
        pass

    def check(self, context: Context):
        """
        Проверяет значение по правилам текущего класса и не изменяет состояние.

        ### Аргументы:
        :param context: контекст обработки события

        ### Пример использования:
        ```py
        chatGPTHandler.check(context = context)
        ```
        """

        # here
        # return

        context.autocenter.prove_request(context)

    def process(self, context: Context):
        """
        Передаёт текущий `Context` выбранному обработчику и обновляет `context.handler` по результату.

        ### Аргументы:
        :param context: контекст обработки события

        ### Пример использования:
        ```py
        chatGPTHandler.process(context = context)
        ```
        """
        context.autocenter.process_request(context, delayed = True)


class NoHandlers():

    """
    Описывает handler app-layer для выбора и запуска нужной сессии.

    ### Методы
    - `__init__`: Создаёт объект и сохраняет app-layer ссылки, которые нужны обработчикам.
    - `check`: Проверяет значение по правилам текущего класса и не изменяет состояние.
    - `process`: Передаёт текущий `Context` выбранному обработчику и обновляет `context.handler` по результату.

    ### Жизненный цикл
    Создаётся app-layer кодом, участвует в обработке пользовательского события и сохраняет изменённое состояние через существующие runtime/storage механизмы.

    ### Пример использования
    ```py
    noHandlers: NoHandlers
    ```
    """
    def __init__(self):
        """
        Создаёт `NoHandlers` и сохраняет app-layer ссылки, которые нужны обработчикам.

        ### Примеры вызова:
        ```py
        noHandlers: NoHandlers = NoHandlers()
        ```
        """
        pass

    def check(self, context: Context):
        """
        Проверяет значение по правилам текущего класса и не изменяет состояние.

        ### Аргументы:
        :param context: контекст обработки события

        ### Пример использования:
        ```py
        noHandlers.check(context = context)
        ```
        """
        user: User = context.user

        if user.get_access_level() < 1 and context.has_event():
            if context.is_callback():
                user.go_session(MainSession, context, None, None)
            else:
                session: NoHandlersSession = user.go_session(NoHandlersSession, context)
                context.set_handler(session)
        else:
            pass


    def process(self, context: Context):
        """
        Передаёт текущий `Context` выбранному обработчику и обновляет `context.handler` по результату.

        ### Аргументы:
        :param context: контекст обработки события

        ### Пример использования:
        ```py
        noHandlers.process(context = context)
        ```
        """
        context.handler.process(context)


import relay.users as _users_module
import relay.users.user as _user_module

_users_module.Context = Context
_user_module.Context = Context
