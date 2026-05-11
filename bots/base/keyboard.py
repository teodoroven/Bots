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

from bots.compat import BotTypes, Iterable, Never
from bots.types import KEYBOARD_TYPE

from bots.base.button import Button

class Keyboard():
    """
    Базовая клавиатура transport-layer.
    Хранит строки кнопок, inline-флаг и ширину раскладки; Telegram/VK
    наследники превращают это состояние в конкретный объект SDK.

    ### Поля
    - `KEYBOARD_TYPE`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.
    - `MAX_BUTTON_LENGTH`: ограничение размера, которое защищает transport/API от слишком длинного payload.
    - `inline`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.
    - `max_width`: ограничение размера, которое защищает transport/API от слишком длинного payload.
    - `buttons`: хранит кнопки клавиатуры для операций этого объекта.

    ### Методы
    - `__init__`: Создаёт объект и сохраняет данные, нужные transport-layer для отправки, сравнения или восстановления объекта.
    - `dumps`: Возвращает JSON-совместимый снимок объекта для storage или callback payload.
    - `check_editable`: Проверяет editable перед использованием.
    - `get_unused_buttons`: Возвращает unused buttons из текущего состояния `Keyboard`.
    - `check_inline`: Проверяет inline перед использованием.

    ### Жизненный цикл
    Экземпляры создаются из конфигурации транспорта, принимают события платформы и отдают app-layer унифицированные wrapper-объекты.

    ### Пример использования
    ```py
    keyboard: Keyboard
    ```
    """
    KEYBOARD_TYPE = BotTypes.KEYBOARD_TYPE
    MAX_BUTTON_LENGTH: int = 40


    def __init__(self, buttons: Iterable[str | Button], max_width: int, inline: bool):
        """
        Создаёт клавиатуру `Keyboard` и сохраняет набор кнопок для отправки через конкретный transport-адаптер.

        ### Аргументы:
        :param buttons: кнопки, которые нужно показать пользователю
        :param max_width: максимальная ширина строки кнопок
        :param inline: признак inline-клавиатуры

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        keyboard = Keyboard(buttons = buttons, max_width = max_width, inline = inline)
        ```
        """

        # inline=True -> кнопки в сообщении, inline=False -> кнопки под клавиатурой

        self.inline: bool = bool(inline)

        # Максимальное количество кнопок в ряду
        self.max_width: int = int(max_width)

        # Список кнопок для сохранения клавиатуры
        self.buttons: list[Bot.Keyboard.Button] = []

        if not isinstance(inline, bool):
            raise ValueError(f"Некорректное значение аргумента {inline=}")

    def __repr__(self) -> str:
        classname: str = "Vkbot.Keyboard" if hasattr(self, "unused_buttons") else "Telebot.Keyboard"
        inline = self.inline
        max_width = self.max_width
        buttons = ",".join(repr(button) for button in self.buttons)
        return f"{classname}({inline=} {max_width=} len={len(self.buttons)})[{buttons}]"

    def dumps(self) -> KEYBOARD_TYPE:
        """
        Возвращает JSON-совместимый снимок объекта для storage или callback payload.

        :return: JSON-совместимый словарь для сохранения или передачи между слоями

        ### Пример использования:
        ```py
        keyboard.dumps()
        ```
        """
        return {
            "buttons": [button.dumps() for button in self.buttons],
            "max_width": int(self.max_width),
            "inline": bool(self.inline)
        }

    def check_editable(self) -> bool:
        """
        Проверяет значение `editable` перед сохранением или использованием.

        :return: `True`, если значение `editable` перед сохранением или использованием; иначе `False`

        ### Пример использования:
        ```py
        keyboard.check_editable()
        ```
        """
        return self.inline

    def get_unused_buttons(self) -> list[Never]:
        """
        Возвращает кнопки, которые не вошли в раскладку клавиатуры.

        :return: unused buttons

        ### Пример использования:
        ```py
        keyboard.get_unused_buttons()
        ```
        """
        return []

    def check_inline(self) -> bool:
        """
        Проверяет значение inline-флага клавиатуры.

        :return: `True`, если значение inline-флага клавиатуры; иначе `False`

        ### Пример использования:
        ```py
        keyboard.check_inline()
        ```
        """
        return bool(self.inline)
