"""
Описывает runtime-обработку GPT-контента.
Модуль относится к архитектурной зоне: прикладной слой `relay`, который связывает пользователей, сессии, доменную модель, GPT, уведомления и runtime-логику приложения.

### Публичные классы
- `GptContentMixin`: runtime-логика GPT-контента.

### Публичные функции
- Публичные функции отсутствуют.

### Связи
Используется app-layer сценариями, обработчиками, сессиями и runtime-миксинами для единого пользовательского потока между ботами, GPT и storage.
"""

from __future__ import annotations


class GptContentMixin:
    """
    Добавляет `App` операции gptcontent без привязки к transport-layer.
    Mixin рассчитан на включение в `App` и работает с его registry, storage, пользователями, ботами и очередями.

    ### Методы
    - `create_question`: Создаёт вопрос анкеты или GPT-контекста и связывает результат с текущим app-layer состоянием.
    - `remove_question`: Удаляет вопрос анкеты или GPT-контекста из внутреннего состояния или storage.
    - `add_answer`: Добавляет ответ пользователя в GPT batch.
    - `get_questions`: Возвращает вопросы анкеты или GPT-контекста из текущего состояния `GptContentMixin`.
    - `set_context`: Проверяет и сохраняет контекст обработки события в состоянии `GptContentMixin`.
    - `add_context`: Добавляет доменный GPT-контекст в запрос.
    - `create_context`: Создаёт контекст обработки события и связывает результат с текущим app-layer состоянием.
    - `remove_context`: Удаляет контекст обработки события из внутреннего состояния или storage.

    ### Жизненный цикл
    Создаётся app-layer кодом, участвует в обработке пользовательского события и сохраняет изменённое состояние через существующие runtime/storage механизмы.

    ### Пример использования
    ```py
    app: GptContentMixin
    ```
    """
    def create_question(self, content: str) -> int:
        """
        Создаёт question и связывает результат с текущим объектом.

        ### Аргументы:
        :param content: содержимое доменного элемента

        :return: созданный объект: question

        ### Пример использования:
        ```py
        gptContentMixin.create_question(content = content)
        ```
        """
        rows: list[str] = content.split("\n")

        question: str = ""

        answers: list[str] = []

        if len(rows) == 1:

            question = content

        else:

            question, *answers = rows

        question_id: int = self.create_id()

        context_question: Question = Question(question_id, question, answers)

        self.questions[question_id] = context_question

        self.add_element(context_question, self.questions_folder.id)


        self.save_gpt()

        self.save_root()

        return context_question

    def remove_question(self, question_id: int) -> bool:
        """
        Удаляет GPT-вопрос из выбранного набора.

        ### Аргументы:
        :param question_id: question id

        :return: значение, которое runtime использует для продолжения обработки события

        ### Пример использования:
        ```py
        gptContentMixin.remove_question(question_id = question_id)
        ```
        """
        if self.remove_element(question_id, from_id = self.questions_folder.id):

            self.save_root()

            self.save_gpt()

            return True

        return False

    def add_answer(self, question_id: int, answer: str) -> bool:
        """
        Добавляет ответ пользователя в GPT batch.

        ### Аргументы:
        :param question_id: question id
        :param answer: ответ пользователя

        :return: значение, которое runtime использует для продолжения обработки события

        ### Пример использования:
        ```py
        gptContentMixin.add_answer(question_id = question_id, answer = answer)
        ```
        """
        context_question: Question = self.find_element(question_id, Question)

        if answer:

            answer = str(answer).strip()

        if context_question and answer:

            context_question.answers.append(answer)

            self.save_gpt()

            self.save_root()

    def get_questions(self) -> list[Question]:
        """
        Возвращает вопросы, выбранные для GPT-запроса.

        :return: строка вида `Филиал «Название»` или `Элемент «id»`s

        ### Пример использования:
        ```py
        gptContentMixin.get_questions()
        ```
        """
        result: list[Question] = []

        for question in self.questions_folder.elements:

            if question.check():

                result.append(question)

        return result

    def set_context(self, context_id: int) -> SystemContext | None:
        """
        Проверяет и сохраняет context в объекте.

        ### Аргументы:
        :param context_id: context id

        :return: значение, которое runtime использует для продолжения обработки события

        ### Пример использования:
        ```py
        gptContentMixin.set_context(context_id = context_id)
        ```
        """
        if context_id in self.contexts:

            self.system_context = self.contexts[context_id]

            self.save_gpt()

            return self.system_context

        else:

            return None

    def add_context(self, content: str) -> SystemContext | None:
        """
        Добавляет доменный GPT-контекст в запрос.

        ### Аргументы:
        :param content: содержимое доменного элемента

        :return: значение, которое runtime использует для продолжения обработки события

        ### Пример использования:
        ```py
        gptContentMixin.add_context(content = content)
        ```
        """

        if not self.system_context:

            return None

        self.system_context.add_content(content)

        self.save_gpt()

        return self.system_context

    def create_context(self, content: str) -> int:
        """
        Создаёт context и связывает результат с текущим объектом.

        ### Аргументы:
        :param content: содержимое доменного элемента

        :return: созданный объект: context

        ### Пример использования:
        ```py
        gptContentMixin.create_context(content = content)
        ```
        """
        context_id: int = self.create_id()

        system_context: SystemContext = SystemContext(context_id, content)

        self.contexts[context_id] = system_context

        self.add_element(system_context, self.contexts_folder.id)


        self.save_gpt()

        self.save_root()

        return system_context

    def remove_context(self, context_id: int) -> bool:
        """
        Удаляет GPT-контекст из выбранного набора.

        ### Аргументы:
        :param context_id: context id

        :return: значение, которое runtime использует для продолжения обработки события

        ### Пример использования:
        ```py
        gptContentMixin.remove_context(context_id = context_id)
        ```
        """
        if self.remove_element(context_id, from_id = self.contexts_folder.id):

            if self.system_context and self.system_context.id == context_id:

                self.system_context = None

            self.save_gpt()

            self.save_root()

            return True

        return False
