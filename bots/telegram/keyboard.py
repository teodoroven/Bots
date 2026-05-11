"""
Описывает клавиатуру сообщения.
Модуль относится к архитектурной зоне: слой унификации транспортов `bots`, который скрывает различия Telegram и VK за общими объектами сообщений, клавиатур, вложений и событий.

### Публичные классы
- `Keyboard`: модель клавиатуры сообщения.

### Публичные функции
- Публичные функции отсутствуют.

### Связи
Используется транспортным слоем и wrapper-логикой, чтобы app-layer работал с `Message`, `Keyboard`, `Button`, `Attachment` и `Event` без привязки к конкретной соцсети.
"""

from __future__ import annotations


from bots.utils.mapping import get_from, get_int
from bots.utils.text import cut
from bots.compat import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Iterable,
    KeyboardButton,
    Never,
    ReplyKeyboardMarkup,
)

from bots.base.bindings import Bot
from bots.base.attachment import Attachment as BaseAttachment
from bots.base.button import Button as BaseButton
from bots.base.keyboard import Keyboard as BaseKeyboard
from bots.base.message import Message as BaseMessageClass
from bots.base.voice_message import VoiceMessage as BaseVoiceMessage

from bots.telegram.button import Button

class Keyboard(BaseKeyboard):
    """
    Telegram inline/reply keyboard.
    Превращает базовые строки кнопок в `InlineKeyboardMarkup` или
    `ReplyKeyboardMarkup`, учитывая ширину строк и inline-режим.

    ### Поля
    - `keyboard`: хранит клавиатуру сообщения для операций этого объекта.

    ### Методы
    - `loads`: Восстанавливает объект из JSON-совместимого словаря.
    - `create_button`: Создаёт кнопку клавиатуры и связывает результат с текущим app-layer состоянием.
    - `__init__`: Создаёт объект и сохраняет данные, нужные transport-layer для отправки, сравнения или восстановления объекта.
    - `update`: Синхронизирует данные сценария с уже отправленными UI-сообщениями.
    - `get_unused_buttons`: Возвращает unused buttons из текущего состояния `Keyboard`.
    - `get_keyboard`: Возвращает клавиатуру сообщения из текущего состояния `Keyboard`.

    ### Жизненный цикл
    Экземпляры создаются из конфигурации транспорта, принимают события платформы и отдают app-layer унифицированные wrapper-объекты.

    ### Пример использования
    ```py
    keyboard: Keyboard
    ```
    """



    def loads(data: "Telebot.Keyboard.KEYBOARD_TYPE") -> Telebot.Keyboard:
        """
        Восстанавливает объект из JSON-совместимого словаря.

        ### Аргументы:
        :param data: сериализованный словарь

        :return: восстановленный объект или загруженное состояние

        ### Пример использования:
        ```py
        keyboard.loads(data = data)
        ```
        """
        buttons: list["Telebot.Keyboard.Button.BUTTON_TYPE"] = get_from(data, "buttons")
        max_width: int = get_int(data, -1, "max_width")
        inline: bool = get_from(data, "inline")

        keyboard: Telebot.Keyboard = Telebot.Keyboard(
            [button if isinstance(button, str) else Telebot.Keyboard.Button.loads(button) for button in buttons],
            max_width = max_width, inline = inline
        )
        return keyboard

    @classmethod
    def create_button(cls, button: Bot.Keyboard.Button | str, inline: bool) -> Telebot.Keyboard.Button | None:
        """
        Создаёт button и связывает результат с текущим объектом.

        ### Аргументы:
        :param button: кнопка клавиатуры
        :param inline: признак inline-клавиатуры

        :return: созданный объект: button

        ### Пример использования:
        ```py
        Keyboard.create_button(button = button, inline = inline)
        ```
        """
        if isinstance(button, cls.Button):
            return button
        elif isinstance(button, Bot.Keyboard.Button):
            return cls.Button(text = button.get_text(), callback_data = button.callback_data, url = button.url)
        elif isinstance(button, str):
            return cls.Button(button)
        else:
            return None

    def __init__(self, buttons: Iterable[str | Telebot.Keyboard.Button], max_width: int, inline: bool):
        """
        Создаёт клавиатуру `Keyboard` и сохраняет набор кнопок для отправки через конкретный transport-адаптер.

        ### Аргументы:
        :param buttons: кнопки, которые нужно показать пользователю
        :param max_width: максимальная ширина строки кнопок
        :param inline: признак inline-клавиатуры

        ### Пример использования:
        ```py
        keyboard = Keyboard(buttons = buttons, max_width = max_width, inline = inline)
        ```
        """
        super().__init__(buttons, inline = inline, max_width = max_width)

        # Поле с клавиатурой
        self.keyboard: InlineKeyboardMarkup | ReplyKeyboardMarkup = None

        self.update(buttons)

    def update(self, buttons: Iterable[str | Telebot.Keyboard.Button]):
        """
        Синхронизирует данные сценария с уже отправленными UI-сообщениями.

        ### Аргументы:
        :param buttons: кнопки, которые нужно показать пользователю

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        keyboard.update(buttons = buttons)
        ```
        """
        self.buttons.clear()

        # Кнопки под сообщением
        if self.inline:
            self.keyboard = InlineKeyboardMarkup(row_width = self.max_width)
            buttons_list: list[InlineKeyboardButton] = []

            # Распаковка указанных кнопок
            for button in buttons:
                button: Telebot.Keyboard.Button | None = self.__class__.create_button(button, self.inline)

                if button is None:
                    raise ValueError(f"Некорректное значение аргумента {buttons=}")

                # В кнопку не помещается больше 40 символов
                text: str = cut(button.get_text(), self.__class__.MAX_BUTTON_LENGTH)
                kwarg: dict[str, str] = button.get_kwarg()

                if text and kwarg:
                    buttons_list.append(InlineKeyboardButton(text, **kwarg))
                    self.buttons.append(button)

            self.keyboard.add(*buttons_list)

        # Кнопки над клавиатурой
        else:
            self.keyboard = ReplyKeyboardMarkup(resize_keyboard = True)
            buttons_list = []

            for button in buttons:
                if not isinstance(button, Bot.Keyboard.Button):
                    button: Telebot.Keyboard.Button = self.__class__.Button(button)

                text: str = cut(button.get_text(), self.__class__.MAX_BUTTON_LENGTH)
                buttons_list.append(KeyboardButton(text))
                self.buttons.append(button)

            self.keyboard.add(*buttons_list)

    def get_unused_buttons(self) -> list[Never]:
        """
        Возвращает кнопки, которые не вошли в Telegram-клавиатуру.

        :return: unused buttons

        ### Пример использования:
        ```py
        keyboard.get_unused_buttons()
        ```
        """
        return []

    def get_keyboard(self) -> str:
        """
        Возвращает сохранённую клавиатуру сообщения.

        :return: клавиатура сообщения

        :raises TypeError: если входные или сохранённые данные имеют неподдерживаемый формат

        ### Пример использования:
        ```py
        keyboard.get_keyboard()
        ```
        """
        if isinstance(self.keyboard, InlineKeyboardMarkup | ReplyKeyboardMarkup):
            return self.keyboard
        else:
            raise TypeError()
