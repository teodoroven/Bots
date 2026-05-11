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

from bots.base.bindings import Bot
from bots.base.attachment import Attachment as BaseAttachment
from bots.base.button import Button as BaseButton
from bots.base.keyboard import Keyboard as BaseKeyboard
from bots.base.message import Message as BaseMessageClass
from bots.base.voice_message import VoiceMessage as BaseVoiceMessage

class Button(BaseButton):
    """
    VK-кнопка клавиатуры.
    Преобразует общий текст/callback/color в данные, которые принимает
    `vk_api.keyboard.VkKeyboard`.

    ### Поля
    - `BUTTON_TYPE`: часть transport-состояния, используемая при сборке, сравнении или отправке wrapper-объекта.
    - `DEFAULT_MIN_WIDTH`: значение, используемое конструктором при отсутствии явного аргумента.
    - `DEFAULT_BUTTON_TYPE`: значение, используемое конструктором при отсутствии явного аргумента.
    - `MIN_WIDTH_VALUES`: идентификатор объекта или связанной сущности, по которому runtime восстанавливает связь между слоями.
    - `min_width`: ограничение размера, которое защищает transport/API от слишком длинного payload.

    ### Методы
    - `loads`: Восстанавливает объект из JSON-совместимого словаря.
    - `__init__`: Создаёт объект и сохраняет данные, нужные transport-layer для отправки, сравнения или восстановления объекта.
    - `dumps`: Возвращает JSON-совместимый снимок объекта для storage или callback payload.
    - `check_min_width`: Проверяет min width перед использованием.
    - `set_min_width`: Проверяет и сохраняет значение `min width` в `Button`.
    - `get_min_width`: Возвращает min width из текущего состояния `Button`.

    ### Жизненный цикл
    Экземпляры создаются из конфигурации транспорта, принимают события платформы и отдают app-layer унифицированные wrapper-объекты.

    ### Пример использования
    ```py
    button: Button
    ```
    """
    BUTTON_TYPE = BotTypes.BUTTON_TYPE
    DEFAULT_MIN_WIDTH: int = 1
    DEFAULT_BUTTON_TYPE: str = "text"

    MIN_WIDTH_VALUES: dict[bool, tuple[int]] = {
        # inline=True
        True: (1, 2),
        # inline=False
        False: (1, 2, 3, 4)
    }

    @staticmethod
    def loads(data: BUTTON_TYPE) -> Vkbot.Keyboard.Button:
        """
        Восстанавливает объект из JSON-совместимого словаря.

        ### Аргументы:
        :param data: сериализованный словарь

        :return: восстановленная VK-кнопка

        ### Пример использования:
        ```py
        Button.loads(data = data)
        ```
        """
        text: str = get_from(data, "text")
        color: int = get_int(data, -1, "color")
        min_width: int = get_int(data, -1, "min_width")
        callback_data: str | None = get_from(data, "callback_data")
        url: str | None = get_from(data, "url")
        return Vkbot.Keyboard.Button(text, color, min_width, callback_data, url)

    def __init__(self, text: str, color: Literal[0, 1, 2, 3] | str | VkKeyboardColor = Bot.Keyboard.Button.DEFAULT_COLOR, min_width: Literal[1, 2, 3, 4] = DEFAULT_MIN_WIDTH, callback_data: str | None = None, url: str | None = None):
        """
        Создаёт кнопку `Button` для transport-layer и сохраняет данные, из которых конкретный адаптер собирает клавиатуру.

        ### Аргументы:
        :param text: текст
        :param color: цвет кнопки в терминах конкретного транспорта
        :param min_width: min width
        :param callback_data: payload callback-кнопки
        :param url: ссылка для кнопки или вложения

        ### Пример использования:
        ```py
        button = Button(text = text, color = color, min_width = min_width, callback_data = callback_data, url = url)
        ```
        """
        super().__init__(text, color, callback_data, url)
        self.min_width: int = -1
        self.set_min_width(min_width)

    def dumps(self) -> BUTTON_TYPE:
        """
        Возвращает JSON-совместимый снимок объекта для storage или callback payload.

        :return: JSON-совместимый словарь для сохранения или передачи между слоями

        ### Пример использования:
        ```py
        button.dumps()
        ```
        """
        result: "Vkbot.Keyboard.Button.BUTTON_TYPE" = super().dumps()

        result.update({
            "min_width": self.get_min_width()
        })

        return result


    def check_min_width(self, min_width: int) -> bool:
        """
        Проверяет значение `min width` перед сохранением или использованием.

        ### Аргументы:
        :param min_width: min width

        :return: `True`, если значение `min width` перед сохранением или использованием; иначе `False`

        ### Пример использования:
        ```py
        button.check_min_width(min_width = min_width)
        ```
        """
        return isinstance(min_width, int) and min_width > 0 and min_width < 5

    def set_min_width(self, min_width: int):
        """
        Проверяет и сохраняет значение `min width`.

        ### Аргументы:
        :param min_width: min width

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        button.set_min_width(min_width = min_width)
        ```
        """
        if self.check_min_width(min_width):
            self.min_width = min_width
        else:
            raise ValueError(f"Некорректное значение аргумента {min_width=} при {self.inline=}")

    def get_min_width(self) -> int:
        """
        Возвращает минимальную ширину кнопки для VK-клавиатуры.

        :return: min width

        :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

        ### Пример использования:
        ```py
        button.get_min_width()
        ```
        """
        if self.check_min_width(self.min_width):
            return self.min_width
        else:
            raise ValueError(f"Некорректное значение атрибута {self.min_width=} при {self.inline=}")
