"""
Описывает кнопку клавиатуры конкретного слоя.
Модуль относится к архитектурной зоне: слой унификации транспортов `bots`, который скрывает различия Telegram и VK за общими объектами сообщений, клавиатур, вложений и событий.

### Публичные классы
- `Button`: модель кнопки клавиатуры бота.

### Публичные функции
- Публичные функции отсутствуют.

### Связи
Используется транспортным слоем и wrapper-логикой, чтобы app-layer работал с `Message`, `Keyboard`, `Button`, `Attachment` и `Event` без привязки к конкретной соцсети.
"""

from __future__ import annotations


from bots.utils.mapping import get_from, get_int
from bots.compat import BotTypes, Literal, VkKeyboardColor
from bots.types import BUTTON_TYPE, Literal

class Button():
    """
    Базовая кнопка inline-клавиатуры.
    Хранит текст, callback payload и цвет; Telegram/VK наследники превращают
    это состояние в конкретные SDK-объекты клавиатуры.

    ### Поля
    - `BUTTON_TYPE`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.
    - `DEFAULT_BUTTON_TYPE`: значение, используемое конструктором при отсутствии явного аргумента.
    - `DEFAULT_COLOR`: значение, используемое конструктором при отсутствии явного аргумента.
    - `COLORS`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.
    - `text`: текстовое содержимое, которое показывается пользователю, отправляется в GPT или сохраняется в доменной модели.
    - `color`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.
    - `type`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.
    - `callback_data`: данные интерактивной кнопки или клавиатуры, которые transport-layer отправляет вместе с сообщением.
    - `url`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.

    ### Методы
    - `loads`: Восстанавливает объект из JSON-совместимого словаря.
    - `__init__`: Создаёт объект и сохраняет данные, нужные transport-layer для отправки, сравнения или восстановления объекта.
    - `dumps`: Возвращает JSON-совместимый снимок объекта для storage или callback payload.
    - `check_text`: Проверяет text перед использованием.
    - `set_text`: Проверяет и сохраняет значение `text` в `Button`.
    - `get_text`: Возвращает подпись кнопки.
    - `check_color`: Проверяет color перед использованием.
    - `set_color`: Проверяет и сохраняет значение `color` в `Button`.
    - `get_color`: Возвращает сохранённый цвет кнопки.
    - `check_callback_data`: Проверяет непустой callback payload.

    ### Жизненный цикл
    Экземпляры создаются из конфигурации транспорта, принимают события платформы и отдают app-layer унифицированные wrapper-объекты.

    ### Пример использования
    ```py
    button: Button
    ```
    """
    BUTTON_TYPE = BotTypes.BUTTON_TYPE
    DEFAULT_BUTTON_TYPE: str = "text"
    DEFAULT_COLOR: VkKeyboardColor = VkKeyboardColor.PRIMARY

    COLORS: dict[tuple[int, str, VkKeyboardColor], VkKeyboardColor] = {
        (0, "PRIMARY", "BLUE", "СИНИЙ", "СИНЯЯ", "ГОЛУБОЙ", "СИНИЙ", "#5181B8",
        VkKeyboardColor.PRIMARY): VkKeyboardColor.PRIMARY,
        (1, "SECONDARY", "WHITE", "БЕЛЫЙ", "БЕЛАЯ", "#FFFFFF",
        VkKeyboardColor.SECONDARY): VkKeyboardColor.SECONDARY,
        (2, "NEGATIVE", "RED", "КРАСНЫЙ", "КРАСНАЯ", "#E64646",
        VkKeyboardColor.NEGATIVE): VkKeyboardColor.NEGATIVE,
        (3, "POSITIVE", "GREEN", "ЗЕЛЕНЫЙ", "ЗЕЛЁНАЯ", "ЗЕЛЕНЫЙ", "ЗЕЛЕНАЯ", "#4BB34B",
        VkKeyboardColor.POSITIVE): VkKeyboardColor.POSITIVE,
    }

    @staticmethod
    def loads(data: BUTTON_TYPE) -> Bot.Keyboard.Button:
        """
        Восстанавливает объект из JSON-совместимого словаря.

        ### Аргументы:
        :param data: сериализованный словарь

        :return: восстановленная кнопка

        ### Пример использования:
        ```py
        Button.loads(data = data)
        ```
        """
        text: str = get_from(data, "text")
        color: int = get_int(data, Bot.Keyboard.Button.DEFAULT_COLOR, "color")
        callback_data: str | None = get_from(data, "callback_data")
        url: str | None = get_from(data, "url")
        return Bot.Keyboard.Button(text, color = color, callback_data = callback_data, url = url)

    def __init__(self, text: str, color: Literal[0, 1, 2, 3] | str | VkKeyboardColor = DEFAULT_COLOR, callback_data: str | None = "", url: str | None = None):
        """
        Создаёт кнопку `Button` для transport-layer и сохраняет данные, из которых конкретный адаптер собирает клавиатуру.

        ### Аргументы:
        :param text: текст
        :param color: цвет кнопки в терминах конкретного транспорта
        :param callback_data: payload callback-кнопки
        :param url: ссылка для кнопки или вложения

        ### Пример использования:
        ```py
        button = Button(text = text, color = color, callback_data = callback_data, url = url)
        ```
        """
        self.text: str = ""
        self.color: VkKeyboardColor = self.__class__.DEFAULT_COLOR
        self.type: Literal["text", "callback_data", "url"] = self.__class__.DEFAULT_BUTTON_TYPE
        self.callback_data: str | None = None
        self.url: str | None = None

        self.set_text(text)
        self.set_color(color)
        self.set_callback_data(callback_data or (text if not url else None))
        self.set_url(url)

    def __repr__(self) -> str:
        text: str = repr(self.text)

        if self.callback_data:
            callback_data = self.callback_data
            if callback_data != self.text:
                return f"<{text} {callback_data=}>"
            else:
                return f"<{text} c>"
        elif self.url:
            url = self.url
            return f"<{text} {url=}>"
        else:
            return f"<{text}>"

    def dumps(self) -> BUTTON_TYPE:
        """
        Возвращает JSON-совместимый снимок объекта для storage или callback payload.

        :return: JSON-совместимый словарь для сохранения или передачи между слоями

        ### Пример использования:
        ```py
        button.dumps()
        ```
        """
        return {
            "text": self.get_text(),
            "color": tuple(self.__class__.COLORS.values()).index(self.get_color()),
            "type": self.type if self.type in ("text", "callback_data", "url") else self.__class__.DEFAULT_BUTTON_TYPE,
            "callback_data": self.get_callback_data() if self.type == "callback_data" else None,
            "url": self.get_url() if self.type == "url" else None
        }


    def check_text(self, text: str) -> bool:
        """
        Проверяет текст кнопки.

        ### Аргументы:
        :param text: текст

        :return: `True`, если передана непустая строка; иначе `False`

        ### Пример использования:
        ```py
        button.check_text(text = text)
        ```
        """
        return isinstance(text, str) and str(text).strip()

    def set_text(self, text: str):
        """
        Проверяет и сохраняет значение `text` в `Button`.

        ### Аргументы:
        :param text: текст сообщения или пользовательского ввода

        :raises ValueError: если значение не проходит локальную проверку перед сохранением

        ### Пример использования:
        ```py
        button.set_text(text = text)
        ```
        """
        if self.check_text(text):
            self.text = text
        else:
            raise ValueError(f"Некорректное значение аргумента {text=}")

    def get_text(self) -> str:
        """
        Возвращает сохранённый текст сообщения.

        :return: текст текущего сообщения

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        button.get_text()
        ```
        """
        if self.check_text(self.text):
            return str(self.text).strip()
        else:
            raise ValueError(f"Некорректное значение атрибута {self.text=}")


    def check_color(self, color: Literal[0, 1, 2, 3] | str | VkKeyboardColor) -> bool:
        """
        Проверяет значение `color` перед сохранением или использованием.

        ### Аргументы:
        :param color: цвет кнопки в терминах конкретного транспорта

        :return: `True`, если значение `color` перед сохранением или использованием; иначе `False`

        ### Пример использования:
        ```py
        button.check_color(color = color)
        ```
        """
        if isinstance(color, str):
            color = str(color).upper()

        for keys in self.COLORS:
            if color in keys:
                return True

        return False

    def set_color(self, color: Literal[0, 1, 2, 3] | str | VkKeyboardColor):
        """
        Проверяет и сохраняет значение `color`.

        ### Аргументы:
        :param color: цвет кнопки в терминах конкретного транспорта

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        button.set_color(color = color)
        ```
        """
        if isinstance(color, str):
            color = str(color).upper()

        for keys, value in self.COLORS.items():
            if color in keys:
                self.color = value
                return

        raise ValueError(f"Некорректное значение аргумента {color=}")

    def get_color(self) -> VkKeyboardColor:
        """
        Возвращает сохранённый цвет кнопки после локальной проверки.

        :return: color

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        button.get_color()
        ```
        """
        if self.check_color(self.color):
            return self.color
        else:
            raise ValueError(f"Некорректное значение аргумента {getattr(self, 'color', None)=}")


    def check_callback_data(self, callback_data: str) -> bool:
        """
        Проверяет callback payload перед сохранением в кнопку.
        Базовая реализация требует только непустую строку; конкретные обработчики
        разбирают содержимое payload позже.

        ### Аргументы:
        :param callback_data: payload callback-кнопки

        :return: `True`, если payload callback-кнопки можно разобрать; иначе `False`

        ### Пример использования:
        ```py
        button.check_callback_data(callback_data = callback_data)
        ```
        """
        return isinstance(callback_data, str) and callback_data

    def set_callback_data(self, callback_data: str | None):
        """
        Проверяет и сохраняет значение `callback data` в `Button`.

        ### Аргументы:
        :param callback_data: данные callback-кнопки, пришедшие из транспорта

        :raises ValueError: если значение не проходит локальную проверку перед сохранением

        ### Пример использования:
        ```py
        button.set_callback_data(callback_data = callback_data)
        ```
        """
        if callback_data is None:
            self.callback_data = None

            if self.type == "callback_data":
                self.type = self.__class__.DEFAULT_BUTTON_TYPE
        elif self.check_callback_data(callback_data):
            if self.type == "url":
                raise ValueError(f"Для кнопки со ссылкой нельзя установить callback_data")

            self.callback_data = callback_data
            self.type = "callback_data"
        else:
            raise ValueError(f"Некорректное значение аргумента {callback_data=}")

    def get_callback_data(self) -> str:
        """
        Возвращает аргументы callback payload текущей кнопки.

        :return: payload callback-кнопки

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        button.get_callback_data()
        ```
        """
        if self.type != "callback_data":
            raise ValueError(f"Кнопка имеет callback_data только если её тип 'callback_data', не {self.type}")
        elif self.check_callback_data(self.callback_data):
            return str(self.callback_data)
        else:
            raise ValueError(f"Некорректное значение атрибута {self.callback_data=}")


    def check_url(self, url: str) -> bool:
        """
        Проверяет значение `url` перед сохранением или использованием.

        ### Аргументы:
        :param url: ссылка для кнопки или вложения

        :return: `True`, если значение `url` перед сохранением или использованием; иначе `False`

        ### Пример использования:
        ```py
        button.check_url(url = url)
        ```
        """
        return isinstance(url, str) and url

    def set_url(self, url: str | None):
        """
        Проверяет и сохраняет значение `url`.

        ### Аргументы:
        :param url: ссылка для кнопки или вложения

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        button.set_url(url = url)
        ```
        """
        if url is None:
            self.url = None

            if self.type == "url":
                self.type = self.__class__.DEFAULT_BUTTON_TYPE
        elif self.check_url(url):
            if self.type == "callback_data":
                raise ValueError(f"Для кнопки с callback_data нельзя установить ссылку")

            self.url = url
            self.type = "url"
        else:
            raise ValueError(f"Некорректное значение аргумента {url=}")

    def get_url(self) -> str:
        """
        Возвращает сохранённый URL вложения.

        :return: url

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        button.get_url()
        ```
        """
        if self.type != "url":
            raise ValueError(f"Кнопка имеет ссылку только если её тип 'url', не {self.type}")
        elif self.check_url(self.url):
            return str(self.url).strip()
        else:
            raise ValueError(f"Некорректное значение атрибута {self.url=}")


    def check_type(self) -> bool:
        """
        Проверяет согласованность transport-типа кнопки с сохранённым payload.

        :return: `True`, если тип кнопки соответствует заполненному text, callback_data или url; иначе `False`

        ### Пример использования:
        ```py
        button.check_type()
        ```
        """
        if self.check_callback_data(self.callback_data) and self.type == "callback_data":
            return True
        elif self.check_url(self.url) and self.type == "url":
            return True
        elif self.check_text(self.text) and self.type == self.__class__.DEFAULT_BUTTON_TYPE:
            return True
        else:
            return False

    def get_type(self) -> Literal["text", "callback_data", "url"]:
        """
        Возвращает сохранённый тип объекта.

        :return: тип текущего объекта

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        button.get_type()
        ```
        """
        if self.check_type():
            return self.type
        else:
            raise ValueError(f"Некорректное значение атрибута {self.type=}")
