"""
Описывает диалоги клиента и администратора через бота.
Модуль относится к архитектурной зоне: прикладной слой `relay`, который связывает пользователей, сессии, доменную модель, GPT, уведомления и runtime-логику приложения.

### Публичные классы
- `Conversation`: модель активного диалога клиента и администратора.

### Публичные функции
- Публичные функции отсутствуют.

### Связи
Используется app-layer сценариями, обработчиками, сессиями и runtime-миксинами для единого пользовательского потока между ботами, GPT и storage.
"""

from __future__ import annotations


from bots import Bot
from bots import Message
from callbacks import CALLBACK_CLOSEDIALOG
from callbacks import CALLBACK_FINISHDIALOG
from callbacks import CALLBACK_REMOVE
from callbacks import CONV_CALLBACK
from .common import (
    BotTypes,
    Lock,
    Storage,
    abstractmethod,
    datetime,
)
from .config import BOT_KEYS, MAX_HISTORY, get_phrase
from .users import User
from .utils import (
    catch_parsefiles,
    is_int,
    join_callback,
    log_warn,
    split_callback,
)
from bots.utils.mapping import get_from
from .callback_data import Callback


class Conversation():
    """
    `Conversation` ведёт live-диалог между пользователем и администраторами и хранит сообщения, участников и removable UI.

    ### Поля
    - `id`: внутренний идентификатор записи или доменного объекта.
    - `storage_key`: ключ записи пользователя или документа в storage-layer.
    - `storage`: storage API, через который диалог сохраняет состояние.
    - `get_bot`: callback для получения transport-адаптера по ключу.
    - `create_message_id`: идентификатор объекта или связанной сущности, по которому runtime восстанавливает связь между слоями.
    - `message_id`: идентификатор объекта или связанной сущности, по которому runtime восстанавливает связь между слоями.
    - `message`: хранит wrapper-сообщение для операций этого объекта.
    - `users`: хранит пользователей для операций этого объекта.
    - `admins`: хранит настройки администраторов для операций этого объекта.
    - `messages`: сообщения, которые приложение хранит для обновления интерфейса пользователя.

    ### Методы
    - `__init__`: Создаёт объект и сохраняет app-layer ссылки, которые нужны обработчикам.
    - `dumps`: Возвращает JSON-совместимый снимок объекта для storage или callback payload.
    - `create_message_id`: Создаёт message id и связывает результат с текущим app-layer состоянием.
    - `get_bot`: Возвращает bot из текущего состояния `Conversation`.
    - `get_callback`: Возвращает callback-событие из текущего состояния `Conversation`.
    - `check_callback_data`: Проверяет callback data перед использованием.
    - `parse_callback`: Разбирает callback payload transport-события.
    - `get_remove_button`: Возвращает remove button из текущего состояния `Conversation`.
    - `add_removable`: Добавляет removable-сообщение в список сообщений для удаления.
    - `remove_message`: Удаляет wrapper-сообщение из внутреннего состояния или storage.

    ### Жизненный цикл
    Создаётся app-layer кодом, участвует в обработке пользовательского события и сохраняет изменённое состояние через существующие runtime/storage механизмы.

    ### Пример использования
    ```py
    conversation: Conversation
    ```
    """
    class Participant():
        """
        `Participant` связывает сторону live-диалога с transport-ботом и пользовательским сообщением.

        ### Поля
        - `user`: хранит состояние пользователя для операций этого объекта.
        - `bot`: transport-адаптер, с которым работает объект.
        - `chat_id`: идентификатор объекта или связанной сущности, по которому runtime восстанавливает связь между слоями.

        ### Методы
        - `__init__`: Создаёт объект и сохраняет app-layer ссылки, которые нужны обработчикам.
        - `dumps`: Возвращает JSON-совместимый снимок объекта для storage или callback payload.

        ### Жизненный цикл
        Создаётся app-layer кодом, участвует в обработке пользовательского события и сохраняет изменённое состояние через существующие runtime/storage механизмы.

        ### Пример использования
        ```py
        participant: Participant
        ```
        """

        def __init__(self, user: User, bot: BOT, chat_id: int):
            """
            Инициализирует `Participant` для стороны live-диалога и привязывает bot, пользователя и служебные сообщения.

            ### Аргументы:
            :param user: пользователь приложения
            :param bot: transport-адаптер
            :param chat_id: идентификатор чата

            ### Пример использования:
            ```py
            participant = Participant(user = user, bot = bot, chat_id = chat_id)
            ```
            """
            self.user: User = user
            self.bot: BOT = bot
            self.chat_id: int = int(chat_id)

        def __repr__(self) -> str:
            user_id: int = self.user.id
            chat_id: int = self.chat_id
            bot: BOT = self.bot
            return f"Participant({user_id=} {chat_id=} {bot=})"

        def dumps(self) -> BotTypes.PARTICIPANT_TYPE:
            """
            Возвращает JSON-совместимый снимок объекта для storage или callback payload.

            :return: JSON-совместимый словарь для сохранения или передачи между слоями

            ### Пример использования:
            ```py
            participant.dumps()
            ```
            """
            return {
                "user_id": int(self.user.id),
                "bot_key": (self.bot.get_bot_key()),
                "chat_id": int(self.chat_id)
            }


    def __init__(
            self,
            conv_id: int,
            storage_key: str,
            get_bot: Callable[[BOT_KEY], BOT],
            create_message_id: Callable[[], int],
            storage: Storage | None = None,
            username: str | None = "",
            create_message: bool = True,
            ):
        """
        Инициализирует live-диалог, подключает storage и восстанавливает участников, события и removable-сообщения.

        ### Аргументы:
        :param conv_id: conv id
        :param storage_key: storage key
        :param get_bot: get bot
        :param create_message_id: create message id
        :param storage: storage API приложения
        :param username: имя пользователя
        :param create_message: create message

        ### Пример использования:
        ```py
        conversation = Conversation(conv_id = conv_id, storage_key = storage_key, get_bot = get_bot, create_message_id = create_message_id, storage = storage, username = username, create_message = create_message)
        ```
        """
        self.id: int = int(conv_id)
        self.storage_key: str = str(storage_key)
        self.storage: Storage | None = storage
        self.get_bot = get_bot
        self.create_message_id = create_message_id

        message_id: int = self.create_message_id() if create_message else 0

        # Сообщение, в котором хранятся все сообщения в чатах участников
        self.message: Message | None = Message(message_id) if create_message else None
        # Участники чата
        self.users: dict[BOT_KEY, dict[int, Conversation.Participant]] = {}
        # Список администраторов чата `User.id: int`
        self.admins: set[int] = set()
        # История сообщений чата
        self.messages: list[Message.MessagesGroup] = []
        # Сообщения с кнопкой удаления
        self.removable_messages: dict[str, Bot.Message] = {}

        self.buttons: list[Bot.Keyboard.Button] = [
            Bot.Keyboard.Button(get_phrase("close_dialog"), callback_data = self.get_callback(CALLBACK_CLOSEDIALOG)),
            Bot.Keyboard.Button(get_phrase("finish_dialog"), callback_data = self.get_callback(CALLBACK_FINISHDIALOG))
        ]

        self.admin_messages: dict[int, Message] = self.load_admin_messages({}, username = username) if create_message else {}

        self.lock: Lock = Lock()

    def dumps(self) -> BotTypes.CONVERSATION_TYPE:
        """
        Возвращает JSON-совместимый снимок объекта для storage или callback payload.

        :return: JSON-совместимый словарь для сохранения или передачи между слоями

        ### Пример использования:
        ```py
        conversation.dumps()
        ```
        """


        return {
            "id": int(self.id),
            "message": self.message.dumps(),
            "messages": [group.dumps() for group in self.messages],
            "users": {
                str(bot_key): {
                    int(party.chat_id): party.dumps() for chat_id, party in parties.items()
                } for bot_key, parties in self.users.items()
            },
            "admins": list(map(int, self.admins)),
            "admin_messages": {
                int(index): message.dumps() for index, message in self.admin_messages.items()
            },
            "removable_messages": {
                callback_data: message.dumps() for callback_data, message in self.removable_messages.items()
            }
        }

    @abstractmethod
    def create_message_id(self) -> int:
        """
        Создаёт message id и связывает результат с текущим app-layer состоянием.

        :return: созданный объект для message id

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Примеры вызова:
        ```py
        conversation.create_message_id()
        ```
        """
        raise NotImplementedError()

    @abstractmethod
    def get_bot(self, bot_key: BOT_KEY) -> BOT:
        """
        Возвращает привязанный transport-адаптер.

        ### Аргументы:
        :param bot_key: ключ транспорта

        :return: transport-адаптер

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        conversation.get_bot(bot_key = bot_key)
        ```
        """
        raise NotImplementedError()

    def get_callback(self, *args: Iterable) -> str:
        """
        Возвращает callback payload для текущего объекта.

        :return: callback

        ### Пример использования:
        ```py
        conversation.get_callback(args = args)
        ```
        """
        return Callback(None, CONV_CALLBACK, self.id, *args).stringfy()

    def check_callback_data(self, callback_data: str) -> bool:
        """
        Проверяет, можно ли разобрать payload callback-кнопки.

        ### Аргументы:
        :param callback_data: payload callback-кнопки

        :return: `True`, если payload callback-кнопки можно разобрать; иначе `False`

        ### Пример использования:
        ```py
        conversation.check_callback_data(callback_data = callback_data)
        ```
        """
        callback: Callback = Callback.loads(callback_data)

        if callback.session_id is not None:
            return False

        if len(callback.args) < 3:
            return False

        # WARNING: int -> str чтобы не было TypeError при приведении к int
        return callback.args[0] == CONV_CALLBACK and str(callback.args[1]) == str(self.id)

    def parse_callback(self, callback_data: str) -> list[str]:
        """
        Разбирает callback payload transport-события.

        ### Аргументы:
        :param callback_data: данные callback-кнопки, пришедшие из транспорта

        :return: результат выполнения операции

        ### Пример использования:
        ```py
        conversation.parse_callback(callback_data = callback_data)
        ```
        """
        return Callback.loads(callback_data).args[2:]

    def get_remove_button(self, message: Bot.Message) -> Bot.Keyboard.Button:
        """
        Возвращает кнопку удаления сообщения.

        :return: remove button
        """
        callback_data: str = join_callback(CALLBACK_REMOVE, message.get_bot_key(), message.get_chat_id(), message.get_owner_id(), message.get_id())
        return Bot.Keyboard.Button(get_phrase("remove"), callback_data = callback_data)

    def add_removable(self, removable_messages: list[Bot.Message]):
        """
        Запоминает сообщение, которое можно удалить при обновлении live-диалога.

        ### Аргументы:
        :param removable_messages: removable messages

        ### Пример использования:
        ```py
        conversation.add_removable(removable_messages = removable_messages)
        ```
        """
        for message in removable_messages:
            callback_data: str = message.get_remove_callback()
            self.removable_messages[callback_data] = message

    def remove_message(self, remove_key: str, bot_key: BOT_KEY, message_id: int):
        """
        Удаляет сообщение из removable-списка live-диалога.

        ### Аргументы:
        :param remove_key: remove key
        :param bot_key: ключ транспорта
        :param message_id: идентификатор сообщения

        ### Пример использования:
        ```py
        conversation.remove_message(remove_key = remove_key, bot_key = bot_key, message_id = message_id)
        ```
        """
        if remove_key in self.removable_messages:
            text: str = get_phrase("deleted")

            message: Bot.Message = self.removable_messages[remove_key]
            message.set_text(text)
            message.set_keyboard(None)
            message.edit()

            del self.removable_messages[remove_key]

        for group in self.messages:
            if group.bot.get_bot_key() == bot_key:
                for message in list(group.messages):
                    if message.id == message_id:
                        group.messages.remove(message)
                        return

    def save(self):
        """
        Записывает текущее JSON-представление через storage API.

        :raises RuntimeError: если объект ещё не связан с необходимым runtime-состоянием

        ### Пример использования:
        ```py
        conversation.save()
        ```
        """
        if self.storage is None:
            raise RuntimeError(f"Не задано хранилище для диалога {self.id=}")

        self.storage.save_conversation(self.id, self.dumps())

    def load(self, get_bot: Callable[[BOT_KEY], BOT], get_user: Callable[[BOT_KEY, int], User]):
        """
        Загружает JSON-представление и восстанавливает поля объекта.

        ### Аргументы:
        :param get_bot: get bot
        :param get_user: get user

        :raises RuntimeError: если объект ещё не связан с необходимым runtime-состоянием

        ### Пример использования:
        ```py
        conversation.load(get_bot = get_bot, get_user = get_user)
        ```
        """
        if self.storage is None:
            raise RuntimeError(f"Не задано хранилище для диалога {self.id=}")

        data: BotTypes.CONVERSATION_TYPE = self.storage.load_conversation(self.id)
        self.load_conv(data, get_bot, get_user)

    def load_conv(self, data: BotTypes.CONVERSATION_TYPE, get_bot: Callable[[BOT_KEY], BOT], get_user: Callable[[BOT_KEY, int], User]):
        """
        Загружает данные из storage или внешнего transport/API и приводит их к объектам проекта.

        ### Аргументы:
        :param data: сериализованный словарь
        :param get_bot: get bot
        :param get_user: get user

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        conversation.load_conv(data = data, get_bot = get_bot, get_user = get_user)
        ```
        """
        with catch_parsefiles((self.storage_key,), "load_conversation"):
            message_data: dict = get_from(data, "message", default = {}, types = (dict,))
            self.message = Message.loads(message_data, get_bot)

        with catch_parsefiles((self.storage_key,), "load_conversation"):
            self.admins = set(map(int, data.get("admins", [])))

        with catch_parsefiles((self.storage_key,), "load_conversation"):
            self.id = get_int(data, -1, "id")

        if self.id < 0:
            raise ValueError(f"Некорректное значение словаря с ключом data['id']={repr(data.get('id'))}")

        with catch_parsefiles((self.storage_key,), "load_conversation"):
            for group_data in data.get("messages", []):
                with catch_parsefiles((self.storage_key,), "load_conversation"):
                    bot_key: BOT_KEY = group_data["bot_key"]
                    bot: BOT = get_bot(bot_key)
                    group: Message.MessagesGroup = Message.MessagesGroup.loads(group_data, bot)
                    self.messages.append(group)

        # WARNING:
        while len(self.messages) > MAX_HISTORY:
            self.messages.pop(0)
            # logger.error("Conversation.load_conv pop!")

        with catch_parsefiles((self.storage_key,), "load_conversation"):
            self.admin_messages.update(self.load_admin_messages(data))

        with catch_parsefiles((self.storage_key,), "load_conversation"):
            result: list[Bot.Message] = []

            for callback_data, message_data in data.get("removable_messages", {}).items():
                with catch_parsefiles((self.storage_key,), "load_removable"):
                    args: list[str] = split_callback(callback_data)
                    _, bot_key, chat_id, owner_id, message_id = args

                    if bot_key not in BOT_KEYS:
                        removable_messages = data.get("removable_messages")
                        raise ValueError(f"Некорректное значение {bot_key=} под ключом {removable_messages=} аргумента data")

                    if not is_int(owner_id):
                        removable_messages = data.get("removable_messages")
                        raise ValueError(f"Некорректное значение {owner_id=} под ключом {removable_messages=} аргумента data")
                    else:
                        owner_id: int = int(owner_id)

                    if not is_int(chat_id):
                        removable_messages = data.get("removable_messages")
                        raise ValueError(f"Некорректное значение {chat_id=} под ключом {removable_messages=} аргумента data")
                    else:
                        chat_id: int = int(chat_id)

                    if not is_int(message_id):
                        removable_messages = data.get("removable_messages")
                        raise ValueError(f"Некорректное значение {message_id=} под ключом {removable_messages=} аргумента data")
                    else:
                        message_id: int = int(message_id)

                    bot: BOT = self.get_bot(bot_key)
                    message: Bot.Message = bot.__class__.Message.loads(message_data, type(bot), bot.bot)
                    result.append(message)

            self.add_removable(result)

        # with catch_parsefiles((self.storage_key,), "load_conversation"):
        for party_bot_key, parties in data.get("users", {}).items():
            # with catch_parsefiles((self.storage_key,), "load_conversation"):
            for party_chat_id, party_data in parties.items():
                # with catch_parsefiles((self.storage_key,), "load_conversation"):
                user_id: int = get_int(party_data, -1, "user_id")
                bot_key: str = get_from(party_data, "bot_key")
                chat_id: int = get_int(party_data, -1, "chat_id")

                if bot_key != party_bot_key:
                    raise ValueError(f"Некорректный {bot_key=}. Значение аргумента data под ключом users для {bot_key=} {chat_id=} не соответствует.")

                if str(chat_id) != str(party_chat_id):
                    raise ValueError(f"Некорректный {chat_id=}. Значение аргумента data под ключом users для {bot_key=} {chat_id=} не соответствует.")

                bot: BOT = get_bot(bot_key)
                user: User = get_user(bot_key, int(chat_id))

                if str(user.id) != str(user_id):
                    raise ValueError(f"Некорректный {user_id=}. Значение аргумента data под ключом users для {bot_key=} {chat_id=} не соответствует.")

                party: Conversation.Participant = Conversation.Participant(user, bot, int(chat_id))
                self.add_party(party, save = False)

        self.print_admin_messages()

    def find_group(self, context: Context) -> Message.MessagesGroup | None:
        """
        Ищет group по данным, которые пришли из вызывающего слоя.

        ### Аргументы:
        :param context: контекст обработки события с app, bot, user, handler и message

        :return: найденное значение для group или None, если записи нет

        ### Пример использования:
        ```py
        conversation.find_group(context = context)
        ```
        """
        text: str = context.event.get_text()
        message_id: int = context.bot.__class__.get_message_id(context.event)
        return context.user.find_group(context.autocenter.get_bot, message_id, context.event, text, context.event.get_date())

    def create_group(self, context: Context) -> Message.MessagesGroup:
        """
        Создаёт group и связывает результат с текущим app-layer состоянием.

        ### Аргументы:
        :param context: контекст обработки события с app, bot, user, handler и message

        :return: созданный объект для group

        ### Пример использования:
        ```py
        conversation.create_group(context = context)
        ```
        """
        chat_id: int = context.get_chat_id()
        messages: list[Bot.Message] = [context.bot.__class__.Message.from_event(context.event, context.bot.bot)]
        username: str = context.user.get_username(context.bot.get_bot_key())
        date: datetime = datetime.now()
        return Message.MessagesGroup(context.bot, chat_id, chat_id, messages, username, date)

    def add_event(self, context: Context) -> Message.MessagesGroup:
        """
        Сохраняет transport-событие в очереди или истории объекта.

        ### Аргументы:
        :param context: контекст обработки события с app, bot, user, handler и message

        :return: результат выполнения операции

        ### Пример использования:
        ```py
        conversation.add_event(context = context)
        ```
        """
        group: Message.MessagesGroup = self.find_group(context) or self.create_group(context)
        self.messages.append(group)

        bot_key: BOT_KEY = context.bot.get_bot_key()
        chat_id: int = context.get_chat_id()
        messages_group: Message.MessagesGroup


        if self.message.has_groups(bot_key, chat_id):
            messages_group = self.message.get_last_group(bot_key, chat_id)
            messages_group.messages += group.messages

        self.save()

    def update(self):
        """
        Синхронизирует данные сценария с уже отправленными UI-сообщениями.

        ### Пример использования:
        ```py
        conversation.update()
        ```
        """
        # for group in self.messages:
        removable_messages: list[Bot.Message] = self.message.edit_groups(self.messages, get_footer = self.get_footer, get_remove_button = self.get_remove_button)
        self.add_removable(removable_messages)
        self.save()


    def check_admin(self, user_id: int) -> bool:
        """
        Проверяет значение `admin` перед сохранением или использованием.

        ### Аргументы:
        :param user_id: user id

        :return: `True`, если значение `admin` перед сохранением или использованием; иначе `False`

        ### Пример использования:
        ```py
        conversation.check_admin(user_id = user_id)
        ```
        """
        return user_id in self.admins

    def delete_party(self, bot_key: BOT_KEY, chat_id: int):
        """
        Удаляет party из внутреннего состояния или storage.

        ### Аргументы:
        :param bot_key: ключ транспорта, например `vkbot` или `telebot`
        :param chat_id: идентификатор чата в конкретной платформе

        :raises ValueError: если значение не проходит локальную проверку перед сохранением

        ### Пример использования:
        ```py
        conversation.delete_party(bot_key = bot_key, chat_id = chat_id)
        ```
        """
        if bot_key not in BOT_KEYS:
            raise ValueError(f"Некорректное значение аргумента {bot_key=}")

        if bot_key in self.users and chat_id in self.users[bot_key]:
            del self.users[bot_key][chat_id]
        else:
            log_warn(f"Пользователь {bot_key=} {chat_id=} уже покинул чат")

    def add_party(self, party: Participant, admin_role: bool = False, save: bool = True):
        """
        Добавляет участника к live-диалогу.

        ### Аргументы:
        :param party: сторона диалога или участник переписки
        :param admin_role: admin role
        :param save: нужно ли сохранить изменённое состояние

        ### Пример использования:
        ```py
        conversation.add_party(party = party, admin_role = admin_role, save = save)
        ```
        """
        changed: bool = False
        user_id: int = party.user.id
        bot_key: BOT_KEY = party.bot.get_bot_key()
        chat_id: int = party.chat_id

        with self.lock:
            if bot_key not in self.users or user_id not in self.users[bot_key]:
                changed = True

                if bot_key in self.users:
                    self.users[bot_key][chat_id] = party
                else:
                    self.users[bot_key] = {
                        int(chat_id): party
                    }

        if admin_role is not None:
            changed = True

            if admin_role:
                self.admins.add(user_id)
            else:
                self.admins.discard(user_id)

        if changed and save:
            self.save()


    def create_party(self, user: User, bot: BOT, chat_id: int, admin_role: bool = False) -> Conversation.Participant:
        """
        Создаёт party и связывает результат с текущим объектом.

        ### Аргументы:
        :param user: пользователь приложения
        :param bot: transport-адаптер
        :param chat_id: идентификатор чата
        :param admin_role: admin role

        :return: созданный объект: party

        ### Пример использования:
        ```py
        conversation.create_party(user = user, bot = bot, chat_id = chat_id, admin_role = admin_role)
        ```
        """
        party: Conversation.Participant = self.__class__.Participant(user, bot, chat_id)
        self.add_party(party, admin_role = admin_role)
        return party

    def find_party(self, bot_key: BOT_KEY, chat_id: int, admin_role: bool = False) -> Conversation.Participant | None:
        """
        Ищет party в текущих данных объекта или storage.

        ### Аргументы:
        :param bot_key: ключ транспорта
        :param chat_id: идентификатор чата
        :param admin_role: admin role

        :return: party или None, если подходящей записи нет

        ### Пример использования:
        ```py
        conversation.find_party(bot_key = bot_key, chat_id = chat_id, admin_role = admin_role)
        ```
        """
        return self.users.get(bot_key, {}).get(chat_id, None)

    def any_party(self, bot_key: BOT_KEY):
        """
        Проверяет, есть ли в диалоге хотя бы один участник выбранного транспорта.

        ### Аргументы:
        :param bot_key: ключ транспорта

        :return: `True`, если для transport key есть участники; иначе `False`

        ### Пример использования:
        ```py
        conversation.any_party(bot_key = bot_key)
        ```
        """
        return bot_key in self.users and len(self.users[bot_key]) > 0

    def check_attachment(self, attachment: Bot.Attachment) -> bool:
        """
        Проверяет, поддерживается ли переданное вложение transport-адаптером.

        ### Аргументы:
        :param attachment: вложение

        :return: `True`, если поддерживается ли переданное вложение transport-адаптером; иначе `False`

        ### Пример использования:
        ```py
        conversation.check_attachment(attachment = attachment)
        ```
        """
        if isinstance(attachment, Telebot.Attachment):
            if not isinstance(attachment, Telebot.PhotoAttachment):
                if self.any_party("vkbot"):
                    return False
        elif isinstance(attachment, Vkbot.Attachment):
            if self.any_party("telebot"):
                return False
            elif not isinstance(attachment, Vkbot.PhotoAttachment):
                return False
        return True

    def get_footer(self, attachments: list[Bot.Attachment], from_bot_key: BOT_KEY, to_bot_key: BOT_KEY) -> str:
        """
        Возвращает footer для пересылаемого сообщения.

        ### Аргументы:
        :param attachments: вложения
        :param from_bot_key: ключ исходного транспорта
        :param to_bot_key: ключ транспорта получателя

        :return: footer

        ### Пример использования:
        ```py
        conversation.get_footer(attachments = attachments, from_bot_key = from_bot_key, to_bot_key = to_bot_key)
        ```
        """
        footer: str = ""
        failed_attachments: list[Bot.Attachment] = []

        for attachment in attachments:
            if not self.check_attachment(attachment):
                if isinstance(attachment, Vkbot.PhotoAttachment | Telebot.PhotoAttachment):
                    attachment_photo: str = get_phrase("attachment_photo")
                    footer = f"{footer}\n{attachment_photo}"
                elif isinstance(attachment, Vkbot.VideoAttachment | Telebot.VideoAttachment):
                    attachment_video: str = get_phrase("attachment_video")
                    footer = f"{footer}\n{attachment_video}"
                elif isinstance(attachment, Vkbot.AudioAttachment | Telebot.AudioAttachment):
                    attachment_audio: str = get_phrase("attachment_audio")
                    footer = f"{footer}\n{attachment_audio}"
                elif isinstance(attachment, Vkbot.DocAttachment | Telebot.DocAttachment):
                    attachment_doc: str = get_phrase("attachment_doc")
                    footer = f"{footer}\n{attachment_doc}"

                failed_attachments.append(attachment)

        # WARNING: Изменение message.attachments
        for attachment in failed_attachments:
            attachments.remove(attachment)

        return footer

    def join(self, user: User, bot: BOT, chat_id: int, admin_role: bool = False, last_messages: int = 0):
        """
        Меняет состав участников live-диалога и синхронизирует связанные сообщения.

        ### Аргументы:
        :param user: пользователь приложения
        :param bot: transport-адаптер
        :param chat_id: идентификатор чата
        :param admin_role: admin role
        :param last_messages: last messages

        :return: результат выполнения операции

        ### Пример использования:
        ```py
        conversation.join(user = user, bot = bot, chat_id = chat_id, admin_role = admin_role, last_messages = last_messages)
        ```
        """
        def get_header(message: Bot.Message, username: str, owner_id: int, chat_id: int = chat_id):
            header: str
            bot_key: BOT_KEY = bot.get_bot_key()
            username = user.get_username(bot_key)

            if message.forward_messages:
                header = get_phrase("header_forward_messages").format(len(message.forward_messages))
            else:
                header = get_phrase("header_single_message")

            # Сообщение от бота
            if isinstance(message, bot.__class__.Message):
                if owner_id == chat_id:
                    username = get_phrase("sender_is_you")
            elif group:
                username = username.replace("@", group.bot.__class__.URL).replace("_", "%5F")

            date: datetime = message.get_date() or (group and group.date) or datetime.now()
            header_from: str = get_phrase("header_from")

            return f"_{header} {header_from} {username} - ({strftime(date)}):_ \n{message.get_text()}"

        bot_key: BOT_KEY = bot.get_bot_key()
        party: Conversation.Participant = self.find_party(bot_key, chat_id)
        party = party or self.create_party(user, bot, chat_id, admin_role = admin_role)

        get_header = get_header if admin_role else Message.get_header
        groups: list[Message.MessagesGroup] = [] if admin_role else user.get_last_conversation(self.get_bot, bot_key)
        group: Message.MessagesGroup | None = groups[-1] if groups else None
        # for group in groups:

        # for group in self.messages:

        messages: list[Bot.Message] = sum((group.messages for group in groups), [])
        # for message in messages:

        self.message.add_recipient(bot_key, chat_id)

        if last_messages > 0 and not self.messages:
            self.message.messages[bot_key][chat_id].clear()

            for g in groups:
                self.messages.append(g)

            if group and messages:
                self.message.add_group(bot_key, chat_id, Message.MessagesGroup(bot, chat_id, chat_id, messages, group.username, group.date, group.compression))

        removable_messages: list[Bot.Message] = self.message.send_groups(self.messages, bot, chat_id, bot.group_id, messages, get_header = get_header, get_footer = self.get_footer, get_remove_button = self.get_remove_button)
        self.add_removable(removable_messages)
        self.save()

    def join_admin(self, context: Context, username: str, conv_bot_key: BOT_KEY):
        """
        Меняет состав участников live-диалога и синхронизирует связанные сообщения.

        ### Аргументы:
        :param context: контекст обработки события
        :param username: имя пользователя
        :param conv_bot_key: conv bot key

        ### Пример использования:
        ```py
        conversation.join_admin(context = context, username = username, conv_bot_key = conv_bot_key)
        ```
        """
        if conv_bot_key != context.bot.get_bot_key():
            username = username.replace("@", self.get_bot(conv_bot_key).__class__.URL).replace("_", "%5F")

        if self.messages:
            self.send_admin_message(0, context, text = f"_Чат с пользователем {username}:_")
            self.join(context.user, context.bot, context.get_chat_id(), admin_role = True)
            self.send_admin_message(2, context)
        else:
            for i in range(3):
                self.send_admin_message(i, context)

            self.join(context.user, context.bot, context.get_chat_id(), admin_role = True)

    def leave(self, bot_key: BOT_KEY, chat_id: int):
        """
        Меняет состав участников live-диалога и синхронизирует связанные сообщения.

        ### Аргументы:
        :param bot_key: ключ транспорта
        :param chat_id: идентификатор чата

        ### Пример использования:
        ```py
        conversation.leave(bot_key = bot_key, chat_id = chat_id)
        ```
        """
        self.delete_party(bot_key, chat_id)
        self.save()

    def leave_admin(self, bot_key: BOT_KEY, chat_id: int):
        """
        Меняет состав участников live-диалога и синхронизирует связанные сообщения.

        ### Аргументы:
        :param bot_key: ключ транспорта
        :param chat_id: идентификатор чата

        ### Пример использования:
        ```py
        conversation.leave_admin(bot_key = bot_key, chat_id = chat_id)
        ```
        """


        self.message.delete_groups(bot_key, chat_id)
        self.delete_admin_messages(bot_key, chat_id)
        self.leave(bot_key, chat_id)


    """admin_messages"""


    def load_admin_messages(self, data: BotTypes.CONVERSATION_TYPE, username: str | None = None) -> dict[int, Message]:
        """
        Загружает данные из storage или внешнего transport/API и приводит их к объектам проекта.

        ### Аргументы:
        :param data: сериализованный словарь
        :param username: имя пользователя

        :return: результат выполнения операции

        ### Пример использования:
        ```py
        conversation.load_admin_messages(data = data, username = username)
        ```
        """
        result: dict[int, Message] = {}
        messages_data: dict[int, dict] = get_from(data, "admin_messages", types = (dict,), default = {})

        if messages_data:
            for index, message_data in messages_data.items():
                index: int = int(index)
                message: Message = Message.loads(message_data, self.get_bot)
                result[index] = message

        if result:
            return result
        else:
            return {
                0: Message(self.create_message_id(), get_phrase("admin_message_header")
                ) if not username else Message(self.create_message_id(), get_phrase("admin_message_username").format(username)),
                1: Message(self.create_message_id(), get_phrase("admin_message_empty")),
                2: Message(self.create_message_id(), get_phrase("admin_message_footer"), buttons = list(self.buttons))
            }

    def delete_admin_messages(self, bot_key: BOT_KEY, chat_id: int):
        """
        Удаляет admin messages из внутреннего состояния или storage.

        ### Аргументы:
        :param bot_key: ключ транспорта, например `vkbot` или `telebot`
        :param chat_id: идентификатор чата в конкретной платформе

        ### Пример использования:
        ```py
        conversation.delete_admin_messages(bot_key = bot_key, chat_id = chat_id)
        ```
        """
        for index in range(len(self.admin_messages)):
            if index != 1 or not self.messages:
                # try:
                self.admin_messages[index].delete(bot_key, chat_id)
                # except Exception as err:
                #     warn(f"{err.__class__}: {err}")

        self.print_admin_messages()

    def send_admin_message(self, index: int, context: Context, text: str | None = None):
        """
        Отправляет или переотправляет подготовленное сообщение через доступный transport/API.

        ### Аргументы:
        :param index: позиция элемента в списке
        :param context: контекст обработки события
        :param text: текст

        ### Пример использования:
        ```py
        conversation.send_admin_message(index = index, context = context, text = text)
        ```
        """
        chat_id: int = context.get_chat_id()

        if text is not None:
            self.admin_messages[index].set_text(text)

        context.autocenter.catch_message_send(self.admin_messages[index], context.bot, chat_id, parse_mode = MARKDOWN)
        self.print_admin_messages()

    def delete_admin_message(self, index: int):
        """
        Удаляет admin message через доступный слой API или storage.

        ### Аргументы:
        :param index: позиция элемента в списке

        ### Пример использования:
        ```py
        conversation.delete_admin_message(index = index)
        ```
        """


        self.admin_messages[index].delete()
        self.print_admin_messages()

    def resend_admin_message(self, index: int, text: str | None = None):
        """
        Отправляет или переотправляет подготовленное сообщение через доступный transport/API.

        ### Аргументы:
        :param index: позиция элемента в списке
        :param text: текст

        ### Пример использования:
        ```py
        conversation.resend_admin_message(index = index, text = text)
        ```
        """


        if text is not None:
            self.admin_messages[index].set_text(text)

        self.admin_messages[index].resend(parse_mode = MARKDOWN)
        self.print_admin_messages()

    def print_admin_messages(self):
        """
        Отладочный hook для вывода сообщений администраторов.

        ### Пример использования:
        ```py
        conversation.print_admin_messages()
        ```
        """
        return
