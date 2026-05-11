"""
Загружает и выдаёт локализованные фразы проекта.
Модуль находится рядом с entrypoint-слоем и предоставляет `Phrases` и
`PHRASES_TYPE` для app-layer, transport-layer и старых compatibility imports.
Фразы читаются из JSON-файлов через `modules.readfiles`.
"""

from __future__ import annotations

import json

from random import choice
from typing import Literal

from modules import readfiles


PHRASES_TYPE = dict[str, dict[str, dict[str, tuple[str, ...]]]]


class Phrases():

    """
    Хранилище локализованных фраз проекта.
    Данные хранятся в структуре `type_key -> phrase_key -> lang -> tuple[str]`.
    При запросе одной фразы класс выбирает случайный вариант для нужного языка,
    а если ключ не найден, возвращает сам `phrase_key`.

    ### Поля
    - `lang`: текущий язык локализации, который используется при чтении фраз без явного `lang`.
    - `phrases`: загруженные фразы по типу, ключу и языку.

    ### Методы
    - `__init__`: Создаёт объект и заполняет его начальное состояние
    - `set_lang`: меняет текущий язык локализации.
    - `load`: Читает сохранённые фразы и заполняет словарь локализации
    - `add_phrase`: добавляет набор строк для ключа фразы.
    - `get_phrase`: возвращает случайную строку для ключа фразы.
    - `get_phrase_list`: возвращает все строки для ключа фразы.
    - `get_key_phrase`: ищет ключ по тексту локализованной фразы.

    ### Жизненный цикл
    Создаётся при старте приложения, загружает JSON-файлы в память и дальше
    используется как read-mostly справочник текстов для сообщений и меню.

    ### Пример использования
    ```py
        phrases = Phrases(json_filenames = json_filenames, lang = lang)
    ```
    """
    def __init__(self, json_filenames: tuple[str, ...], lang: Literal["ru", "en"]):
        """
        Создаёт хранилище фраз, сохраняет язык и загружает JSON-файлы.

        ### Аргументы:
        :param json_filenames: основные и резервные JSON-файлы локализации
        :param lang: язык, который используется при запросах без явного `lang`
        """
        self.lang: Literal["ru", "en"]
        self.phrases: PHRASES_TYPE = {
            "textContent": {}
        }
        self.set_lang(lang)
        self.load(json_filenames)

    def set_lang(self, lang: Literal["ru", "en"]):
        """
        Сохраняет текущий язык локализации.
        Метод меняет только in-memory поле `lang`.

        ### Аргументы:
        :param lang: язык локализации

        ### Пример использования:
        ```py
        obj.set_lang(lang = lang)
        ```
        """
        self.lang = str(lang).lower()

    def load(self, json_filenames: tuple[str, ...]):
        """
        Читает первый доступный JSON-файл и заполняет словарь локализации.
        Ожидается структура `type_key -> phrase_key -> lang -> list[str]`.
        Метод меняет только in-memory словарь `phrases`; если файлы не найдены
        или пусты, объект остаётся с уже существующими фразами.

        ### Аргументы:
        :param json_filenames: JSON-файлы с локализованными фразами

        ### Пример использования:
        ```py
        obj.load(json_filenames = json_filenames)
        ```
        """
        content: str | None = readfiles(json_filenames)

        if not content:
            return None

        data: dict[str, dict[str, dict[str, list[str] | tuple[str, ...]]]] = json.loads(content)
        type_key: str
        phrase_key: str
        lang: str
        strings: list[str] | tuple[str, ...]

        for type_key, types in data.items():
            for phrase_key, phrases in types.items():
                for lang, strings in phrases.items():
                    self.add_phrase(str(type_key), str(phrase_key), str(lang), tuple(map(str, strings)))

    def add_phrase(self, type_key: Literal["textContent"], phrase_key: str, lang: Literal["ru", "en"], strings: tuple[str, ...]):
        """
        Добавляет строки локализации для заданного типа, ключа и языка.
        Метод меняет только in-memory словарь `phrases`.

        ### Аргументы:
        :param type_key: раздел фраз, например `textContent`
        :param phrase_key: ключ фразы внутри раздела
        :param lang: язык локализации
        :param strings: варианты текста для выбранного языка

        ### Пример использования:
        ```py
        obj.add_phrase(type_key = type_key, phrase_key = phrase_key, lang = lang, strings = strings)
        ```
        """
        if type_key not in self.phrases:
            self.phrases[type_key] = {}

        if phrase_key not in self.phrases[type_key]:
            self.phrases[type_key][phrase_key] = {}

        self.phrases[type_key][phrase_key][lang] = strings

    def get_phrase(self, phrase_key: str, type_key: Literal["textContent"] = "textContent", lang: Literal["ru", "en"] | None = None) -> str:
        """
        Возвращает локализованную строку для ключа фразы.
        Если для ключа есть несколько вариантов, выбирает один случайно. Если
        ключ или язык отсутствует, возвращает `phrase_key`.

        ### Аргументы:
        :param phrase_key: ключ фразы внутри раздела
        :param type_key: раздел фраз, например `textContent`
        :param lang: язык локализации

        :return: найденная строка или исходный `phrase_key`

        ### Пример использования:
        ```py
        result = obj.get_phrase(phrase_key = phrase_key, type_key = type_key, lang = lang)
        ```
        """
        if lang is None:
            lang = self.lang

        phrases_list: tuple[str, ...] = self.phrases.get(type_key, {}).get(phrase_key, {}).get(lang, (phrase_key,))

        if len(phrases_list) == 1:
            return str(phrases_list[0])
        elif phrases_list:
            return str(choice(phrases_list))
        else:
            return str(phrase_key)

    def get_phrase_list(self, phrase_key: str, type_key: Literal["textContent"] = "textContent", lang: Literal["ru", "en"] | None = None) -> tuple[str, ...]:
        """
        Возвращает все варианты локализованной строки для ключа фразы.

        ### Аргументы:
        :param phrase_key: ключ фразы внутри раздела
        :param type_key: раздел фраз, например `textContent`
        :param lang: язык локализации

        :return: найденная строка, список строк или ключ фразы

        ### Пример использования:
        ```py
        result = obj.get_phrase_list(phrase_key = phrase_key, type_key = type_key, lang = lang)
        ```
        """
        if lang is None:
            lang = self.lang

        phrases_list: tuple[str, ...] = self.phrases.get(type_key, {}).get(phrase_key, {}).get(lang, (phrase_key,))
        return phrases_list

    def get_key_phrase(self, phrase_string: str, type_key: Literal["textContent"] = "textContent", lang: Literal["ru", "en"] | None = None) -> str | None:
        """
        Ищет ключ фразы по её локализованному тексту.

        ### Аргументы:
        :param phrase_string: текст фразы, по которому нужно найти ключ
        :param type_key: раздел фраз, например `textContent`
        :param lang: язык локализации

        :return: найденная строка, список строк или ключ фразы

        ### Пример использования:
        ```py
        result = obj.get_key_phrase(phrase_string = phrase_string, type_key = type_key, lang = lang)
        ```
        """
        if lang is None:
            lang = self.lang

        phrase_key: str
        languages: dict[str, tuple[str, ...]]

        for phrase_key, languages in self.phrases.get(type_key, {}).items():
            if lang in languages:
                phrases_list: tuple[str, ...] = languages[lang]

                if phrase_string in phrases_list:
                    return phrase_key

            lang_code: str
            lang_phrases: tuple[str, ...]

            for lang_code, lang_phrases in languages.items():
                if phrase_string in lang_phrases:
                    return phrase_key

        return None
