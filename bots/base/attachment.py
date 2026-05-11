"""
Описывает базовое вложение сообщения и его сериализацию.
Модуль относится к архитектурной зоне: слой унификации транспортов `bots`, который скрывает различия Telegram и VK за общими объектами сообщений, клавиатур, вложений и событий.

### Публичные классы
- `Attachment`: базовая модель вложения сообщения.

### Публичные функции
- Публичные функции отсутствуют.

### Связи
Используется транспортным слоем и wrapper-логикой, чтобы app-layer работал с `Message`, `Keyboard`, `Button`, `Attachment` и `Event` без привязки к конкретной соцсети.
"""

from __future__ import annotations

from bots.compat import (
    BotTypes,
    BytesIO,
    Never,
    abspath,
    abstractmethod,
    isfile,
)
from bots.types import ATTACHMENT_TYPE

class Attachment():
    """
    Базовый контракт transport-вложения.
    Хранит platform id, локальный filename и байты файла; конкретные Telegram/VK
    классы добавляют сетевую загрузку, upload и правила сериализации.

    ### Поля
    - `ATTACHMENT_TYPE`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.
    - `id`: внутренний идентификатор записи или доменного объекта.
    - `filename`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.
    - `data`: загруженное содержимое файла в памяти; заполняется transport-реализацией `download`.

    ### Методы
    - `__init__`: Создаёт объект и сохраняет данные, нужные transport-layer для отправки, сравнения или восстановления объекта.
    - `dumps`: Возвращает JSON-совместимый снимок объекта для storage или callback payload.
    - `compare`: Сравнивает объект с другим вложением того же transport-типа.
    - `save_as`: Сохраняет загруженные байты в файл.
    - `set_id`: Проверяет и сохраняет значение `id` в `Attachment`.
    - `get_id`: Возвращает id из текущего состояния `Attachment`.
    - `get_type`: Возвращает type из текущего состояния `Attachment`.
    - `check_filename`: Проверяет filename перед использованием.
    - `set_filename`: Проверяет и сохраняет значение `filename` в `Attachment`.
    - `get_filename`: Возвращает filename из текущего состояния `Attachment`.

    ### Жизненный цикл
    Экземпляры создаются из конфигурации транспорта, принимают события платформы и отдают app-layer унифицированные wrapper-объекты.

    ### Пример использования
    ```py
    attachment: Attachment
    ```
    """
    ATTACHMENT_TYPE = BotTypes.ATTACHMENT_TYPE

    def __init__(self, attachment_id: int | str):
        """
        Создаёт вложение `Attachment` и сохраняет transport-данные, нужные для отправки или восстановления сообщения.

        ### Аргументы:
        :param attachment_id: attachment id

        ### Пример использования:
        ```py
        attachment = Attachment(attachment_id = attachment_id)
        ```
        """
        self.id: int | str = ""
        self.filename: str = ""
        self.set_id(attachment_id)

        self.data: BytesIO | None = None

    def dumps(self) -> ATTACHMENT_TYPE:
        """
        Возвращает JSON-совместимый снимок объекта для storage или callback payload.

        :return: JSON-совместимый словарь для сохранения или передачи между слоями

        ### Пример использования:
        ```py
        attachment.dumps()
        ```
        """
        return {
            "id": self.get_id(),
            "filename": self.get_filename(),
            "classname": self.__class__.__name__
        }

    def compare(self, attachment: Bot.Attachment):
        """
        Сравнивает вложение с другим вложением по сохранённому id.

        ### Аргументы:
        :param attachment: вложение wrapper-сообщения

        :return: `True`, если id вложений совпадают; иначе `False`

        ### Пример использования:
        ```py
        attachment.compare(attachment = attachment)
        ```
        """
        return attachment.get_id() == self.get_id()

    def save_as(self, filename: str):
        """
        Сохраняет подготовленные данные в storage, файл или transport-объект.

        ### Аргументы:
        :param filename: имя файла

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        attachment.save_as(filename = filename)
        ```
        """
        if not self.check():
            raise ValueError(f"Некорректное значение атрибута {self.data=}. Перед сохранением необходимо загрузить файл методом download.")

        with open(filename, "wb") as file:
            self.data.seek(0)
            file.write(self.data.read())

    @abstractmethod
    def set_id(self, attachment_id: int | str) -> Never:
        """
        Базовый контракт проверки и сохранения transport id вложения.
        Реальные правила id зависят от Telegram/VK и реализуются наследниками.

        ### Аргументы:
        :param attachment_id: id вложения в формате конкретного транспорта

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        attachment.set_id(attachment_id = attachment_id)
        ```
        """
        raise NotImplementedError("Вместо используйте Vkbot.Attachment или Telebot.Attachment")

    def get_id(self) -> int | str:
        """
        Возвращает сохранённый идентификатор объекта.

        :return: идентификатор текущего объекта

        ### Пример использования:
        ```py
        attachment.get_id()
        ```
        """
        return self.id

    @abstractmethod
    def get_type(self) -> Never:
        """
        Возвращает сохранённый тип объекта.

        :return: тип текущего объекта

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        attachment.get_type()
        ```
        """
        raise NotImplementedError("Вместо используйте Vkbot.Attachment или Telebot.Attachment")


    def check_filename(self, filename: str) -> bool:
        """
        Проверяет, можно ли использовать строку как имя файла.

        ### Аргументы:
        :param filename: имя файла

        :return: `True`, если строку можно использовать как имя файла; иначе `False`

        ### Пример использования:
        ```py
        attachment.check_filename(filename = filename)
        ```
        """
        return isinstance(filename, str) and (self.id or isfile(filename))

    def set_filename(self, filename: str):
        """
        Проверяет и сохраняет имя файла в объекте.

        ### Аргументы:
        :param filename: имя файла

        :raises FileNotFoundError: если нижележащий слой сообщает об ошибке операции

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        attachment.set_filename(filename = filename)
        ```
        """
        if self.check_filename(filename):
            self.filename = abspath(filename)
        elif isinstance(filename, str):
            raise FileNotFoundError(f"Некорректное значение аргумента {filename=}. Файл обязан сущестовать")
        else:
            raise ValueError(f"Некорректное значение аргумента {filename=}")

    def get_filename(self) -> str:
        """
        Возвращает сохранённое имя файла.

        :return: имя файла

        :raises FileNotFoundError: если нижележащий слой сообщает об ошибке операции

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        attachment.get_filename()
        ```
        """
        if self.check_filename(self.filename):
            return self.filename
        elif isinstance(self.filename, str):
            raise FileNotFoundError(f"Некорректное значение атрибута {self.filename=}. Файл обязан сущестовать")
        else:
            raise ValueError(f"Некорректное значение атрибута {self.filename=}")
