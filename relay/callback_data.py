"""
Описывает callback data, которой обмениваются кнопки, сессии и обработчики.
Модуль относится к архитектурной зоне: прикладной слой `relay`, который связывает пользователей, сессии, доменную модель, GPT, уведомления и runtime-логику приложения.

### Публичные классы
- `Callback`: структура callback data для кнопок и сессий.

### Публичные функции
- Публичные функции отсутствуют.

### Связи
Используется app-layer сценариями, обработчиками, сессиями и runtime-миксинами для единого пользовательского потока между ботами, GPT и storage.
"""

from __future__ import annotations




from bots.types import JSONABLE
from callbacks import ACTION_CALLBACK
from callbacks import ANSWER_CALLBACK
from callbacks import SESSION_CALLBACK
from .common import json
from .utils import catch_json, catch_parsefiles, join_callback, split_callback
class Callback():

    """
    Хранит payload callback-кнопки для app-layer.

    `Callback` связывает кнопку transport-layer с конкретной session-логикой:
    в строку payload попадает id сессии и дополнительные JSON-совместимые
    аргументы, которые обработчик восстановит после нажатия пользователем.

    ### Поля
    - `session_id`: runtime-зависимость или поле, используемое текущим session-сценарием.
      Значение `None` сохраняется как часть payload, когда кнопка не привязана
      к конкретной сессии.
    - `args`: JSON-совместимые аргументы callback-обработчика. Они передаются
      позиционно и сериализуются через `join_callback`.

    ### Методы
    - `loads`: разбирает строковый payload transport-кнопки.
    - `__init__`: сохраняет id сессии и аргументы callback.
    - `stringfy`: собирает строку payload для кнопки.

    ### Жизненный цикл
    Создаётся при сборке кнопок меню, передаётся transport-layer как строка и
    восстанавливается обработчиком входящего callback-события.

    ### Пример использования
    ```py
    callback = Callback(session_id = session.id, action)
    ```
    """
    def loads(string: str) -> Callback:
        """
        Разбирает строковый callback payload и возвращает `Callback`.

        Метод ожидает строку, собранную через `join_callback`, где первый
        элемент указывает на session-callback, второй хранит id сессии, а
        остальные элементы становятся `args`.

        ### Аргументы:
        :param string: строка callback data из transport-события

        :return: восстановленный callback с id сессии и аргументами

        :raises ValueError: если payload не содержит session-callback

        ### Пример использования:
        ```py
        callback = Callback.loads(string = event.callback_data)
        ```
        """
        args: list[str] = split_callback(string)

        if args:
            if args[0] == SESSION_CALLBACK:
                session_id: str = args[1]
                return Callback(None if session_id == "None" else int(session_id), *args[2:])

        raise ValueError(f"Callback не содержит данные о сессии: {repr(string)}")

        result: Callback = Callback()
        data: dict = {}

        with catch_json():
            data = json.loads(string)

        with catch_parsefiles():
            session_id: int | None = data["session"]

            if isinstance(session_id, int) and Session.check_id(session_id):
                result.session_id = session_id

        with catch_parsefiles():
            result.args = split_callback(data["args"])

        return result

    def __init__(self, session_id: int | None, *args: Iterable[JSONABLE]):
        """
        Создаёт callback payload для кнопки и сохраняет id session-сценария вместе с аргументами обработчика.

        ### Аргументы:
        :param session_id: id session-сценария или `None` для callback без привязки
        :param args: дополнительные сериализуемые аргументы callback/session-сценария

        :raises ValueError: если один из аргументов нельзя представить как JSON-совместимое значение

        ### Пример использования:
        ```py
        callback = Callback(session_id = session_id, args = args)
        ```
        """
        self.session_id: int | None = None if session_id is None else int(session_id)
        self.args: list[JSONABLE] = list(args)

        for elem in self.args:
            if not isinstance(elem, JSONABLE):
                raise ValueError(f"Некорректное значение одного из аргументов, аргумент обязан быть приводимым к JSON {repr(elem)}")

    def stringfy(self) -> str:
        """
        Собирает строку callback data для transport-кнопки.

        :return: строковый payload, который можно положить в кнопку Telegram/VK

        ### Пример использования:
        ```py
        callback.stringfy()
        ```
        """
        return join_callback(SESSION_CALLBACK, None if self.session_id is None else int(self.session_id), *self.args)
