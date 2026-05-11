"""
Содержит helper-функции для сокращения и форматирования текста.
Модуль относится к архитектурной зоне: слой унификации транспортов `bots`, который скрывает различия Telegram и VK за общими объектами сообщений, клавиатур, вложений и событий.

### Публичные классы
- Публичные классы отсутствуют.

### Публичные функции
- `cut`: обрезает `Iterable` или `str` до заданной длины.
- `preceding`: экранирует спецсимволы для Markdown-разметки транспорта.

### Связи
Используется транспортным слоем и wrapper-логикой, чтобы app-layer работал с `Message`, `Keyboard`, `Button`, `Attachment` и `Event` без привязки к конкретной соцсети.
"""

from __future__ import annotations

from bots.compat import Iterable

def cut(obj: Iterable | str, max_length: int = float("inf"), dots: bool = False) -> Iterable:
    """
    Обрезает индексируемый объект, если его длина превышает `max_length`.
    Если `dots=True` и `obj` является строкой, в конец результата добавляется
    `...`, когда многоточие помещается в `max_length`. Для нестроковых объектов
    `dots` не меняет результат.

    ### Аргументы:
    :param obj: объект для обрезки
    :param max_length: максимальная длина результата
    :param dots: добавлять ли `...` при обрезке строки

    ### Примеры вызова:
    ```
    cut("1234567890", 5) # "12345"
    cut("12", 5) # "12"
    cut("1234567890") # "1234567890"
    cut("1234567890", 5, dots = True) # "12..."
    cut("1234567890", 3, dots = True) # "123"
    cut((1, 2, 3, 4, 5), 2) # (1, 2)
    cut([1, 2, 3, 4, 5], 2) # [1, 2]
    cut([1, 2, 3, 4, 5], 2, dots = True) # [1, 2]
    cut(1) # TypeError
    ```

    ### Пример использования:
    ```
    if len(text) > MAX_BUTTON_LENGTH:
        text = cut(text, MAX_BUTTON_LENGTH, dots = True)
    ```

    ### Вызываемые исключения:
    :raises TypeError: если `obj` не поддерживает `len` или срез.

    :return: исходный объект или его обрезанная копия
    """
    if len(obj) > max_length:
        if isinstance(obj, str):
            max_length: int = int(max_length) - len("..." if dots and max_length > 3 else "")
            return obj[:max_length].rstrip() + ("..." if dots else "")
        else:
            return obj[:max_length]
    else:
        return obj
def preceding(string: str):
    """
    Экранирует спецсимволы Telegram MarkdownV2 для отправки через `telebot`.
    Функция добавляет обратный слэш перед символами `[]()~`>#+-=|{}.!`.

    ### Аргументы:
    :param string: исходный текст для Telegram MarkdownV2

    :return: строка с экранированными MarkdownV2-символами
    """
    symbols: tuple[tuple[str, str]] = (
        # ("_", "\_"),
        # ("*", "\*"),
        ("[", "\\["),
        ("]", "\\]"),
        ("(", "\\("),
        (")", "\\)"),
        ("~", "\\~"),
        ("`", "\\`"),
        (">", "\\>"),
        ("#", "\\#"),
        ("+", "\\+"),
        ("-", "\\-"),
        ("=", "\\="),
        ("|", "\\|"),
        ("{", "\\{"),
        ("}", "\\}"),
        (".", "\\."),
        ("!", "\\!")
    )

    for before, after in symbols:
        string = string.replace(before, after)

    return string
