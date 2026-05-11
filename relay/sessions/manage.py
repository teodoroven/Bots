"""
Описывает сессии управления доменными элементами.
Модуль относится к архитектурной зоне: прикладной слой `relay`, который связывает пользователей, сессии, доменную модель, GPT, уведомления и runtime-логику приложения.

### Публичные классы
- `ManageSession`: сессия управления доменным элементом.
- `Mode`: режим управления в сессии.
- `ModeSession`: сессия с режимами управления.
- `ChangeContentSession`: сессия изменения содержимого элемента.

### Публичные функции
- Публичные функции отсутствуют.

### Связи
Используется app-layer сценариями, обработчиками, сессиями и runtime-миксинами для единого пользовательского потока между ботами, GPT и storage.
"""

from __future__ import annotations


from relay.common import BotTypes, Iterable, abstractmethod
from relay.config import (
    BUTTON_LENGTH,
    INPUT_LENGTH,
    MAX_INPUT_LENGTH,
    MAX_PRINT_LENGTH,
    get_phrase,
)
from .base import MenuSession, Session
from .level import Level, LevelSession
from relay.utils import log_warn
from relay.callback_data import Callback


class ManageSession(MenuSession):
    """
    Описывает пользовательскую или административную сессию `ManageSession`.
    Сессия хранит состояние текущего пользовательского сценария, обновляет сообщения и завершает себя через общий session lifecycle.

    ### Поля
    - `find_element`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `_next_level`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `remove`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `restore`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `enable`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `disable`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `element_id`: идентификатор объекта или связанной сущности, по которому runtime восстанавливает связь между слоями.
    - `element_class`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `always_actions`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `removed_actions`: runtime-зависимость или поле, используемое текущим session-сценарием.

    ### Методы
    - `__init__`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `dumps`: Возвращает JSON-совместимый снимок объекта для storage или callback payload.
    - `update`: Синхронизирует данные сценария с уже отправленными UI-сообщениями.
    - `update_data`: Обновляет data с учётом текущего состояния объекта.
    - `find_element`: Ищет элемент доменной модели по данным, которые пришли из вызывающего слоя.
    - `remove`: Удаляет или помечает элемент так, как ожидает текущий слой приложения.
    - `restore`: Восстанавливает ранее удалённый или сериализованный объект в рабочее состояние.
    - `enable`: Меняет флаг доступности или настройку объекта и оставляет остальное состояние без изменений.
    - `disable`: Меняет флаг доступности или настройку объекта и оставляет остальное состояние без изменений.
    - `choose_element`: Выполняет следующий шаг текущей сессии.

    ### Жизненный цикл
    Создаётся app-layer кодом, участвует в обработке пользовательского события и сохраняет изменённое состояние через существующие runtime/storage механизмы.

    ### Пример использования
    ```py
    session: ManageSession
    ```
    """
    def __init__(self, session_id: int, context: Context, data: dict, message: Message):
        """
        Создаёт session-объект `ManageSession` и сохраняет состояние пользовательского сценария между входящими событиями.

        ### Аргументы:
        :param session_id: идентификатор сессии
        :param context: контекст обработки события
        :param data: сериализованный словарь
        :param message: сообщение проекта или сообщение конкретного транспорта

        ### Пример использования:
        ```py
        session = ManageSession(session_id = session_id, context = context, data = data, message = message)
        ```
        """
        super().__init__(session_id, context, data, message)
        self.find_element = context.autocenter.find_element
        self._next_level = context.autocenter.next_level

        self.remove = context.autocenter.remove_element
        self.restore = context.autocenter.restore_element
        self.enable = context.autocenter.enable_element
        self.disable = context.autocenter.disable_element

        self.element_id: int = get_int(data, -1, "element_id")
        self.element_class: type[Element] = Element

        # Действия над элементом, которые доступны всегда
        self.always_actions: dict[str, str] = {

        }

        # Действия над элементом, которые доступны только если он не удалён/удалён
        self.removed_actions: dict[bool, dict[str, str]] = {
            True: {
                "restore": RESTORE_CALLBACK
            },
            False: {
                "remove": REMOVE_CALLBACK
            }
        }

        # Действия над элементом, которые доступны только если элемент имеет соответствующее состояние enabled
        self.enabled_actions: dict[bool, dict[str, str]] = {
            True: {
                "disable": DISABLE_CALLBACK
            },
            False: {
                "enable": ENABLE_CALLBACK
            }
        }

    def __repr__(self) -> str:
        log_info: list[str] = [super().__repr__()]
        element_id = self.element_id
        try:
            element = self.find_element(element_id)
        except Exception as err:
            element = err
        log_info.append(f"{element_id=} {element=}")
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
            "element_id": int(self.element_id)
        })

        return result

    def update(self):
        """
        Синхронизирует данные сценария с уже отправленными UI-сообщениями.

        ### Пример использования:
        ```py
        session.update()
        ```
        """
        self.input_default()

    def update_data(self, data: dict):
        """
        Обновляет data с учётом текущего состояния объекта.

        ### Аргументы:
        :param data: JSON-совместимые данные для соответствующего repository

        ### Пример использования:
        ```py
        session.update_data(data = data)
        ```
        """
        self.input.set_choosen([])
        self.element_id = get_int(data, -1, "element_id")


    @abstractmethod
    def find_element(self, element_id: int, element_class: type[Element]) -> Element | None:
        """
        Ищет доменный элемент в текущих данных объекта или storage.

        ### Аргументы:
        :param element_id: идентификатор доменного элемента
        :param element_class: element class

        :return: доменный элемент или None, если подходящей записи нет

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        session.find_element(element_id = element_id, element_class = element_class)
        ```
        """
        raise NotImplementedError()

    @abstractmethod
    def remove(self, element_id: int, from_id: int | None = None) -> bool:
        """
        Удаляет или помечает элемент так, как ожидает текущий слой приложения.

        ### Аргументы:
        :param element_id: идентификатор доменного элемента
        :param from_id: id контейнера, из которого удалён элемент

        :return: результат шага сессии

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        session.remove(element_id = element_id, from_id = from_id)
        ```
        """
        raise NotImplementedError()

    @abstractmethod
    def restore(self, element_id: int) -> int | None:
        """
        Восстанавливает ранее удалённый или сериализованный объект в рабочее состояние.

        ### Аргументы:
        :param element_id: идентификатор доменного элемента

        :return: результат шага сессии

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        session.restore(element_id = element_id)
        ```
        """
        raise NotImplementedError()

    @abstractmethod
    def enable(self, element_id: int):
        """
        Меняет флаг доступности или настройку объекта и оставляет остальное состояние без изменений.

        ### Аргументы:
        :param element_id: идентификатор доменного элемента

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        session.enable(element_id = element_id)
        ```
        """
        raise NotImplementedError()

    @abstractmethod
    def disable(self, element_id: int):
        """
        Меняет флаг доступности или настройку объекта и оставляет остальное состояние без изменений.

        ### Аргументы:
        :param element_id: идентификатор доменного элемента

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        session.disable(element_id = element_id)
        ```
        """
        raise NotImplementedError()

    @abstractmethod
    def choose_element(self):
        """
        Выполняет следующий шаг текущей сессии.

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        session.choose_element()
        ```
        """
        raise NotImplementedError()

    @abstractmethod
    def _next_level(self, bot_key: BOT_KEY, chat_id: int, session_class: type[ManageSession], data: dict | None, message: Message | None = None):
        raise NotImplementedError()

    def get_element(self) -> Element | None:
        """
        Возвращает привязанный доменный элемент.

        :return: доменный элемент

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        session.get_element()
        ```
        """
        if self.element_id >= 0:
            return self.find_element(self.element_id, self.element_class)
        else:
            raise ValueError(f"Некорректное значение атрибута {self.element_id=}")

    def validate_element(self) -> bool:
        """
        Проверяет значение перед переходом к следующему шагу сценария.

        :return: результат шага сессии

        :raises RuntimeError: если объект ещё не связан с необходимым runtime-состоянием

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        session.validate_element()
        ```
        """
        if self.get_element():
            return True
        else:
            if isinstance(self.element_id, int) and self.element_id >= 0:
                raise RuntimeError(f"Некорректное значение атрибута {self.element_id=}. Элемент с таким идентификатором не найден")
            else:
                raise ValueError(f"Некорректное значение атрибута {self.element_id=}")
            self.finish()
            return False


    def change_content(self, bot_key: BOT_KEY, chat_id: int):
        """
        Выполняет следующий шаг текущей сессии.

        ### Аргументы:
        :param bot_key: ключ транспорта
        :param chat_id: идентификатор чата

        ### Пример использования:
        ```py
        session.change_content(bot_key = bot_key, chat_id = chat_id)
        ```
        """
        self._next_level(bot_key, chat_id, ChangeContentSession, {
            "element_id": int(self.element_id),
            "mode_add": False
        })#, message = self.get_message())

    def add_content(self, bot_key: BOT_KEY, chat_id: int):
        """
        Добавляет текстовый блок в GPT-контекст или вопрос.

        ### Аргументы:
        :param bot_key: ключ транспорта, например `vkbot` или `telebot`
        :param chat_id: идентификатор чата в конкретной платформе

        ### Пример использования:
        ```py
        session.add_content(bot_key = bot_key, chat_id = chat_id)
        ```
        """
        self._next_level(bot_key, chat_id, ChangeContentSession, {
            "element_id": int(self.element_id),
            "mode_add": True
        })#, message = self.get_message())


    def get_answers(self) -> list[Never]:
        """
        Возвращает варианты ответа для текущего меню.

        :return: варианты ответа

        ### Пример использования:
        ```py
        session.get_answers()
        ```
        """
        return []

    def get_description(self) -> str:
        """
        Возвращает описание текущего режима управления.

        :return: description

        ### Пример использования:
        ```py
        session.get_description()
        ```
        """
        if self.__class__.DESCRIPTION_KEY:
            return get_phrase(self.__class__.DESCRIPTION_KEY)
        else:
            return ""

    def get_question(self, answers: dict[str, JSONABLE] = {}) -> str:
        """
        Возвращает краткое описание элемента для вывода в чат.

        ### Аргументы:
        :param answers: варианты ответа

        :return: строка вида `Филиал «Название»` или `Элемент «id»`

        ### Пример использования:
        ```py
        session.get_question(answers = answers)
        ```
        """
        element: Element | None = self.get_element()

        if element:
            description: str = self.get_description()

            if description:
                description = f"\n{description}"

            return f"{element.get_title(answers)}{description}"
        else:
            return get_phrase("element_removed").format(self.element_id)

    def get_actions(self, answers: Iterable[str] = {}) -> dict[str, str]:
        """
        Возвращает действия, доступные для выбранного доменного элемента.

        ### Аргументы:
        :param answers: варианты ответа

        :return: actions

        ### Пример использования:
        ```py
        session.get_actions(answers = answers)
        ```
        """
        result: dict[str, str] = self.always_actions.copy()
        element: Element | None = self.get_element()

        if element:
            removed: bool = element.check_removed()
            result.update(self.removed_actions[removed])

        if element and isinstance(element, InteractiveMixin):
            enabled: bool = element.enabled
            result.update(self.enabled_actions[enabled])

        return result

    def get_back(self) -> Callback | None:
        """
        Возвращает callback возврата из режима управления элементом.

        :return: callback кнопки «назад» или `None`

        ### Пример использования:
        ```py
        session.get_back()
        ```
        """
        if self.user.get_back(self.id):
            return self.finish
        else:
            return None

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
        if isinstance(context.handler, self.__class__):
            self.input_process(context)
        else:
            self.input_default()

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
        session.process_action(bot_key = bot_key, chat_id = chat_id, action = action)
        ```
        """


        try:
            if action == CHOOSE_CALLBACK:
                self.choose_element()
            elif action == CHANGE_CALLBACK:
                self.change_content(bot_key, chat_id)
                return True
            elif action == ADD_CALLBACK:
                self.add_content(bot_key, chat_id)
                return True
            elif action == REMOVE_CALLBACK:
                self.remove_element()
            elif action == RESTORE_CALLBACK:
                self.restore_element()
            elif action == ENABLE_CALLBACK:
                self.enable_element()
            elif action == DISABLE_CALLBACK:
                self.disable_element()
            else:
                return False
        except NotImplementedError:
            self.show_message("access_denied")

        self.update()
        return True


    def remove_element(self):
        """
        Удаляет элемент доменной модели из внутреннего состояния или storage.

        ### Примеры вызова:
        ```py
        session.remove_element()
        ```
        """
        element: Element | None = self.get_element()

        if element:
            self.remove(element.id, from_id = element.parent_id)
        else:
            self.validate_element()

    def restore_element(self):
        """
        Восстанавливает ранее удалённый или сериализованный объект в рабочее состояние.

        ### Пример использования:
        ```py
        session.restore_element()
        ```
        """
        element: Element | None = self.get_element()

        if not element:
            self.validate_element()
        elif element.removed_from is not None:
            self.restore(element.id)
        else:
            self.show_phrase("already_restored")

    def enable_element(self):
        """
        Меняет флаг доступности или настройку объекта и оставляет остальное состояние без изменений.

        ### Пример использования:
        ```py
        session.enable_element()
        ```
        """
        self.enable(self.element_id)
        self.update()

    def disable_element(self):
        """
        Меняет флаг доступности или настройку объекта и оставляет остальное состояние без изменений.

        ### Пример использования:
        ```py
        session.disable_element()
        ```
        """
        self.disable(self.element_id)
        self.update()


class Mode():

    """
    `Mode` хранит состояние многошагового пользовательского сценария между входящими событиями.
    Сессия хранит состояние текущего пользовательского сценария, обновляет сообщения и завершает себя через общий session lifecycle.

    ### Поля
    - `name`: человекочитаемое имя бота в конфигурации и логах.
    - `method`: runtime-зависимость или поле, используемое текущим session-сценарием.

    ### Методы
    - `__init__`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `method`: Вызывает сохранённый обработчик режима или уровня.

    ### Жизненный цикл
    Создаётся app-layer кодом, участвует в обработке пользовательского события и сохраняет изменённое состояние через существующие runtime/storage механизмы.

    ### Пример использования
    ```py
    mode: Mode
    ```
    """
    def __init__(self, name: str, method: Callable):
        """
        Создаёт session-объект `Mode` и сохраняет состояние пользовательского сценария между входящими событиями.

        ### Аргументы:
        :param name: имя
        :param method: callable-обработчик

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        mode = Mode(name = name, method = method)
        ```
        """
        self.name: str = str(name)
        self.method = method

        if not self.name:
            raise ValueError(f"Некорректное значение аргумента {name=}")

        if (not method) or not callable(method):
            raise ValueError(f"Некорректное значение аргумента {method=}")

    @abstractmethod
    def method(self: ModeSession, context: Context | None):
        """
        Вызывает сохранённый обработчик режима или уровня.

        ### Аргументы:
        :param context: контекст обработки события

        ### Пример использования:
        ```py
        mode.method(context = context)
        ```
        """


class ModeSession(ManageSession):
    """
    Описывает пользовательскую или административную сессию `ModeSession`.
    Сессия хранит состояние текущего пользовательского сценария, обновляет сообщения и завершает себя через общий session lifecycle.

    ### Поля
    - `DESCRIPTION_KEY`: ключ сериализации или transport-события, по которому объект отличает один вариант данных от другого.
    - `ALREADY_EXISTS_KEY`: ключ сериализации или transport-события, по которому объект отличает один вариант данных от другого.
    - `mode`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `next_session`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `element_class`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `modes`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `always_actions`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `choosing_actions`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `removed_actions`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `enabled_actions`: runtime-зависимость или поле, используемое текущим session-сценарием.

    ### Методы
    - `__init__`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `dumps`: Возвращает JSON-совместимый снимок объекта для storage или callback payload.
    - `reset`: Возвращает сценарий к начальному шагу и обновляет UI при необходимости.
    - `update`: Синхронизирует данные сценария с уже отправленными UI-сообщениями.
    - `check_mode`: Проверяет mode перед использованием.
    - `find_mode`: Ищет mode по данным, которые пришли из вызывающего слоя.
    - `set_mode`: Проверяет и сохраняет значение `mode` в `ModeSession`.
    - `execute_mode`: Выполняет следующий шаг текущей сессии.
    - `start_mode`: Запускает mode в runtime-потоке приложения.
    - `get_mode`: Возвращает mode из текущего состояния `ModeSession`.

    ### Жизненный цикл
    Создаётся app-layer кодом, участвует в обработке пользовательского события и сохраняет изменённое состояние через существующие runtime/storage механизмы.

    ### Пример использования
    ```py
    session: ModeSession
    ```
    """
    DESCRIPTION_KEY: str = ""
    ALREADY_EXISTS_KEY: str = "already_exists"

    def __init__(self, session_id: int, context: Context, data: dict, message: Message):
        """
        Создаёт session-объект `ModeSession` и сохраняет состояние пользовательского сценария между входящими событиями.

        ### Аргументы:
        :param session_id: идентификатор сессии
        :param context: контекст обработки события
        :param data: сериализованный словарь
        :param message: сообщение проекта или сообщение конкретного транспорта

        ### Пример использования:
        ```py
        session = ModeSession(session_id = session_id, context = context, data = data, message = message)
        ```
        """
        super().__init__(session_id, context, data, message)

        self.mode: Mode | None = None
        self.next_session: type[Session] | None = None
        self.element_class = Folder

        # Все режимы управления элементами
        self.modes: list[Mode] = [
            Mode("create", self.mode_create),
            Mode("remove", self.mode_remove),
            Mode("restore", self.mode_restore),
            Mode("enable", self.mode_enable),
            Mode("disable", self.mode_disable)
        ]

        # Режимы, доступные всегда
        self.always_actions: dict[str, str] = {
            "create": CREATE_CALLBACK
        }

        # Режимы, доступные при наличии хотя бы одного элемента
        self.choosing_actions: dict[str, str] = {

        }

        # Режимы, доступные при наличии хотя бы одного элемента с соответствующим статусом removed
        self.removed_actions: dict[bool, dict[str, str]] = {
            True: {
                "restore": RESTORE_CALLBACK
            },
            False: {
                "remove": REMOVE_CALLBACK
            }
        }

        # Режимы, доступные при наличии хотя бы одного элемента с соответствующим статусом enabled
        self.enabled_actions: dict[bool, dict[str, str]] = {
            True: {
                "disable": DISABLE_CALLBACK
            },
            False: {
                "enable": ENABLE_CALLBACK
            }
        }

    def __repr__(self) -> str:
        log_info: list[str] = [super().__repr__()]
        mode = self.mode
        log_info.append(f"{mode=}")
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
            "mode": "" if self.mode is None else self.mode.name
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
        self.set_mode()
        super().reset(message)

    def update(self):
        """
        Синхронизирует данные сценария с уже отправленными UI-сообщениями.

        ### Пример использования:
        ```py
        session.update()
        ```
        """
        if self.check_mode():
            self.process(None)
        else:
            self.input_default()


    def check_mode(self) -> bool:
        """
        Проверяет значение `mode` перед сохранением или использованием.

        :return: `True`, если значение `mode` перед сохранением или использованием; иначе `False`

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        session.check_mode()
        ```
        """
        if self.mode is None:
            return False
        elif self.mode in self.modes:
            return True
        else:
            raise ValueError(f"Некорректное значение атрибута {self.mode=}")

    def find_mode(self, mode: Literal["create", "remove", "restore"]):
        """
        Ищет mode в текущих данных объекта или storage.

        ### Аргументы:
        :param mode: режим работы session-меню

        :return: mode или None, если подходящей записи нет

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        session.find_mode(mode = mode)
        ```
        """


        for elem in self.modes:
            if elem.name == mode:
                return elem

        raise ValueError(f"Некорректное значение аргумента {mode=}")

    def set_mode(self, mode: Literal["create", "remove", "restore", ""] = ""):
        """
        Проверяет и сохраняет значение `mode`.

        ### Аргументы:
        :param mode: режим работы session-меню

        ### Пример использования:
        ```py
        session.set_mode(mode = mode)
        ```
        """
        if mode == "":
            self.mode = None
        else:
            self.mode = self.find_mode(mode)

    def execute_mode(self, context: Context | None = None):
        """
        Выполняет следующий шаг текущей сессии.

        ### Аргументы:
        :param context: контекст обработки события

        ### Пример использования:
        ```py
        session.execute_mode(context = context)
        ```
        """
        self.mode.method(context)

    def start_mode(self, mode: Literal["create", "remove", "restore"]):
        """
        Запускает сценарий обработки и подготавливает первое сообщение или задачу.

        ### Аргументы:
        :param mode: режим работы session-меню

        ### Пример использования:
        ```py
        session.start_mode(mode = mode)
        ```
        """
        self.input.set_choosen([])
        self.set_mode(mode)
        self.execute_mode()

    def get_mode(self) -> Literal["create", "remove", "restore", ""]:
        """
        Возвращает активный режим CRUD/управления.

        :return: mode

        ### Пример использования:
        ```py
        session.get_mode()
        ```
        """
        if self.check_mode():
            return self.mode.name
        else:
            return ""


    def check_choosing(self) -> bool:
        """
        Проверяет значение `choosing` перед сохранением или использованием.

        :return: `True`, если значение `choosing` перед сохранением или использованием; иначе `False`

        ### Пример использования:
        ```py
        session.check_choosing()
        ```
        """
        return self.check_mode()

    def check_choosen(self, elem: Element | InteractiveMixin) -> bool:
        """
        Проверяет значение `choosen` перед сохранением или использованием.

        ### Аргументы:
        :param elem: доменный элемент из текущего контейнера

        :return: `True`, если значение `choosen` перед сохранением или использованием; иначе `False`

        ### Пример использования:
        ```py
        session.check_choosen(elem = elem)
        ```
        """
        if isinstance(elem, InteractiveMixin):
            return elem.enabled
        else:
            return False

    def process_empty(self) -> bool:
        """
        Обрабатывает empty в текущем пользовательском или transport-layer потоке.

        :return: результат обработки, если нижележащий handler его возвращает

        ### Примеры вызова:
        ```py
        session.process_empty()
        ```
        """
        if len(self.get_answers()) > 0:
            return False

        self.show_phrase("no_elements")
        self.reset()
        return True


    def get_back(self) -> Callback | None:
        """
        Возвращает callback возврата: сброс режима или стандартный back.

        :return: callback кнопки «назад» или `None`

        ### Пример использования:
        ```py
        session.get_back()
        ```
        """
        if self.check_mode():
            return self.reset
        else:
            return super().get_back()

    @abstractmethod
    def get_restore_list(self) -> list[Element]:
        """
        Возвращает элементы, доступные для восстановления.

        :return: restore list

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        session.get_restore_list()
        ```
        """
        raise NotImplementedError()

    def get_enabled_list(self, enabled: bool) -> list[Element]:
        """
        Возвращает элементы, доступные для включения или отключения.

        ### Аргументы:
        :param enabled: нужное состояние включения элемента

        :return: enabled list

        ### Пример использования:
        ```py
        session.get_enabled_list(enabled = enabled)
        ```
        """
        element: Folder | None = self.get_element()

        if element:
            result: list[Element] = []

            for elem in element.elements:
                if isinstance(elem, InteractiveMixin) and elem.enabled == enabled:
                    result.append(elem)

            return result
        else:
            self.validate_element()
            return []

    def get_container(self) -> list[Element]:
        """
        Возвращает контейнер доменных элементов, которым управляет сессия.

        :return: container

        ### Пример использования:
        ```py
        session.get_container()
        ```
        """
        element: Folder | None = self.get_element()

        if self.mode:
            match self.mode.name:
                case "restore":
                    return self.get_restore_list()
                case "enable":
                    return self.get_enabled_list(enabled = False)
                case "disable":
                    return self.get_enabled_list(enabled = True)

        if element:
            return element.elements
        else:
            self.validate_element()
            return []

    def get_answers(self) -> dict[str, int]:
        """
        Возвращает варианты ответа для текущего меню.

        :return: варианты ответа

        ### Пример использования:
        ```py
        session.get_answers()
        ```
        """
        answers: dict[str, str] = {}
        choosen: list[str] = []
        seting_choosen: bool = not self.check_choosing()

        if seting_choosen:
            self.input.set_choosen([])

        elements: list[Element] = self.get_container()
        for i in range(len(elements)):
            elem = elements[i]
            answer: str = cut(elem.get_answer(cut_string = True), 40)
            answer_key: str = answer
            i = 1

            while answer_key in answers and i < 100:
                i += 1
                ans = cut(answer, BUTTON_LENGTH - len(f" ({i})"), dots = True)
                answer_key = f"{ans} ({i})"

            # WARNING:
            if i >= 100:
                continue

            answers[answer_key] = elem.id

            if seting_choosen and self.check_choosen(elem):
                self.input.choosen.append(answer)

        return answers

    def get_actions(self, answers: dict[str, JSONABLE] = {}) -> dict[str, str]:
        """
        Возвращает callback-действия для текущего режима управления.

        ### Аргументы:
        :param answers: варианты ответа

        :return: actions

        ### Пример использования:
        ```py
        session.get_actions(answers = answers)
        ```
        """
        element_ids: Iterable[int] = answers.values()
        elements: list[Element] = []

        for element_id in element_ids:
            element: Element | None = self.find_element(element_id)

            if element:
                elements.append(element)

        result: dict[str, str] = {}

        if not self.check_mode():
            result.update(self.always_actions)

        if len(answers) > 0:
            result.update(self.choosing_actions)

        for enabled, actions in self.enabled_actions.items():
            if any(isinstance(elem, InteractiveMixin) and elem.enabled == enabled for elem in elements):
                result.update(actions)

        for removed, actions in self.removed_actions.items():
            if any(elem.check_removed() == removed for elem in elements):
                result.update(actions)

        return result

    def get_created(self, element: Element) -> str:
        """
        Возвращает признак, что элемент был создан в этой сессии.

        ### Аргументы:
        :param element: доменный элемент

        :return: created

        ### Пример использования:
        ```py
        session.get_created(element = element)
        ```
        """
        message: str = get_phrase(element.__class__.CREATED_KEY)
        answer: str = element.get_answer(cut_string = False)

        match message.count("{}"):
            case 2:
                nominative: str = get_phrase(element.__class__.NOMINATIVE_KEY)
                return message.format(nominative, answer)
            case 1:
                return message.format(answer)
            case _:
                return message


    def get_removed(self, removed: int, not_removed: int, single_element: str = "") -> str:
        """
        Возвращает признак, что элемент был помечен удалённым.

        ### Аргументы:
        :param removed: список удалённых элементов
        :param not_removed: список элементов, которые не удалось удалить
        :param single_element: признак операции над одним доменным элементом

        :return: removed

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        session.get_removed(removed = removed, not_removed = not_removed, single_element = single_element)
        ```
        """
        element: Folder | None = self.get_element()
        element_class: type[Element] = element.elements_type if element else Element
        message: str

        if removed < 0:
            raise ValueError(f"Некорректное значение аргумента {removed=}")
        elif removed > 1:
            message = get_phrase(element_class.REMOVED_KEY).format(str(removed))
        elif removed:
            nominative: str = get_phrase(element_class.NOMINATIVE_KEY).lower()
            message = get_phrase(element_class.REMOVED_SINGLE_KEY).format(nominative.capitalize(), single_element or nominative.capitalize())
        else:
            message = get_phrase(element_class.REMOVED_NONE_KEY)

        if not_removed < 0:
            raise ValueError(f"Некорректное значение аргумента {not_removed=}")
        elif not_removed > 0:
            text: str = get_phrase(element_class.REMOVED_FAIL_KEY).format(str(not_removed))
            return f"{message}\n{text}"
        else:
            return message

    def get_changed(self, enabling: bool, changed: int, not_changed: int, single_element: str = "") -> str:
        """
        Возвращает признак, что содержимое элемента было изменено.

        ### Аргументы:
        :param enabling: True для включения элемента, False для отключения
        :param changed: список успешно изменённых элементов
        :param not_changed: список элементов без изменений
        :param single_element: признак операции над одним доменным элементом

        :return: changed

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        session.get_changed(enabling = enabling, changed = changed, not_changed = not_changed, single_element = single_element)
        ```
        """
        element: Folder | None = self.get_element()
        element_class: type[Element] = element.elements_type if element else Element
        message: str

        CHANGED_KEY: str = "enabled" if enabling else "disabled"
        CHANGED_NONE_KEY: str = "enabled_none" if enabling else "disabled_none"
        CHANGED_SINGLE_KEY: str = "enabled_single" if enabling else "disabled_single"
        CHANGED_FAIL_KEY: str = "enabled_fail" if enabling else "disabled_fail"

        if changed < 0:
            raise ValueError(f"Некорректное значение аргумента {changed=}")
        elif changed > 1:
            message = get_phrase(CHANGED_KEY).format(str(changed))
        elif changed:
            nominative: str = get_phrase(element_class.NOMINATIVE_KEY).lower()
            message = get_phrase(CHANGED_SINGLE_KEY).format(nominative.capitalize(), single_element or nominative.capitalize())
        else:
            message = get_phrase(CHANGED_NONE_KEY)

        if not_changed < 0:
            raise ValueError(f"Некорректное значение аргумента {not_changed=}")
        elif not_changed > 0:
            text: str = get_phrase(CHANGED_FAIL_KEY).format(str(not_changed))
            return f"{message}\n{text}"
        else:
            return message


    @abstractmethod
    def check_content(self, content: str) -> bool:
        """
        Проверяет, можно ли сохранить строку как содержимое доменного элемента.

        ### Аргументы:
        :param content: содержимое доменного элемента

        :return: `True`, если строку можно сохранить как содержимое; иначе `False`

        ### Пример использования:
        ```py
        session.check_content(content = content)
        ```
        """
        return len(content) < INPUT_LENGTH

    @abstractmethod
    def create_element(self, content: str) -> Element:
        """
        Создаёт доменный элемент и связывает результат с текущим объектом.

        ### Аргументы:
        :param content: содержимое доменного элемента

        :return: созданный объект: доменный элемент

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        session.create_element(content = content)
        ```
        """
        raise NotImplementedError()

    @abstractmethod
    def remove_element(self, element_id: int) -> bool:
        """
        Удаляет доменный элемент из текущего контейнера.

        ### Аргументы:
        :param element_id: идентификатор доменного элемента

        :return: результат шага сессии

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        session.remove_element(element_id = element_id)
        ```
        """
        raise NotImplementedError()

    def remove_elements(self, element_ids: list[int]) -> int:
        """
        Удаляет выбранные доменные элементы из контейнера.

        ### Аргументы:
        :param element_ids: идентификаторы доменных элементов

        :return: результат шага сессии

        ### Пример использования:
        ```py
        session.remove_elements(element_ids = element_ids)
        ```
        """
        removed: int = 0

        for element_id in element_ids:
            removed += int(self.remove_element(element_id))

        return removed

    @abstractmethod
    def enable_element(self, element_id: int) -> bool:
        """
        Меняет флаг доступности или настройку объекта и оставляет остальное состояние без изменений.

        ### Аргументы:
        :param element_id: идентификатор доменного элемента

        :return: результат шага сессии

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        session.enable_element(element_id = element_id)
        ```
        """
        raise NotImplementedError()

    @abstractmethod
    def disable_element(self, element_id: int) -> bool:
        """
        Меняет флаг доступности или настройку объекта и оставляет остальное состояние без изменений.

        ### Аргументы:
        :param element_id: идентификатор доменного элемента

        :return: результат шага сессии

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        session.disable_element(element_id = element_id)
        ```
        """
        raise NotImplementedError()

    def toggle_elements(self, element_ids: list[int], enabling: bool) -> int:
        """
        Меняет флаг доступности или настройку объекта и оставляет остальное состояние без изменений.

        ### Аргументы:
        :param element_ids: идентификаторы доменных элементов
        :param enabling: True для включения элемента, False для отключения

        :return: результат шага сессии

        ### Пример использования:
        ```py
        session.toggle_elements(element_ids = element_ids, enabling = enabling)
        ```
        """
        changed: int = 0

        for element_id in element_ids:
            if enabling:
                changed += int(self.enable_element(element_id))
            else:
                changed += int(self.disable_element(element_id))

        return changed


    def mode_create(self, context: Context | None):
        """
        Переводит session-меню в режим `create`.

        ### Аргументы:
        :param context: контекст обработки события

        ### Пример использования:
        ```py
        session.mode_create(context = context)
        ```
        """
        content, is_callback = self.get_command(context)
        folder: Folder | None = self.get_element()

        text = cut(content, MAX_PRINT_LENGTH)

        if not folder:
            self.validate_element()
            return

        elements_type: type[Filial | Date | MonthDate | Question | Question] = folder.elements_type

        if not context:
            # Первоначальный запуск режима
            if not hasattr(elements_type, "CREATING_KEY"):
                elem: str = get_phrase(elements_type.NOMINATIVE_KEY)
                message: str = get_phrase("cant_create").format(elem, folder.get_answer())
                self.show_message(message)
                self.reset()
                return

            create_question: str = get_phrase(elements_type.CREATING_KEY)
            actions: dict = {}

            empty_allowed: bool = elements_type.check_content("")

            if empty_allowed:
                actions.update({
                    "empty": EMPTY_CALLBACK
                })

            self.input.update(create_question, answers = [], choosen = [], actions = actions, cancel = True, back = True)
            return
        elif is_callback:
            callback_data: str = context.get_callback_string(1)

            if callback_data == EMPTY_CALLBACK:
                content = ""
            else:
                # failed
                context.remove_handler()
                return
        elif not elements_type.check_content(content):
            self.incorrect()
            return

        element: Element = self.create_element(content)
        message: str = self.get_created(element)
        self.reset(message)

    def mode_remove(self, context: Context | None):
        """
        Переводит session-меню в режим `remove`.

        ### Аргументы:
        :param context: контекст обработки события

        ### Пример использования:
        ```py
        session.mode_remove(context = context)
        ```
        """
        if self.process_empty():
            return

        if not context:
            # Первоначальный запуск режима
            remove_question: str = get_phrase("remove_question")
            answers: dict[str, str] = self.get_answers()
            self.input.update(remove_question, answers = answers, actions = [], choosen = [], cancel = True, back = True, max = max(2, len(answers)))
            return
        elif context.is_callback():
            callback_data: str = context.get_callback_string()

            if callback_data == CONFIRM_CALLBACK:
                options: list[JSONABLE] = []

                for answer in self.input.choosen:
                    options.append(self.input.get_answer(answer))

                removed: int = self.remove_elements(options)
                not_removed: int = len(options) - removed
                message: str = self.get_removed(removed, not_removed, options[0] if options else "")
                self.reset(message)
                return

        context.remove_handler()
        return

    def mode_restore(self, context: Context | None):
        """
        Переводит session-меню в режим `restore`.

        ### Аргументы:
        :param context: контекст обработки события

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        session.mode_restore(context = context)
        ```
        """
        raise NotImplementedError()

    def mode_enabling(self, context: Context | None, enable_question: str, enabling: bool):
        """
        Переводит session-меню в режим `enabling`.

        ### Аргументы:
        :param context: контекст обработки события
        :param enable_question: enable question
        :param enabling: True для включения элемента, False для отключения

        ### Пример использования:
        ```py
        session.mode_enabling(context = context, enable_question = enable_question, enabling = enabling)
        ```
        """
        if self.process_empty():
            return

        if not context:
            # Первоначальный запуск режима
            answers: dict[str, str] = self.get_answers()
            self.input.update(get_phrase(enable_question), answers = answers, actions = [], choosen = [], cancel = True, back = True, max = max(2, len(answers)))
            return
        elif context.is_callback():
            callback_data: str = context.get_callback_string()

            if callback_data == CONFIRM_CALLBACK:
                options: list[JSONABLE] = []

                for answer in self.input.choosen:
                    options.append(self.input.get_answer(answer))

                changed: int = self.toggle_elements(options, enabling)
                not_changed: int = len(options) - changed
                message: str = self.get_changed(enabling, changed, not_changed, options[0] if options else "")
                self.reset(message)
                return

        context.remove_handler()
        return

    def mode_enable(self, context: Context | None):
        """
        Переводит session-меню в режим `enable`.

        ### Аргументы:
        :param context: контекст обработки события

        ### Пример использования:
        ```py
        session.mode_enable(context = context)
        ```
        """
        self.mode_enabling(context, "enable_question", True)

    def mode_disable(self, context: Context | None):
        """
        Переводит session-меню в режим `disable`.

        ### Аргументы:
        :param context: контекст обработки события

        ### Пример использования:
        ```py
        session.mode_disable(context = context)
        ```
        """
        self.mode_enabling(context, "disable_question", False)


    def process(self, context: Context | None):
        """
        Передаёт текущий `Context` выбранному обработчику и обновляет `context.handler` по результату.

        ### Аргументы:
        :param context: контекст обработки события

        ### Пример использования:
        ```py
        session.process(context = context)
        ```
        """

        # text = cut(context.event.get_text(), 60) if context.has_event() else None

        if self.check_mode():
            self.execute_mode(context)

            if context:
                if context.has_handler():
                    # success
                    return
                else:
                    context.set_handler(self)

        if context is None:
            self.input_default()
        else:
            super().process(context)

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
        session.process_action(bot_key = bot_key, chat_id = chat_id, action = action)
        ```
        """


        if action == CREATE_CALLBACK:
            self.start_mode("create")
        elif action == CHANGE_CALLBACK:
            self.change_content(bot_key, chat_id)
        elif action == REMOVE_CALLBACK:
            self.start_mode("remove")
        elif action == RESTORE_CALLBACK:
            self.start_mode("restore")
        elif action == ENABLE_CALLBACK:
            self.start_mode("enable")
        elif action == DISABLE_CALLBACK:
            self.start_mode("disable")
        else:
            return False

        return True

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
        session.process_answer(bot_key = bot_key, chat_id = chat_id, answer = answer)
        ```
        """
        if answer in self.get_answers().values():
            if self.next_session is None:
                session = self
                log_warn(f"Нет следующего уровня {session=} {answer=}")
                self.show_phrase("access_denied")
                self.input_default()
            else:
                self.next_level(bot_key, chat_id, answer)
            return True

        self.input_default()
        return False

    def get_next_level(self, element_id: int) -> dict[str, int]:
        """
        Возвращает следующий шаг сценария управления.

        ### Аргументы:
        :param element_id: идентификатор доменного элемента

        :return: next level

        ### Пример использования:
        ```py
        session.get_next_level(element_id = element_id)
        ```
        """
        return {
            "element_id": int(element_id)
        }

    def next_level(self, bot_key: BOT_KEY, chat_id: int, element_id: int) -> bool:
        """
        Переходит к следующему уровню пользовательского сценария.

        ### Аргументы:
        :param bot_key: ключ транспорта
        :param chat_id: идентификатор чата
        :param element_id: идентификатор доменного элемента

        :return: результат шага сессии

        ### Пример использования:
        ```py
        session.next_level(bot_key = bot_key, chat_id = chat_id, element_id = element_id)
        ```
        """
        self._next_level(bot_key, chat_id, self.next_session, self.get_next_level(element_id))

    @abstractmethod
    def _next_level(self, bot_key: BOT_KEY, chat_id: int, session_class: type[ManageSession], data: dict | None):
        raise NotImplementedError()


class ChangeContentSession(LevelSession):

    """
    Описывает пользовательскую или административную сессию `ChangeContentSession`.
    Сессия хранит состояние текущего пользовательского сценария, обновляет сообщения и завершает себя через общий session lifecycle.

    ### Поля
    - `find_element`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `change_element`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `extend_element`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `element_id`: идентификатор объекта или связанной сущности, по которому runtime восстанавливает связь между слоями.
    - `mode_add`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `levels`: runtime-зависимость или поле, используемое текущим session-сценарием.

    ### Методы
    - `__init__`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `find_element`: Ищет элемент доменной модели по данным, которые пришли из вызывающего слоя.
    - `change_element`: Выполняет следующий шаг текущей сессии.
    - `extend_element`: Выполняет следующий шаг текущей сессии.
    - `check`: Проверяет значение по правилам текущего класса и не изменяет состояние.
    - `dumps`: Возвращает JSON-совместимый снимок объекта для storage или callback payload.
    - `get_element`: Возвращает элемент доменной модели из текущего состояния `ChangeContentSession`.
    - `validate_element`: Проверяет ограничения для элемент доменной модели и при необходимости завершает лишние объекты.
    - `check_content`: Проверяет текст доменного элемента перед сохранением.
    - `set_content`: Проверяет и сохраняет текст доменного элемента в состоянии `ChangeContentSession`.

    ### Жизненный цикл
    Создаётся app-layer кодом, участвует в обработке пользовательского события и сохраняет изменённое состояние через существующие runtime/storage механизмы.

    ### Пример использования
    ```py
    session: ChangeContentSession
    ```
    """
    def __init__(self, session_id: int, context: Context, data: dict, message: Message):
        """
        Создаёт session-объект `ChangeContentSession` и сохраняет состояние пользовательского сценария между входящими событиями.

        ### Аргументы:
        :param session_id: идентификатор сессии
        :param context: контекст обработки события
        :param data: сериализованный словарь
        :param message: сообщение проекта или сообщение конкретного транспорта

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        session = ChangeContentSession(session_id = session_id, context = context, data = data, message = message)
        ```
        """
        super().__init__(session_id, context, data, message)
        self.find_element = context.autocenter.find_element
        self.change_element = context.autocenter.change_element
        self.extend_element = context.autocenter.extend_element

        self.element_id: int = get_int(data, -1, "element_id")
        self.mode_add: bool | None = get_from(data, "mode_add", types = (bool,), default = None)

        if self.mode_add is None:
            mode_add = data.get("mode_add")
            raise ValueError(f"Некорректное значение под ключом {mode_add=} аргумента {data=}")

        self.levels: list[Level] = [
            Level(self.ask_content)
        ]

        self.load_levels(data)

    def __repr__(self) -> str:
        log_info: list[str] = [super().__repr__()]
        mode_add = self.mode_add
        log_info.append(f"{mode_add=}")
        return "\n".join(log_info)


    @abstractmethod
    def find_element(self, element_id: int, element_class: type[Element]) -> Element | None:
        """
        Ищет доменный элемент в текущих данных объекта или storage.

        ### Аргументы:
        :param element_id: идентификатор доменного элемента
        :param element_class: element class

        :return: доменный элемент или None, если подходящей записи нет

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        session.find_element(element_id = element_id, element_class = element_class)
        ```
        """
        raise NotImplementedError()

    @abstractmethod
    def change_element(self, element_id: int, content: str) -> bool:
        """
        Выполняет следующий шаг текущей сессии.

        ### Аргументы:
        :param element_id: идентификатор доменного элемента
        :param content: содержимое доменного элемента

        :return: результат шага сессии

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        session.change_element(element_id = element_id, content = content)
        ```
        """
        raise NotImplementedError()

    @abstractmethod
    def extend_element(self, element_id: int, content: str) -> bool:
        """
        Выполняет следующий шаг текущей сессии.

        ### Аргументы:
        :param element_id: идентификатор доменного элемента
        :param content: содержимое доменного элемента

        :return: результат шага сессии

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        session.extend_element(element_id = element_id, content = content)
        ```
        """
        raise NotImplementedError()


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
        if context.has_event() and self.check_asked(self.levels[0]):
            for attachment in context.event.attachments:
                if isinstance(attachment, Telebot.DocAttachment):
                    return True
        return super().check(context)

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
            "element_id": int(self.element_id),
            "mode_add": bool(self.mode_add)
        })

        return result

    def get_element(self) -> Element | None:
        """
        Возвращает привязанный доменный элемент.

        :return: доменный элемент

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        session.get_element()
        ```
        """
        if self.element_id >= 0:
            return self.find_element(self.element_id)
        else:
            raise ValueError(f"Некорректное значение атрибута {self.element_id=}")

    def validate_element(self) -> bool:
        """
        Проверяет значение перед переходом к следующему шагу сценария.

        :return: результат шага сессии

        :raises RuntimeError: если объект ещё не связан с необходимым runtime-состоянием

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        session.validate_element()
        ```
        """
        if self.get_element():
            return True
        else:
            if isinstance(self.element_id, int) and self.element_id >= 0:
                raise RuntimeError(f"Некорректное значение атрибута {self.element_id=}. Элемент с таким идентификатором не найден")
            else:
                raise ValueError(f"Некорректное значение атрибута {self.element_id=}")
            self.finish()
            return False

    def check_content(self, content: str) -> bool:
        """
        Проверяет, можно ли сохранить строку как содержимое доменного элемента.

        ### Аргументы:
        :param content: содержимое доменного элемента

        :return: `True`, если строку можно сохранить как содержимое; иначе `False`

        ### Пример использования:
        ```py
        session.check_content(content = content)
        ```
        """
        if len(content) > MAX_INPUT_LENGTH:
            return False

        element: Element | None = self.get_element()

        if element:
            if self.mode_add:
                return element.__class__.check_content_add(content)
            else:
                return element.__class__.check_content(content)
        else:
            self.validate_element()
            return False

    def set_content(self, content: str) -> bool:
        """
        Проверяет и записывает текст доменного элемента.

        ### Аргументы:
        :param content: содержимое доменного элемента

        :return: результат шага сессии

        ### Пример использования:
        ```py
        session.set_content(content = content)
        ```
        """
        return self.change_element(self.element_id, content)

    def add_content(self, content: str) -> bool:
        """
        Добавляет текстовое содержимое к доменному элементу.

        ### Аргументы:
        :param content: содержимое доменного элемента

        :return: результат шага сессии

        ### Пример использования:
        ```py
        session.add_content(content = content)
        ```
        """
        return self.extend_element(self.element_id, content)

    def check_empty_allowed(self) -> bool:
        """
        Проверяет значение `empty allowed` перед сохранением или использованием.

        :return: `True`, если значение `empty allowed` перед сохранением или использованием; иначе `False`

        ### Пример использования:
        ```py
        session.check_empty_allowed()
        ```
        """
        return self.check_content("")

    def input_default(self, make_last: bool = True):
        """
        Показывает форму добавления или редактирования текущего доменного элемента.

        ### Аргументы:
        :param make_last: нужно ли переместить меню в конец истории сообщений

        ### Пример использования:
        ```py
        session.input_default(make_last = make_last)
        ```
        """
        element: Element | None = self.get_element()

        if not element:
            self.validate_element()
            return

        edit_question: str = get_phrase(element.__class__.ADD_KEY) if self.mode_add else get_phrase(element.__class__.EDIT_KEY)
        actions: dict = {}

        if self.check_empty_allowed():
            actions.update({
                "empty": EMPTY_CALLBACK
            })

        self.input.update(edit_question, answers = [], choosen = [], actions = actions, cancel = True, back = True)

    def ask_content(self, level: Level, context: Context | None):
        """
        Показывает пользователю вопрос для шага `content`.

        ### Аргументы:
        :param level: уровень сценария
        :param context: контекст обработки события

        :return: результат шага сессии

        ### Пример использования:
        ```py
        session.ask_content(level = level, context = context)
        ```
        """
        def get_content() -> str | None:
            for attachment in context.event.get_attachments():
                try:
                    filename: str = attachment.make_filename(context.bot, ATTACHMENTS_FOLDER)

                    if isfile(filename) and only_extension(filename).lower() == DOC_EXTENSIONS[1]:
                        with open(filename, "r", encoding = "utf-8") as file:
                            return file.read()
                except Exception as err:
                    log_warn(f"Возникла ошибка при обработке {attachment=}")

            return None

        if self.check_confirmed(level):
            self.next_level(context)
            return
        elif context and context.has_event():
            content, is_callback = self.get_command(context)

            if self.check_asked(level):
                if is_callback:
                    callback_data: str = context.get_callback_string(1)

                    if callback_data == EMPTY_CALLBACK:
                        content = ""
                    else:
                        context.remove_handler()
                        return
                elif context.event.attachments:
                    content = get_content()

                if isinstance(content, str) and self.check_content(content):
                    self.set_value(level, content)
                    self.set_asked(level, False)
                    self.set_confirmed(level, True)
                    self.next_level(None)
                    return
                else:
                    self.incorrect()

        self.input_default()
        self.set_asked(level, True)

    def final_level(self):
        """
        Завершает текущий уровень сценария и передаёт управление дальше.

        ### Пример использования:
        ```py
        session.final_level()
        ```
        """
        element: Element | None = self.get_element()

        if not element:
            self.validate_element()
            return

        content: str | None = self.get_value(self.levels[0], str)

        if content is None:
            self.show_phrase("content_required")
            self.reset()
            return

        message: str = get_phrase("edit_failed")

        if self.mode_add:
            if self.add_content(content):
                message = get_phrase(element.__class__.ADDED_KEY)
        elif self.set_content(content):
            message = get_phrase(element.__class__.EDITED_KEY)

        if "{}" in message:
            message = message.format(element.get_answer(cut_string = False))

        self.show_message(message)
        self.finish()
