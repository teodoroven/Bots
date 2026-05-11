"""
Описывает базовые сущности модуля.
Модуль относится к архитектурной зоне: прикладной слой `relay`, который связывает пользователей, сессии, доменную модель, GPT, уведомления и runtime-логику приложения.

### Публичные классы
- `Element`: базовый элемент доменной структуры.
- `NamedElement`: именованный элемент доменной структуры.
- `Folder`: контейнер доменных элементов.
- `Root`: корневой контейнер доменной структуры.
- `NamedFolder`: именованный контейнер доменных элементов.

### Публичные функции
- Публичные функции отсутствуют.

### Связи
Используется app-layer сценариями, обработчиками, сессиями и runtime-миксинами для единого пользовательского потока между ботами, GPT и storage.
"""

from __future__ import annotations




from relay.common import (
    Any,
    BotTypes,
    Generic,
    T,
    abstractmethod,
)
from relay.config import BUTTON_LENGTH, MAX_INPUT_LENGTH, get_phrase, logger_sessions
from bots.utils.mapping import get_int
from relay.utils import is_int
class Element():
    """
    Базовый элемент доменной модели автошколы.
    Элемент хранит стабильный `id`, ссылку на родителя `parent_id` и отметку
    мягкого удаления `removed_from`. Наследники используют этот контракт для
    филиалов, дат, GPT-настроек и других объектов, которые app-layer показывает
    в меню и сохраняет через storage API.

    ### Поля
    - `NOMINATIVE_KEY`: ключ локализации названия одного элемента.
    - `MULTIPLE_KEY`: ключ локализации названия списка элементов.
    - `EDIT_KEY`: ключ локализации сообщения о запрете изменения.
    - `CREATED_KEY`: ключ локализации сообщения о создании элемента.
    - `EDITED_KEY`: ключ локализации сообщения об изменении элемента.
    - `ADDED_KEY`: ключ локализации сообщения о добавлении элемента.
    - `REMOVED_KEY`: ключ локализации сообщения об удалении элементов.
    - `REMOVED_NONE_KEY`: ключ локализации сообщения, когда удалять нечего.
    - `REMOVED_SINGLE_KEY`: ключ локализации сообщения об удалении одного элемента.
    - `REMOVED_FAIL_KEY`: ключ локализации сообщения об ошибке удаления.

    Методы `set_content` и `add_content` задают общий интерфейс изменения
    текстового содержимого, но конкретную запись выполняют наследники.
    """
    NOMINATIVE_KEY: str = "element"
    MULTIPLE_KEY: str = "elements"
    EDIT_KEY: str = "cant_change"
    CREATED_KEY: str = "created"
    EDITED_KEY: str = "edited"
    ADDED_KEY: str = "added"

    REMOVED_KEY: str = "removed"
    REMOVED_NONE_KEY: str = "removed_none"
    REMOVED_SINGLE_KEY: str = "removed_single"
    REMOVED_FAIL_KEY: str = "removed_fail"

    @classmethod
    def check_content(cls, content: str) -> bool:
        """
        Проверяет, можно ли сохранить строку как содержимое доменного элемента.
        Базовое правило общее для админских форм: строка должна быть непустой и
        короче `MAX_INPUT_LENGTH`.

        ### Аргументы:
        :param content: содержимое доменного элемента

        :return: `True`, если содержимое можно сохранить; иначе `False`

        ### Пример использования:
        ```py
        Element.check_content(content = content)
        ```
        """
        return content != "" and len(content) < MAX_INPUT_LENGTH

    @classmethod
    def check_content_add(cls, content: str) -> bool:
        """
        Проверяет, что строка нового содержимого не пустая.

        ### Аргументы:
        :param content: содержимое доменного элемента

        :return: `True`, если строка непустая; иначе `False`

        ### Пример использования:
        ```py
        Element.check_content_add(content = content)
        ```
        """
        return content != ""

    @classmethod
    def loads(cls, data: BotTypes.ELEMENT_TYPE) -> Element:
        """
        Восстанавливает объект из JSON-совместимого словаря.

        ### Аргументы:
        :param data: сериализованный словарь

        :return: восстановленный объект или загруженное состояние

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        Element.loads(data = data)
        ```
        """
        element_id: int = get_int(data, -1, "id")
        parent_id: int = get_int(data, None, "parent_id")
        removed_from: int = get_int(data, None, "removed_from")

        result = cls(element_id)
        result.parent_id = None if parent_id is None else int(parent_id)
        result.removed_from = None if removed_from is None else int(removed_from)

        if is_int(parent_id) and parent_id < 0:
            parent_id = data.get("parent_id")
            raise ValueError(f"Некорректное значение под ключом {parent_id=} словаря {data=}")

        if is_int(removed_from) and removed_from < 0:
            removed_from = data.get("removed_from")
            raise ValueError(f"Некорректное значение под ключом {removed_from=} словаря {data=}")

        if isinstance(result, InteractiveMixin):
            result.enabled = get_from(data, "enabled", types = (bool,), default = True)

        return result

    def __init__(self, element_id: int):
        """
        Создаёт доменный элемент и сохраняет его идентификатор.

        ### Аргументы:
        :param element_id: идентификатор доменного элемента

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        element = Element(element_id = element_id)
        ```
        """
        self.id = int(element_id)
        self.parent_id: int | None = None
        self.removed_from: int | None = None

        if element_id < 0:
            raise ValueError(f"Некорректное значение аргумента {element_id=}")

    def dumps(self) -> BotTypes.ELEMENT_TYPE:
        """
        Возвращает JSON-совместимый снимок базовых полей доменного элемента.
        Текущая реализация возвращает словарь сразу после `classname`, `id`, `parent_id` и `removed_from`.

        :return: словарь с базовыми полями доменного элемента

        ### Пример использования:
        ```py
        element.dumps()
        ```
        """
        return {
            "classname": self.__class__.__name__,
            "id": int(self.id),
            "parent_id": None if self.parent_id is None else int(self.parent_id),
            "removed_from": None if self.removed_from is None else int(self.removed_from)
        }

    def get_answer(self, cut_string: bool = True) -> str:
        """
        Возвращает строку, показываемую пользователю как вариант ответа.

        ### Аргументы:
        :param cut_string: нужно ли сокращать строку до длины кнопки

        :return: ответ пользователя

        ### Пример использования:
        ```py
        element.get_answer(cut_string = cut_string)
        ```
        """
        nominative: str = get_phrase(self.__class__.NOMINATIVE_KEY)
        result: str = f"{nominative} «{self.id}»"

        if len(result) <= BUTTON_LENGTH:
            return result
        else:
            return cut(result, BUTTON_LENGTH, dots = True)

    def get_question(self) -> str:
        """
        Возвращает краткое описание элемента для вывода в чат.

        :return: строка вида `Филиал «Название»` или `Элемент «id»`
        """
        return self.get_answer(cut_string = False)

    def get_title(self, answers: dict[str, JSONABLE]) -> str:
        """
        Возвращает заголовок элемента для меню и списков.

        ### Аргументы:
        :param answers: варианты ответа

        :return: заголовок элемента для пользовательского интерфейса

        ### Пример использования:
        ```py
        element.get_title(answers = answers)
        ```
        """
        return self.get_question()

    def get_notification(self) -> str:
        """
        Возвращает текст элемента для административного уведомления.

        :return: строка, которую можно вставить в уведомление

        ### Пример использования:
        ```py
        element.get_notification()
        ```
        """
        return Element.get_answer(self, cut_string = False)

    def check_removed(self) -> bool:
        """
        Проверяет, помечен ли элемент как удалённый.

        :return: `True`, если `removed_from` содержит id прежнего контейнера; иначе `False`

        ### Пример использования:
        ```py
        element.check_removed()
        ```
        """
        return self.removed_from is not None

    def move_to(self, folder_id: int):
        """
        Переносит элемент в другую folder/root структуру, записывая новый `parent_id`.

        ### Аргументы:
        :param folder_id: id папки или root-структуры, которая должна стать родителем элемента

        ### Пример использования:
        ```py
        element.move_to(folder_id = folder_id)
        ```
        """
        self.parent_id = int(folder_id)

    def remove(self, from_id: int):
        """
        Помечает элемент как удалённый из указанной folder/root структуры через `removed_from`.

        ### Аргументы:
        :param from_id: id папки или root-структуры, из которой элемент был удалён

        ### Пример использования:
        ```py
        element.remove(from_id = from_id)
        ```
        """
        self.removed_from = int(from_id)

    @abstractmethod
    def set_content(self, content: str) -> bool:
        """
        Проверяет и записывает текст доменного элемента.

        ### Аргументы:
        :param content: содержимое доменного элемента

        :return: результат доменной операции

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        element.set_content(content = content)
        ```
        """
        raise NotImplementedError()

    @abstractmethod
    def add_content(self, content: str) -> bool:
        """
        Добавляет текстовое содержимое к доменному элементу.

        ### Аргументы:
        :param content: содержимое доменного элемента

        :return: результат доменной операции

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        element.add_content(content = content)
        ```
        """
        raise NotImplementedError()


class NamedElement(Element):
    """
    Доменный элемент с человекочитаемым именем.
    Используется для объектов автошколы и настроек, которые отображаются в
    меню по имени, а не только по `id`. При `lang_name=True` имя трактуется как
    ключ локализации и читается через `get_phrase`.

    `set_content` заменяет имя и возвращает, изменилось ли оно фактически.
    """
    EDIT_KEY: str = "rename_question"

    @classmethod
    def loads(cls, data: BotTypes.ELEMENT_TYPE) -> NamedElement:
        """
        Восстанавливает объект из JSON-совместимого словаря.

        ### Аргументы:
        :param data: сериализованный словарь

        :return: восстановленный объект или загруженное состояние

        ### Пример использования:
        ```py
        NamedElement.loads(data = data)
        ```
        """
        element_id: int = get_int(data, -1, "id")
        name: str = data.get("name", "")
        lang_name: bool = data.get("lang_name", False)
        return cls(element_id, name, lang_name)

    def __init__(self, element_id: int, name: str, lang_name: bool = False):
        """
        Создаёт именованный доменный элемент.
        Пустое или состоящее только из пробелов имя считается ошибкой, потому
        что такой объект невозможно нормально показать в меню.

        ### Аргументы:
        :param element_id: идентификатор доменного элемента
        :param name: отображаемое имя или ключ локализации
        :param lang_name: нужно ли читать `name` через `get_phrase`

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        namedElement = NamedElement(element_id = element_id, name = name, lang_name = lang_name)
        ```
        """
        super().__init__(element_id)
        self.name: str = str(name)
        self.lang_name: bool = bool(lang_name)

        if not self.name.strip():
            raise ValueError(f"Некорректное значение аргумента {name=}")

    def dumps(self) -> BotTypes.ELEMENT_TYPE:
        """
        Возвращает JSON-совместимый снимок объекта для storage или callback payload.

        :return: JSON-совместимый словарь для сохранения или передачи между слоями

        ### Пример использования:
        ```py
        namedElement.dumps()
        ```
        """
        result: BotTypes.ELEMENT_TYPE = super().dumps()

        result.update({
            "lang_name": bool(self.lang_name),
            "name": str(self.name)
        })

        return result

    def get_name(self) -> str:
        """
        Возвращает отображаемое имя элемента.
        Если `lang_name=True`, сохранённое имя используется как ключ локализации.

        :return: локализованное или сохранённое имя

        ### Пример использования:
        ```py
        namedElement.get_name()
        ```
        """
        if self.lang_name:
            return get_phrase(self.name)
        else:
            return str(self.name)

    def get_answer(self, cut_string: bool = True) -> str:
        """
        Возвращает строку, показываемую пользователю как вариант ответа.

        ### Аргументы:
        :param cut_string: нужно ли сокращать строку до длины кнопки

        :return: ответ пользователя

        ### Пример использования:
        ```py
        namedElement.get_answer(cut_string = cut_string)
        ```
        """
        result: str = self.get_name().strip() or super().get_answer()

        if len(result) <= BUTTON_LENGTH:
            return result
        else:
            return cut(result, BUTTON_LENGTH)

    def get_question(self) -> str:
        """
        Возвращает краткое описание элемента для вывода в чат.

        :return: строка вида `Филиал «Название»` или `Элемент «id»`

        ### Пример использования:
        ```py
        namedElement.get_question()
        ```
        """
        nominative: str = get_phrase(self.__class__.NOMINATIVE_KEY)
        return f"{nominative} «{self.get_answer()}»"

    def set_content(self, content: str) -> bool:
        """
        Заменяет имя элемента на переданный текст.
        Метод меняет только in-memory состояние объекта; сохранение выполняет
        вызывающий app/runtime слой.

        ### Аргументы:
        :param content: содержимое доменного элемента

        :return: `True`, если имя изменилось; иначе `False`

        ### Пример использования:
        ```py
        namedElement.set_content(content = content)
        ```
        """
        content_before: str = self.get_name()
        self.name = content
        return content_before != self.name


class Folder(Element, Generic[T]):
    """
    Контейнер доменных элементов.
    `Folder` хранит список дочерних объектов, назначает им `parent_id`, умеет
    сериализовать вложенные элементы и используется как основа для каталогов
    филиалов, дат, контекстов, вопросов и лимитов.

    Методы удаления меняют только список `elements`; запись в storage выполняет
    вызывающий runtime.
    """
    NOMINATIVE_KEY: str = "folder"
    MULTIPLE_KEY: str = "folders"

    @classmethod
    def loads(cls, data: BotTypes.ELEMENT_TYPE, load_element: Callable[[BotTypes.ELEMENT_TYPE], Element]) -> Folder[Element]:
        """
        Восстанавливает папку и её дочерние элементы из JSON-совместимого словаря.

        ### Аргументы:
        :param data: сериализованный словарь
        :param load_element: функция registry, восстанавливающая дочерний элемент

        :return: восстановленная папка с дочерними элементами

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        Folder.loads(data = data, load_element = load_element)
        ```
        """


        folder_id: int = get_int(data, -1, "id")

        if folder_id < 0:
            id = data.get("id")
            raise ValueError(f"Некорректное значение под ключом {id=} аргумента {data=}")

        result = cls(folder_id)

        for element_data in data.get("elements", []):
            element: Element | None = load_element(element_data)

            if element:
                result.add_element(element)

        return result

    def __init__(self, folder_id: int):
        """
        Создаёт пустой контейнер доменных элементов.

        ### Аргументы:
        :param folder_id: id папки или root-контейнера

        ### Пример использования:
        ```py
        folder = Folder(folder_id = folder_id)
        ```
        """
        Element.__init__(self, folder_id)
        self.elements: list[Element] = []
        self.elements_type: type[Element] | Any = Any

    def dumps(self) -> BotTypes.ELEMENT_TYPE:
        """
        Возвращает JSON-совместимый снимок папки и дочерних элементов.

        :return: словарь с базовыми полями папки и списком `elements`

        ### Пример использования:
        ```py
        folder.dumps()
        ```
        """
        result: BotTypes.ELEMENT_TYPE = super().dumps()

        result.update({
            "elements": [element.dumps() for element in self.elements]
        })

        return result

    def add_element(self, element: Element):
        """
        Привязывает доменный элемент к текущему контейнеру.

        ### Аргументы:
        :param element: доменный элемент

        ### Пример использования:
        ```py
        folder.add_element(element = element)
        ```
        """
        element.parent_id = self.id

        if element not in self.elements:
            self.elements.append(element)

    def remove_element(self, element: Element):
        """
        Удаляет элемент из списка `elements` этой папки.
        Метод не помечает сам элемент как удалённый и не пишет в storage.

        ### Аргументы:
        :param element: доменный элемент, который должен быть удалён из папки

        ### Пример использования:
        ```py
        folder.remove_element(element = element)
        ```
        """
        if element in self.elements:
            self.elements.remove(element)

    def remove_id(self, element_id: int) -> bool:
        """
        Удаляет все элементы с указанным id из коллекции.

        ### Аргументы:
        :param element_id: идентификатор доменного элемента

        :return: `True`, если хотя бы один элемент был удалён; иначе `False`

        ### Пример использования:
        ```py
        folder.remove_id(element_id = element_id)
        ```
        """
        removed: bool = False

        for elem in list(self.elements):
            if elem.id == element_id:
                self.remove_element(elem)
                removed = True

        return removed

    def get_answer(self, cut_string: bool = True) -> str:
        """
        Возвращает строку, показываемую пользователю как вариант ответа.

        ### Аргументы:
        :param cut_string: нужно ли сокращать строку до длины кнопки

        :return: ответ пользователя

        ### Пример использования:
        ```py
        folder.get_answer(cut_string = cut_string)
        ```
        """
        nominative: str = get_phrase(self.__class__.NOMINATIVE_KEY)
        result: str = f"{nominative} «{self.id}»"

        if len(result) <= BUTTON_LENGTH:
            return result
        else:
            return cut(result, BUTTON_LENGTH)

    def get_title(self, answers: dict[str, JSONABLE]) -> str:
        """
        Возвращает заголовок элемента для меню и списков.

        ### Аргументы:
        :param answers: варианты ответа

        :return: заголовок элемента для пользовательского интерфейса

        ### Пример использования:
        ```py
        folder.get_title(answers = answers)
        ```
        """
        folder_elements: str = get_phrase("elements")

        if self.elements_type is not Any and hasattr(self.elements_type, "MULTIPLE_KEY"):
            folder_elements = get_phrase(self.elements_type.MULTIPLE_KEY)

        return f"{self.get_question()}\n{folder_elements}: {len(answers)}"


class Root(Folder, Generic[T]):
    """
    `Root` хранит часть доменной модели автошколы и участвует в сериализации дерева приложения.
    Объект участвует в доменном дереве автошколы и сериализуется через registry элементов приложения.

    ### Поля
    - `NOMINATIVE_KEY`: ключ локализации названия одного элемента.
    - `MULTIPLE_KEY`: ключ локализации названия списка элементов.

    ### Методы
    - `__init__`: Создаёт объект и сохраняет связи доменного дерева автошколы.

    ### Жизненный цикл
    Создаётся app-layer кодом, участвует в обработке пользовательского события и сохраняет изменённое состояние через существующие runtime/storage механизмы.

    ### Пример использования
    ```py
    root: Root
    ```
    """
    NOMINATIVE_KEY: str = "root"
    MULTIPLE_KEY: Never = NotImplemented

    def __init__(self, _: Never = None):
        """
        Создаёт root-контейнер доменного дерева.

        ### Аргументы:
        :param _: compatibility placeholder; значение игнорируется

        ### Пример использования:
        ```py
        root = Root()
        ```
        """
        super().__init__(folder_id = 0)


class NamedFolder(NamedElement, Folder[T]):

    """
    Описывает папку доменной модели автошколы `NamedFolder`.
    Объект участвует в доменном дереве автошколы и сериализуется через registry элементов приложения.

    ### Методы
    - `loads`: Восстанавливает объект из JSON-совместимого словаря.
    - `__init__`: Создаёт объект и сохраняет связи доменного дерева автошколы.
    - `dumps`: Возвращает JSON-совместимый снимок объекта для storage или callback payload.

    ### Жизненный цикл
    Создаётся app-layer кодом, участвует в обработке пользовательского события и сохраняет изменённое состояние через существующие runtime/storage механизмы.

    ### Пример использования
    ```py
    namedFolder: NamedFolder
    ```
    """
    @classmethod
    def loads(cls, data: BotTypes.ELEMENT_TYPE, load_element: Callable[[BotTypes.ELEMENT_TYPE], Element]) -> NamedFolder[Element]:
        """
        Восстанавливает объект из JSON-совместимого словаря.

        ### Аргументы:
        :param data: сериализованный словарь
        :param load_element: load element

        :return: восстановленный объект или загруженное состояние

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        NamedFolder.loads(data = data, load_element = load_element)
        ```
        """
        folder_id: int = get_int(data, -1, "id")

        if folder_id < 0:
            id = data.get("id")
            raise ValueError(f"Некорректное значение аргумента data под ключом {id=}")

        name: str = data.get("name", "")
        lang_name: str = data.get("lang_name", False)
        result = cls(folder_id, name, lang_name)

        for element_data in data.get("elements", []):
            element: Element | None = load_element(element_data)

            if element:
                result.add_element(element)

        return result

    def __init__(self, folder_id: int, name: str, lang_name: bool = False):
        """
        Создаёт доменный объект `NamedFolder` и сохраняет связи, по которым дерево автошколы восстанавливается и обходится.

        ### Аргументы:
        :param folder_id: id папки или root-контейнера
        :param name: имя
        :param lang_name: имя языка локализации

        ### Пример использования:
        ```py
        namedFolder = NamedFolder(folder_id = folder_id, name = name, lang_name = lang_name)
        ```
        """
        super().__init__(folder_id, name, lang_name)
        # NamedElement.__init__(self, folder_id, name, lang_name)
        # Folder.__init__(self, folder_id)

    def dumps(self) -> BotTypes.ELEMENT_TYPE:
        """
        Возвращает JSON-совместимый снимок объекта для storage или callback payload.

        :return: JSON-совместимый словарь для сохранения или передачи между слоями

        ### Пример использования:
        ```py
        namedFolder.dumps()
        ```
        """
        result: BotTypes.ELEMENT_TYPE = super().dumps()

        result.update({
            "name": str(self.name),
            "lang_name": bool(self.lang_name),
            "elements": [element.dumps() for element in self.elements]
        })

        return result
