"""
Описывает сообщение соответствующего транспортного или wrapper-слоя.
Модуль относится к архитектурной зоне: слой унификации транспортов `bots`, который скрывает различия Telegram и VK за общими объектами сообщений, клавиатур, вложений и событий.

### Публичные классы
- `Message`: модель сообщения или wrapper-сообщения в соответствующем слое.

### Публичные функции
- Публичные функции отсутствуют.

### Связи
Используется транспортным слоем и wrapper-логикой, чтобы app-layer работал с `Message`, `Keyboard`, `Button`, `Attachment` и `Event` без привязки к конкретной соцсети.
"""

from __future__ import annotations


from bots.constants import BOT, MARKDOWN, logger_telegram
from bots.utils.mapping import get_from, get_int
from bots.compat import (
    ATTACHMENTS_FOLDER,
    Any,
    BotTypes,
    Callable,
    Iterable,
    TelebotMessage,
    abspath,
    abstractmethod,
    datetime,
    isfile,
    normpath,
    traceback,
)
from bots.types import Any, BOT_KEY, MESSAGE_TYPE

from bots.base.bindings import Bot
from bots.wrapper.message_group import MessagesGroup

class Message():
    """
    Бизнес-wrapper сообщения, которое может состоять из нескольких
    platform-specific сообщений. Хранит отправленные группы по bot/chat,
    управляет отправкой, редактированием, удалением и событиями как единой сущностью.

    ### Поля
    - `MESSAGE_TYPE`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.
    - `id`: внутренний идентификатор записи или доменного объекта.
    - `text`: текстовое содержимое, которое показывается пользователю, отправляется в GPT или сохраняется в доменной модели.
    - `filenames`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.
    - `buttons`: хранит кнопки клавиатуры для операций этого объекта.
    - `max_width`: ограничение размера, которое защищает transport/API от слишком длинного payload.
    - `inline`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.
    - `messages`: сообщения, которые приложение хранит для обновления интерфейса пользователя.

    ### Методы
    - `loads`: Восстанавливает объект из JSON-совместимого словаря.
    - `__init__`: Создаёт объект и сохраняет данные, нужные transport-layer для отправки, сравнения или восстановления объекта.
    - `dumps`: Возвращает JSON-совместимый снимок объекта для storage или callback payload.
    - `get_header`: Возвращает header из текущего состояния `Message`.
    - `get_footer`: Возвращает footer из текущего состояния `Message`.
    - `get_remove_button`: Возвращает remove button из текущего состояния `Message`.
    - `check_sent`: Проверяет sent перед использованием.
    - `get_remove_callback`: Возвращает remove callback из текущего состояния `Message`.
    - `update_groups`: Обновляет groups с учётом текущего состояния объекта.
    - `send_groups`: Отправляет groups через доступный transport-layer адаптер.

    ### Жизненный цикл
    Экземпляры создаются из конфигурации транспорта, принимают события платформы и отдают app-layer унифицированные wrapper-объекты.

    ### Пример использования
    ```py
    message: Message
    ```
    """
    MESSAGE_TYPE = BotTypes.MESSAGE_WRAPPER_TYPE


    def loads(data: MESSAGE_TYPE, get_bot: Callable) -> Message:
        """
        Восстанавливает объект из JSON-совместимого словаря.

        ### Аргументы:
        :param data: сериализованный словарь
        :param get_bot: get bot

        :return: восстановленный объект или загруженное состояние

        ### Пример использования:
        ```py
        message.loads(data = data, get_bot = get_bot)
        ```
        """
        id: int = get_int(data, -1, "id")

        text: str = get_from(data, "text")
        buttons_list: list[dict[str, str]] = get_from(data, "buttons", types = (list,), default = [])
        buttons: list[Bot.Keyboard.Button] = [Bot.Keyboard.Button.loads(button_data) for button_data in buttons_list]

        max_width: int = get_int(data, -1, "max_width")
        inline: bool = get_from(data, "inline")
        filenames: list[str] = get_from(data, "filenames")

        message: Message = Message(id, text, buttons, max_width, inline, filenames)

        messages: dict[str, dict[int, list["Message.MessagesGroup.GROUP_TYPE"]]] = get_from(data, "messages")
        for bot_key, messages_groups in messages.items():
            for chat_id, groups in messages_groups.items():
                for group in groups:
                    messages_group: Message.MessagesGroup = Message.MessagesGroup.loads(group, get_bot(bot_key))
                    message.add_group(bot_key, messages_group.get_chat_id(), messages_group)

        return message

    def __init__(self, message_id: int, text: str = "", buttons: Iterable[str | Bot.Keyboard.Button] = [], max_width: int = 2, inline: bool = True, filenames: Iterable[str] = []):
        """
        Создаёт wrapper `Message` и сохраняет данные сообщения или события без привязки app-layer к SDK платформы.

        ### Аргументы:
        :param message_id: идентификатор сообщения
        :param text: текст
        :param buttons: кнопки, которые нужно показать пользователю
        :param max_width: максимальная ширина строки кнопок
        :param inline: признак inline-клавиатуры
        :param filenames: имена файлов

        ### Пример использования:
        ```py
        message = Message(message_id = message_id, text = text, buttons = buttons, max_width = max_width, inline = inline, filenames = filenames)
        ```
        """
        self.id: int = -1
        self.text: str = ""
        self.filenames: list[str] = []

        self.buttons: list[Bot.Keyboard.Button] = []
        self.max_width: int = None
        self.inline: bool = None

        self.messages: dict[BOT_KEY, dict[int, list[Message.MessagesGroup]]] = {}
        self.set_id(message_id)
        self.set_text(text)
        self.set_keyboard(buttons, inline = inline, max_width = max_width)
        self.set_filenames(filenames)

    def __repr__(self) -> str:
        id: int = self.id
        text: str = self.text
        filenames: list[str] = self.filenames
        buttons: list[str] = self.buttons
        max_width: int = self.max_width
        inline: bool = self.inline
        messages: str = ""

        for bot_key, groups in self.messages.items():
            messages += f"\n  {bot_key=}"

            for chat_id, groups_list in groups.items():
                messages += f"\n    {chat_id=}"

                for group in groups_list:
                    string: str = repr(group)

                    for s in string.split("\n"):
                        messages += f"\n      {s}"

                messages += f"\n    <"

            messages += f"\n  <<"
        return f"Message({id=} {text=} {filenames=} {buttons=} {inline=} {max_width})[{messages}]"

    def dumps(self) -> MESSAGE_TYPE:
        """
        Возвращает JSON-совместимый снимок объекта для storage или callback payload.

        :return: JSON-совместимый словарь для сохранения или передачи между слоями

        ### Пример использования:
        ```py
        message.dumps()
        ```
        """
        return {
            "id": self.get_id(),
            "text": str(self.text),
            "filenames": [str(filename) for filename in self.filenames],
            "buttons": [button.dumps() for button in self.buttons],
            "max_width": int(self.max_width),
            "inline": bool(self.inline),
            "messages": {
                bot_key: {
                    chat_id: [
                        group.dumps() for group in groups
                    ] for chat_id, groups in messages_groups.items()
                } for bot_key, messages_groups in self.messages.items()
            }
        }

    @abstractmethod
    def get_header(message: Bot.Message, username: str, owner_id: int) -> str:
        """
        Возвращает header wrapper-сообщения из текста исходного transport-сообщения.

        ### Аргументы:
        :param message: transport-сообщение, текст которого станет header
        :param username: имя пользователя, доступное наследникам для форматирования header
        :param owner_id: id владельца сообщения, доступный наследникам для форматирования header

        :return: текст header для пересылки или отображения

        ### Пример использования:
        ```py
        message.get_header(message = message, username = username, owner_id = owner_id)
        ```
        """
        return message.get_text()

    @abstractmethod
    def get_footer(attachments: list[Bot.Attachment], from_bot_key: BOT_KEY, to_bot_key: BOT_KEY) -> str:
        """
        Возвращает footer wrapper-сообщения для набора вложений при переносе между transport-адаптерами.
        Базовая реализация footer не добавляет.

        ### Аргументы:
        :param attachments: вложения исходного сообщения
        :param from_bot_key: transport key исходного сообщения
        :param to_bot_key: transport key получателя

        :return: текст footer или пустая строка

        ### Пример использования:
        ```py
        message.get_footer(attachments = attachments, from_bot_key = from_bot_key, to_bot_key = to_bot_key)
        ```
        """
        return ""

    @abstractmethod
    def get_remove_button(message: Bot.Message) -> Bot.Keyboard.Button:
        """
        Создаёт кнопку удаления для wrapper-сообщения.
        Наследники задают transport-specific callback и внешний вид кнопки.

        ### Аргументы:
        :param message: transport-сообщение, для которого нужна кнопка удаления

        :return: кнопка удаления сообщения

        :raises NotImplementedError: если transport-specific реализация не задана

        ### Пример использования:
        ```py
        message.get_remove_button(message = message)
        ```
        """
        raise NotImplementedError()

    def check_sent(self, bot_key: BOT_KEY, chat_id: int) -> bool:
        """
        Проверяет, есть ли у wrapper-сообщения отправленные группы для указанного транспорта и чата.

        ### Аргументы:
        :param bot_key: ключ транспорта
        :param chat_id: идентификатор чата

        :return: `True`, если для пары `bot_key`/`chat_id` сохранена хотя бы одна группа сообщений; иначе `False`

        ### Пример использования:
        ```py
        message.check_sent(bot_key = bot_key, chat_id = chat_id)
        ```
        """
        if bot_key not in self.messages:
            return False

        if chat_id not in self.messages[bot_key]:
            return False

        for messages_group in self.messages[bot_key][chat_id]:
            existing_messages: list[Bot.Message] = messages_group.messages

            for message in existing_messages:
                if message.was_sent():
                    return True

        return False

    def get_remove_callback(self, message: Bot.Message, bot_key: BOT_KEY, chat_id: int):
        """
        Возвращает callback для кнопки удаления указанного сообщения

        :param message: Сообщение, которое будет удалено по нажатию на кнопку.
        :param bot_key: В какой бот отправляется новое сообщение с кнопкой удаления указанного.
        :param chat_id: Идентификатор пользователя, которому отправляется новое сообщение с кнопкой удаления указанного.
        """
        remove_key: tuple = (bot_key, chat_id, message.get_bot_key(), message.get_owner_id(), message.get_chat_id(), message.get_id())
        return CALLBACK_SEPARATOR.join(tuple(map(str, remove_key)))

    def update_groups(self, groups: Iterable[MessagesGroup], bot: BOT, chat_id: int, owner_id: int, messages: Iterable[Bot.Message] = [], get_header: Callable = get_header, get_footer: Callable = get_footer, get_remove_button: Callable = get_remove_button) -> list[Bot.Message]:
        """
        Получает на вход сообщения в группах (группы могут быть от разных отправителей) и возвращает список сообщений для чата bot, chat_id.
        Функция старается оставить в результате старые сообщения из аргумента messages. Если список пуст, то все сообщения будут новыми.
        - Одинаковые сообщения (bot_key, owner_id, chat_id) будут оставлены без изменений (или отредактированы, если сообщения отличаются compare(text, attachments, forward, reply)).
        - Сообщения из той же соцсети (bot_key) будут пересланы через forward группами из подряд идущих сообщений (даже из разных групп массива `groups`), но могут быть разделены следующей категорией:
        - Остальные сообщения будут отправлены как новые.

        :param groups: Группы с сообщениями из чата, которые нужно будет отправить.
        :param bot: Бот, через который нужно будет отправить сообщения.
        :param chat_id: Чат, в который нужно будет отправить сообщения.
        :param owner_id: Идентификатор группы (бота), от лица которого нужно будет отправить сообщения.
        :param messages: Сообщения, которые уже есть в чате и их можно использовать для редактирования, чтобы не отправлять новые.
        :param get_header: Функция должна принимать аргументы (message: Bot.Message, username: str, owner_id: int) и возвращать новый текст сообщения str, текст будет заменён у новых сообщений, отредактированных и у заголовка пересланных сообщений, сообщения оставленные без изменений не будут отредактированы.
        :param get_footer: Функция должна принимать аргументы (attachments: list[Bot.Attachment], from_bot_key: BOT_KEY, to_bot_key: BOT_KEY) и возвращать дополниение к тексту сообщения str, текст будет добавлен к новым сообщениям, отредактированным и к заголовкам пересланных сообщений.
        :param get_remove_button: Функция должна принимать аргументы (message: Bot.Message) и возвращать кнопку `Bot.Keyboard.Button` с `callback_data`.
        """
        old_messages = list(messages)
        messages_list: list[Bot.Message] = []
        forward_list: list[tuple[Bot.Message, str, int]] = []

        to_bot_key: BOT_KEY = bot.get_bot_key()

        def chain_broken():
            """
            Цепочка подряд идущих сообщений распалась.
            При разделении группы на сообщения, функция старается оставить уже имеющиеся в чате сообщения либо без изменений, либо отредактировать их, чтобы не отправлять новые сообщения.
            """
            old_messages.clear()

        def forward():
            """
            Формирует результирующий список, добавляя туда пересылаемые сообщения с подписью.
            """
            if forward_list:
                username: str = ""
                owner_id: int = -1
                forward_messages: list[Bot.Message] = []

                for mes, username, owner_id_ in forward_list:
                    forward_messages.append(mes)

                message: Bot.Message = bot.__class__.Message(bot.bot, owner_id, "", forward = forward_messages)
                message.set_text(get_header(message, username, owner_id))
                messages_list.append(message)
                forward_list.clear()

        def add_forward(message: Bot.Message, username: str, owner_id: int):
            """
            Формирует список сообщений для пересылки, но не добавляет их в результирующий список.

            :param username: Отправитель сообщения берётся из группы.
            :param owner_id: Отправитель сообщения берётся из группы.
            """
            forward_list.append((message, username, owner_id))

        def add_message(new_message: Bot.Message, username: str, owner_id: int, from_bot_key: BOT_KEY, old_mes: Bot.Message | None = None):
            """
            Формирует результирующий список на основе существующих сообщений.
            Если цепочка распадётся, то следующие сообщения будут только новыми (пересланными или созданными).
            Цепочка распадается если встречается сообщение, которое нельзя отредактировать или оставить без изменений.

            :param username: Отправитель сообщения берётся из группы.
            :param owner_id: Отправитель сообщения берётся из группы.
            """

            if len(messages_list) < len(old_messages):
                old_message: Bot.Message = old_messages[len(messages_list)]
                old_mes = old_message

                if isinstance(old_message, bot.__class__.Message):
                    if old_message.get_owner_id() in (owner_id, new_message.get_owner_id()):
                        if old_message.was_sent() and old_message.get_chat_id() == chat_id:
                            if old_message.compare(new_message):
                                messages_list.append(old_message)
                                return
                            elif old_message.check_editable():

                                if old_message.get_text() != new_message.get_text():
                                    old_message.set_text(get_header(new_message, username, owner_id))

                                if old_message.get_keyboard() != new_message.get_keyboard():
                                    old_message.set_keyboard(new_message.keyboard)

                                messages_list.append(old_message)
                                return

                    #     else:
                    # else:

                    chain_broken()

                    if old_message.check_editable():
                        add_forward(old_message, username, owner_id)
                        return

            chain_broken()
            # forward()
            header: str = get_header(new_message, group.username, group.owner_id)

            if header != new_message.text and old_mes:
                keyboard: Bot.Keyboard = bot.__class__.Keyboard([
                    get_remove_button(old_mes)
                ], max_width = 2, inline = True)
                new_message.set_keyboard(keyboard)
            else:
                new_message.clear_keyboard()

            new_message.set_text(header)
            messages_list.append(new_message)

        i = 10
        for group in groups:
            from_bot_key: BOT_KEY = group.bot.get_bot_key()

            for message in group.messages:
                attachments_list: list[Bot.Attachment] = list(message.attachments)
                footer: str = ""

                if from_bot_key != to_bot_key:
                    footer = get_footer(attachments_list, from_bot_key, to_bot_key)

                text: str = message.get_text() + footer
                keyboard: Bot.Keyboard | None = None

                if message.keyboard:
                    buttons: list[Bot.Keyboard.Button] = []

                    for button in message.keyboard.buttons:
                        # Дублируем кнопки для отслеживания ответов бота, но кнопки не кликабельны
                        buttons.append(bot.__class__.Keyboard.Button(button.get_text(), callback_data = ""))

                    keyboard: Bot.Keyboard = bot.__class__.Keyboard(buttons, max_width = message.keyboard.max_width, inline = message.keyboard.inline)

                attachments: list[Bot.Attachment] = []

                for mes_att in attachments_list:
                    attachment: Vkbot.PhotoAttachment | Vkbot.VideoAttachment | Vkbot.AudioAttachment | Vkbot.DocAttachment | Telebot.PhotoAttachment | Telebot.VideoAttachment | Telebot.AudioAttachment | Telebot.DocAttachment = mes_att

                    if bot.__class__.check_attachment(attachment):
                        attachments.append(attachment)
                    else:
                        # here
                        try:
                            filename: str = attachment.make_filename(group.bot, ATTACHMENTS_FOLDER)
                        except Exception as err:
                            logger_telegram.exception(err)
                            exc_type, exc_value, exc_traceback = sys.exc_info()
                            formatted_traceback: list[str] = traceback.format_exception(exc_type, exc_value, exc_traceback)

                            try:
                                dumps = mes_att.dumps()
                            except Exception as err:
                                dumps = err

                            try:
                                bot_key = bot.get_bot_key()
                            except Exception as err:
                                bot_key = err

                            logger_telegram.error(
                                "Ошибка при отправке вложения %s получателю bot_key=%s chat_id=%s dumps=%s\n%s",
                                mes_att,
                                bot_key,
                                chat_id,
                                dumps,
                                "".join(formatted_traceback),
                            )
                        else:
                            att = bot.get_attachment(filename, compression = True)
                            attachments.append(att)

                new_message: Bot.Message = bot.__class__.Message(bot.bot, owner_id, text, keyboard = keyboard, attachments = attachments)

                old_mes: Bot.Message | None = None

                if len(group.messages) == 1:
                    old_mes = group.messages[0]

                    if not old_mes.check_editable():
                        old_mes = None

                add_message(new_message, group.username, group.owner_id, group.bot.get_bot_key(), old_mes = old_mes)

        # forward()
        return messages_list

    def send_groups(self, groups: Iterable[MessagesGroup], bot: BOT, chat_id: int, owner_id: int, messages: Iterable[Bot.Mesage] = [], compression: bool = True, get_header: Callable = get_header, get_footer: Callable = get_footer, get_remove_button: Callable = get_remove_button):
        """
        Получает на вход сообщения в группах (группы могут быть от разных отправителей) и отправляет список сообщений для чата bot, chat_id.
        Функция старается оставить в результате старые сообщения из аргумента messages. Если список пуст, то все сообщения будут новыми.
        - Одинаковые сообщения (bot_key, owner_id, chat_id) будут оставлены без изменений (или отредактированы, если сообщения отличаются compare(text, attachments, forward, reply)).
        - Сообщения из той же соцсети (bot_key) будут пересланы через forward группами из подряд идущих сообщений (даже из разных групп массива `groups`), но могут быть разделены следующей категорией:
        - Остальные сообщения будут отправлены как новые.

        :param groups: Группы с сообщениями из чата, которые нужно отправить.
        :param bot: Бот, через который нужно отправить сообщения.
        :param chat_id: Чат, в который нужно отправить сообщения.
        :param owner_id: Идентификатор группы (бота), от лица которого нужно отправить сообщения.
        :param messages: Сообщения, которые уже есть в чате и их можно использовать для редактирования, чтобы не отправлять новые.
        :param get_header: Функция должна принимать аргументы (message: Bot.Message, username: str, owner_id: int) и возвращать новый текст сообщения str, текст будет заменён у новых сообщений, отредактированных и у заголовка пересланных сообщений, сообщения оставленные без изменений не будут отредактированы.
        :param get_footer: Функция должна принимать аргументы (attachments: list[Bot.Attachment], from_bot_key: BOT_KEY, to_bot_key: BOT_KEY) и возвращать дополниение к тексту сообщения str, текст будет добавлен к новым сообщениям, отредактированным и к заголовкам пересланных сообщений.
        :param get_remove_button: Функция должна принимать аргументы (message: Bot.Message) и возвращать кнопку `Bot.Keyboard.Button` с `callback_data`.
        """
        # Получаем цепочку сообщений
        messages: list[Bot.Message] = self.update_groups(groups, bot, chat_id, owner_id, messages = messages, get_header = get_header, get_footer = get_footer, get_remove_button = get_remove_button)
        messages_list: list[Bot.Message] = []
        username: str = ""
        removable_messages: list[Bot.Message] = []

        # Отправляем сообщения и сохраняем ответ сервера
        for message in messages:
            kwargs: dict[str, bool] = {}

            if isinstance(message, Telebot.Message):
                kwargs["forward_after"] = True
                kwargs["parse_mode"] = MARKDOWN
            elif isinstance(message, Vkbot.Message):
                kwargs["parse_mode"] = MARKDOWN

            was_sent: bool = message.was_sent()

            if not message.was_sent():
                responses: dict[str, TelebotMessage] | None = message.send(chat_id, **kwargs)

                # Отправка одного сообщения ничего не вернёт
                # Но отправка группы вложений вернёт сразу несколько событий, которые надо обработать
                if responses:
                    parsed: list[Telebot.Message] = bot.parse_responses(responses, datetime.now(), bot.group_id)

                    if parsed:
                        username = parsed[0].get_username()
                        messages_list += parsed
                    else:
                        username = message.get_username()
                        messages_list.append(message)
                else:
                    username = message.get_username()
                    messages_list.append(message)

                if message.get_remove_callback():
                    removable_messages.append(message)

        # for message in messages_list:

        # Сохраняем сообщения для редактирования в дальнейшем
        self.add_messages(bot, chat_id, bot.group_id, messages_list, compression, username, datetime.now())

        bot_key: BOT_KEY = bot.get_bot_key()
        # for group in self.messages[bot_key][chat_id]:
        return removable_messages

    def get_groups(self, bot_key: BOT_KEY, chat_id: int) -> list[Message.MessagesGroup]:
        """
        Возвращает сохранённые группы transport-сообщений для указанного транспорта и чата.

        ### Аргументы:
        :param bot_key: ключ транспорта
        :param chat_id: идентификатор чата

        :return: группы сообщений, созданные при отправке этого wrapper-сообщения

        :raises RuntimeError: если wrapper-сообщение ещё не отправлялось в указанный транспорт или чат

        ### Пример использования:
        ```py
        message.get_groups(bot_key = bot_key, chat_id = chat_id)
        ```
        """
        if bot_key in self.messages and chat_id in self.messages[bot_key] and self.messages[bot_key][chat_id]:
            return self.messages[bot_key][chat_id]
        else:
            raise RuntimeError(f"Сообщение не было отправлено на адрес {chat_id=}. Перед редактированием сначала отправьте его.")

    def edit_groups(self, groups: Iterable[MessagesGroup], get_header: Callable = get_header, get_footer: Callable = get_footer, get_remove_button: Callable = get_remove_button):
        """
        Получает на вход сообщения в группах (группы могут быть от разных отправителей) и обновляет сообщения во всех чатах.
        Функция старается оставить в результате старые сообщения (которые уже есть в чате), сохранённые после вызова метода send_groups.
        - Одинаковые сообщения (bot_key, owner_id, chat_id) будут оставлены без изменений (или отредактированы, если сообщения отличаются compare(text, attachments, forward, reply)).
        - Сообщения из той же соцсети (bot_key) будут пересланы через forward группами из подряд идущих сообщений (даже из разных групп массива `groups`), но могут быть разделены следующей категорией:
        - Остальные сообщения будут отправлены как новые.

        :param groups: Группы с сообщениями из чата, которые нужно отправить.
        :param get_header: Функция должна принимать аргументы (message: Bot.Message, username: str, owner_id: int) и возвращать новый текст сообщения str, текст будет заменён у новых сообщений, отредактированных и у заголовка пересланных сообщений, сообщения оставленные без изменений не будут отредактированы.
        :param get_footer: Функция должна принимать аргументы (attachments: list[Bot.Attachment], from_bot_key: BOT_KEY, to_bot_key: BOT_KEY) и возвращать дополниение к тексту сообщения str, текст будет добавлен к новым сообщениям, отредактированным и к заголовкам пересланных сообщений.
        :param get_remove_button: Функция должна принимать аргументы (message: Bot.Message) и возвращать кнопку `Bot.Keyboard.Button` с `callback_data`.
        """
        removable_messages: list[Bot.Message] = []

        for bot_key in self.messages:
            for chat_id in self.messages[bot_key]:
                messages_group: Message.MessagesGroup = self.get_last_group(bot_key, chat_id)
                bot: BOT = messages_group.bot
                compression: bool = messages_group.compression
                existing_messages: list[Bot.Message] = []

                for group in self.get_groups(bot_key, chat_id):
                    existing_messages += group.messages

                expected_messages: list[Bot.Message] = self.update_groups(groups, bot, chat_id, bot.group_id, messages = existing_messages, get_header = get_header, get_footer = get_footer, get_remove_button = get_remove_button)
                result_messages: list[Bot.Message] = []

                for message in expected_messages:
                    responses: dict[str, TelebotMessage] | None = None

                    was_sent = message.was_sent()
                    was_changed = message.was_changed()
                    check_editable = message.check_editable()

                    if message.get_text().strip() or message.get_attachments():
                        if message.check_editable():
                            if message.was_changed():
                                responses = message.edit()
                            # else:
                        elif was_sent and (not was_changed) and (not check_editable) and chat_id == message.get_owner_id():
                            pass
                        else:
                            responses = message.send(chat_id)

                    if responses:
                        parsed: list[Telebot.Message] = bot.parse_responses(responses, datetime.now(), bot.group_id)

                        if parsed:
                            result_messages += parsed
                        else:
                            result_messages.append(message)
                    else:
                        result_messages.append(message)

                    if message.get_remove_callback():
                        removable_messages.append(message)

                # for message in messages_group.messages:

                all_messages: list[Bot.Message] = messages_group.messages + result_messages
                result_messages = []

                for message in all_messages:
                    if message not in result_messages:
                        if message.chat_id is not None:
                            result_messages.append(message)

                result_messages.sort(key = lambda message: message.get_date("SENT") or message.get_date("MESSAGE_NEW"))

                messages_group.messages = result_messages

                # for message in result_messages:

                self.messages[bot_key][chat_id] = [messages_group]

                # bot_key: BOT_KEY = bot.get_bot_key()
                # for group in self.messages[bot_key][chat_id]:
        return removable_messages

    def delete_groups(self, bot_key_filter: str | Any = Any, chat_id_filter: int | Any = Any):
        """
        Удаляет groups через доступный слой API или storage.

        ### Аргументы:
        :param bot_key_filter: bot key filter
        :param chat_id_filter: chat id filter

        ### Пример использования:
        ```py
        message.delete_groups(bot_key_filter = bot_key_filter, chat_id_filter = chat_id_filter)
        ```
        """
        deleting: list[tuple[str, int]] = []

        for bot_key in self.messages:
            if bot_key_filter is Any or bot_key == bot_key_filter:
                for chat_id in self.messages[bot_key]:
                    if chat_id_filter is Any or chat_id == chat_id_filter:
                        messages_group: Message.MessagesGroup = self.get_last_group(bot_key, chat_id)

                        for message in messages_group.messages:
                            try:
                                if message.check_editable():
                                    message.delete()
                            except ValueError as err:
                                logger_telegram.exception(f"delete_groups {bot_key_filter=} {chat_id_filter=} {err=}")

                        deleting.append((bot_key, chat_id))

        for bot_key, chat_id in deleting:
            del self.messages[bot_key][chat_id]


    def update(self, bot: BOT, messages: list[Bot.Message], compression: bool = True) -> list[Bot.Message]:
        """
        Синхронизирует данные сценария с уже отправленными UI-сообщениями.

        ### Аргументы:
        :param bot: transport-адаптер
        :param messages: сообщения или группы сообщений для обработки
        :param compression: признак сжатия вложения

        :return: список transport-сообщений после синхронизации группы

        ### Пример использования:
        ```py
        message.update(bot = bot, messages = messages, compression = compression)
        ```
        """
        attachments: list[Bot.Attachment] = bot.get_attachments(self.filenames, compression = compression)
        old_messages: list[Bot.Message] = list(messages)
        new_messages: list[Bot.Message] = bot.split(self.text, self.buttons, attachments, max_width = self.max_width, inline = self.inline, reply = None, forward = [])
        messages_list: list[Bot.Message] = bot.get_matches(old_messages, new_messages)

        # Удаляем лишние сообщения
        for message in old_messages:
            if message not in messages_list:
                message.delete()

        # Редактируем оставшиеся сообщения
        for i, old_message in enumerate(messages_list):
            new_message: Bot.Message = new_messages[i]

            if old_message.get_text() != new_message.get_text():
                old_message.set_text(new_message.get_text())

            if old_message.get_keyboard() != new_message.get_keyboard():
                old_message.set_keyboard(new_message.keyboard)

        # Добавляем новые сообщения
        return messages_list + new_messages[len(messages_list):]

    def send(self, bot: BOT, chat_id: int, compression: bool = True, parse_mode: str = ""):
        """
        Отправляет сообщение или вложение через transport-layer.

        ### Аргументы:
        :param bot: transport-адаптер
        :param chat_id: идентификатор чата
        :param compression: признак сжатия вложения
        :param parse_mode: режим разметки сообщения

        ### Пример использования:
        ```py
        message.send(bot = bot, chat_id = chat_id, compression = compression, parse_mode = parse_mode)
        ```
        """
        username: str = ""

        # Получаем цепочку сообщений
        messages: list[Bot.Message] = self.update(bot, messages = [], compression = compression)
        messages_list: list[Bot.Message] = []

        # Отправляем сообщения и сохраняем ответ сервера
        for message in messages:
            message: Vkbot.Message | Telebot.Message
            responses: dict[str, TelebotMessage] | None = message.send(chat_id, parse_mode = parse_mode)

            # Отправка одного сообщения ничего не вернёт
            # Но отправка группы вложений вернёт сразу несколько событий, которые надо обработать
            if responses:
                parsed: list[Telebot.Message] = bot.parse_responses(responses, datetime.now(), bot.group_id)

                if parsed:
                    username = parsed[0].get_username()
                    messages_list += parsed
                else:
                    username = message.get_username()
                    messages_list.append(message)
            else:
                username = message.get_username()
                messages_list.append(message)

            message.set_owner_id(bot.group_id)

        # Сохраняем сообщения для редактирования в дальнейшем
        self.add_messages(bot, chat_id, bot.group_id, messages_list, compression, username, datetime.now())

    def edit(self, force_resend: bool = False, prevent_resend: bool = False):
        """
        Обновляет уже отправленное сообщение, если транспорт позволяет редактирование.

        ### Аргументы:
        :param force_resend: force resend
        :param prevent_resend: prevent resend

        ### Пример использования:
        ```py
        message.edit(force_resend = force_resend, prevent_resend = prevent_resend)
        ```
        """
        for bot_key in self.messages:
            for chat_id in self.messages[bot_key]:
                messages_group: Message.MessagesGroup = self.get_last_group(bot_key, chat_id)
                bot: BOT = messages_group.bot
                compression: bool = messages_group.compression
                existing_messages: list[Bot.Message] = messages_group.messages
                expected_messages: list[Bot.Message] = self.update(bot, messages = existing_messages, compression = compression)
                result_messages: list[Bot.Message] = []

                for message in expected_messages:
                    responses: dict[str, TelebotMessage] | None = None

                    if message.check_editable():
                        if force_resend:
                            message.delete()
                            responses = message.send(chat_id)
                        elif message.was_changed():
                            responses = message.edit(prevent_resend = prevent_resend)
                    else:
                        responses = message.send(chat_id)

                    if responses:
                        parsed: list[Telebot.Message] = bot.parse_responses(responses, datetime.now(), bot.group_id)

                        if parsed:
                            result_messages += parsed
                        else:
                            result_messages.append(message)
                    else:
                        result_messages.append(message)

                messages_group.messages = result_messages

    def delete(self, bot_key_filter: str | Any = Any, chat_id_filter: int | Any = Any):
        """
        Удаляет отправленное сообщение через transport-layer.

        ### Аргументы:
        :param bot_key_filter: bot key filter
        :param chat_id_filter: chat id filter

        ### Пример использования:
        ```py
        message.delete(bot_key_filter = bot_key_filter, chat_id_filter = chat_id_filter)
        ```
        """
        deleting: dict[str, list[int]] = {}

        for bot_key in self.messages:
            if bot_key_filter is Any or bot_key == bot_key_filter:
                for chat_id in self.messages[bot_key]:
                    if chat_id_filter is Any or chat_id == chat_id_filter:
                        messages_group: Message.MessagesGroup = self.get_last_group(bot_key, chat_id)
                        for message in messages_group.messages:
                            if message.check_editable():
                                message.delete()

                                if bot_key in deleting:
                                    deleting[bot_key].append(chat_id)
                                else:
                                    deleting[bot_key] = [chat_id]

        for bot_key, chat_ids in deleting.items():
            for chat_id in chat_ids:
                del self.messages[bot_key][chat_id]


    def resend(self, parse_mode: str = ""):
        """
        Отправляет или переотправляет подготовленное сообщение через доступный transport/API.

        ### Аргументы:
        :param parse_mode: режим разметки сообщения

        ### Пример использования:
        ```py
        message.resend(parse_mode = parse_mode)
        ```
        """
        recipients: dict[str, dict[int, BOT]] = {}

        for bot_key, chat_ids in self.messages.items():
            for chat_id, groups in chat_ids.items():
                if groups:
                    bot: BOT = groups[-1].bot

                    if bot_key in recipients:
                        recipients[bot_key][chat_id] = bot
                    else:
                        recipients[bot_key] = {chat_id: bot}

        self.delete()
        self.messages.clear()

        for bot_key, bots in recipients.items():
            for chat_id, bot in bots.items():
                self.send(bot, chat_id, parse_mode = parse_mode)

    def was_sent(self, bot_key: BOT_KEY, chat_id: int) -> bool:
        """
        Проверяет, есть ли у wrapper-сообщения данные об успешной отправке.

        ### Аргументы:
        :param bot_key: ключ транспорта
        :param chat_id: идентификатор чата

        :return: `True`, если есть ли у wrapper-сообщения данные об успешной отправке; иначе `False`

        ### Пример использования:
        ```py
        message.was_sent(bot_key = bot_key, chat_id = chat_id)
        ```
        """
        return bot_key in self.messages and chat_id in self.messages[bot_key]

    # Методы работы с полями

    def check_id(self, message_id: int) -> bool:
        """
        Проверяет допустимость идентификатора.

        ### Аргументы:
        :param message_id: идентификатор сообщения

        :return: `True`, если допустимость идентификатора; иначе `False`

        ### Пример использования:
        ```py
        message.check_id(message_id = message_id)
        ```
        """
        return isinstance(message_id, int) and message_id >= 0

    def set_id(self, message_id: int):
        """
        Проверяет и сохраняет идентификатор в объекте.

        ### Аргументы:
        :param message_id: идентификатор сообщения

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        message.set_id(message_id = message_id)
        ```
        """
        if self.check_id(message_id):
            self.id = message_id
        else:
            raise ValueError(f"Некорректное значение аргумента {message_id=}")

    def get_id(self) -> int:
        """
        Возвращает сохранённый идентификатор объекта.

        :return: идентификатор текущего объекта

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        message.get_id()
        ```
        """
        if self.check_id(self.id):
            return self.id
        else:
            raise ValueError(f"Некорректное значение атрибута {self.id=}")


    def set_text(self, text: str):
        """
        Проверяет и сохраняет значение `text` в `Message`.

        ### Аргументы:
        :param text: текст сообщения или пользовательского ввода

        ### Пример использования:
        ```py
        message.set_text(text = text)
        ```
        """
        self.text = text


    def add_recipient(self, bot_key: BOT_KEY, chat_id: int):
        """
        Регистрирует получателя wrapper-сообщения.

        ### Аргументы:
        :param bot_key: ключ транспорта, например `vkbot` или `telebot`
        :param chat_id: идентификатор чата в конкретной платформе

        ### Пример использования:
        ```py
        message.add_recipient(bot_key = bot_key, chat_id = chat_id)
        ```
        """
        bot_key: BOT_KEY = str(bot_key)
        chat_id: int = int(chat_id)

        if bot_key not in self.messages:
            self.messages[bot_key] = {}

        if chat_id not in self.messages[bot_key]:
            self.messages[bot_key][chat_id] = []

    def add_group(self, bot_key: BOT_KEY, chat_id: int, messages_group: MessagesGroup):
        """
        Добавляет группу отправленных transport-сообщений.

        ### Аргументы:
        :param bot_key: ключ транспорта
        :param chat_id: идентификатор чата
        :param messages_group: messages group

        :raises TypeError: если входные или сохранённые данные имеют неподдерживаемый формат

        ### Пример использования:
        ```py
        message.add_group(bot_key = bot_key, chat_id = chat_id, messages_group = messages_group)
        ```
        """
        self.add_recipient(bot_key, chat_id)


        if isinstance(messages_group, self.__class__.MessagesGroup):
            self.messages[bot_key][chat_id].append(messages_group)
        else:
            raise TypeError(f"Некорректное значение аргумента {messages_group=}")

    def add_messages(self, bot: BOT, chat_id: int, owner_id: int, messages: Iterable[Bot.Message], compression: bool, username: str, date: datetime):
        """
        Добавляет отправленные transport-сообщения в wrapper-группу.

        ### Аргументы:
        :param bot: transport-адаптер
        :param chat_id: идентификатор чата
        :param owner_id: идентификатор владельца сообщения
        :param messages: сообщения или группы сообщений для обработки
        :param compression: признак сжатия вложения
        :param username: имя пользователя
        :param date: время сообщения или события

        :return: созданная `MessagesGroup`, добавленная в wrapper-сообщение

        ### Пример использования:
        ```py
        message.add_messages(bot = bot, chat_id = chat_id, owner_id = owner_id, messages = messages, compression = compression, username = username, date = date)
        ```
        """
        messages_group = self.__class__.MessagesGroup(bot, chat_id, owner_id, messages, username, date, compression)
        bot_key: BOT_KEY = bot.get_bot_key()
        return self.add_group(bot_key, chat_id, messages_group)

    def has_groups(self, bot_key: BOT_KEY, chat_id: int) -> bool:
        """
        Проверяет наличие groups.

        ### Аргументы:
        :param bot_key: ключ транспорта
        :param chat_id: идентификатор чата

        :return: `True`, если наличие groups; иначе `False`

        ### Пример использования:
        ```py
        message.has_groups(bot_key = bot_key, chat_id = chat_id)
        ```
        """
        return bot_key in self.messages and chat_id in self.messages[bot_key] and self.messages[bot_key][chat_id]

    def get_last_group(self, bot_key: BOT_KEY, chat_id: int) -> Message.MessagesGroup:
        """
        Возвращает последнюю отправленную группу сообщений для bot/chat.

        ### Аргументы:
        :param bot_key: ключ транспорта
        :param chat_id: идентификатор чата

        :return: last group

        :raises RuntimeError: если объект ещё не связан с необходимым runtime-состоянием

        ### Пример использования:
        ```py
        message.get_last_group(bot_key = bot_key, chat_id = chat_id)
        ```
        """
        if bot_key in self.messages and chat_id in self.messages[bot_key] and self.messages[bot_key][chat_id]:
            return self.messages[bot_key][chat_id][-1]
        else:
            raise RuntimeError(f"Сообщение не было отправлено на адрес {chat_id=}. Перед редактированием сначала отправьте его.")

    def set_filenames(self, filenames: Iterable[str]):
        """
        Проверяет и сохраняет имена файлов в объекте.

        ### Аргументы:
        :param filenames: имена файлов

        :raises FileNotFoundError: если нижележащий слой сообщает об ошибке операции

        ### Пример использования:
        ```py
        message.set_filenames(filenames = filenames)
        ```
        """
        self.filenames.clear()

        for filename in filenames:
            filename = abspath(normpath(str(filename)))
            if isfile(filename):
                self.filenames.append(filename)
            else:
                raise FileNotFoundError(filename)


    def check_keyboard(self, buttons: Iterable[str | Bot.Keyboard.Button], max_width: int, inline: bool) -> bool:
        """
        Проверяет допустимость клавиатуры сообщения.

        ### Аргументы:
        :param buttons: кнопки, которые нужно показать пользователю
        :param max_width: максимальная ширина строки кнопок
        :param inline: признак inline-клавиатуры

        :return: `True`, если допустимость клавиатуры сообщения; иначе `False`

        ### Пример использования:
        ```py
        message.check_keyboard(buttons = buttons, max_width = max_width, inline = inline)
        ```
        """
        if not isinstance(inline, bool):
            return False

        if (not isinstance(max_width, int)) or max_width < 1:
            return False

        return all(buttons, lambda button: isinstance(button, str) or isinstance(button, Bot.Keyboard.Button))

    def get_keyboard(self, bot: BOT, buttons: Iterable[str | Bot.Keyboard.Button]) -> Bot.Keyboard:
        """
        Возвращает сохранённую клавиатуру сообщения.

        ### Аргументы:
        :param bot: transport-адаптер
        :param buttons: кнопки, которые нужно показать пользователю

        :return: клавиатура сообщения

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        message.get_keyboard(bot = bot, buttons = buttons)
        ```
        """
        if not isinstance(self.inline, bool):
            raise ValueError(f"Некорректное значение атрибута {self.inline=}")
        elif (not isinstance(self.max_width, int)) or self.max_width < 1:
            raise ValueError(f"Некорректное значение атрибута {self.max_width=}")
        else:
            buttons_list: list[Bot.Keyboard.Button] = []

            for button in buttons:
                if isinstance(button, Bot.Keyboard.Button):
                    pass
                elif isinstance(button, str):
                    button: Bot.Keyboard.Button = bot.__class__.Keyboard.Button(button)
                else:
                    raise ValueError(f"Некорректное значение атрибута {self.buttons=}")

                buttons_list.append(button)

            return bot.__class__.Keyboard(buttons_list, max_width = self.max_width, inline = self.inline)

    def set_keyboard(self, buttons: Iterable[str | Bot.Keyboard.Button] = [], inline: bool | None = None, max_width: int | None = None):
        """
        Проверяет и сохраняет клавиатура в объекте.

        ### Аргументы:
        :param buttons: кнопки, которые нужно показать пользователю
        :param inline: признак inline-клавиатуры
        :param max_width: максимальная ширина строки кнопок

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        message.set_keyboard(buttons = buttons, inline = inline, max_width = max_width)
        ```
        """
        if inline is None:
            inline = self.inline

        if max_width is None:
            max_width = self.max_width

        if not isinstance(inline, bool):
            raise ValueError(f"Некорректное значение аргумента {inline=}")
        elif (not isinstance(max_width, int)) or max_width < 1:
            raise ValueError(f"Некорректное значение аргумента {max_width=}")
        elif not all(isinstance(button, str) or isinstance(button, Bot.Keyboard.Button) for button in buttons):
            raise ValueError(f"Некорректное значение аргумента {buttons=}")
        else:
            self.buttons = [Bot.Keyboard.Button(button) if isinstance(button, str) else button for button in buttons]
            self.max_width = int(max_width)
            self.inline = bool(inline)

    def get_last(self) -> tuple[BOT_KEY, datetime] | None:
        """
        Возвращает последнюю сохранённую группу сообщений.

        :return: last

        ### Пример использования:
        ```py
        message.get_last()
        ```
        """
        dates: dict[BOT_KEY, list[datetime]] = {
            "vkbot": [],
            "telebot": []
        }

        for bot_key, groups in self.messages.items():
            if groups:
                group: Message.MessagesGroup = groups[-1]

                if group.messages:
                    for message in group.messages:
                        for key in Bot.BaseMessage.KEYS:
                            date: datetime | None = message.get_date(key)

                            if date:
                                if bot_key in dates:
                                    dates[bot_key].append(date)
                                else:
                                    dates[bot_key] = [date]

        if len(dates) == 1:
            bot_key: BOT_KEY = tuple(dates.keys())[0]
            return (bot_key, max(dates[bot_key]))
        elif not dates:
            return None

        max_date: datetime | None = None
        result: BOT_KEY | None = None

        for bot_key, dates_list in dates.items():
            date: datetime = max(dates_list)

            if max_date is None or date > max_date:
                max_date = date
                result = bot_key

        return (result, max_date)
