"""
Описывает GPT-запросы, ответы и wrapper провайдера.
Модуль относится к архитектурной зоне: прикладной слой `relay`, который связывает пользователей, сессии, доменную модель, GPT, уведомления и runtime-логику приложения.

### Публичные классы
- `Question`: доменный GPT-вопрос и ответы.
- `SystemContext`: доменный системный GPT-контекст.
- `Limit`: доменный лимит GPT-токенов.
- `Client`: доменный GPT-клиент с лимитами.

### Публичные функции
- Публичные функции отсутствуют.

### Связи
Используется app-layer сценариями, обработчиками, сессиями и runtime-миксинами для единого пользовательского потока между ботами, GPT и storage.
"""

from __future__ import annotations




from relay.common import (
    BotTypes,
    Iterable,
    T,
    Thread,
    datetime,
)
from relay.config import BUTTON_LENGTH, MAX_INPUT_LENGTH, get_phrase
from .base import Element
from relay.utils import log_warn, parse_period
class Question(Element):
    """
    `Question` хранит часть доменной модели автошколы и участвует в сериализации дерева приложения.
    Объект участвует в доменном дереве автошколы и сериализуется через registry элементов приложения.

    ### Поля
    - `NOMINATIVE_KEY`: ключ локализации названия одного элемента.
    - `MULTIPLE_KEY`: ключ локализации названия списка элементов.
    - `CREATING_KEY`: ключ сериализации или transport-события, по которому объект отличает один вариант данных от другого.
    - `EDIT_KEY`: ключ локализации сообщения о запрете изменения.
    - `ADD_KEY`: ключ сериализации или transport-события, по которому объект отличает один вариант данных от другого.
    - `question`: хранит вопрос анкеты или GPT-контекста для операций этого объекта.
    - `answers`: хранит варианты ответа для операций этого объекта.

    ### Методы
    - `loads`: Восстанавливает объект из JSON-совместимого словаря.
    - `__init__`: Создаёт объект и сохраняет связи доменного дерева автошколы.
    - `dumps`: Возвращает JSON-совместимый снимок объекта для storage или callback payload.
    - `check`: Проверяет значение по правилам текущего класса и не изменяет состояние.
    - `get_answer`: Возвращает ответ пользователя из текущего состояния `Question`.
    - `get_title`: Возвращает title из текущего состояния `Question`.
    - `set_content`: Проверяет и сохраняет контент GPT-запроса в состоянии `Question`.
    - `add_content`: Добавляет текстовый блок в GPT-контекст или вопрос.

    ### Жизненный цикл
    Создаётся app-layer кодом, участвует в обработке пользовательского события и сохраняет изменённое состояние через существующие runtime/storage механизмы.

    ### Пример использования
    ```py
    question: Question
    ```
    """
    NOMINATIVE_KEY: str = "question_single"
    MULTIPLE_KEY: str = "questions"
    CREATING_KEY: str = "create_question_element"
    EDIT_KEY: str = "edit_question"
    ADD_KEY: str = "add_answer"

    def loads(data: BotTypes.QUESTION_TYPE) -> Question:
        """
        Восстанавливает объект из JSON-совместимого словаря.

        ### Аргументы:
        :param data: сериализованный словарь

        :return: восстановленный объект или загруженное состояние

        ### Пример использования:
        ```py
        question.loads(data = data)
        ```
        """
        question_id: int = get_int(data, -1, "id")
        question: str = data.get("question", "")
        answers: Iterable[str] = data.get("answers", [])
        return Question(question_id, question, answers)

    def __init__(self, question_id: int, question: str, answers: Iterable[str]):
        """
        Создаёт доменный GPT-объект `Question` и сохраняет настройки, которые затем сериализуются в дерево приложения.

        ### Аргументы:
        :param question_id: question id
        :param question: текст или объект вопроса
        :param answers: варианты ответа

        ### Пример использования:
        ```py
        question = Question(question_id = question_id, question = question, answers = answers)
        ```
        """
        super().__init__(question_id)
        self.question: str = str(question)
        self.answers: list[str] = list(map(str, answers))

    def dumps(self) -> BotTypes.QUESTION_TYPE:
        """
        Возвращает JSON-совместимый снимок объекта для storage или callback payload.

        :return: JSON-совместимый словарь для сохранения или передачи между слоями

        ### Пример использования:
        ```py
        question.dumps()
        ```
        """
        result: BotTypes.QUESTION_TYPE = super().dumps()

        result.update({
            "question": str(self.question),
            "answers": [str(answer) for answer in self.answers]
        })

        return result

    def check(self) -> bool:
        """
        Проверяет значение по правилам текущего класса и не изменяет состояние.

        :return: результат доменной операции

        ### Пример использования:
        ```py
        question.check()
        ```
        """
        return self.question.strip() and any(answer for answer in self.answers)

    def get_answer(self, cut_string: bool = True):
        """
        Возвращает строку, показываемую пользователю как вариант ответа.

        ### Аргументы:
        :param cut_string: нужно ли сокращать строку до длины кнопки

        :return: ответ пользователя

        ### Пример использования:
        ```py
        question.get_answer(cut_string = cut_string)
        ```
        """
        result: str = str(self.question).strip()

        if not result:
            return super().get_answer(cut_string = cut_string)
        elif cut_string:
            return cut(result, BUTTON_LENGTH, dots = T)
        else:
            return result

    def get_title(self, answers: dict[str, JSONABLE]) -> str:
        """
        Возвращает заголовок элемента для меню и списков.

        ### Аргументы:
        :param answers: варианты ответа

        :return: заголовок элемента для пользовательского интерфейса

        ### Пример использования:
        ```py
        question.get_title(answers = answers)
        ```
        """
        title: str = Element.get_answer(self, cut_string = False)

        if not self.question:
            no_question: str = get_phrase("no_question")
            title = f"{title}: {no_question}"
        elif not self.answers:
            no_answers: str = get_phrase("no_answers")
            title = f"{title}: {no_answers}"

        return title

    def set_content(self, content: str) -> bool:
        """
        Проверяет и записывает текст доменного элемента.

        ### Аргументы:
        :param content: содержимое доменного элемента

        :return: результат доменной операции

        ### Пример использования:
        ```py
        question.set_content(content = content)
        ```
        """
        content_before: str = str(self.dumps())
        question, *answers = content.split("\n")
        self.question = str(question).strip()
        self.answers.clear()

        for answer in answers:
            answer = answer.strip()

            if answer:
                self.answers.append(answer)

        return content_before != str(self.dumps())

    def add_content(self, content: str) -> bool:
        """
        Добавляет текстовое содержимое к доменному элементу.

        ### Аргументы:
        :param content: содержимое доменного элемента

        :return: результат доменной операции

        ### Пример использования:
        ```py
        question.add_content(content = content)
        ```
        """
        content = content.strip()

        if content:
            self.answers.append(content)
            return True
        else:
            return False


class SystemContext(Element):
    """
    `SystemContext` хранит часть доменной модели автошколы и участвует в сериализации дерева приложения.
    Объект участвует в доменном дереве автошколы и сериализуется через registry элементов приложения.

    ### Поля
    - `NOMINATIVE_KEY`: ключ локализации названия одного элемента.
    - `MULTIPLE_KEY`: ключ локализации названия списка элементов.
    - `CREATING_KEY`: ключ сериализации или transport-события, по которому объект отличает один вариант данных от другого.
    - `EDIT_KEY`: ключ локализации сообщения о запрете изменения.
    - `ADD_KEY`: ключ сериализации или transport-события, по которому объект отличает один вариант данных от другого.
    - `content`: хранит контент GPT-запроса для операций этого объекта.
    - `tokens`: часть доменной модели автошколы, используемая при обходе и сериализации дерева.

    ### Методы
    - `check_content`: Проверяет контент GPT-запроса перед использованием.
    - `loads`: Восстанавливает объект из JSON-совместимого словаря.
    - `__init__`: Создаёт объект и сохраняет связи доменного дерева автошколы.
    - `dumps`: Возвращает JSON-совместимый снимок объекта для storage или callback payload.
    - `count_tokens`: Подсчитывает значение, которое используется при проверке лимитов или подготовке GPT-запроса.
    - `get_tokens`: Возвращает tokens из текущего состояния `SystemContext`.
    - `add_content`: Добавляет текстовый блок в GPT-контекст или вопрос.
    - `set_context`: Проверяет и сохраняет контекст обработки события в состоянии `SystemContext`.
    - `get_context`: Возвращает контекст обработки события из текущего состояния `SystemContext`.
    - `set_content`: Проверяет и сохраняет контент GPT-запроса в состоянии `SystemContext`.

    ### Жизненный цикл
    Создаётся app-layer кодом, участвует в обработке пользовательского события и сохраняет изменённое состояние через существующие runtime/storage механизмы.

    ### Пример использования
    ```py
    systemContext: SystemContext
    ```
    """
    NOMINATIVE_KEY: str = "context_single"
    MULTIPLE_KEY: str = "contexts"
    CREATING_KEY: str = "create_context"
    EDIT_KEY: str = "change_context"
    ADD_KEY: str = "add_context"

    @classmethod
    def check_content(cls, content: str) -> bool:
        """
        Проверяет, можно ли сохранить строку как содержимое доменного элемента.

        ### Аргументы:
        :param content: содержимое доменного элемента

        :return: `True`, если строку можно сохранить как содержимое; иначе `False`

        ### Пример использования:
        ```py
        SystemContext.check_content(content = content)
        ```
        """
        return len(content) < MAX_INPUT_LENGTH

    def loads(data: BotTypes.SYSTEM_CONTEXT_TYPE) -> SystemContext:
        """
        Восстанавливает объект из JSON-совместимого словаря.

        ### Аргументы:
        :param data: сериализованный словарь

        :return: восстановленный объект или загруженное состояние

        ### Пример использования:
        ```py
        systemContext.loads(data = data)
        ```
        """
        context_id: int = get_int(data, -1, "id")
        content: str = data.get("content", "")
        t: int = get_int(data, -1, "tokens")
        tokens: int | None = t

        if tokens < 0:
            tokens = None
        elif content and tokens == 0:
            tokens = data.get("tokens")
            log_warn(f"Некорректное значение аргумента `data` под ключом {tokens=} при значении {content=}")
            tokens = None

        return SystemContext(context_id, content, tokens)

    def __init__(self, context_id: int, content: str, tokens: int | None = None):
        """
        Создаёт доменный GPT-объект `SystemContext` и сохраняет настройки, которые затем сериализуются в дерево приложения.

        ### Аргументы:
        :param context_id: context id
        :param content: содержимое доменного элемента
        :param tokens: количество токенов

        ### Пример использования:
        ```py
        systemContext = SystemContext(context_id = context_id, content = content, tokens = tokens)
        ```
        """
        super().__init__(context_id)
        self.content: str = str(content)
        self.tokens: int | None = None if tokens is None else int(tokens)

        if self.tokens is None or (isinstance(self.tokens, int) and self.tokens < 0):
            pass
        # else:
        #     raise ValueError(f"Некорректное значение аргумента {tokens=}")

    def dumps(self) -> BotTypes.SYSTEM_CONTEXT_TYPE:
        """
        Возвращает JSON-совместимый снимок объекта для storage или callback payload.

        :return: JSON-совместимый словарь для сохранения или передачи между слоями

        ### Пример использования:
        ```py
        systemContext.dumps()
        ```
        """
        result: BotTypes.SYSTEM_CONTEXT_TYPE = super().dumps()

        result.update({
            "content": str(self.content),
            "tokens": None if self.tokens is None else int(self.tokens)
        })

        return result

    def count_tokens(self, model: Model | None = None, back: bool = False):
        """
        Подсчитывает значение, которое используется при проверке лимитов или подготовке GPT-запроса.

        ### Аргументы:
        :param model: GPT-модель
        :param back: callback возврата к предыдущему шагу

        :return: результат доменной операции

        ### Пример использования:
        ```py
        systemContext.count_tokens(model = model, back = back)
        ```
        """
        if back:
            return Thread(target = lambda: self.count_tokens(model)).start()

        if not self.content:
            self.tokens = 0
            return

        tokens: int = count_tokens([{"role": "system", "content": self.content}], model)
        self.tokens = int(tokens)

    def get_tokens(self, model: Model | None = None) -> int:
        """
        Возвращает сохранённое количество GPT-токенов.

        ### Аргументы:
        :param model: GPT-модель

        :return: оставшийся лимит токенов

        ### Пример использования:
        ```py
        systemContext.get_tokens(model = model)
        ```
        """
        if self.tokens is None or model is not None:
            self.count_tokens(model)

        return int(self.tokens)

    def add_content(self, content: str):
        """
        Добавляет текстовое содержимое к доменному элементу.

        ### Аргументы:
        :param content: содержимое доменного элемента

        ### Пример использования:
        ```py
        systemContext.add_content(content = content)
        ```
        """
        self.set_context(f"{self.content}\n{content}")

    def set_context(self, content: str):
        """
        Проверяет и сохраняет значение `context`.

        ### Аргументы:
        :param content: содержимое доменного элемента

        ### Пример использования:
        ```py
        systemContext.set_context(content = content)
        ```
        """
        content = str(content)

        if self.content != content:
            self.tokens = None

        self.content = str(content)

    def get_context(self, questions: list[Question]) -> str:
        """
        Возвращает GPT-контекст.

        ### Аргументы:
        :param questions: вопросы, которые нужно поместить в папку или обработать

        :return: context

        ### Пример использования:
        ```py
        systemContext.get_context(questions = questions)
        ```
        """
        content: str = str(self.content).strip()

        if "{}" in content and questions:
            questions_header: str = get_phrase("questions_header") + "\n"
            question_string: str = get_phrase("question_string")
            result: str = f"\n{questions_header}"

            for question in questions:
                answers: str = ", ".join(f"'{answer}'" for answer in question.answers)
                result += question_string.format(question.question, answers)

            return content.format(result)
        else:
            return content

    def set_content(self, content: str) -> bool:
        """
        Проверяет и записывает текст доменного элемента.

        ### Аргументы:
        :param content: содержимое доменного элемента

        :return: результат доменной операции

        ### Пример использования:
        ```py
        systemContext.set_content(content = content)
        ```
        """
        content_before: str = str(self.content)
        self.set_context(content)
        return content_before != self.content

    def add_content(self, content: str) -> bool:
        """
        Добавляет текстовое содержимое к доменному элементу.

        ### Аргументы:
        :param content: содержимое доменного элемента

        :return: результат доменной операции

        ### Пример использования:
        ```py
        systemContext.add_content(content = content)
        ```
        """
        content_before: str = str(self.content)
        self.set_context(f"{content_before}\n{content}")
        return content_before != self.content


class Limit(Element):
    """
    `Limit` хранит часть доменной модели автошколы и участвует в сериализации дерева приложения.
    Объект участвует в доменном дереве автошколы и сериализуется через registry элементов приложения.

    ### Поля
    - `NOMINATIVE_KEY`: ключ локализации названия одного элемента.
    - `MULTIPLE_KEY`: ключ локализации названия списка элементов.
    - `CREATING_KEY`: ключ сериализации или transport-события, по которому объект отличает один вариант данных от другого.
    - `period`: часть доменной модели автошколы, используемая при обходе и сериализации дерева.
    - `limit`: хранит лимит GPT для операций этого объекта.
    - `date`: хранит доступную дату записи для операций этого объекта.
    - `left`: часть доменной модели автошколы, используемая при обходе и сериализации дерева.
    - `shared`: часть доменной модели автошколы, используемая при обходе и сериализации дерева.

    ### Методы
    - `loads`: Восстанавливает объект из JSON-совместимого словаря.
    - `__init__`: Создаёт объект и сохраняет связи доменного дерева автошколы.
    - `dumps`: Возвращает JSON-совместимый снимок объекта для storage или callback payload.
    - `copy`: Создаёт независимую копию объекта без изменения исходного состояния.
    - `debit_tokens`: Списывает tokens с лимитов GPT-клиентов пользователя.
    - `prove_period`: Проверяет введённое пользователем значение для шага `period`.
    - `reset`: Возвращает сценарий к начальному шагу и обновляет UI при необходимости.
    - `check_reset`: Проверяет reset перед использованием.
    - `update`: Синхронизирует данные сценария с уже отправленными UI-сообщениями.
    - `get_answer`: Возвращает ответ пользователя из текущего состояния `Limit`.

    ### Жизненный цикл
    Создаётся app-layer кодом, участвует в обработке пользовательского события и сохраняет изменённое состояние через существующие runtime/storage механизмы.

    ### Пример использования
    ```py
    limit: Limit
    ```
    """
    NOMINATIVE_KEY: str = "limit_single"
    MULTIPLE_KEY: str = "limits"
    CREATING_KEY: str = "create_limit"

    def loads(data: BotTypes.LIMIT_TYPE) -> Limit:
        """
        Восстанавливает объект из JSON-совместимого словаря.

        ### Аргументы:
        :param data: сериализованный словарь

        :return: восстановленный объект или загруженное состояние

        ### Пример использования:
        ```py
        limit.loads(data = data)
        ```
        """
        limit_id: int = get_int(data, 0, "id")
        period: int = get_int(data, 0, "period")
        limit: int = get_int(data, 0, "limit")
        date: datetime = get_date(data, "date")
        left: int = get_int(data, 0, "left")
        shared: bool = get_from(data, "shared", types = (bool,))
        return Limit(limit_id, period, limit, date, left, shared)

    def __init__(self, limit_id: int, period: int, limit: int, date: datetime, left: int, shared: bool):
        """
        Создаёт доменный GPT-объект `Limit` и сохраняет настройки, которые затем сериализуются в дерево приложения.

        ### Аргументы:
        :param limit_id: limit id
        :param period: период действия лимита или статистики
        :param limit: лимит GPT
        :param date: время сообщения или события
        :param left: оставшийся объём лимита
        :param shared: общий ли лимит для нескольких пользователей

        ### Пример использования:
        ```py
        limit = Limit(limit_id = limit_id, period = period, limit = limit, date = date, left = left, shared = shared)
        ```
        """
        super().__init__(limit_id)
        self.period: int = int(period)
        self.limit: int = int(limit)
        self.date: datetime = date
        self.left: int = int(left)
        self.shared: bool = bool(shared)

    def dumps(self) -> BotTypes.LIMIT_TYPE:
        """
        Возвращает JSON-совместимый снимок объекта для storage или callback payload.

        :return: JSON-совместимый словарь для сохранения или передачи между слоями

        ### Пример использования:
        ```py
        limit.dumps()
        ```
        """
        result: BotTypes.LIMIT_TYPE = super().dumps()

        result.update({
            "id": int(self.id),
            "period": int(self.period),
            "limit": int(self.limit),
            "date": int(self.date.timestamp()),
            "left": int(self.left),
            "shared": bool(self.shared)
        })

        return result

    def copy(self, limit_id: int) -> Limit:
        """
        Создаёт независимую копию объекта без изменения исходного состояния.

        ### Аргументы:
        :param limit_id: limit id

        :return: результат доменной операции

        ### Пример использования:
        ```py
        limit.copy(limit_id = limit_id)
        ```
        """
        return Limit(limit_id, self.period, self.limit, self.date, self.left, self.shared)

    def debit_tokens(self, tokens: int):
        """
        Списывает tokens с лимитов GPT-клиентов пользователя.

        ### Аргументы:
        :param tokens: количество токенов, списываемое с лимитов клиента

        ### Пример использования:
        ```py
        limit.debit_tokens(tokens = tokens)
        ```
        """
        self.left -= int(tokens)

    def prove_period(self) -> bool:
        """
        Проверяет введённое пользователем значение для шага `period`.

        :return: результат доменной операции

        ### Пример использования:
        ```py
        limit.prove_period()
        ```
        """
        current_time = datetime.now()
        time_passed = current_time - self.date
        return time_passed.total_seconds() >= self.period

    def reset(self):
        """
        Возвращает сценарий к начальному шагу и обновляет UI при необходимости.

        ### Пример использования:
        ```py
        limit.reset()
        ```
        """
        self.date = datetime.now()
        self.left = int(self.limit)

    def check_reset(self):
        """
        Проверяет значение `reset` перед сохранением или использованием.

        ### Пример использования:
        ```py
        limit.check_reset()
        ```
        """
        if self.prove_period():
            self.reset()

    def update(self, limit: Limit):
        """
        Синхронизирует данные сценария с уже отправленными UI-сообщениями.

        ### Аргументы:
        :param limit: лимит GPT

        ### Пример использования:
        ```py
        limit.update(limit = limit)
        ```
        """
        reset: bool = False

        if limit.period != self.period:
            self.period = limit.period
            reset = True

        if limit.limit != self.limit:
            self.limit = limit.limit
            reset = True

            if self.left > self.limit:
                self.left = self.limit

        if reset:
            self.reset()

    def get_answer(self, cut_string: bool = True) -> str:
        """
        Возвращает строку, показываемую пользователю как вариант ответа.

        ### Аргументы:
        :param cut_string: нужно ли сокращать строку до длины кнопки

        :return: ответ пользователя

        ### Пример использования:
        ```py
        limit.get_answer(cut_string = cut_string)
        ```
        """
        period_string: str = parse_period(self.period)

        if self.shared:
            return get_phrase("shared_client").format(period_string)
        else:
            return get_phrase("user_client").format(period_string)


class Client():
    """
    `Client` хранит часть доменной модели автошколы и участвует в сериализации дерева приложения.
    Объект участвует в доменном дереве автошколы и сериализуется через registry элементов приложения.

    ### Поля
    - `id`: внутренний идентификатор записи или доменного объекта.
    - `limits`: хранит лимиты GPT для операций этого объекта.

    ### Методы
    - `loads`: Восстанавливает объект из JSON-совместимого словаря.
    - `__init__`: Создаёт объект и сохраняет связи доменного дерева автошколы.
    - `add_limit`: Добавляет лимит в список ограничений GPT-клиента.
    - `remove_id`: Удаляет id из внутреннего состояния или storage.
    - `debit_tokens`: Списывает tokens с лимитов GPT-клиентов пользователя.
    - `dumps`: Возвращает JSON-совместимый снимок объекта для storage или callback payload.
    - `find_limit`: Ищет лимит GPT по данным, которые пришли из вызывающего слоя.
    - `update_limits`: Обновляет лимиты GPT с учётом текущего состояния объекта.

    ### Жизненный цикл
    Создаётся app-layer кодом, участвует в обработке пользовательского события и сохраняет изменённое состояние через существующие runtime/storage механизмы.

    ### Пример использования
    ```py
    client: Client
    ```
    """
    def loads(data: BotTypes.CLIENT_TYPE) -> Client:
        """
        Восстанавливает объект из JSON-совместимого словаря.

        ### Аргументы:
        :param data: сериализованный словарь

        :return: восстановленный объект или загруженное состояние

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        client.loads(data = data)
        ```
        """
        client_id: int = get_int(data, -1, "id")

        if client_id < 0:
            id = client_id
            raise ValueError(f"Некорректное значение под ключом {id=}")

        client: Client = Client(client_id)

        for limit_data in data.get("limits", []):
            limit: Limit = Limit.loads(limit_data)
            client.limits.append(limit)

        return client

    def __init__(self, client_id: int):
        """
        Создаёт доменный GPT-объект `Client` и сохраняет настройки, которые затем сериализуются в дерево приложения.

        ### Аргументы:
        :param client_id: client id

        ### Пример использования:
        ```py
        client = Client(client_id = client_id)
        ```
        """
        self.id: int = int(client_id)
        self.limits: list[Limit] = []

    def add_limit(self, limit: Limit):
        """
        Добавляет лимит в список ограничений GPT-клиента.

        ### Аргументы:
        :param limit: настройка лимита GPT для клиента или пользователя

        ### Пример использования:
        ```py
        client.add_limit(limit = limit)
        ```
        """
        self.limits.append(limit)

    def remove_id(self, limit_id: int) -> bool:
        """
        Удаляет элемент с указанным id из коллекции.

        ### Аргументы:
        :param limit_id: limit id

        :return: результат доменной операции

        ### Пример использования:
        ```py
        client.remove_id(limit_id = limit_id)
        ```
        """
        removed: bool = False

        for limit in list(self.limits):
            if limit.id == limit_id:
                self.limits.remove(limit)
                removed = True

        return removed

    def debit_tokens(self, tokens: int):
        """
        Списывает tokens с лимитов GPT-клиентов пользователя.

        ### Аргументы:
        :param tokens: количество токенов, списываемое с лимитов клиента

        ### Пример использования:
        ```py
        client.debit_tokens(tokens = tokens)
        ```
        """
        for limit in self.limits:
            limit.debit_tokens(tokens)


    def dumps(self) -> BotTypes.CLIENT_TYPE:
        """
        Возвращает JSON-совместимый снимок объекта для storage или callback payload.

        :return: JSON-совместимый словарь для сохранения или передачи между слоями

        ### Пример использования:
        ```py
        client.dumps()
        ```
        """
        return {
            "id": int(self.id),
            "limits": [limit.dumps() for limit in self.limits]
        }

    def find_limit(self, period: int) -> Limit | None:
        """
        Ищет лимит GPT в текущих данных объекта или storage.

        ### Аргументы:
        :param period: период действия лимита или статистики

        :return: лимит GPT или None, если подходящей записи нет

        ### Пример использования:
        ```py
        client.find_limit(period = period)
        ```
        """
        period = int(period)

        for limit in self.limits:
            if limit.period == period:
                return limit

        return None

    def update_limits(self, client: Client, create_limit: Callable[Limit]):
        """
        Обновляет limits по текущему состоянию объекта.

        ### Аргументы:
        :param client: клиент или пользователь GPT-сценария
        :param create_limit: create limit

        ### Пример использования:
        ```py
        client.update_limits(client = client, create_limit = create_limit)
        ```
        """
        periods: list[int] = [int(limit.period) for limit in client.limits]
        required_limits: dict[int, Limit] = {
            int(limit.period): limit for limit in client.limits
        }
        current_limits: dict[int, Limit] = {}

        for limit in list(self.limits):
            period: int = int(limit.period)

            if period in periods:
                periods.remove(period)
                current_limits[period] = limit
            else:
                self.limits.remove(limit)

        for key in required_limits:
            required_limit: Limit = required_limits[key]
            current_limit: Limit | None = current_limits.get(key, None)

            if current_limit:
                current_limit.update(required_limit)
            else:
                self.limits.append(create_limit(required_limit.period, required_limit.limit, shared = False, user_only = True))
