"""
Описывает пошаговый механизм уровней сессии.
Модуль относится к архитектурной зоне: прикладной слой `relay`, который связывает пользователей, сессии, доменную модель, GPT, уведомления и runtime-логику приложения.

### Публичные классы
- `Stage`: этап пошаговой сессии.
- `Value`: значение этапа пошаговой сессии.
- `Level`: уровень пошаговой сессии.
- `LevelSession`: сессия с уровнями ввода.

### Публичные функции
- Публичные функции отсутствуют.

### Связи
Используется app-layer сценариями, обработчиками, сессиями и runtime-миксинами для единого пользовательского потока между ботами, GPT и storage.
"""

from __future__ import annotations


from relay.common import (
    Any,
    BotTypes,
    Callable,
    abstractmethod,
    json,
)
from .base import MenuSession
from relay.utils import log_warn
from relay.callback_data import Callback


class Stage():
    """
    `Stage` хранит состояние многошагового пользовательского сценария между входящими событиями.
    Сессия хранит состояние текущего пользовательского сценария, обновляет сообщения и завершает себя через общий session lifecycle.

    ### Поля
    - `asked`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `confirming`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `confirmed`: runtime-зависимость или поле, используемое текущим session-сценарием.

    ### Методы
    - `__init__`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `dumps`: Возвращает JSON-совместимый снимок объекта для storage или callback payload.
    - `reset`: Возвращает сценарий к начальному шагу и обновляет UI при необходимости.
    - `load`: Загружает JSON-представление и восстанавливает поля объекта.

    ### Жизненный цикл
    Создаётся app-layer кодом, участвует в обработке пользовательского события и сохраняет изменённое состояние через существующие runtime/storage механизмы.

    ### Пример использования
    ```py
    stage: Stage
    ```
    """

    def __init__(self, asked: bool = False, confirming: bool = False, confirmed: bool = False):
        """
        Создаёт session-объект `Stage` и сохраняет состояние пользовательского сценария между входящими событиями.

        ### Аргументы:
        :param asked: был ли уже задан вопрос пользователю
        :param confirming: ожидается ли подтверждение пользователя
        :param confirmed: подтверждено ли действие пользователем

        ### Пример использования:
        ```py
        stage = Stage(asked = asked, confirming = confirming, confirmed = confirmed)
        ```
        """
        self.asked: bool = bool(asked)
        self.confirming: bool = bool(confirming)
        self.confirmed: bool = bool(confirmed)

    def dumps(self) -> BotTypes.STAGE_TYPE:
        """
        Возвращает JSON-совместимый снимок объекта для storage или callback payload.

        :return: JSON-совместимый словарь для сохранения или передачи между слоями

        ### Пример использования:
        ```py
        stage.dumps()
        ```
        """
        return {
            "asked": bool(self.asked),
            "confirming": bool(self.confirming),
            "confirmed": bool(self.confirmed)
        }

    def reset(self):
        """
        Возвращает сценарий к начальному шагу и обновляет UI при необходимости.

        ### Пример использования:
        ```py
        stage.reset()
        ```
        """
        self.asked = False
        self.confirming = False
        self.confirmed = False

    def load(self, data: BotTypes.STAGE_TYPE):
        """
        Загружает JSON-представление и восстанавливает поля объекта.

        ### Аргументы:
        :param data: сериализованный словарь

        ### Пример использования:
        ```py
        stage.load(data = data)
        ```
        """


        for key in ("asked", "confirming", "confirmed"):
            if key in data and isinstance(data[key], bool):
                setattr(self, key, data[key])

    def __repr__(self):
        return f"Stage (asked={self.asked}, confirming={self.confirming}, confirmed={self.confirmed})"


class Value():
    """
    `Value` хранит состояние многошагового пользовательского сценария между входящими событиями.
    Сессия хранит состояние текущего пользовательского сценария, обновляет сообщения и завершает себя через общий session lifecycle.

    ### Поля
    - `value`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `stage`: runtime-зависимость или поле, используемое текущим session-сценарием.

    ### Методы
    - `loads`: Восстанавливает объект из JSON-совместимого словаря.
    - `__init__`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `dumps`: Возвращает JSON-совместимый снимок объекта для storage или callback payload.

    ### Жизненный цикл
    Создаётся app-layer кодом, участвует в обработке пользовательского события и сохраняет изменённое состояние через существующие runtime/storage механизмы.

    ### Пример использования
    ```py
    value: Value
    ```
    """

    @classmethod
    def loads(cls, data: BotTypes.VALUE_TYPE) -> Value:
        """
        Восстанавливает объект из JSON-совместимого словаря.

        ### Аргументы:
        :param data: сериализованный словарь

        :return: восстановленный объект или загруженное состояние

        ### Пример использования:
        ```py
        Value.loads(data = data)
        ```
        """
        value: str = data.get("value")
        stage: BotTypes.STAGE_TYPE = data.get("stage")
        try:
            value = json.loads(value)
        except:
            value = None
        return cls(value, Stage(**stage))

    def __init__(self, value: Any | None, stage: Stage):
        """
        Создаёт session-объект `Value` и сохраняет состояние пользовательского сценария между входящими событиями.

        ### Аргументы:
        :param value: значение уровня или настройки
        :param stage: этап прохождения сценария

        ### Пример использования:
        ```py
        value = Value(value = value, stage = stage)
        ```
        """
        self.value: Any | None = value
        self.stage: Stage = stage

    def __repr__(self):
        asked: bool = self.stage.asked
        confirming: bool = self.stage.confirming
        return  f"{self.__class__.__name__}({self.value}) {asked=} {confirming=}"

    def dumps(self) -> BotTypes.VALUE_TYPE:
        """
        Возвращает JSON-совместимый снимок объекта для storage или callback payload.

        :return: JSON-совместимый словарь для сохранения или передачи между слоями

        ### Пример использования:
        ```py
        value.dumps()
        ```
        """
        return {
            # "type": self.__class__.__name__,
            "value": json.dumps(self.value),
            "stage": self.stage.dumps()
        }


class Level():

    """
    `Level` хранит состояние многошагового пользовательского сценария между входящими событиями.
    Сессия хранит состояние текущего пользовательского сценария, обновляет сообщения и завершает себя через общий session lifecycle.

    ### Поля
    - `value`: runtime-зависимость или поле, используемое текущим session-сценарием.

    ### Методы
    - `__init__`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `dumps`: Возвращает JSON-совместимый снимок объекта для storage или callback payload.
    - `reset`: Возвращает сценарий к начальному шагу и обновляет UI при необходимости.
    - `load`: Загружает JSON-представление и восстанавливает поля объекта.
    - `get_value`: Возвращает value из текущего состояния `Level`.
    - `method`: Вызывает сохранённый обработчик режима или уровня.
    - `set_method`: Проверяет и сохраняет значение `method` в `Level`.
    - `get_method`: Возвращает method из текущего состояния `Level`.
    - `call_method`: Вызывает обработчик текущего уровня с переданным context.

    ### Жизненный цикл
    Создаётся app-layer кодом, участвует в обработке пользовательского события и сохраняет изменённое состояние через существующие runtime/storage механизмы.

    ### Пример использования
    ```py
    level: Level
    ```
    """
    def __init__(self, method: Callable[None]):
        """
        Создаёт session-объект `Level` и сохраняет состояние пользовательского сценария между входящими событиями.

        ### Аргументы:
        :param method: callable-обработчик

        ### Пример использования:
        ```py
        level = Level(method = method)
        ```
        """
        self.value: Value | None = None
        self.set_method(method)

    def __repr__(self) -> str:
        value = self.value
        try:
            method = self.method.__name__
        except Exception as err:
            method = err
        return f"{self.__class__.__name__}({method=} {value=})"

    def dumps(self) -> BotTypes.LEVEL_TYPE:
        """
        Возвращает JSON-совместимый снимок объекта для storage или callback payload.

        :return: JSON-совместимый словарь для сохранения или передачи между слоями

        ### Пример использования:
        ```py
        level.dumps()
        ```
        """
        return {
            "value": self.get_value().dumps()
        }

    def reset(self):
        """
        Возвращает сценарий к начальному шагу и обновляет UI при необходимости.

        ### Пример использования:
        ```py
        level.reset()
        ```
        """
        self.value.stage.reset()

    def load(self, data: BotTypes.LEVEL_TYPE = {}):
        """
        Загружает JSON-представление и восстанавливает поля объекта.

        ### Аргументы:
        :param data: сериализованный словарь

        ### Пример использования:
        ```py
        level.load(data = data)
        ```
        """
        value_data: BotTypes.VALUE_TYPE = data.get("value", {})

        if value_data and isinstance(value_data, dict):
            self.value = Value.loads(value_data)
        else:
            self.value = Value(None, Stage())

    def get_value(self) -> Value:
        """
        Возвращает сохранённое значение шага state-machine.

        :return: value

        :raises RuntimeError: если объект ещё не связан с необходимым runtime-состоянием

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        level.get_value()
        ```
        """
        if isinstance(self.value, Value):
            return self.value
        elif self.value is None:
            raise RuntimeError(f"Сначала вызовите метод load у объекта {self}")
        else:
            raise ValueError(f"Некорректное значение атрибута {self.value=}")

    @abstractmethod
    def method(self: LevelSession, level: Level, context: Context | None):
        """
        Вызывает сохранённый обработчик режима или уровня.

        ### Аргументы:
        :param level: уровень сценария
        :param context: контекст обработки события

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        level.method(level = level, context = context)
        ```
        """
        raise NotImplementedError()

    def set_method(self, method: Callable[None]):
        """
        Проверяет и сохраняет значение `method`.

        ### Аргументы:
        :param method: callable-обработчик

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        level.set_method(method = method)
        ```
        """
        if method and callable(method):
            self.method = method
        else:
            raise ValueError(f"Некорректное значение аргумента {method=}")

    def get_method(self) -> Callable[None]:
        """
        Возвращает обработчик, привязанный к текущему шагу.

        :return: method

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        level.get_method()
        ```
        """
        if self.method and callable(self.method):
            return self.method
        else:
            raise ValueError(f"Некорректное значение атрибута {self.method=}")

    def call_method(self, context: Context | None):
        """
        Вызывает обработчик текущего уровня с переданным context.

        ### Аргументы:
        :param context: контекст обработки события

        ### Пример использования:
        ```py
        level.call_method(context = context)
        ```
        """
        method: Callable = self.get_method()
        method(self, context)


class LevelSession(MenuSession):

    """
    Описывает пользовательскую или административную сессию `LevelSession`.
    Сессия хранит состояние текущего пользовательского сценария, обновляет сообщения и завершает себя через общий session lifecycle.

    ### Поля
    - `level`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `levels`: runtime-зависимость или поле, используемое текущим session-сценарием.

    ### Методы
    - `__init__`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `load_levels`: Загружает levels из storage.
    - `dumps`: Возвращает JSON-совместимый снимок объекта для storage или callback payload.
    - `reset`: Возвращает сценарий к начальному шагу и обновляет UI при необходимости.
    - `get_back`: Возвращает back из текущего состояния `LevelSession`.
    - `level_1`: Выполняет следующий шаг текущей сессии.
    - `check_level`: Проверяет level перед использованием.
    - `set_level`: Проверяет и сохраняет значение `level` в `LevelSession`.
    - `get_level`: Возвращает level из текущего состояния `LevelSession`.
    - `update`: Синхронизирует данные сценария с уже отправленными UI-сообщениями.

    ### Жизненный цикл
    Создаётся app-layer кодом, участвует в обработке пользовательского события и сохраняет изменённое состояние через существующие runtime/storage механизмы.

    ### Пример использования
    ```py
    session: LevelSession
    ```
    """
    def __init__(self, session_id: int, context: Context, data: dict, message: Message):
        """
        Создаёт session-объект `LevelSession` и сохраняет состояние пользовательского сценария между входящими событиями.

        ### Аргументы:
        :param session_id: идентификатор сессии
        :param context: контекст обработки события
        :param data: сериализованный словарь
        :param message: сообщение проекта или сообщение конкретного транспорта

        ### Пример использования:
        ```py
        session = LevelSession(session_id = session_id, context = context, data = data, message = message)
        ```
        """
        super().__init__(session_id, context, data, message)
        self.level: int = get_int(data, 0, "level")

        self.levels: list[Level] = [
            Level(self.level_1)
        ]

        # self.load_levels(data)

    def __repr__(self) -> str:
        log_info: list[str] = [super().__repr__()]
        for i, level in enumerate(self.levels):
            log_info.append(f"level{i}={repr(level)}")
        return "\n".join(log_info)

    def load_levels(self, data: BotTypes.SESSION_TYPE):
        """
        Загружает levels из storage.

        ### Аргументы:
        :param data: JSON-совместимые данные для соответствующего repository

        ### Пример использования:
        ```py
        session.load_levels(data = data)
        ```
        """
        levels_data: list[BotTypes.LEVEL_TYPE] = []

        for level_data in data.get("levels", []):
            if level_data and isinstance(level_data, dict):
                levels_data.append(level_data)
            else:
                levels = data.get("levels")
                log_warn(f"Некорректное значение под ключом {levels=} аргумента {data=}")

        for i in range(len(self.levels)):
            level: Level = self.levels[i]

            if i < len(levels_data):
                level_data = levels_data[i]
                level.load(level_data)
            else:
                level.load()

        if levels_data and len(levels_data) != len(self.levels):
            levels = data.get("levels")
            log_warn(f"Некорректное значение под ключом {levels=} аргумента {data=}. Несоответствие длины списка")

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
            "input": self.input.dumps(),
            "level": int(self.level),
            "levels": [level.dumps() for level in self.levels]
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
        super().reset(message)
        self.level = 0

    def get_back(self) -> Callback | None:
        """
        Возвращает callback перехода на предыдущий шаг сценария.

        :return: callback кнопки «назад» или `None`

        ### Пример использования:
        ```py
        session.get_back()
        ```
        """
        return self.prev_level

    @abstractmethod
    def level_1(self, level: Level, context: Context | None):
        """
        Выполняет следующий шаг текущей сессии.

        ### Аргументы:
        :param level: уровень сценария
        :param context: контекст обработки события

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        session.level_1(level = level, context = context)
        ```
        """
        raise NotImplementedError()

    def check_level(self, level: int) -> bool:
        """
        Проверяет значение `level` перед сохранением или использованием.

        ### Аргументы:
        :param level: уровень сценария

        :return: `True`, если значение `level` перед сохранением или использованием; иначе `False`

        ### Пример использования:
        ```py
        session.check_level(level = level)
        ```
        """
        return level >= 0 and level < len(self.levels)

    def set_level(self, level: int):
        """
        Проверяет и сохраняет значение `level`.

        ### Аргументы:
        :param level: уровень сценария

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        session.set_level(level = level)
        ```
        """
        level = int(level)

        if self.check_level(level):
            self.level = level
        else:
            raise ValueError(f"Некорректное значение аргумента {level=}")

    def _get_level(self) -> int:
        level: int = int(self.level)

        if self.check_level(level):
            return level
        else:
            raise ValueError(f"Некорректное значение атрибута {self.level=}")

    def get_level(self) -> Level:
        """
        Возвращает индекс текущего шага сценария.

        :return: level

        ### Пример использования:
        ```py
        session.get_level()
        ```
        """
        level: int = self._get_level()
        return self.levels[level]

    def update(self):
        """
        Синхронизирует данные сценария с уже отправленными UI-сообщениями.

        ### Пример использования:
        ```py
        session.update()
        ```
        """
        self.get_level().call_method(None)

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
        text: str | None = context.event.text if context and context.event else None

        level: Level = self.get_level()
        level.call_method(context)

        if context and not context.has_handler():
            if context.is_callback():
                args = context.get_callback_data()

                context.set_handler(self)
                self.input_process(context)

            if context.has_handler():
                return  # success

            self.incorrect()


    @abstractmethod
    def final_level(self):
        """
        Завершает текущий уровень сценария и передаёт управление дальше.

        ### Пример использования:
        ```py
        session.final_level()
        ```
        """
        self.finish()

    def change_level(self, level: int, reset: bool = True):
        """
        Меняет активный уровень пользовательского сценария.

        ### Аргументы:
        :param level: уровень сценария
        :param reset: нужно ли сбросить текущее состояние

        ### Пример использования:
        ```py
        session.change_level(level = level, reset = reset)
        ```
        """
        self.set_level(level)
        level: Level = self.get_level()
        level.reset() if reset else None
        self.input.reset()
        self.process(None)

    def next_level(self, context: Context | None):
        """
        Переходит к следующему уровню пользовательского сценария.

        ### Аргументы:
        :param context: контекст обработки события

        ### Пример использования:
        ```py
        session.next_level(context = context)
        ```
        """


        current_level: int = self._get_level()

        if self.check_level(current_level + 1):
            self.change_level(current_level + 1)
        else:
            self.final_level()

    def prev_level(self):
        """
        Возвращает сценарий на предыдущий уровень.

        ### Пример использования:
        ```py
        session.prev_level()
        ```
        """
        current_level: int = self._get_level()

        if current_level == 0 or not self.check_level(current_level - 1):
            self.finish()
        else:
            self.change_level(current_level - 1)


    def confirmed(self, context: Context | None) -> bool | None:
        """
        Обрабатывает подтверждение выбранного действия.

        ### Аргументы:
        :param context: контекст обработки события

        :return: результат шага сессии

        ### Пример использования:
        ```py
        session.confirmed(context = context)
        ```
        """
        if context is None:
            return None
        else:
            return self.input.check_confrimed(context.event.text, context.is_callback())


    def check_confirmed(self, level: Level) -> bool:
        """
        Проверяет значение `confirmed` перед сохранением или использованием.

        ### Аргументы:
        :param level: уровень сценария

        :return: `True`, если значение `confirmed` перед сохранением или использованием; иначе `False`

        ### Пример использования:
        ```py
        session.check_confirmed(level = level)
        ```
        """
        return bool(level.value.stage.confirmed)

    def check_confirming(self, level: Level) -> bool:
        """
        Проверяет значение `confirming` перед сохранением или использованием.

        ### Аргументы:
        :param level: уровень сценария

        :return: `True`, если значение `confirming` перед сохранением или использованием; иначе `False`

        ### Пример использования:
        ```py
        session.check_confirming(level = level)
        ```
        """
        return bool(level.value.stage.confirming)

    def check_asked(self, level: Level) -> bool:
        """
        Проверяет значение `asked` перед сохранением или использованием.

        ### Аргументы:
        :param level: уровень сценария

        :return: `True`, если значение `asked` перед сохранением или использованием; иначе `False`

        ### Пример использования:
        ```py
        session.check_asked(level = level)
        ```
        """
        return bool(level.value.stage.asked)

    def set_confirmed(self, level: Level, confirmed: bool):
        """
        Проверяет и сохраняет значение `confirmed`.

        ### Аргументы:
        :param level: уровень сценария
        :param confirmed: подтверждено ли действие пользователем

        ### Пример использования:
        ```py
        session.set_confirmed(level = level, confirmed = confirmed)
        ```
        """
        level.value.stage.confirmed = bool(confirmed)

    def set_confirming(self, level: Level, confirming: bool):
        """
        Проверяет и сохраняет значение `confirming`.

        ### Аргументы:
        :param level: уровень сценария
        :param confirming: ожидается ли подтверждение пользователя

        ### Пример использования:
        ```py
        session.set_confirming(level = level, confirming = confirming)
        ```
        """
        level.value.stage.confirming = bool(confirming)

    def set_asked(self, level: Level, asked: bool):
        """
        Проверяет и сохраняет значение `asked`.

        ### Аргументы:
        :param level: уровень сценария
        :param asked: был ли уже задан вопрос пользователю

        ### Пример использования:
        ```py
        session.set_asked(level = level, asked = asked)
        ```
        """
        level.value.stage.asked = bool(asked)

    def set_value(self, level: Level, value: Any | None):
        """
        Проверяет и сохраняет значение `value`.

        ### Аргументы:
        :param level: уровень сценария
        :param value: значение уровня или настройки

        ### Пример использования:
        ```py
        session.set_value(level = level, value = value)
        ```
        """
        level.value.value = value

    def get_value(self, level: Level, value_type: type | None = None) -> Any | None:
        """
        Возвращает значение, введённое или выбранное на уровне.

        ### Аргументы:
        :param level: уровень сценария
        :param value_type: value type

        :return: value

        ### Пример использования:
        ```py
        session.get_value(level = level, value_type = value_type)
        ```
        """
        result: Any | None = level.value.value

        if value_type is None or isinstance(result, value_type):
            return result
        else:
            return None
