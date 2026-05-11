"""
Описывает интерактивные элементы каталога автошколы.
Модуль относится к архитектурной зоне: прикладной слой `relay`, который связывает пользователей, сессии, доменную модель, GPT, уведомления и runtime-логику приложения.

### Публичные классы
- `InteractiveMixin`: mixin интерактивного доменного элемента.
- `Date`: доменная дата записи или расписания.
- `MonthDate`: доменная дата с месячной группировкой.
- `Filial`: доменный филиал автошколы.

### Публичные функции
- Публичные функции отсутствуют.

### Связи
Используется app-layer сценариями, обработчиками, сессиями и runtime-миксинами для единого пользовательского потока между ботами, GPT и storage.
"""

from __future__ import annotations




from relay.common import BotTypes, Never, datetime
from relay.config import get_phrase, get_phrase_list
from .base import Element, NamedFolder
class InteractiveMixin():
    """
    Добавляет `App` операции interactive без привязки к transport-layer.
    Объект участвует в доменном дереве автошколы и сериализуется через registry элементов приложения.

    ### Поля
    - `ENABLED_KEY`: ключ сериализации или transport-события, по которому объект отличает один вариант данных от другого.
    - `DISABLED_KEY`: ключ сериализации или transport-события, по которому объект отличает один вариант данных от другого.
    - `enabled`: часть доменной модели автошколы, используемая при обходе и сериализации дерева.

    ### Методы
    - `loads`: Восстанавливает объект из JSON-совместимого словаря.
    - `__init__`: Создаёт объект и сохраняет связи доменного дерева автошколы.
    - `dumps`: Возвращает JSON-совместимый снимок объекта для storage или callback payload.
    - `get_title`: Возвращает title из текущего состояния `InteractiveMixin`.
    - `get_notification`: Возвращает уведомление администратора из текущего состояния `InteractiveMixin`.

    ### Жизненный цикл
    Создаётся app-layer кодом, участвует в обработке пользовательского события и сохраняет изменённое состояние через существующие runtime/storage механизмы.

    ### Пример использования
    ```py
    app: InteractiveMixin
    ```
    """
    ENABLED_KEY: str = "element_enabled"
    DISABLED_KEY: str = "element_disabled"

    @classmethod
    def loads(cls, data: BotTypes.ELEMENT_TYPE, *args) -> InteractiveMixin:
        """
        Восстанавливает объект из JSON-совместимого словаря.

        ### Аргументы:
        :param data: сериализованный словарь
        :param args: дополнительные сериализуемые аргументы callback/session-сценария

        :return: восстановленный объект или загруженное состояние

        ### Пример использования:
        ```py
        InteractiveMixin.loads(data = data, args = args)
        ```
        """
        instance = super().loads(data, *args)
        instance.enabled = data.get("enabled", True)
        return instance

    def __init__(self, *args, **kwargs):
        """
        Создаёт `InteractiveMixin` и сохраняет связи доменного дерева автошколы.

        ### Примеры вызова:
        ```py
        app: InteractiveMixin = InteractiveMixin(args = args, kwargs = kwargs)
        ```
        """
        enabled: bool = kwargs.pop('enabled', True) if kwargs else True
        super().__init__(*args, **kwargs)
        self.enabled: bool = bool(enabled)

    def dumps(self) -> BotTypes.ELEMENT_TYPE:
        """
        Возвращает JSON-совместимый снимок объекта для storage или callback payload.

        :return: JSON-совместимый словарь для сохранения или передачи между слоями

        ### Пример использования:
        ```py
        interactiveMixin.dumps()
        ```
        """
        result = super().dumps()

        result.update({
            "enabled": bool(self.enabled)
        })

        return result

    def get_title(self: Element, answers: dict[str, JSONABLE]):
        """
        Возвращает заголовок элемента для меню и списков.

        ### Аргументы:
        :param answers: варианты ответа

        :return: заголовок элемента для пользовательского интерфейса

        ### Пример использования:
        ```py
        interactiveMixin.get_title(answers = answers)
        ```
        """
        element_enabled: str = get_phrase(self.__class__.ENABLED_KEY if self.enabled else self.__class__.DISABLED_KEY)
        return f"{super().get_title(answers)}, {element_enabled}"

    def get_notification(self: Element) -> str:
        """
        Возвращает текст элемента для административного уведомления.

        :return: строка, которую можно вставить в уведомление

        ### Пример использования:
        ```py
        interactiveMixin.get_notification()
        ```
        """
        title: str = get_phrase(self.__class__.ACCUSATIVE_KEY).lower()
        id: int = self.id
        return f"{title} «{self.get_answer(cut_string = False)}» ({id=})"


class Date(InteractiveMixin, Element):
    """
    `Date` хранит часть доменной модели автошколы и участвует в сериализации дерева приложения.
    Объект участвует в доменном дереве автошколы и сериализуется через registry элементов приложения.

    ### Поля
    - `DATE_FORMAT`: часть доменной модели автошколы, используемая при обходе и сериализации дерева.
    - `NOMINATIVE_KEY`: ключ локализации названия одного элемента.
    - `ACCUSATIVE_KEY`: ключ сериализации или transport-события, по которому объект отличает один вариант данных от другого.
    - `MULTIPLE_KEY`: ключ локализации названия списка элементов.
    - `ENABLED_KEY`: ключ сериализации или transport-события, по которому объект отличает один вариант данных от другого.
    - `DISABLED_KEY`: ключ сериализации или transport-события, по которому объект отличает один вариант данных от другого.
    - `CREATING_KEY`: ключ сериализации или transport-события, по которому объект отличает один вариант данных от другого.
    - `date`: хранит доступную дату записи для операций этого объекта.

    ### Методы
    - `check_content`: Проверяет название филиала перед сохранением.
    - `from_answer`: Обновляет или читает доменное состояние автошколы без обращения к transport-layer.
    - `loads`: Восстанавливает объект из JSON-совместимого словаря.
    - `__init__`: Создаёт объект и сохраняет связи доменного дерева автошколы.
    - `dumps`: Возвращает JSON-совместимый снимок объекта для storage или callback payload.
    - `get_date`: Возвращает доступную дату записи из текущего состояния `Date`.
    - `get_answer`: Возвращает ответ пользователя из текущего состояния `Date`.
    - `get_question`: Возвращает вопрос анкеты или GPT-контекста из текущего состояния `Date`.

    ### Жизненный цикл
    Создаётся app-layer кодом, участвует в обработке пользовательского события и сохраняет изменённое состояние через существующие runtime/storage механизмы.

    ### Пример использования
    ```py
    date: Date
    ```
    """
    DATE_FORMAT: str = "%d.%m.%Y"

    NOMINATIVE_KEY: str = "date_single"
    ACCUSATIVE_KEY: str = "date_accusative"
    MULTIPLE_KEY: str = "dates"
    ENABLED_KEY: str = "date_enabled"
    DISABLED_KEY: str = "date_disabled"
    CREATING_KEY: str = "create_date"

    @classmethod
    def check_content(cls, content: str) -> bool:
        """
        Проверяет, можно ли сохранить строку как содержимое доменного элемента.

        ### Аргументы:
        :param content: содержимое доменного элемента

        :return: `True`, если строку можно сохранить как содержимое; иначе `False`

        ### Пример использования:
        ```py
        Date.check_content(content = content)
        ```
        """
        return cls.from_answer(content) is not None

    @classmethod
    def from_answer(cls, answer: str) -> datetime | None:
        """
        Обновляет или читает доменное состояние автошколы без обращения к transport-layer.

        ### Аргументы:
        :param answer: ответ пользователя

        :return: результат доменной операции

        ### Пример использования:
        ```py
        Date.from_answer(answer = answer)
        ```
        """
        try:
            return datetime.strptime(str(answer).strip(), cls.DATE_FORMAT)
        except:
            return None

    @classmethod
    def loads(cls, data: BotTypes.ELEMENT_TYPE) -> Date:
        """
        Восстанавливает объект из JSON-совместимого словаря.

        ### Аргументы:
        :param data: сериализованный словарь

        :return: восстановленный объект или загруженное состояние

        ### Пример использования:
        ```py
        Date.loads(data = data)
        ```
        """
        result = super().loads(data)
        result.date = datetime.fromisoformat(data["date"])
        return result

    def __init__(self, date_id: int, date: datetime = None):
        """
        Создаёт доменный объект `Date` и сохраняет связи, по которым дерево автошколы восстанавливается и обходится.

        ### Аргументы:
        :param date_id: date id
        :param date: время сообщения или события

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        date = Date(date_id = date_id, date = date)
        ```
        """
        super().__init__(date_id)
        self.date: datetime = date

        if not isinstance(date, datetime):
            if date is not None:
                raise ValueError(f"Некорректное значение аргумента {date=}")

    def dumps(self) -> BotTypes.ELEMENT_TYPE:
        """
        Возвращает JSON-совместимый снимок объекта для storage или callback payload.

        :return: JSON-совместимый словарь для сохранения или передачи между слоями

        ### Пример использования:
        ```py
        date.dumps()
        ```
        """
        result: BotTypes.ELEMENT_TYPE = super().dumps()

        result.update({
            "date": self.date.isoformat()
        })

        return result

    def get_date(self) -> datetime:
        """
        Возвращает сохранённую дату или время события.

        :return: время сообщения или события

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        date.get_date()
        ```
        """
        if isinstance(self.date, datetime):
            return self.date
        else:
            raise ValueError(f"Некорректное значение атрибута {self.date=}")

    def get_answer(self, cut_string: bool = True) -> str:
        """
        Возвращает строку, показываемую пользователю как вариант ответа.

        ### Аргументы:
        :param cut_string: нужно ли сокращать строку до длины кнопки

        :return: ответ пользователя

        ### Пример использования:
        ```py
        date.get_answer(cut_string = cut_string)
        ```
        """
        return self.get_date().strftime(Date.DATE_FORMAT)

    def get_question(self) -> str:
        """
        Возвращает краткое описание элемента для вывода в чат.

        :return: строка вида `Филиал «Название»` или `Элемент «id»`

        ### Пример использования:
        ```py
        date.get_question()
        ```
        """
        nominative: str = get_phrase(self.__class__.NOMINATIVE_KEY)
        return f"{nominative} «{self.get_answer()}»"


class MonthDate(Date):
    """
    `MonthDate` хранит часть доменной модели автошколы и участвует в сериализации дерева приложения.
    Объект участвует в доменном дереве автошколы и сериализуется через registry элементов приложения.

    ### Поля
    - `CREATING_KEY`: ключ сериализации или transport-события, по которому объект отличает один вариант данных от другого.

    ### Методы
    - `__init__`: Создаёт объект и сохраняет связи доменного дерева автошколы.
    - `get_month_index`: Возвращает month index из текущего состояния `MonthDate`.
    - `get_answer`: Возвращает ответ пользователя из текущего состояния `MonthDate`.

    ### Жизненный цикл
    Создаётся app-layer кодом, участвует в обработке пользовательского события и сохраняет изменённое состояние через существующие runtime/storage механизмы.

    ### Пример использования
    ```py
    monthDate: MonthDate
    ```
    """
    CREATING_KEY: str = "create_month_date"

    def __init__(self, date_id: int, date: datetime = None):
        """
        Создаёт доменный объект `MonthDate` и сохраняет связи, по которым дерево автошколы восстанавливается и обходится.

        ### Аргументы:
        :param date_id: date id
        :param date: время сообщения или события

        ### Пример использования:
        ```py
        monthDate = MonthDate(date_id = date_id, date = date)
        ```
        """
        InteractiveMixin.__init__(self, date_id)
        super().__init__(date_id, date)

    def __repr__(self) -> str:
        return f"MonthDate({self.get_answer(cut_string = False)} {Date.get_answer(self, cut_string = False)})"

    def get_month_index(self) -> int:
        """
        Возвращает индекс месяца в календарном списке.

        :return: month index

        ### Пример использования:
        ```py
        monthDate.get_month_index()
        ```
        """
        return self.get_date().month - 1

    def get_answer(self, cut_string: bool = True) -> str:
        """
        Возвращает строку, показываемую пользователю как вариант ответа.

        ### Аргументы:
        :param cut_string: нужно ли сокращать строку до длины кнопки

        :return: ответ пользователя

        ### Пример использования:
        ```py
        monthDate.get_answer(cut_string = cut_string)
        ```
        """
        date: datetime = self.get_date() if self.date else None
        months_list: list[str] = get_phrase_list("months_nominative")
        month_index: int = self.get_month_index()
        return f"{months_list[month_index]} {date.year}"


class Filial(InteractiveMixin, NamedFolder):
    """
    `Filial` хранит часть доменной модели автошколы и участвует в сериализации дерева приложения.
    Объект участвует в доменном дереве автошколы и сериализуется через registry элементов приложения.

    ### Поля
    - `NOMINATIVE_KEY`: ключ локализации названия одного элемента.
    - `ACCUSATIVE_KEY`: ключ сериализации или transport-события, по которому объект отличает один вариант данных от другого.
    - `MULTIPLE_KEY`: ключ локализации названия списка элементов.
    - `DISABLED_KEY`: ключ сериализации или transport-события, по которому объект отличает один вариант данных от другого.
    - `CREATING_KEY`: ключ сериализации или transport-события, по которому объект отличает один вариант данных от другого.
    - `lang_name`: часть доменной модели автошколы, используемая при обходе и сериализации дерева.
    - `elements`: хранит элементы доменной модели для операций этого объекта.
    - `elements_type`: часть доменной модели автошколы, используемая при обходе и сериализации дерева.

    ### Методы
    - `__init__`: Создаёт объект и сохраняет связи доменного дерева автошколы.
    - `has_date`: Проверяет наличие время сообщения или события.
    - `has_element`: Проверяет наличие доменный элемент.

    ### Жизненный цикл
    Создаётся app-layer кодом, участвует в обработке пользовательского события и сохраняет изменённое состояние через существующие runtime/storage механизмы.

    ### Пример использования
    ```py
    filial: Filial
    ```
    """
    NOMINATIVE_KEY: str = "filial_single"
    ACCUSATIVE_KEY: str = "filial_single"
    MULTIPLE_KEY: str = "filials"
    DISABLED_KEY: str = "filial_disabled"
    CREATING_KEY: str = "create_filial"

    def __init__(self, filial_id: int, name: str, lang_name: Never = Never):
        """
        Создаёт доменный объект `Filial` и сохраняет связи, по которым дерево автошколы восстанавливается и обходится.

        ### Аргументы:
        :param filial_id: filial id
        :param name: имя
        :param lang_name: имя языка локализации

        ### Пример использования:
        ```py
        filial = Filial(filial_id = filial_id, name = name, lang_name = lang_name)
        ```
        """
        super().__init__(filial_id, name, False)
        self.lang_name = False
        self.elements: list[Date] = []
        self.elements_type = Date

    def has_date(self, date: str):
        """
        Проверяет наличие время сообщения или события.

        ### Аргументы:
        :param date: время сообщения или события

        :return: `True`, если наличие время сообщения или события; иначе `False`

        ### Пример использования:
        ```py
        filial.has_date(date = date)
        ```
        """
        for elem in self.elements:
            if elem.get_answer(cut_string = True) == date:
                return True
        return False

    def has_element(self, date: Date) -> bool:
        """
        Проверяет наличие доменный элемент.

        ### Аргументы:
        :param date: время сообщения или события

        :return: `True`, если наличие доменный элемент; иначе `False`

        ### Пример использования:
        ```py
        filial.has_element(date = date)
        ```
        """
        return date in self.elements or self.has_date(date.get_answer(cut_string = True))
