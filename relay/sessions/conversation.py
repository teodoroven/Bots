"""
Описывает сессию диалога клиента и администратора.
Модуль относится к архитектурной зоне: прикладной слой `relay`, который связывает пользователей, сессии, доменную модель, GPT, уведомления и runtime-логику приложения.

### Публичные классы
- `ConvSession`: сессия диалога клиента и администратора.

### Публичные функции
- Публичные функции отсутствуют.

### Связи
Используется app-layer сценариями, обработчиками, сессиями и runtime-миксинами для единого пользовательского потока между ботами, GPT и storage.
"""

from __future__ import annotations




from relay.common import BotTypes, abstractmethod
from relay.config import BUTTON_LENGTH, get_phrase
from relay.conversations import Conversation
from .base import Session
from relay.utils import catch_parsefiles
class ConvSession(Session):
    """
    Описывает пользовательскую или административную сессию `ConvSession`.
    Сессия хранит состояние текущего пользовательского сценария, обновляет сообщения и завершает себя через общий session lifecycle.

    ### Поля
    - `find_conv`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `user_id`: идентификатор объекта или связанной сущности, по которому runtime восстанавливает связь между слоями.
    - `bot_key`: хранит ключ транспорта для операций этого объекта.
    - `chat_id`: идентификатор объекта или связанной сущности, по которому runtime восстанавливает связь между слоями.
    - `conv_id`: идентификатор объекта или связанной сущности, по которому runtime восстанавливает связь между слоями.
    - `admin_role`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `admin_notifications`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `message`: хранит wrapper-сообщение для операций этого объекта.

    ### Методы
    - `__init__`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `dumps`: Возвращает JSON-совместимый снимок объекта для storage или callback payload.
    - `find_conv`: Ищет conv по данным, которые пришли из вызывающего слоя.
    - `process`: Передаёт текущий `Context` выбранному обработчику и обновляет `context.handler` по результату.
    - `add_message`: Привязывает wrapper-сообщение к live-диалогу.
    - `update_notifications`: Обновляет уведомления администраторов с учётом текущего состояния объекта.
    - `resend_notifications`: Отправляет или переотправляет подготовленное сообщение через доступный transport/API.

    ### Жизненный цикл
    Создаётся app-layer кодом, участвует в обработке пользовательского события и сохраняет изменённое состояние через существующие runtime/storage механизмы.

    ### Пример использования
    ```py
    session: ConvSession
    ```
    """
    def __init__(self, session_id: int, context: Context, data: dict, message: Message):
        """
        Создаёт session-объект `ConvSession` и сохраняет состояние пользовательского сценария между входящими событиями.

        ### Аргументы:
        :param session_id: идентификатор сессии
        :param context: контекст обработки события
        :param data: сериализованный словарь
        :param message: сообщение проекта или сообщение конкретного транспорта

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        :raises TypeError: если входные или сохранённые данные имеют неподдерживаемый формат

        ### Пример использования:
        ```py
        session = ConvSession(session_id = session_id, context = context, data = data, message = message)
        ```
        """
        super().__init__(session_id, context, data, message)
        self.find_conv = context.autocenter.find_conv

        self.user_id: int = context.user.id
        self.bot_key: BOT_KEY = context.bot.get_bot_key()
        self.chat_id: int = context.get_chat_id()
        self.conv_id: int = get_int(data, -1, "conv_id")
        self.admin_role: bool = bool(data.get("admin_role", False))
        self.admin_notifications: list[Message] = []

        for message_data in data.get("admin_notifications", []):
            with catch_parsefiles(tuple(), "load_conv_notifications"):
                if message_data:
                    if type(message_data) is dict:
                        message: Message = Message.loads(message_data, context.autocenter.get_bot)
                        self.admin_notifications.append(message)
                    else:
                        raise TypeError(f"Ожидался {message_data=} типа dict, а получен {type(message_data)}")

        if self.conv_id < 0:
            raise ValueError(f"Некорректное значение аргумента data['conv_id']={repr(data.get('conv_id'))}")


    def dumps(self) -> BotTypes.SESSION_TYPE:
        """
        Возвращает JSON-совместимый снимок объекта для storage или callback payload.

        :return: JSON-совместимый словарь для сохранения или передачи между слоями

        ### Пример использования:
        ```py
        session.dumps()
        ```
        """
        result: BotTypes.SESSION_TYPE = super().dumps()

        result.update({
            "user_id": int(self.user_id),
            "bot_key": self.bot_key,
            "chat_id": int(self.chat_id),
            "conv_id": int(self.conv_id),
            "admin_role": bool(self.admin_role),
            "admin_notifications": [message.dumps() for message in self.admin_notifications]
        })

        return result

    @abstractmethod
    def find_conv(self, chat_id: int) -> Conversation | None:
        """
        Ищет conv по данным, которые пришли из вызывающего слоя.

        ### Аргументы:
        :param chat_id: идентификатор чата в конкретной платформе

        :return: найденное значение для conv или None, если записи нет

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        session.find_conv(chat_id = chat_id)
        ```
        """

        # FIMXE: возможно переименовать метод в get_conv?

        raise NotImplementedError("Метод find_conv устанавливается в методе __init__")

    def process(self, context: Context):
        """
        Передаёт текущий `Context` выбранному обработчику и обновляет `context.handler` по результату.

        ### Аргументы:
        :param context: контекст обработки события

        ### Пример использования:
        ```py
        session.process(context = context)
        ```
        """


        conv: Conversation | None = self.find_conv(self.conv_id)
        bot_key: BOT_KEY = context.bot.get_bot_key()

        if not conv:
            context.autocenter.send(context, get_phrase("incorrect"))
            context.remove_handler()
            return

        if context.is_callback():
            callback_data: str = context.get_callback_string(2)

            if callback_data == CALLBACK_CLOSEDIALOG:
                chat_id: int = context.get_chat_id()
                conv.leave_admin(bot_key, chat_id)
                return
            elif callback_data == CALLBACK_FINISHDIALOG:
                context.autocenter.finish_conv(conv)
                return
            else:
                context.remove_handler()
                return

            # return

        for attachment in context.event.attachments:
            if not conv.check_attachment(attachment):
                if conv.check_admin(context.user.id):
                    self.show_phrase("cant_send_attachment")
                    return

        self.update_notifications(context)
        conv.add_event(context)
        conv.update()
        conv.delete_admin_message(1)
        conv.resend_admin_message(2, text = get_phrase("admin_message_resend"))
        conv.save()

    def add_message(self, message: Message):
        """
        Привязывает wrapper-сообщение к live-диалогу.

        ### Аргументы:
        :param message: wrapper-сообщение, которое можно отправить, обновить или сохранить

        ### Пример использования:
        ```py
        session.add_message(message = message)
        ```
        """
        self.admin_notifications.append(message)

    def update_notifications(self, context: Context):
        """
        Обновляет уведомления администраторов с учётом текущего состояния объекта.

        ### Аргументы:
        :param context: контекст обработки события с app, bot, user, handler и message

        ### Пример использования:
        ```py
        session.update_notifications(context = context)
        ```
        """
        text: str = cut(context.event.get_text().strip().replace("\n", " "), BUTTON_LENGTH)

        for message in self.admin_notifications:
            message.set_text(f"{message.text}\n- {text}")
            message.edit(prevent_resend = True)

    def resend_notifications(self, bot_key: BOT_KEY, chat_id: int):
        """
        Отправляет или переотправляет подготовленное сообщение через доступный transport/API.

        ### Аргументы:
        :param bot_key: ключ транспорта
        :param chat_id: идентификатор чата

        ### Пример использования:
        ```py
        session.resend_notifications(bot_key = bot_key, chat_id = chat_id)
        ```
        """
        for message in self.admin_notifications:
            if message.check_sent(bot_key, chat_id):
                message.edit(prevent_resend = False)
