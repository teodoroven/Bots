"""
Описывает папки доменной структуры.
Модуль относится к архитектурной зоне: прикладной слой `relay`, который связывает пользователей, сессии, доменную модель, GPT, уведомления и runtime-логику приложения.

### Публичные классы
- `RootFolder`: корневая папка доменного каталога.
- `FilialsFolder`: папка филиалов.
- `DatesFolder`: папка дат.
- `ContextsFolder`: папка GPT-контекстов.
- `QuestionsFolder`: папка GPT-вопросов.
- `LimitsFolder`: папка GPT-лимитов.

### Публичные функции
- Публичные функции отсутствуют.

### Связи
Используется app-layer сценариями, обработчиками, сессиями и runtime-миксинами для единого пользовательского потока между ботами, GPT и storage.
"""

from __future__ import annotations




from .base import NamedFolder
from .catalog import Filial, MonthDate
from .gpt import Limit, Question, SystemContext
class RootFolder(NamedFolder):

    """
    Описывает папку доменной модели автошколы `RootFolder`.
    Объект участвует в доменном дереве автошколы и сериализуется через registry элементов приложения.

    ### Методы
    - `__init__`: Создаёт объект и сохраняет связи доменного дерева автошколы.
    - `get_question`: Возвращает вопрос анкеты или GPT-контекста из текущего состояния `RootFolder`.

    ### Жизненный цикл
    Создаётся app-layer кодом, участвует в обработке пользовательского события и сохраняет изменённое состояние через существующие runtime/storage механизмы.

    ### Пример использования
    ```py
    rootFolder: RootFolder
    ```
    """
    def __init__(self, folder_id: int, name: str, lang_name: bool = False):
        """
        Создаёт доменный объект `RootFolder` и сохраняет связи, по которым дерево автошколы восстанавливается и обходится.

        ### Аргументы:
        :param folder_id: id папки или root-контейнера
        :param name: имя
        :param lang_name: имя языка локализации

        ### Пример использования:
        ```py
        rootFolder = RootFolder(folder_id = folder_id, name = name, lang_name = lang_name)
        ```
        """
        super().__init__(folder_id, name, lang_name)

    def get_question(self) -> Literal[""]:
        """
        Возвращает краткое описание элемента для вывода в чат.

        :return: строка вида `Филиал «Название»` или `Элемент «id»`

        ### Пример использования:
        ```py
        rootFolder.get_question()
        ```
        """
        return ""


class FilialsFolder(RootFolder):

    """
    Описывает папку доменной модели автошколы `FilialsFolder`.
    Объект участвует в доменном дереве автошколы и сериализуется через registry элементов приложения.

    ### Поля
    - `elements`: хранит элементы доменной модели для операций этого объекта.
    - `elements_type`: часть доменной модели автошколы, используемая при обходе и сериализации дерева.

    ### Методы
    - `__init__`: Создаёт объект и сохраняет связи доменного дерева автошколы.

    ### Жизненный цикл
    Создаётся app-layer кодом, участвует в обработке пользовательского события и сохраняет изменённое состояние через существующие runtime/storage механизмы.

    ### Пример использования
    ```py
    filialsFolder: FilialsFolder
    ```
    """
    def __init__(self, folder_id: int, name: Literal["filials"] = "filials", lang_name: Literal[True] = True):
        """
        Создаёт доменный объект `FilialsFolder` и сохраняет связи, по которым дерево автошколы восстанавливается и обходится.

        ### Аргументы:
        :param folder_id: id папки или root-контейнера
        :param name: имя
        :param lang_name: имя языка локализации

        ### Пример использования:
        ```py
        filialsFolder = FilialsFolder(folder_id = folder_id, name = name, lang_name = lang_name)
        ```
        """
        super().__init__(folder_id, "filials", lang_name = True)
        self.elements: list[Filial]
        self.elements_type: type[Filial] = Filial


class DatesFolder(RootFolder):

    """
    Описывает папку доменной модели автошколы `DatesFolder`.
    Объект участвует в доменном дереве автошколы и сериализуется через registry элементов приложения.

    ### Поля
    - `elements`: хранит элементы доменной модели для операций этого объекта.
    - `elements_type`: часть доменной модели автошколы, используемая при обходе и сериализации дерева.

    ### Методы
    - `__init__`: Создаёт объект и сохраняет связи доменного дерева автошколы.

    ### Жизненный цикл
    Создаётся app-layer кодом, участвует в обработке пользовательского события и сохраняет изменённое состояние через существующие runtime/storage механизмы.

    ### Пример использования
    ```py
    datesFolder: DatesFolder
    ```
    """
    def __init__(self, folder_id: int, name: Literal["dates"] = "dates", lang_name: Literal[True] = True):
        """
        Создаёт доменный объект `DatesFolder` и сохраняет связи, по которым дерево автошколы восстанавливается и обходится.

        ### Аргументы:
        :param folder_id: id папки или root-контейнера
        :param name: имя
        :param lang_name: имя языка локализации

        ### Пример использования:
        ```py
        datesFolder = DatesFolder(folder_id = folder_id, name = name, lang_name = lang_name)
        ```
        """
        super().__init__(folder_id, "dates", lang_name = True)
        self.elements: list[MonthDate]
        self.elements_type: type[MonthDate] = MonthDate


class ContextsFolder(RootFolder):

    """
    Описывает папку доменной модели автошколы `ContextsFolder`.
    Объект участвует в доменном дереве автошколы и сериализуется через registry элементов приложения.

    ### Поля
    - `elements`: хранит элементы доменной модели для операций этого объекта.
    - `elements_type`: часть доменной модели автошколы, используемая при обходе и сериализации дерева.

    ### Методы
    - `__init__`: Создаёт объект и сохраняет связи доменного дерева автошколы.
    - `set_elements`: Проверяет и сохраняет элементы доменной модели в состоянии `ContextsFolder`.

    ### Жизненный цикл
    Создаётся app-layer кодом, участвует в обработке пользовательского события и сохраняет изменённое состояние через существующие runtime/storage механизмы.

    ### Пример использования
    ```py
    contextsFolder: ContextsFolder
    ```
    """
    def __init__(self, folder_id: int, name: Literal["contexts"] = "contexts", lang_name: Literal[True] = True):
        """
        Создаёт доменный объект `ContextsFolder` и сохраняет связи, по которым дерево автошколы восстанавливается и обходится.

        ### Аргументы:
        :param folder_id: id папки или root-контейнера
        :param name: имя
        :param lang_name: имя языка локализации

        ### Пример использования:
        ```py
        contextsFolder = ContextsFolder(folder_id = folder_id, name = name, lang_name = lang_name)
        ```
        """
        super().__init__(folder_id, "contexts", lang_name = True)
        self.elements: list[SystemContext]
        self.elements_type: type[SystemContext] = SystemContext

    def set_elements(self, contexts: list[SystemContext]):
        """
        Проверяет и сохраняет значение `elements`.

        ### Аргументы:
        :param contexts: GPT-контексты, которые нужно поместить в папку

        ### Пример использования:
        ```py
        contextsFolder.set_elements(contexts = contexts)
        ```
        """
        self.elements.clear()

        for system_context in contexts:
            self.add_element(system_context)


class QuestionsFolder(RootFolder):

    """
    Описывает папку доменной модели автошколы `QuestionsFolder`.
    Объект участвует в доменном дереве автошколы и сериализуется через registry элементов приложения.

    ### Поля
    - `elements`: хранит элементы доменной модели для операций этого объекта.
    - `elements_type`: часть доменной модели автошколы, используемая при обходе и сериализации дерева.

    ### Методы
    - `__init__`: Создаёт объект и сохраняет связи доменного дерева автошколы.
    - `set_elements`: Проверяет и сохраняет элементы доменной модели в состоянии `QuestionsFolder`.

    ### Жизненный цикл
    Создаётся app-layer кодом, участвует в обработке пользовательского события и сохраняет изменённое состояние через существующие runtime/storage механизмы.

    ### Пример использования
    ```py
    questionsFolder: QuestionsFolder
    ```
    """
    def __init__(self, folder_id: int, name: Literal["questions"] = "questions", lang_name: Literal[True] = True):
        """
        Создаёт доменный объект `QuestionsFolder` и сохраняет связи, по которым дерево автошколы восстанавливается и обходится.

        ### Аргументы:
        :param folder_id: id папки или root-контейнера
        :param name: имя
        :param lang_name: имя языка локализации

        ### Пример использования:
        ```py
        questionsFolder = QuestionsFolder(folder_id = folder_id, name = name, lang_name = lang_name)
        ```
        """
        super().__init__(folder_id, "questions", lang_name = True)
        self.elements: list[Question] = self.elements
        self.elements_type: type[Question] = Question

    def set_elements(self, questions: list[Question]):
        """
        Проверяет и сохраняет значение `elements`.

        ### Аргументы:
        :param questions: вопросы, которые нужно поместить в папку или обработать

        ### Пример использования:
        ```py
        questionsFolder.set_elements(questions = questions)
        ```
        """
        self.elements.clear()

        for question in questions:
            self.add_element(question)


class LimitsFolder(RootFolder):

    """
    Описывает папку доменной модели автошколы `LimitsFolder`.
    Объект участвует в доменном дереве автошколы и сериализуется через registry элементов приложения.

    ### Поля
    - `elements`: хранит элементы доменной модели для операций этого объекта.
    - `elements_type`: часть доменной модели автошколы, используемая при обходе и сериализации дерева.

    ### Методы
    - `__init__`: Создаёт объект и сохраняет связи доменного дерева автошколы.
    - `set_elements`: Проверяет и сохраняет элементы доменной модели в состоянии `LimitsFolder`.

    ### Жизненный цикл
    Создаётся app-layer кодом, участвует в обработке пользовательского события и сохраняет изменённое состояние через существующие runtime/storage механизмы.

    ### Пример использования
    ```py
    limitsFolder: LimitsFolder
    ```
    """
    def __init__(self, folder_id: int, name: Literal["limits"] = "limits", lang_name: Literal[True] = True):
        """
        Создаёт доменный объект `LimitsFolder` и сохраняет связи, по которым дерево автошколы восстанавливается и обходится.

        ### Аргументы:
        :param folder_id: id папки или root-контейнера
        :param name: имя
        :param lang_name: имя языка локализации

        ### Пример использования:
        ```py
        limitsFolder = LimitsFolder(folder_id = folder_id, name = name, lang_name = lang_name)
        ```
        """
        super().__init__(folder_id, "limits", lang_name = True)
        self.elements: list[Limit] = self.elements
        self.elements_type: type[Limit] = Limit

    def set_elements(self, limits: list[Limit]):
        """
        Проверяет и сохраняет значение `elements`.

        ### Аргументы:
        :param limits: лимиты GPT, которые нужно поместить в папку

        ### Пример использования:
        ```py
        limitsFolder.set_elements(limits = limits)
        ```
        """
        self.elements.clear()

        for limit in limits:
            self.add_element(limit)
