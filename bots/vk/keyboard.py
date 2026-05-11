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
from bots.compat import BotTypes, Iterable, Literal, VkKeyboard
from bots.types import KEYBOARD_TYPE, Literal

from bots.base.bindings import Bot
from bots.base.attachment import Attachment as BaseAttachment
from bots.base.button import Button as BaseButton
from bots.base.keyboard import Keyboard as BaseKeyboard
from bots.base.message import Message as BaseMessageClass
from bots.base.voice_message import VoiceMessage as BaseVoiceMessage

from bots.vk.button import Button

class Keyboard(BaseKeyboard):
    """
    VK-клавиатура для `messages.send`.
    Собирает строки кнопок в `VkKeyboard`, учитывая inline-режим, ширину строк
    и ограничения VK на callback payload.

    ### Поля
    - `KEYBOARD_TYPE`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.
    - `MAX_BUTTON_LENGTH`: ограничение размера, которое защищает transport/API от слишком длинного payload.
    - `keyboard`: хранит клавиатуру сообщения для операций этого объекта.
    - `unused_buttons`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.

    ### Методы
    - `loads`: Восстанавливает объект из JSON-совместимого словаря.
    - `create_button`: Создаёт кнопку клавиатуры и связывает результат с текущим app-layer состоянием.
    - `__init__`: Создаёт объект и сохраняет данные, нужные transport-layer для отправки, сравнения или восстановления объекта.
    - `update`: Синхронизирует данные сценария с уже отправленными UI-сообщениями.
    - `dumps`: Возвращает JSON-совместимый снимок объекта для storage или callback payload.
    - `get_unused_buttons`: Возвращает unused buttons из текущего состояния `Keyboard`.
    - `get_keyboard`: Возвращает клавиатуру сообщения из текущего состояния `Keyboard`.

    ### Жизненный цикл
    Экземпляры создаются из конфигурации транспорта, принимают события платформы и отдают app-layer унифицированные wrapper-объекты.

    ### Пример использования
    ```py
    keyboard: Keyboard
    ```
    """
    KEYBOARD_TYPE = BotTypes.KEYBOARD_TYPE
    MAX_BUTTON_LENGTH: int = 40


    def loads(data: KEYBOARD_TYPE) -> Vkbot.Keyboard:
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
        buttons: list[dict[str, str]] = get_from(data, "buttons")
        max_width: int = get_int(data, -1, "max_width")
        inline: bool = get_from(data, "inline")
        unused_buttons: list[dict[str, str]] = get_from(data, "unused_buttons")

        keyboard: Vkbot.Keyboard = Vkbot.Keyboard(
            [button if isinstance(button, str) else Vkbot.Keyboard.Button.loads(button) for button in buttons],
            max_width = max_width, inline = inline
        )
        keyboard.unused_buttons = [button if isinstance(button, str) else Vkbot.Keyboard.Button.loads(button) for button in unused_buttons]
        return keyboard

    @classmethod
    def create_button(cls, button: Bot.Keyboard.Button | str, inline: bool) -> Vkbot.Keyboard.Button | None:
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

        # Распаковка текста, цвета и ширины кнопки

        if isinstance(button, cls.Button):
            return button
        elif isinstance(button, Bot.Keyboard.Button):
            return cls.Button(text = button.get_text(), color = button.get_color(), callback_data = button.callback_data, url = button.url)
        # Если кнопка передана как строка (только текст)
        elif isinstance(button, str):
            # default callback_data
            if inline:
                return cls.Button(button, callback_data = button)
            else:
                return cls.Button(button)
        else:
            return None

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
        super().__init__(buttons, inline = inline, max_width = max_width)

        # Поле с клавиатурой
        self.keyboard: VkKeyboard

        # Список кнопок из buttons, которые не влезли в клавиатуру из-за ограничений
        self.unused_buttons: list[Vkbot.Keyboard.Button] = []

        # Максимальное количество кнопок в одном ряду
        if self.max_width not in Vkbot.Keyboard.Button.MIN_WIDTH_VALUES.get(self.inline):
            raise ValueError(f"Некорректное значение аргумента {max_width=} при {self.inline=}, список корректных значений: {Vkbot.Keyboard.Button.MIN_WIDTH_VALUES.get(self.inline)}")

        self.update(buttons)

    def update(self, buttons: Iterable[str | Button]):
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

        # Максимум 2 или 4 ячейки в ряду
        max_line: Literal[2, 4]

        # Максимум 5 или 9 рядов
        max_lines: Literal[5, 9]

        # Максимум 10 или 40 ячеек, кнопка шириной=2 занимает 2 ячейки, шириной=1 занимает 1 ячейку
        max_cells: Literal[10, 40]

        # Ограничения клавиатуры
        if self.inline:
            # Кнопки в сообщении
            self.keyboard: VkKeyboard = VkKeyboard(one_time = False, inline = True)
            max_line = 2
            max_lines: int = 5
            max_cells: int = 10
        else:
            # Кнопки под полем ввода
            self.keyboard: VkKeyboard = VkKeyboard()
            max_line: int = 4
            # WARNING: Ограничение 9 вместо 10, потому что 10 не работает
            max_lines: int = 10 - 1
            max_cells: int = 40

        self.test: str = ""

        # Оставшееся количество мест в ряду
        cells_left: int = min(max_line, self.max_width)

        # Список кнопок для сохранения клавиатуры
        self.buttons: list[Vkbot.Keyboard.Button] = []

        for i, button in enumerate(buttons):
            # Флаг обозначает, что достигнуто одно из ограничений и больше ячеек для кнопок нет
            out_of_cells: bool = False

            button: Vkbot.Keyboard.Button | None = self.__class__.create_button(button, inline = self.inline)

            if button is None:
                raise ValueError(f"Некорректное значение аргумента {buttons=}")

            min_width: int = button.get_min_width()

            if min_width > max_line:
                min_width = max_line

            button_type: Literal["text", "callback_data", "url"] = button.get_type()

            # Проверяем остались ли ячейки под кнопку в клавиатуре
            if max_cells >= min_width:
                max_cells -= min_width
            else:
                out_of_cells = True

            if isinstance(button, self.__class__.Button) and button_type in ("callback_data", "url"):
                pass

            # Проверяем остались ли ячейки под кнопку в ряду
            if cells_left >= min_width:
                # Ячейки остались, уменьшаем их количество на ширину кнопки
                cells_left -= min_width
            # Ячейки в ряду кончились, но можно создать ещё один ряд
            elif max_lines > 0 and not out_of_cells:
                self.test += "\n"
                max_lines -= 1
                self.keyboard.add_line()
                cells_left = min(max_line, self.max_width) - min_width
            # Если нельзя создать ещё один ряд, то места кончились
            else:
                out_of_cells = True

            # Места в клавиатуре кончились раньше, чем кнопки
            if out_of_cells:
                # Сохраняем кнопки, которые не влезли
                self.unused_buttons.clear()

                for button in buttons[i:]:
                    self.unused_buttons.append(self.__class__.create_button(button, inline = self.inline))

                break
            # Места ещё остались
            else:
                self.test += f"<{button.get_text()};{button.get_color()}>"

                match button_type:
                    case "callback_data":
                        payload = {"type": button.get_callback_data()}
                        self.keyboard.add_callback_button(button.get_text(), color = button.get_color(), payload = payload)
                    case "open_link":
                        self.keyboard.add_openlink_button(button.get_text(), link = button.get_url())
                    case _:
                        # "text"
                        self.keyboard.add_button(button.get_text(), color = button.get_color())

                self.buttons.append(button)


    def dumps(self) -> KEYBOARD_TYPE:
        """
        Возвращает JSON-совместимый снимок объекта для storage или callback payload.

        :return: JSON-совместимый словарь для сохранения или передачи между слоями

        ### Пример использования:
        ```py
        keyboard.dumps()
        ```
        """
        result: "Vkbot.Keyboard.KEYBOARD_TYPE" = super().dumps()

        result.update({
            "unused_buttons": [button.dumps() for button in self.unused_buttons]
        })

        return result

    def get_unused_buttons(self) -> list[Button]:
        """
        Возвращает кнопки, которые не вошли в VK-клавиатуру.

        :return: unused buttons

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        keyboard.get_unused_buttons()
        ```
        """
        # Проверка типа, в списке неиспользованных кнопок могут быть только кнопки или тексты
        for button in self.unused_buttons:
            if type(button) not in (str, self.__class__.Button):
                raise ValueError(f"Некорректное значение поля Vkbot.Keyboard.unused_buttons, ожидался список строк или Vkbot.Keyboard.Button, а получено {type(button)}")

        return self.unused_buttons

    def get_keyboard(self) -> str:
        """
        Возвращает сохранённую клавиатуру сообщения.

        :return: клавиатура сообщения

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        keyboard.get_keyboard()
        ```
        """
        if isinstance(self.keyboard, VkKeyboard):
            if self.buttons:
                return self.keyboard.get_keyboard()
            else:
                return VkKeyboard.get_empty_keyboard()
        else:
            raise ValueError(f"Некорректное значение атрибута {self.keyboard=}")
