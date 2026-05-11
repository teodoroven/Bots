"""
Описывает базовые сущности модуля.
Модуль относится к архитектурной зоне: прикладной слой `relay`, который связывает пользователей, сессии, доменную модель, GPT, уведомления и runtime-логику приложения.

### Публичные классы
- `Session`: базовая пользовательская сессия.
- `Menu`: управление сообщением меню.
- `Input`: интерактивный ввод меню.
- `MenuInput`: input меню с callback-навигацией.
- `MenuSession`: базовая меню-сессия.

### Публичные функции
- Публичные функции отсутствуют.

### Связи
Используется app-layer сценариями, обработчиками, сессиями и runtime-миксинами для единого пользовательского потока между ботами, GPT и storage.
"""

from __future__ import annotations


from relay.common import BotTypes, Callable, abstractmethod, json
from relay.config import get_phrase, get_phrase_list
from relay.users import User
from relay.utils import is_int, log_warn
from relay.callback_data import Callback


class Session():

    """
    Описывает пользовательскую или административную сессию `Session`.
    Сессия хранит пользователя, transport-адаптер, меню и флаг завершения; визуальная часть сессии живёт в wrapper-сообщении меню.

    ### Поля
    - `id`: идентификатор активной сессии.
    - `user`: пользователь, которому принадлежит сессия.
    - `bot`: transport-адаптер, через который сессия показывает меню.
    - `menu`: объект, управляющий wrapper-сообщением меню.
    - `finished`: флаг завершённой сессии.

    ### Методы
    - `__init__`: Регистрирует сессию у пользователя и создаёт меню.
    - `update`: Синхронизирует данные сессии с UI-сообщением.
    - `update_data`: Контракт обновления сессии из сериализованных данных наследника.
    - `reset`: Контракт возврата сессии к начальному шагу.
    - `load`: Контракт восстановления состояния сессии из storage.
    - `dumps`: Возвращает JSON-совместимый снимок с id сессии.
    - `check_callback_data`: Проверяет, относится ли callback к этой сессии.
    - `check`: Проверяет, может ли сессия обработать текущий `Context`.
    - `process`: Контракт обработки события наследником.
    - `stop`: Удаляет wrapper-сообщение меню; transport-адаптер не останавливает.

    ### Жизненный цикл
    Создаётся при входе пользователя в сценарий, хранится в стеке активных сессий пользователя и удаляет своё UI-сообщение при остановке.

    ### Пример использования
    ```py
    session: Session
    ```
    """
    def __init__(self, session_id: int, context: Context, data: dict, message: Message):
        """
        Создаёт session-объект `Session` и сохраняет состояние пользовательского сценария между входящими событиями.

        ### Аргументы:
        :param session_id: идентификатор сессии
        :param context: контекст обработки события
        :param data: сериализованный словарь
        :param message: сообщение проекта или сообщение конкретного транспорта

        ### Пример использования:
        ```py
        session = Session(session_id = session_id, context = context, data = data, message = message)
        ```
        """
        self.id: int = int(session_id)
        self.user: User = context.user
        self.user.add_session(context.bot.get_bot_key(), self, save = False)

        self.bot: BOT = context.bot
        self.menu: Menu = Menu(self.bot, self.user, message)

        self.finished: bool = False

    def __repr__(self) -> str:
        id = self.id
        user = self.user.id if self.user else None

        try:
            bot_key = self.bot.get_bot_key()
        except Exception as err:
            bot_key = err

        try:
            chat_id = self.user.get_chat_id(bot_key)
        except Exception as err:
            chat_id = err

        finished = self.finished
        try:
            message = self.get_message()
        except Exception as err:
            message = err
        return f"{self.__class__.__name__}({id=} {user=} {bot_key=} {chat_id=} {finished=})"

    @abstractmethod
    def update(self):
        """
        Синхронизирует данные сценария с уже отправленными UI-сообщениями.

        ### Пример использования:
        ```py
        session.update()
        ```
        """
        self.menu.update_message()

    @abstractmethod
    def update_data(self, data: dict):
        """
        Обновляет data с учётом текущего состояния объекта.

        ### Аргументы:
        :param data: JSON-совместимые данные для соответствующего repository

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        session.update_data(data = data)
        ```
        """
        raise NotImplementedError()

    @abstractmethod
    def reset(self, message: str):
        """
        Возвращает сценарий к начальному шагу и обновляет UI при необходимости.

        ### Аргументы:
        :param message: сообщение проекта или сообщение конкретного транспорта

        ### Пример использования:
        ```py
        session.reset(message = message)
        ```
        """
        self.update()

    @abstractmethod
    def load(self, data: BotTypes.SESSION_TYPE):
        """
        Загружает JSON-представление и восстанавливает поля объекта.

        ### Аргументы:
        :param data: сериализованный словарь

        ### Пример использования:
        ```py
        session.load(data = data)
        ```
        """
        pass

    def dumps(self) -> BotTypes.SESSION_TYPE:
        """
        Возвращает JSON-совместимый снимок объекта для storage или callback payload.

        :return: JSON-совместимый словарь для сохранения или передачи между слоями

        ### Пример использования:
        ```py
        session.dumps()
        ```
        """
        return {
            "id": int(self.id)
        }

    def check_callback_data(self, callback_data: str) -> bool:
        """
        Проверяет, относится ли callback payload к этой сессии.

        ### Аргументы:
        :param callback_data: payload callback-кнопки

        :return: `True`, если callback принадлежит этой сессии или не привязан к сессии; иначе `False`

        ### Пример использования:
        ```py
        session.check_callback_data(callback_data = callback_data)
        ```
        """
        callback: Callback = Callback.loads(callback_data)
        # WARNING: int -> str чтобы не было TypeError при приведении к int
        return str(callback.session_id) in (str(self.id), str(None))

    def check(self, context: Context) -> bool:
        """
        Проверяет значение по правилам текущего класса и не изменяет состояние.

        ### Аргументы:
        :param context: контекст обработки события

        :return: результат шага сессии

        ### Пример использования:
        ```py
        session.check(context = context)
        ```
        """
        if self.finished:
            user: User = context.user
            log_warn(f"Непредвиденное наличие завершённой сессии {repr(self)} у пользователя {user=}")
            return False

        if context.is_callback():
            callback_data: str = context.event.get_text()
            return self.check_callback_data(callback_data)
        else:
            return True

    @abstractmethod
    def process(self, context: Context):
        """
        Передаёт текущий `Context` выбранному обработчику и обновляет `context.handler` по результату.

        ### Аргументы:
        :param context: контекст обработки события

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        session.process(context = context)
        ```
        """
        raise NotImplementedError()

    @abstractmethod
    def stop(self):
        """
        Завершает визуальную часть сессии и удаляет связанное wrapper-сообщение.
        Метод очищает сообщение меню, которое принадлежит текущей пользовательской сессии; transport-бота он не останавливает.

        ### Пример использования:
        ```py
        session.stop()
        ```
        """
        self.get_message().delete()

    def stringify(self) -> str:
        """
        Сериализует снимок сессии в JSON-строку.

        :return: JSON-строка результата `dumps()`

        ### Пример использования:
        ```py
        session.stringify()
        ```
        """
        return json.dumps(self.dumps())

    def check_finished(self) -> bool:
        """
        Проверяет, завершена ли текущая сессия.

        :return: `True`, если сессия помечена завершённой; иначе `False`

        ### Пример использования:
        ```py
        session.check_finished()
        ```
        """
        return bool(self.finished)

    def finish(self):
        """
        Выполняет завершение текущей сессии или процесса.

        ### Примеры вызова:
        ```py
        session.finish()
        ```
        """


        self.finished = True

    def get_callback(self, *args: Iterable):
        """
        Возвращает callback payload для текущего объекта.

        :return: callback

        ### Пример использования:
        ```py
        session.get_callback(args = args)
        ```
        """
        return Callback(int(self.id), *args).stringfy()

    def show_message(self, text: str, buttons: Iterable[str | Bot.Keyboard.Button] = [], resend: bool = False) -> Message | None:
        """
        Обновляет текст и inline-кнопки меню активной сессии.
        Для Telegram или при `resend=True` создаёт новое wrapper-сообщение; старое сообщение помечает как несохранённое и удаляет из пользовательского состояния.

        ### Аргументы:
        :param text: новый текст меню
        :param buttons: inline-кнопки или строки, которые нужно показать под меню
        :param resend: нужно ли принудительно переотправить меню новым сообщением

        :return: wrapper-сообщение, которое было сброшено или переотправлено, если оно есть

        ### Пример использования:
        ```py
        session.show_message(text = text, buttons = buttons, resend = resend)
        ```
        """
        bot_key: BOT_KEY = self.bot.get_bot_key()
        if resend or bot_key == "telebot":
            chat_id: int = self.user.get_chat_id(bot_key)
            message: Message | None = self.menu.reset_message()

            if message:
                self.user.set_saved(message, False)
                self.user.delete_message(bot_key, message)

            self.menu.update(text, buttons)
            return self.menu.reset_message()
        else:
            self.menu.update(text, buttons)
            return self.menu.reset_message()

    def show_phrase(self, phrase_key: str,  buttons: Iterable[str | Bot.Keyboard.Button] = [], resend: bool = False) -> Message | None:
        """
        Берёт текст из локализации по `phrase_key` и передаёт его в `show_message`.

        ### Аргументы:
        :param phrase_key: ключ локализованной фразы
        :param buttons: inline-кнопки или строки, которые нужно показать под меню
        :param resend: нужно ли принудительно переотправить меню новым сообщением

        :return: wrapper-сообщение, которое было сброшено или переотправлено, если оно есть

        ### Пример использования:
        ```py
        session.show_phrase(phrase_key = phrase_key, buttons = buttons, resend = resend)
        ```
        """
        return self.show_message(get_phrase(phrase_key), buttons = buttons, resend = resend)

    def get_message(self) -> Message:
        """
        Возвращает wrapper-сообщение, связанное с текущей сессией.

        :return: message

        ### Пример использования:
        ```py
        session.get_message()
        ```
        """
        return self.menu.message


class Menu():
    """
    `Menu` управляет wrapper-сообщением активной сессии.
    Он хранит текущий текст и кнопки меню, обновляет связанное сообщение пользователя и создаёт новое wrapper-сообщение при сбросе.

    ### Поля
    - `bot`: transport-адаптер, через который показывается меню.
    - `user`: пользователь, которому принадлежит меню.
    - `message`: wrapper-сообщение текущего меню.
    - `text`: текст, подготовленный для следующего обновления меню.
    - `buttons`: кнопки, подготовленные для следующего обновления меню.

    ### Методы
    - `__init__`: Привязывает меню к transport-адаптеру, пользователю и wrapper-сообщению.
    - `update`: Запоминает новый текст и кнопки меню.
    - `update_message`: Применяет текст и кнопки к текущему wrapper-сообщению.
    - `reset_message`: Создаёт новое wrapper-сообщение для меню и возвращает предыдущее.

    ### Жизненный цикл
    Создаётся вместе с сессией и обновляет одно меню до завершения или переотправки сессии.

    ### Пример использования
    ```py
    menu: Menu
    ```
    """

    def __init__(self, bot: BOT, user: User, message: Message, max_width: int = 2, compression: bool = True, combine_media: bool = True):
        """
        Создаёт session-объект `Menu` и сохраняет состояние пользовательского сценария между входящими событиями.

        ### Аргументы:
        :param bot: transport-адаптер
        :param user: пользователь приложения
        :param message: сообщение проекта или сообщение конкретного транспорта
        :param max_width: максимальная ширина строки кнопок
        :param compression: признак сжатия вложения
        :param combine_media: нужно ли объединять media-вложения в одном сообщении, когда это допускает transport

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        menu = Menu(bot = bot, user = user, message = message, max_width = max_width, compression = compression, combine_media = combine_media)
        ```
        """
        self.bot: BOT = bot
        self.user: User = user
        self.message: Message = message

        if is_int(max_width) and int(max_width) > 0 and int(max_width) <= 4:
            pass
        else:
            raise ValueError(f"Некорректное значение аргумента {max_width=}")

        self.max_width: int = int(max_width)
        self.compression: bool = bool(compression)


    def reset_message(self) -> Message | None:
        """
        Помечает текущее сообщение как сохранённое, создаёт новое wrapper-сообщение пользователя для текущего `bot_key` и делает его сообщением меню.

        :return: предыдущее wrapper-сообщение, если оно было привязано к меню

        ### Пример использования:
        ```py
        menu.reset_message()
        ```
        """
        message: Message = self.message
        self.user.set_saved(message, True)
        self.message = self.user.create_message(self.bot.get_bot_key())
        return message

    def update(self, text: str = "", buttons: Iterable[str | Vkbot.Keyboard.Button | Telebot.Keyboard.Button] = [], make_last: bool = True):
        """
        Синхронизирует данные сценария с уже отправленными UI-сообщениями.

        ### Аргументы:
        :param text: текст
        :param buttons: кнопки, которые нужно показать пользователю
        :param make_last: нужно ли переместить меню в конец истории сообщений

        ### Пример использования:
        ```py
        menu.update(text = text, buttons = buttons, make_last = make_last)
        ```
        """
        self.message.set_text(text)
        self.message.set_keyboard(buttons, max_width = self.max_width, inline = True)
        self.update_message(make_last)

    def update_message(self, make_last: bool = True):
        """
        Обновляет wrapper-сообщение с учётом текущего состояния объекта.

        ### Аргументы:
        :param make_last: нужно ли сделать сообщение последним в текущем интерфейсе

        ### Пример использования:
        ```py
        menu.update_message(make_last = make_last)
        ```
        """
        bot_key: BOT_KEY = self.bot.get_bot_key()
        chat_id: int = self.user.get_chat_id(bot_key)

        if self.message in self.user.messages[bot_key] and self.message.check_sent(bot_key, chat_id):
            if self.user.is_last_message(bot_key, self.message) or not make_last:
                self.message.edit()
            else:
                self.user.make_last(bot_key, self.message)

            self.user.add_message(bot_key, self.bot.name, self.message)
        else:
            if self.user.app is None:
                self.message.send(self.bot, chat_id)
            else:
                self.user.app.catch_message_send(self.message, self.bot, chat_id)

            self.user.add_message(bot_key, self.bot.name, self.message)


class Input():
    """
    `Input` хранит состояние выбора в меню: вопрос, варианты ответов, действия, выбранные значения и параметры пагинации.
    Он формирует кнопки для wrapper-сообщения и обрабатывает callback-навигацию по ответам и действиям.

    ### Поля
    - `menu`: меню, wrapper-сообщение которого обновляет input.
    - `question`: текст вопроса над вариантами ответа.
    - `answers`: варианты ответа, доступные пользователю.
    - `actions`: действия меню, доступные пользователю.
    - `back`: нужно ли показывать возврат назад.
    - `cancel`: нужно ли показывать действие отмены.
    - `lang_answers`: интерпретировать ключи ответов как ключи локализации.
    - `lang_actions`: интерпретировать ключи действий как ключи локализации.
    - `min`: минимальное число выбранных ответов.
    - `max`: максимальное число выбранных ответов.
    - `choosen`: текущие выбранные ответы; имя поля сохранено с исторической опечаткой.
    - `actions_page`: текущая страница действий при пагинации.
    - `answers_page`: текущая страница ответов при пагинации.
    - `finished`: флаг завершённого input-сценария.
    - `max_buttons`: максимум кнопок, который input старается держать на странице.
    - `max_actions`: максимум действий, показываемых на странице.

    ### Методы
    - `load`: Заполняет поля input из JSON-совместимого словаря.
    - `loads`: Фабричный helper без декоратора; вызывается как `Input.loads(menu, data)`.
    - `dumps`: Возвращает JSON-совместимое состояние input.
    - `update`: Заменяет вопрос, ответы, действия и правила выбора.
    - `update_menu`: Перестраивает кнопки wrapper-сообщения.
    - `process`: Обрабатывает callback или текстовый ответ пользователя.

    ### Жизненный цикл
    Живёт внутри меню-сессии и меняется при каждом выборе, отмене, подтверждении или перелистывании.

    ### Пример использования
    ```py
    input: Input
    ```
    """
    def load(self, data: BotTypes.INPUT_TYPE):
        """
        Загружает JSON-представление и восстанавливает поля объекта.

        ### Аргументы:
        :param data: сериализованный словарь

        ### Пример использования:
        ```py
        input.load(data = data)
        ```
        """
        self.set_question(str(data.get("question", "")))
        self.set_answers(dict[str, JSONABLE](data.get("answers", {})))
        self.set_actions(dict[str, JSONABLE](data.get("actions", {})))
        self.choosen = list[str]([str(x) for x in data.get("choosen", [])])
        self.default = data.get("default", None)
        self.max_buttons = int(data.get("max_buttons", 0))
        self.min = int(data.get("min", 0))
        self.max = int(data.get("max", 1))
        self.required = bool(get_from(data, "required", default = False, types = (bool,)))
        self.confirm = bool(get_from(data, "confirm", default = False, types = (bool,)))
        self.cancel = bool(get_from(data, "cancel", default = False, types = (bool,)))
        self.back = bool(get_from(data, "back", default = False, types = (bool,)))
        self.skip = bool(get_from(data, "skip", default = False, types = (bool,)))
        self.actions_page = data.get("actions_page", None)
        self.answers_page = data.get("answers_page", None)
        self.finished = bool(get_from(data, "finished", default = False, types = (bool,)))
        self.lang_answers = bool(get_from(data, "lang_answers", default = False, types = (bool,)))
        self.lang_actions = bool(get_from(data, "lang_actions", default = False, types = (bool,)))

    @staticmethod
    def loads(menu: Menu, data: BotTypes.INPUT_TYPE) -> Input:
        """
        Создаёт новый `Input` для `menu` и заполняет его данными из storage.

        ### Аргументы:
        :param menu: меню, wrapper-сообщение которого будет обновлять восстановленный input
        :param data: сериализованное состояние input

        :return: новый `Input`, заполненный через `load`

        ### Пример использования:
        ```py
        input = Input.loads(menu, data)
        ```
        """
        result: Input = Input(menu)
        result.load(data)
        return result

    def __init__(self, menu: Menu, max_buttons: int = 50, max_actions: int | None = None, lang_answers: bool = False, lang_actions: bool = False):
        """
        Создаёт session-объект `Input` и сохраняет состояние пользовательского сценария между входящими событиями.

        ### Аргументы:
        :param menu: меню, wrapper-сообщение которого нужно обновлять
        :param max_buttons: максимальное число кнопок на странице меню
        :param max_actions: максимальное число action-кнопок на странице; `None` рассчитывает лимит автоматически
        :param lang_answers: lang answers
        :param lang_actions: lang actions

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        input = Input(menu = menu, max_buttons = max_buttons, max_actions = max_actions, lang_answers = lang_answers, lang_actions = lang_actions)
        ```
        """
        if is_int(max_buttons) and max_buttons > 0:
            pass
        else:
            raise ValueError(f"Некорректное значение аргумента {max_buttons=}")

        if max_actions is None or (is_int(max_actions) and max_actions > 0):
            pass
        else:
            raise ValueError(f"Некорректное значение аргумента {max_actions=}")

        self.menu: Menu = menu
        self.max_buttons: int = int(max_buttons)
        self.max_actions: int | None = None if max_actions is None else int(max_actions)

        self.question: str = ""

        self.answers: dict[str, JSONABLE] = {}
        self.lang_answers: bool = bool(lang_answers)
        self.min: int = 0
        self.max: int = 1

        self.actions: dict[str, JSONABLE] = {}
        self.lang_actions: bool = bool(lang_actions)
        self.choosen: list[str] = []
        self.default: JSONABLE = None
        self.required: bool = False
        self.confirm: bool = False
        self.cancel: bool = False
        self.back: bool = False
        self.skip: bool = False

        self.finished: bool = False
        self.actions_page: int | None = None
        self.answers_page: int | None = None

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.dumps()})"

    def dumps(self) -> BotTypes.INPUT_TYPE:
        """
        Возвращает JSON-совместимый снимок объекта для storage или callback payload.

        :return: JSON-совместимый словарь для сохранения или передачи между слоями

        ### Пример использования:
        ```py
        input.dumps()
        ```
        """
        return {
            "question": str(self.question),
            "answers": dict[str, JSONABLE]({str(k): v for k, v in self.answers.items()}),
            "lang_answers": bool(self.lang_answers),
            "actions": dict[str, JSONABLE]({str(k): v for k, v in self.actions.items()}),
            "lang_actions": bool(self.lang_actions),
            "choosen": list[str]([str(x) for x in self.choosen]),
            "default": self.default,
            "max_buttons": int(self.max_buttons),
            "min": int(self.min),
            "max": int(self.max),
            "required": bool(self.required),
            "confirm": bool(self.confirm),
            "cancel": bool(self.cancel),
            "back": bool(self.back),
            "skip": bool(self.skip),
            "actions_page": self.actions_page,
            "answers_page": self.answers_page,
            "finished": bool(self.finished)
        }

    def reset(self):
        """
        Возвращает сценарий к начальному шагу и обновляет UI при необходимости.

        ### Пример использования:
        ```py
        input.reset()
        ```
        """
        self.choosen.clear()
        self.answers_page = None
        self.actions_page = None

    def set_question(self, question: str):
        """
        Проверяет и сохраняет значение `question`.

        ### Аргументы:
        :param question: текст или объект вопроса

        ### Пример использования:
        ```py
        input.set_question(question = question)
        ```
        """
        self.question = str(question)

    def set_answers(self, answers: Iterable[str] | dict[str, JSONABLE]):
        """
        Проверяет и сохраняет варианты ответа в объекте.

        ### Аргументы:
        :param answers: варианты ответа

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        input.set_answers(answers = answers)
        ```
        """
        if isinstance(answers, dict):
            self.answers.clear()

            for key, value in answers.items():
                key = str(key)

                if key in self.answers:
                    raise ValueError(f"Некорректное значение аргумента answers под ключом {key=}. Варианты ответов с одинаковыми ключами не допускаются (ключ приводится к строке)")

                if isinstance(value, JSONABLE):
                    self.answers[key] = value
                else:
                    raise ValueError(f"Некорректное значение аргумента answers под ключом {key=}. Значение обязательно должно быть приводимым к JSON")
        elif is_iterable(answers):
            self.answers.clear()

            for key in answers:
                key = str(key)
                if key in self.answers:
                    raise ValueError(f"Некорректное значение аргумента answers под ключом {key=}. Варианты ответов с одинаковыми ключами не допускаются (ключ приводится к строке)")

                self.answers[key] = key
        else:
            raise ValueError(f"Некорректное значение аргумента {answers=}")

    def set_actions(self, actions: Iterable[str] | dict[str, JSONABLE], lang_actions: bool = False):
        """
        Проверяет и сохраняет значение `actions`.

        ### Аргументы:
        :param actions: действия меню
        :param lang_actions: lang actions

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        input.set_actions(actions = actions, lang_actions = lang_actions)
        ```
        """
        if isinstance(actions, dict):
            self.actions.clear()

            for key, value in actions.items():
                if isinstance(value, JSONABLE):
                    self.actions[str(key)] = value
                else:
                    raise ValueError(f"Некорректное значение аргумента actions под ключом {key=}. Значение обязательно должно быть приводимым к JSON")
        elif is_iterable(actions):
            self.actions.clear()

            for action in actions:
                self.actions[str(action)] = str(action)
        else:
            raise ValueError(f"Некорректное значение аргумента {actions=}")

    def set_choosen(self, choosen: Iterable[str]):
        """
        Проверяет и сохраняет значение `choosen`.

        ### Аргументы:
        :param choosen: выбранные пользователем ответы

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        input.set_choosen(choosen = choosen)
        ```
        """
        self.choosen.clear()

        for option in choosen:
            if option in self.answers:
                self.choosen.append(option)
            else:
                raise ValueError(f"Некорректное значение аргумента {choosen=}. Вариант {repr(option)} не доступен для выбора (отсутствует в атрибуте answers)")

    @abstractmethod
    def update_back(self):
        """
        Обновляет back с учётом текущего состояния объекта.

        ### Примеры вызова:
        ```py
        input.update_back()
        ```
        """
        pass

    def update(self, question: str | None = None,
            answers: Iterable[str] | dict[str, JSONABLE] | None = None,
            actions: Iterable[str] | dict[str, JSONABLE] | None = None,
            choosen: Iterable[str] | None = None,
            default: Any = object,
            min: int | None = 1,
            max: int | None = 1,
            max_width: int | None = 2,
            confirm: bool | None = None,
            cancel: bool | None = None,
            back: bool | None = None,
            skip: bool | None = None,
            make_last: bool = True):
        """
        Синхронизирует данные сценария с уже отправленными UI-сообщениями.

        ### Аргументы:
        :param question: текст или объект вопроса
        :param answers: варианты ответа
        :param actions: действия меню
        :param choosen: выбранные пользователем ответы
        :param default: исходный выбранный ответ
        :param min: минимальное число выбранных ответов
        :param max: максимальное число выбранных ответов
        :param max_width: максимальная ширина строки кнопок
        :param confirm: нужно ли показывать подтверждение выбора
        :param cancel: нужно ли показывать отмену
        :param back: callback возврата к предыдущему шагу
        :param skip: нужно ли пропустить предупреждение или действие
        :param make_last: нужно ли переместить меню в конец истории сообщений

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        input.update(question = question, answers = answers, actions = actions, choosen = choosen, default = default, min = min, max = max, max_width = max_width, confirm = confirm, cancel = cancel, back = back, skip = skip, make_last = make_last)
        ```
        """
        if question is not None:
            self.set_question(question)

        if answers is not None:
            self.set_answers(answers)

        if actions is not None:
            self.set_actions(actions)

        if choosen is not None:
            self.set_choosen(choosen)

        if default is not object:
            if isinstance(default, JSONABLE):
                self.default = default
            else:
                raise ValueError(f"Некорректное значение аргумента {default=}. Значение обязательно должно быть приводимым к JSON")

        if confirm is None:
            if max is None:
                self.confirm = self.max > 1
            else:
                self.confirm = max > 1
        else:
            self.confirm = bool(confirm)

        if min is not None:
            self.min = int(min)

        if max is not None:
            self.max = int(max)

        if max_width is not None:
            self.menu.max_width = int(max_width)

        if cancel is not None:
            self.cancel = bool(cancel)

        if back is None:
            self.update_back()
        else:
            self.back = bool(back)

        if skip is not None:
            self.skip = bool(skip)

        self.update_menu(make_last = make_last)

    def update_menu(self, session_id: int | None = None, make_last: bool = True):
        """
        Обновляет menu по текущему состоянию объекта.

        ### Аргументы:
        :param session_id: идентификатор сессии
        :param make_last: нужно ли переместить меню в конец истории сообщений

        ### Пример использования:
        ```py
        input.update_menu(session_id = session_id, make_last = make_last)
        ```
        """
        answers: dict[str, JSONABLE] = {}
        actions: dict[str, JSONABLE] = {}
        choosen: list[str] = []

        # WARNING: JSONABLE -> str
        for answer, callback_data in self.answers.items():
            answers[get_phrase(answer) if self.lang_answers else answer] = str(callback_data)

        # WARNING: JSONABLE -> str
        for action, callback_data in self.actions.items():
            actions[get_phrase(action) if self.lang_actions else action] = str(callback_data)

        for option in self.choosen:
            if option in self.answers or option in answers:
                choosen.append(option)

        self.update_page(
            answers = answers,
            actions = actions,
            choosen = choosen,
            session_id = session_id,
            make_last = make_last
        )

    def check_answer(self, answer: str) -> bool:
        """
        Проверяет, совпадает ли ответ пользователя с доступными вариантами.

        ### Аргументы:
        :param answer: ответ пользователя

        :return: `True`, если совпадает ли ответ пользователя с доступными вариантами; иначе `False`

        ### Пример использования:
        ```py
        input.check_answer(answer = answer)
        ```
        """
        return answer in self.answers

    def get_answer(self, answer: str) -> JSONABLE | None:
        """
        Возвращает строку, показываемую пользователю как вариант ответа.

        ### Аргументы:
        :param answer: ответ пользователя

        :return: ответ пользователя

        ### Пример использования:
        ```py
        input.get_answer(answer = answer)
        ```
        """
        if answer in self.answers:
            return self.answers.get(answer)

        for ans in self.answers:
            if ans.startswith(answer):
                return ans

        return None

    def get_callback(self, callback_data: str):
        """
        Возвращает callback payload для текущего объекта.

        ### Аргументы:
        :param callback_data: payload callback-кнопки

        :return: callback

        ### Пример использования:
        ```py
        input.get_callback(callback_data = callback_data)
        ```
        """
        return callback_data

    def update_page(self,
            answers: dict[str, str] = {},
            actions: dict[str, str] = {},
            choosen: Iterable[str] = [],
            select_all: bool | None = None,
            session_id: int | None = None,
            min_width_answers: Literal[1, 2] = 2,
            min_width_actions: Literal[1, 2] = 1,
            make_last: bool = True):
        """
        Обновляет page по текущему состоянию объекта.

        ### Аргументы:
        :param answers: варианты ответа
        :param actions: действия меню
        :param choosen: выбранные пользователем ответы
        :param select_all: нужно ли показывать кнопку выбора всех ответов
        :param session_id: идентификатор сессии
        :param min_width_answers: минимальная ширина кнопок ответов в сетке меню
        :param min_width_actions: минимальная ширина action-кнопок в сетке меню
        :param make_last: нужно ли переместить меню в конец истории сообщений

        :return: результат шага сессии

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        input.update_page(answers = answers, actions = actions, choosen = choosen, select_all = select_all, session_id = session_id, min_width_answers = min_width_answers, min_width_actions = min_width_actions, make_last = make_last)
        ```
        """
        bot: BOT = self.menu.bot
        buttons: list[str | Vkbot.Keyboard.Button | Telebot.Keyboard.Button] = []
        actions_buttons: list[dict[str, str | int]] = []
        actions_extra: list[str] = []

        max_buttons: int = self.max_buttons
        max_actions: int | None = self.max_actions

        def create_action(text: str, callback_data: str, color: int | str | VkKeyboardColor):
            if not Vkbot.Keyboard.Button.check_color(Vkbot.Keyboard.Button, color):
                raise ValueError(f"Некорректное значение аргумента {color=}")

            actions_buttons.append({
                "text": str(text),
                "callback_data": callback_data,
                "color": color
            })

        def get_answer_callback(answer: str):
            return self.get_callback(ANSWER_CALLBACK, cut(answer, 20))

        def get_action_callback(action: str, callback_data: str = ""):
            return self.get_callback(ACTION_CALLBACK, callback_data or action)

        def add_button(
            text: str,
            color: int | str | VkKeyboardColor,
            callback_data: str = "",
            insert_first: bool = False,
            min_width: Literal[1, 2] = min_width_actions
        ):
            button: Vkbot.Keyboard.Button | str

            if isinstance(bot, Vkbot):
                button = Vkbot.Keyboard.Button(text, color, min_width, callback_data)
            elif isinstance(bot, Telebot):
                button = Telebot.Keyboard.Button(text, callback_data = callback_data)

            if insert_first:
                buttons.insert(0, button)
            else:
                buttons.append(button)

        def add_answer(answer: str):
            answer_choosen: bool = answer in choosen
            string: str = f"√ {answer}" if answer_choosen else answer
            add_button(string, 3 if answer_choosen else 1, callback_data = get_answer_callback(answer), insert_first = True, min_width = min_width_answers)

        def add_action(text: str, color: int | str | VkKeyboardColor, callback_data: str):
            # callback: str = get_action_callback(text, callback_data)
            add_button(text, color, callback_data = callback_data)

        # Кнопка выбрать всё доступна только если можно выбрать более 1 варианта
        if select_all != False:
            select_all = len(answers) > 1 and self.max > 1

        # Устанавливаем максимальное количество действий
        if max_actions is None:
            max_actions = max_buttons // 2 - int(select_all)

        if max_actions > max_buttons:
            max_actions = max_buttons

        if min_width_answers != min_width_actions and len(actions) < max_actions:
            # separate_actions
            max_buttons = max_buttons - (max_actions - len(actions) - 1)

        # Формируем действия
        for action, callback_data in actions.items():
            create_action(str(action), get_action_callback(callback_data), 0)

        if self.confirm and len(choosen) >= self.min and len(choosen) <= self.max:
            create_action(get_phrase("confirm"), self.get_callback(CONFIRM_CALLBACK), 3)
        if self.cancel:
            create_action(get_phrase("cancel"), self.get_callback(CANCEL_CALLBACK), 2)
        if self.skip:
            create_action(get_phrase("skip"), self.get_callback(SKIP_CALLBACK), 1)
        if self.back:
            create_action(get_phrase("back"), self.get_callback(BACK_CALLBACK), 0)

        # Режим отображения дополнительных действий
        if self.actions_page is not None:
            remaining_slots: int = max_buttons - 1
            previous_actions: int = 0
            left_actions: int = len(actions_buttons)

            for i in range(self.actions_page):
                if i == 0:
                    if len(actions_buttons) > remaining_slots:
                        previous_actions += remaining_slots - 1
                    else:
                        previous_actions += len(actions_buttons)
                else:
                    left_actions = len(actions_buttons) - previous_actions
                    if left_actions > remaining_slots - 1:
                        previous_actions += remaining_slots - 2
                    else:
                        previous_actions += remaining_slots - 1

            left_actions = len(actions_buttons) - previous_actions
            prev_page: bool = self.actions_page > 0
            next_page: bool = left_actions > remaining_slots
            remaining_slots -= int(prev_page) + int(next_page)
            start: int = previous_actions
            end: int = previous_actions + remaining_slots
            chunk: list[tuple[str, int, int, str]] = actions_buttons[start:end]

            if remaining_slots > len(chunk):
                start -= remaining_slots - len(chunk)
                chunk = actions_buttons[start:end]

            if prev_page:
                add_button(get_phrase("prev_actions"), 0, callback_data = self.get_callback(PREV_ACTIONS_CALLBACK), min_width = 2)

            for action_dictionary in chunk:
                text: str = action_dictionary["text"]
                color: int | str | VkKeyboardColor = action_dictionary["color"]
                callback_data: str = action_dictionary["callback_data"]
                add_action(text, color, callback_data)

            if end < len(actions_buttons):
                add_button(get_phrase("next_actions"), 0, callback_data = self.get_callback(NEXT_ACTIONS_CALLBACK), min_width = 2)

            add_button(get_phrase("back_actions"), 1, callback_data = self.get_callback(BACK_ACTIONS_CALLBACK))
        # Обычный режим
        else:
            # Проверяем сколько действий влезает
            if len(actions_buttons) > max_actions:
                for i in range(len(actions_buttons)):
                    if i < max_actions - 1:
                        action_dictionary = actions_buttons[i]
                        text: str = action_dictionary["text"]
                        color: int | str | VkKeyboardColor = action_dictionary["color"]
                        callback_data: str = action_dictionary["callback_data"]
                        add_action(text, color, callback_data)
                    else:
                        actions_extra.extend(actions_buttons[i:])
                        break

                add_button(get_phrase("more_actions"), 3, callback_data = self.get_callback(MORE_ACTIONS_CALLBACK))
            else:
                for action_dictionary in actions_buttons:
                    text: str = action_dictionary["text"]
                    color: int | str | VkKeyboardColor = action_dictionary["color"]
                    callback_data: str = action_dictionary["callback_data"]
                    add_action(text, color, callback_data)

            # Подсчёт оставшегося места под ответы
            remaining_slots: int = max_buttons - len(buttons) - int(select_all)

            # Переход в режим постраничных ответов
            if self.answers_page is not None:
                previous_answers: int = 0
                left_answers: int = len(answers)

                for i in range(self.answers_page):
                    if i == 0:
                        if len(answers) > remaining_slots:
                            previous_answers += remaining_slots - 1
                        else:
                            previous_answers += len(answers)
                    else:
                        left_answers = len(answers) - previous_answers
                        if left_answers > remaining_slots - 1:
                            previous_answers += remaining_slots - 2
                        else:
                            previous_answers += remaining_slots - 1

                left_answers = len(answers) - previous_answers
                prev_page: bool = self.answers_page > 0
                next_page: bool = left_answers > remaining_slots
                remaining_slots -= int(prev_page) + int(next_page)# + 2
                start: int = previous_answers
                end: int = previous_answers + remaining_slots
                chunk: list[str] = list(answers.keys())[start:end]

                if remaining_slots > len(chunk):
                    start -= remaining_slots - len(chunk)
                    chunk = list(answers.keys())[start:end]

                if next_page:
                    add_button(get_phrase("next_answers"), 0, callback_data = self.get_callback(NEXT_ANSWERS_CALLBACK), min_width = 2, insert_first = True)

                for answer in reversed(chunk):
                    add_answer(answer)

                if prev_page:
                    add_button(get_phrase("prev_answers"), 0, callback_data = self.get_callback(PREV_ANSWERS_CALLBACK), min_width = 2, insert_first = True)
            else:
                if len(answers) > remaining_slots:
                    add_button(get_phrase("next_answers"), 0, callback_data = self.get_callback(NEXT_ANSWERS_CALLBACK), insert_first = True, min_width = 2)

                    # Показываем только те ответы, которые влезают
                    visible_answers: list[str] = tuple(answers.keys())[:remaining_slots - 1]

                    for answer in reversed(visible_answers):
                        add_answer(answer)
                else:
                    for answer in reversed(answers):
                        add_answer(answer)

            if select_all:
                add_button(get_phrase("select_all"), 0 if len(choosen) >= len(answers) else 1, callback_data = self.get_callback(SELECT_ALL_CALLBACK), min_width = 2, insert_first = True)

        self.menu.update(str(self.question), buttons, make_last)  # save = ???


    def incorrect(self, context: Context):
        """
        Выполняет следующий шаг текущей сессии.

        ### Аргументы:
        :param context: контекст обработки события

        ### Пример использования:
        ```py
        input.incorrect(context = context)
        ```
        """


        message: str = get_phrase("incorrect")
        self.menu.update(message)
        self.menu.reset_message()
        self.update_menu()

    def process(self, context: Context):
        """
        Передаёт текущий `Context` выбранному обработчику и обновляет `context.handler` по результату.

        ### Аргументы:
        :param context: контекст обработки события

        ### Пример использования:
        ```py
        input.process(context = context)
        ```
        """
        def skip_command():
            """
            Input не умеет обрабатывать такие команды, поэтому пропускает, чтобы их обработали в следующем обработчике.
            Сообщение об ошибке выводить не требуется.
            """
            context.remove_handler()

        def invalid_command():
            """
            Input знает как обрабатывать такие команды, но команда не содержит достаточно данных или содержит неверные.
            Выводим сообщение об ошибке.
            """
            context.remove_handler()
            self.incorrect(context)

        if context.is_callback():
            callback_data: str = context.get_callback_string()

            if callback_data == PREV_ACTIONS_CALLBACK:
                if self.actions_page is not None:
                    self.actions_page -= 1
            elif callback_data == NEXT_ACTIONS_CALLBACK:
                if self.actions_page is not None:
                    self.actions_page += 1
            elif callback_data == MORE_ACTIONS_CALLBACK:
                self.actions_page = 0
            elif callback_data == BACK_ACTIONS_CALLBACK:
                self.actions_page = None
            elif callback_data == PREV_ANSWERS_CALLBACK:
                if self.answers_page is not None:
                    self.answers_page -= 1

                if self.answers_page == 0:
                    self.answers_page = None
            elif callback_data == NEXT_ANSWERS_CALLBACK:
                if self.answers_page is not None:
                    self.answers_page += 1
                else:
                    self.answers_page = 1
            elif callback_data == SELECT_ALL_CALLBACK:
                if len(self.choosen) >= len(self.answers):
                    self.set_choosen([])
                else:
                    self.set_choosen(self.answers)
            elif callback_data == BACK_CALLBACK:
                self.action_back()
                return
            elif callback_data == CANCEL_CALLBACK:
                self.action_cancel()
                return
            else:
                callback: Callback = context.get_callback()
                bot_key: BOT_KEY = context.bot.get_bot_key()
                chat_id: int = context.get_chat_id()

                if callback_data == ACTION_CALLBACK:
                    if not self.process_action(bot_key, chat_id, callback.args[1]):
                        invalid_command()
                elif callback_data == ANSWER_CALLBACK:
                    answer: str = callback.args[1]

                    if not self.check_answer(answer):
                        for ans in self.answers:
                            if ans.startswith(answer):
                                answer = ans
                                break


                    if not self.process_answer(bot_key, chat_id, answer):
                        invalid_command()
                else:
                    skip_command()

                return
        else:
            skip_command()

        if isinstance(context.handler, Session):
            # input успешно обработал запрос
            self.update_menu(context.handler.id)


    @abstractmethod
    def process_answer(self, bot_key: BOT_KEY, chat_id: int, answer: str) -> bool:
        """
        Обрабатывает ответ пользователя в текущем runtime-контексте.

        ### Аргументы:
        :param bot_key: ключ транспорта
        :param chat_id: идентификатор чата
        :param answer: ответ пользователя

        :return: результат шага сессии

        ### Пример использования:
        ```py
        input.process_answer(bot_key = bot_key, chat_id = chat_id, answer = answer)
        ```
        """


        return False

    @abstractmethod
    def process_action(self, bot_key: BOT_KEY, chat_id: int, action: str) -> bool:
        """
        Обрабатывает действие меню в текущем runtime-контексте.

        ### Аргументы:
        :param bot_key: ключ транспорта
        :param chat_id: идентификатор чата
        :param action: действие меню

        :return: результат шага сессии

        ### Пример использования:
        ```py
        input.process_action(bot_key = bot_key, chat_id = chat_id, action = action)
        ```
        """


        return False

    @abstractmethod
    def action_back(self):
        """
        Обрабатывает пользовательское действие внутри текущего session-сценария.

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        input.action_back()
        ```
        """
        raise NotImplementedError()

    @abstractmethod
    def action_cancel(self):
        """
        Обрабатывает пользовательское действие внутри текущего session-сценария.

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        input.action_cancel()
        ```
        """
        raise NotImplementedError()


class MenuInput(Input):
    """
    `MenuInput` хранит состояние многошагового пользовательского сценария между входящими событиями.
    Сессия хранит состояние текущего пользовательского сценария, обновляет сообщения и завершает себя через общий session lifecycle.

    ### Поля
    - `session`: SQLAlchemy-сессия или app-layer сессия, с которой работает объект.

    ### Методы
    - `loads`: Восстанавливает объект из JSON-совместимого словаря.
    - `__init__`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `get_callback`: Возвращает callback-событие из текущего состояния `MenuInput`.
    - `update_back`: Обновляет back с учётом текущего состояния объекта.
    - `action_back`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `action_cancel`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `process_answer`: Обрабатывает ответ пользователя в текущем пользовательском или transport-layer потоке.
    - `process_action`: Обрабатывает действие меню в текущем пользовательском или transport-layer потоке.
    - `ask_confirm`: Показывает пользователю вопрос для шага `confirm`.
    - `check_confrimed`: Проверяет confrimed перед использованием.

    ### Жизненный цикл
    Создаётся app-layer кодом, участвует в обработке пользовательского события и сохраняет изменённое состояние через существующие runtime/storage механизмы.

    ### Пример использования
    ```py
    menuInput: MenuInput
    ```
    """
    @staticmethod
    def loads(session: ManageSession | LevelSession, menu: Menu, data: BotTypes.INPUT_TYPE) -> MenuInput:
        """
        Восстанавливает объект из JSON-совместимого словаря.

        ### Аргументы:
        :param session: сессия
        :param menu: меню, wrapper-сообщение которого нужно обновлять
        :param data: сериализованный словарь

        :return: восстановленный `MenuInput`

        ### Пример использования:
        ```py
        MenuInput.loads(session = session, menu = menu, data = data)
        ```
        """
        result: MenuInput = MenuInput(session, menu)
        result.load(data)
        return result

    def __init__(self, session: ManageSession | LevelSession, menu: Menu, max_buttons: int = 15, max_actions: int | None = None, lang_answers: bool = False, lang_actions: bool = True):
        """
        Создаёт session-объект `MenuInput` и сохраняет состояние пользовательского сценария между входящими событиями.

        ### Аргументы:
        :param session: сессия
        :param menu: меню, wrapper-сообщение которого нужно обновлять
        :param max_buttons: максимальное число кнопок на странице меню
        :param max_actions: максимальное число action-кнопок на странице; `None` рассчитывает лимит автоматически
        :param lang_answers: lang answers
        :param lang_actions: lang actions

        ### Пример использования:
        ```py
        menuInput = MenuInput(session = session, menu = menu, max_buttons = max_buttons, max_actions = max_actions, lang_answers = lang_answers, lang_actions = lang_actions)
        ```
        """
        super().__init__(menu, max_buttons, max_actions, lang_answers, lang_actions)
        self.session: MenuSession = session

    def get_callback(self, *args: Iterable):
        """
        Возвращает callback payload для текущего объекта.

        :return: callback

        ### Пример использования:
        ```py
        menuInput.get_callback(args = args)
        ```
        """
        return self.session.get_callback(*args)

    def update_back(self):
        """
        Обновляет back с учётом текущего состояния объекта.

        ### Примеры вызова:
        ```py
        menuInput.update_back()
        ```
        """
        self.back = self.session.get_back() is not None

    def action_back(self):
        """
        Обрабатывает пользовательское действие внутри текущего session-сценария.

        ### Пример использования:
        ```py
        menuInput.action_back()
        ```
        """


        self.session.action_back()

    def action_cancel(self):
        """
        Обрабатывает пользовательское действие внутри текущего session-сценария.

        ### Пример использования:
        ```py
        menuInput.action_cancel()
        ```
        """
        self.session.action_cancel()

    def process_answer(self, bot_key: BOT_KEY, chat_id: int, answer: str) -> bool:
        """
        Обрабатывает ответ пользователя в текущем runtime-контексте.

        ### Аргументы:
        :param bot_key: ключ транспорта
        :param chat_id: идентификатор чата
        :param answer: ответ пользователя

        :return: результат шага сессии

        ### Пример использования:
        ```py
        menuInput.process_answer(bot_key = bot_key, chat_id = chat_id, answer = answer)
        ```
        """


        if self.session.check_choosing():
            if answer in self.choosen:
                self.choosen.remove(answer)
            else:
                self.choosen.append(answer)

            self.update_menu()
            return True
        elif self.check_answer(answer):
            value: JSONABLE = self.get_answer(answer)
            return self.session.process_answer(bot_key, chat_id, value)
        else:
            return False

    def process_action(self, bot_key: BOT_KEY, chat_id: int, action: str) -> bool:
        """
        Обрабатывает действие меню в текущем runtime-контексте.

        ### Аргументы:
        :param bot_key: ключ транспорта
        :param chat_id: идентификатор чата
        :param action: действие меню

        :return: результат шага сессии

        ### Пример использования:
        ```py
        menuInput.process_action(bot_key = bot_key, chat_id = chat_id, action = action)
        ```
        """


        return self.session.process_action(bot_key, chat_id, action)

    def ask_confirm(self, question: str):
        """
        Показывает пользователю вопрос для шага `confirm`.

        ### Аргументы:
        :param question: текст или объект вопроса

        ### Пример использования:
        ```py
        menuInput.ask_confirm(question = question)
        ```
        """
        self.update(question, answers = [], actions = {
            "accept": ACCEPT_CALLBACK,
            "decline": DECLINE_CALLBACK
        }, choosen = [], skip = False)

    def check_confrimed(self, text: str, is_callback: bool) -> bool | None:
        """
        Проверяет значение `confrimed` перед сохранением или использованием.

        ### Аргументы:
        :param text: текст
        :param is_callback: is callback

        :return: `True`, если значение `confrimed` перед сохранением или использованием; иначе `False`

        ### Пример использования:
        ```py
        menuInput.check_confrimed(text = text, is_callback = is_callback)
        ```
        """


        if is_callback:
            callback: Callback = Callback.loads(text)
            callback_data: str = callback.args[1]

            if callback_data == ACCEPT_CALLBACK:
                return True
            elif callback_data == DECLINE_CALLBACK:
                return False
            else:
                return None
        else:
            text: str = str(text).strip().upper() if text else ""

            if text in get_phrase_list("confirm_yes"):
                return True
            elif text in get_phrase_list("confirm_no"):
                return False
            else:
                return None


class MenuSession(Session):
    """
    Описывает пользовательскую или административную сессию `MenuSession`.
    Сессия хранит состояние текущего пользовательского сценария, обновляет сообщения и завершает себя через общий session lifecycle.

    ### Поля
    - `input`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `input_data`: runtime-зависимость или поле, используемое текущим session-сценарием.

    ### Методы
    - `__init__`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `dumps`: Возвращает JSON-совместимый снимок объекта для storage или callback payload.
    - `reset`: Возвращает сценарий к начальному шагу и обновляет UI при необходимости.
    - `action_cancel`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `process_answer`: Обрабатывает ответ пользователя в текущем пользовательском или transport-layer потоке.
    - `process_action`: Обрабатывает действие меню в текущем пользовательском или transport-layer потоке.
    - `get_back`: Возвращает back из текущего состояния `MenuSession`.
    - `get_answers`: Возвращает варианты ответа из текущего состояния `MenuSession`.
    - `get_actions`: Возвращает действия меню из текущего состояния `MenuSession`.
    - `get_question`: Возвращает вопрос анкеты или GPT-контекста из текущего состояния `MenuSession`.

    ### Жизненный цикл
    Создаётся app-layer кодом, участвует в обработке пользовательского события и сохраняет изменённое состояние через существующие runtime/storage механизмы.

    ### Пример использования
    ```py
    session: MenuSession
    ```
    """
    def __init__(self, session_id: int, context: Context, data: dict, message: Message):
        """
        Создаёт session-объект `MenuSession` и сохраняет состояние пользовательского сценария между входящими событиями.

        ### Аргументы:
        :param session_id: идентификатор сессии
        :param context: контекст обработки события
        :param data: сериализованный словарь
        :param message: сообщение проекта или сообщение конкретного транспорта

        ### Пример использования:
        ```py
        session = MenuSession(session_id = session_id, context = context, data = data, message = message)
        ```
        """
        super().__init__(session_id, context, data, message)
        self.input: MenuInput
        input_data: dict[str, JSONABLE | dict[str, JSONABLE] | list[str]] = data.get("input", {})

        if input_data:
            self.input = MenuInput.loads(self, self.menu, input_data)
        else:
            self.input = MenuInput(self, self.menu, max_buttons = 15, max_actions = 10, lang_answers = False, lang_actions = True)

    def __repr__(self) -> str:
        log_info: list[str] = [super().__repr__()]
        try:
            input = self.input
            log_info.append(f"{input=}")
        except Exception as err:
            input = err
            log_info.append(f"{input=}")
        return "\n".join(log_info)

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
            "input": self.input.dumps()
        })

        return result

    def reset(self, message: str = ""):
        """
        Возвращает сценарий к начальному шагу и обновляет UI при необходимости.

        ### Аргументы:
        :param message: сообщение проекта или сообщение конкретного транспорта

        ### Пример использования:
        ```py
        session.reset(message = message)
        ```
        """
        if message:
            self.show_message(message)

        self.input.reset()
        self.input_default()

    @abstractmethod
    def action_cancel(self):
        """
        Обрабатывает пользовательское действие внутри текущего session-сценария.

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        session.action_cancel()
        ```
        """
        raise NotImplementedError()

    @abstractmethod
    def process_answer(self, bot_key: BOT_KEY, chat_id: int, answer: str):
        """
        Обрабатывает ответ пользователя в текущем runtime-контексте.

        ### Аргументы:
        :param bot_key: ключ транспорта
        :param chat_id: идентификатор чата
        :param answer: ответ пользователя

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        session.process_answer(bot_key = bot_key, chat_id = chat_id, answer = answer)
        ```
        """
        raise NotImplementedError(f"{answer=}")

    @abstractmethod
    def process_action(self, bot_key: BOT_KEY, chat_id: int, action: str) -> bool:
        """
        Обрабатывает действие меню в текущем runtime-контексте.

        ### Аргументы:
        :param bot_key: ключ транспорта
        :param chat_id: идентификатор чата
        :param action: действие меню

        :return: результат шага сессии

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        session.process_action(bot_key = bot_key, chat_id = chat_id, action = action)
        ```
        """
        raise NotImplementedError(f"{action=}")

    @abstractmethod
    def get_back(self) -> Callback | None:
        """
        Возвращает callback для кнопки возврата в меню.

        :return: callback кнопки «назад» или `None`

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        session.get_back()
        ```
        """
        raise NotImplementedError()

    @abstractmethod
    def get_answers(self) -> dict[str, JSONABLE]:
        """
        Возвращает варианты ответа для текущего меню.

        :return: варианты ответа

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        session.get_answers()
        ```
        """
        raise NotImplementedError()

    @abstractmethod
    def get_actions(self, answers: dict[str, JSONABLE] = {}) -> dict[str, JSONABLE]:
        """
        Возвращает callback-действия, доступные в текущем меню.

        ### Аргументы:
        :param answers: варианты ответа

        :return: actions

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        session.get_actions(answers = answers)
        ```
        """
        raise NotImplementedError()

    @abstractmethod
    def get_question(self, answers: dict[str, JSONABLE] = {}) -> str:
        """
        Возвращает краткое описание элемента для вывода в чат.

        ### Аргументы:
        :param answers: варианты ответа

        :return: строка вида `Филиал «Название»` или `Элемент «id»`

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        session.get_question(answers = answers)
        ```
        """
        raise NotImplementedError()

    def get_command(self, context: Context | None) -> tuple[str | Literal[""], bool]:
        """
        Возвращает строку команды, выбранной в меню.

        ### Аргументы:
        :param context: контекст обработки события

        :return: command

        ### Пример использования:
        ```py
        session.get_command(context = context)
        ```
        """
        if context is not None and context.has_event():
            return (context.event.get_text(), context.is_callback())
        else:
            return ("", False)

    def check_choosing(self) -> bool:
        """
        Проверяет значение `choosing` перед сохранением или использованием.

        :return: `True`, если значение `choosing` перед сохранением или использованием; иначе `False`

        ### Пример использования:
        ```py
        session.check_choosing()
        ```
        """
        return False

    def action_back(self):
        """
        Обрабатывает пользовательское действие внутри текущего session-сценария.

        ### Пример использования:
        ```py
        session.action_back()
        ```
        """
        action_back: Callable | None = self.get_back()

        if action_back and callable(action_back):
            action_back()

    def action_cancel(self):
        """
        Обрабатывает пользовательское действие внутри текущего session-сценария.

        ### Пример использования:
        ```py
        session.action_cancel()
        ```
        """
        self.user.stop()

    def incorrect(self):
        """
        Выполняет следующий шаг текущей сессии.

        ### Пример использования:
        ```py
        session.incorrect()
        ```
        """
        # raise Exception()
        self.show_phrase("incorrect", resend = True)
        self.input.update_menu()

    def input_update(self):
        """
        Обрабатывает пользовательское действие внутри текущего session-сценария.

        ### Пример использования:
        ```py
        session.input_update()
        ```
        """
        self.input.update_menu(self.id)

    def input_default(self, make_last: bool = True):
        """
        Показывает стандартный вопрос меню с ответами, действиями и кнопкой отмены.

        ### Аргументы:
        :param make_last: нужно ли поместить меню последним сообщением пользователя

        ### Пример использования:
        ```py
        session.input_default(make_last = make_last)
        ```
        """
        answers: dict[str, JSONABLE] = self.get_answers()
        self.input.update(
            question = self.get_question(answers),
            answers = answers,
            actions = self.get_actions(answers),
            cancel = True,
            min = 0,
            max = 1,
            make_last = make_last
        )

    def input_process(self, context: Context):
        """
        Обрабатывает пользовательское действие внутри текущего session-сценария.

        ### Аргументы:
        :param context: контекст обработки события

        ### Пример использования:
        ```py
        session.input_process(context = context)
        ```
        """

        # self.input.set_answers(self.get_answers())
        # self.input.actions = self.get_actions(self.input.answers)

        self.input.process(context)
