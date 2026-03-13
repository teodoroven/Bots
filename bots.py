# import
from __future__ import annotations
from modules import *
from callbacks import CALLBACK_REMOVE

# import lib
import re
from abc import abstractmethod
import json
# import pyperclip
# import requests

# import function
from requests import Response
from time import sleep
from threading import Thread
from datetime import datetime
from datetime import timedelta
from io import BufferedReader, BytesIO
from PIL import Image
# from cv2 import VideoCapture

# import types
from warnings import warn
from itertools import chain
from typing import Literal
from typing import Union
from typing import Never
from typing import Any
from typing import NoReturn
from typing import Callable
from collections.abc import Iterable

# import os
from os import getcwd
from os.path import basename
from os.path import join
from os.path import abspath
from os.path import normpath
from os.path import isfile
from os.path import exists
from os.path import splitext

# import vk_api
from vk_api import VkApi
from vk_api import VkUpload
from vk_api.utils import get_random_id
# from vk_api.longpoll import VkLongPoll, VkEventType
# from vk_api.longpoll import Event as VkEvent
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType, DotDict, VkBotEvent
from vk_api.bot_longpoll import VkBotMessageEvent
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from vk_api.exceptions import ApiError

# import telebot
from telebot import TeleBot
from telebot.types import ReplyKeyboardMarkup
from telebot.types import KeyboardButton
from telebot.types import InlineKeyboardMarkup
from telebot.types import InlineKeyboardButton
from telebot.types import InputMediaPhoto
from telebot.types import InputMediaVideo
from telebot.types import InputMediaAudio
from telebot.types import InputMediaDocument
from telebot.types import Message as TelebotMessage
from telebot.types import CallbackQuery
from telebot.types import File
from telebot.types import Voice
from telebot.types import PhotoSize
from telebot.types import Video
from telebot.types import Document
from telebot.types import Audio
from telebot.apihelper import ApiTelegramException

# import speech_recognition
from speech_recognition import Recognizer
from speech_recognition import AudioData
from speech_recognition import WavFile
from speech_recognition import AudioFile
from speech_recognition import UnknownValueError

# import pydub
from pythoncom import CoInitializeEx
from pydub import AudioSegment

AudioSegment_directory: str = join(getcwd(), "modules", "ffmpeg", "bin")
converter_filename: str = join(AudioSegment_directory, "ffmpeg.exe")
ffmpeg_filename: str = join(AudioSegment_directory, "ffmpeg.exe")
ffprobe_filename: str = join(AudioSegment_directory, "ffprobe.exe")

AudioSegment.converter = converter_filename
AudioSegment.ffmpeg = ffmpeg_filename
AudioSegment.ffprobe = ffprobe_filename


# Вывод ошибок при отсутствии файлов pydub


if not isfile(converter_filename):
    warn(converter_filename)

if not isfile(ffmpeg_filename):
    warn(ffmpeg_filename)

if not isfile(ffprobe_filename):
    warn(ffprobe_filename)


# const

BOT = Union["Vkbot", "Telebot"]
BOT_KEY = Literal["vkbot", "telebot"]
JSONABLE = None | bool | int | float | str | list["JSONABLE"] | dict[str, "JSONABLE"]

MARKDOWN: Literal["MarkdownV2"] = "MarkdownV2"
DATE_FORMAT_1: str = "%d.%m.%Y %H:%M:%S"

# Период ожидания следующего события для объединения
EVENT_TIMEOUT: int = 1  # seconds

# Период между сообщениями для объединения
EVENT_PERIOD: float = 1  # seconds

# Период ожидания после неудачной попытки объединения для обработки необъединённых событий
EVENT_INTERVAL: int = 2  # seconds

PHOTO_EXTENSIONS: tuple[str, str, str] = (".jpeg", ".jpg", ".png")
VIDEO_EXTENSIONS: tuple[str] = (".mp4",)
AUDIO_EXTENSIONS: tuple[str, str, str, str] = (".wav", ".mp3", ".ogg", ".oga")
DOC_EXTENSIONS: tuple[str, str, str] = (".bin", ".txt", ".docx")

# Вспомогательные прикладные функции

def strftime(date: datetime) -> str:
    # На выходе значение не будет работать в strptime: используйте .stftime(DATE_FORMAT_BASED)
    # Значение предназначено для отправки в js
    return date.strftime(DATE_FORMAT_1)

def get_from(dictionary: DotDict | dict, *keys, default: Any | None = None, types: Iterable[type] = None, check: Callable | None = None) -> Any | None:
    """
    Возвращает значение из словаря, если оно существует по пути порядковых ключей:
    
    ```
    dictionary: dict = {}
    get_from(dictionary, "key1", "key2")  # Вернёт dictionary["key1"]["key2"]
    
    dotdict: DotDict = DotDict()
    get_from(dotdict, "key1", "key2")  # Вернёт dotdict.key1.key2
    ```
    
    Если любого из key1 или key2 в словаре не будет, то вернётся `default`.
    
    Если значение найдено и передан тип (`type is not None`), то 
    - Вернётся найденное значение, если его тип соответствует указанному `isinstance(value, type)`.
    - Иначе вернётся `default`.
    
    Если значение найдено и передана функция проверки `Callable(check)`, то она будет вызвана с одним аргументом `value`.
    - Если функция возвращает `True`, то вернётся найденное значение.
    - Иначе вернётся `default`.
    
    :param dictionary: Словарь или объект DotDict, из которого извлекается значение по вложенным ключам.
    :param keys: Последовательность ключей или атрибутов для доступа к вложенным значениям.
    :param default: Значение, возвращаемое если по указанному пути ключей значение не найдено или не прошло проверки типа или функции.
    :param types: Если передано, то найденное значение должно соответствовать хотя бы одному типу (проверяется через `isinstance`). Если не соответствует, возвращается `default`.
    :param check: Функция проверки, принимающая найденное значение и возвращающая `True`, если значение корректно, иначе `False`. Если проверка не пройдена, возвращается `default`. Если не передано, то вернётся найденное значение без проверки.

    :rtype: Any | None
    :return: Найденное и проверенное значение по указанному пути ключей или `default`, если значение отсутствует или не прошло проверки.
    """
    sentinel: Never = object()

    for key in keys:
        if hasattr(dictionary, "get"):
            dictionary = dictionary.get(key, sentinel)
        
            if dictionary is not sentinel:
                continue
        
        if hasattr(dictionary, key):
            dictionary = getattr(dictionary, key)
            continue
            
        return default
        
    if types and not any(isinstance(dictionary, t) for t in types):
        return default
    
    if check is not None and not check(dictionary):
        return default
        
    return dictionary


def get_int(dictionary: DotDict | dict, default: int, *keys, check: Callable | None = None) -> int:
    """
    Аналог функции get_from, но возвращает только int.
    - Вернёт default даже если default это не int.
    """
    # if not isinstance(default, int):
    #     raise TypeError("default must be int")
    
    result: int = get_from(dictionary, *keys, default = default, types = (int,), check = check)
    
    if isinstance(result, int):
        return result
    else:
        return default
        raise TypeError("result must be int")
    
    
def get_date(dictionary: DotDict | dict, *keys, default: datetime = datetime.fromtimestamp(0), warning: bool = True) -> datetime:
    timestamp: int = get_int(dictionary, -1, *keys)
    
    if timestamp < 0:
        if warning:
            value: Any | None = get_from(dictionary, *keys)
            warn(f"Некорректное значение поля {repr(value)}")
        
        return default
        
    return datetime.fromtimestamp(timestamp)

def get_timestamp(date: datetime) -> int:
    if date is not None:
        try:
            return int(date.timestamp())
        except OSError:
            # Если дата до 1970-01-01 UTC, вычисляем разницу вручную
            epoch = datetime(1970, 1, 1)
            delta = date - epoch
            return int(delta.total_seconds())

    raise ValueError(f"Некорректный аргумент {date=}")

def is_iterable(obj) -> bool:
    """
    :rtype: "__iter__" in dir(obj)
    :return: Является ли объект итерируемым

    - Пустой итерируемый объект так же вернёт True
    
    ### Примеры вызова:
    ```
    is_iterable("") # True
    is_iterable("1") # True
    is_iterable([]) # True
    is_iterable([1]) # True
    is_iterable(tuple()) # True
    is_iterable(tuple([1])) # True
    is_iterable({}) # True
    is_iterable({1:2}) # True
    is_iterable(set()) # True
    is_iterable(set([1])) # True
    is_iterable(range(1,2)) # True
    is_iterable(1) # False
    is_iterable(None) # False
    is_iterable(True) # False
    is_iterable(False) # False
    is_iterable(join) # False
    is_iterable(platform) # False
    ```
    
    ### Пример использования:
    ```
    message, address = self.udp_socket.recvfrom(BYTES)
    if is_iterable(address):
        from_addr, from_port = address
    ```
    
    ### Аргументы:
    :param obj: Объект, который необходимо проверить на итерируемость
    
    ### Вызываемые исключения:
    - Функция перехватывает TypeError при попытке итерирования объекта
    """
    try:
        for elem in obj:
            return True
    except TypeError:
        return False
    else:
        return True


def is_int(obj) -> bool:
    """
    :rtype: "__iter__" in dir(obj)
    :return: Может ли объект быть приведён к целочисленному типу (int)
    
    - Это НЕ аналог type(obj) is int, работает по-другому!
    - Функция не проверяет int overflow!
    
    ### Примеры вызова:
    ```
    is_int(True) # True
    is_int(False) # True
    is_int(1) # True
    is_int(2.3) # True
    is_int("4") # True
    is_int("5.5") # False
    is_int(None) # False
    is_int(type) # False
    ```

    ### Пример использования:
    ```
    if is_int(obj):
        number: int = int(obj)
    ```
    
    ### Аргументы:
    :param obj: Объект, который необходимо проверить на приводимость к целочисленному типу

    ### Вызываемые исключения:
    - Функция перехватывает любые исключения при попытке int(obj)
    """
    try:
        int(obj)
    except (TypeError, ValueError, OverflowError):
        return False
    else:
        return True

def cut(obj: Iterable | str, max_length: int = float("inf"), dots: bool = False) -> Iterable:
    """
    :rtype: obj[:max_length]
    :return: Обрезанную копию индексируемого объекта, длина которого не превышает указанное значение max_length
    - Если не указывать max_length, возвращает изначальный объект без изменений
    - Если isinstance(obj,str) и dots=True, то в конец строки будет добавлено многоточие, при этом длина строки с точками не будет превышать max_length

    ### Примеры вызова:
    ```
    cut("1234567890",5) # "12345"
    cut("12",5) # "12"
    cut("1234567890") # "1234567890"
    cut("1234567890",5,dots=True) # "12..." # Точки влезли
    cut("1234567890",3,dots=True) # "123" # Точки не влезли
    cut((1,2,3,4,5),2) # (1,2)
    cut([1,2,3,4,5],2) # [1,2]
    cut([1,2,3,4,5],2,dots=True) # [1,2] # Ошибка вызвана не будет, точек не будет
    cut(1) # raise TypeError()
    ```

    ### Пример использования:
    ```
    if len(text) > MAX_BUTTON_LENGTH:
        text = cut(text, MAX_BUTTON_LENGTH, dots=True)
    ```

    ### Аргументы:
    :param obj: Индексируемый объект, который необходимо обрезать
    :param max_length: Целое число - максимальная длина индексируемой копии
    :param dots: Добавлять ли точки в конец строки при обрезании
    
    ### Вызываемые исключения:
    :raises TypeError: if obj is not iterable
    """
    if len(obj) > max_length:
        if isinstance(obj, str):
            max_length: int = int(max_length) - len("..." if dots and max_length > 3 else "")
            return obj[:max_length].rstrip() + ("..." if dots else "")
        else:
            return obj[:max_length]
    else:
        return obj

def diff_sec(date1: datetime, date2: datetime) -> float:
    """
    Разница между датами в секундах
    Если date1 < date2, то положительная
    Иначе отрицательная
    """
    return (date2 - date1).total_seconds()

def only_extension(file_path: str) -> str | Literal[""]:
    r"""
    Извлекает расширение с точкой для указанного адреса файла
    
    ### Примеры вызова:
    ```
    only_filename_with_extension("") # ""
    only_filename_with_extension(r"C:\Users\user\Documents\1.txt") # "1.txt"
    only_filename_with_extension(r"C:\Users\user\Documents\1.TXT") # "1.TXT"
    only_filename_with_extension(r"C:\Users\user\Documents\1.tXt") # "1.tXt"
    only_filename_with_extension(r"C:\Users\user\Documents\1aB.tXt") # "1aB.tXt"
    only_filename_with_extension(r"C:\Users\user\Documents") # "Documents"
    only_filename_with_extension(r"C:\Users\user\Documents\1.") # "1."
    only_filename_with_extension(r"C:\Users\user\Documents\1.1.1.1") # "1.1.1.1"
    only_filename_with_extension("C:/Users/user/Documents/FiLeNaMe.TxT") # "FiLeNaMe.TxT"
    ```
    
    ### Пример использования:
    ```
    if isfile(filename):
        directory:str = only_directory(filename)
        fname:str = only_filename(filename)
        ext:str = only_extension(filename)
        new_filename = join(directory,f"{filename} (1){ext}")
    ```
    
    ### Аргументы:
    :param file_path: Адрес файла с любыми слэшами
    
    ### Вызываемые исключения:
    - TypeError if type(file_path) is not str
    """
    if file_path == "":
        return ""
    else:
        filename: str = basename(normpath(file_path))

    start: int = filename.rfind("\\")
    end: int = filename[start if start >= 0 else 0:].find('.')

    if (end < 0):
        return ""
    elif (start < 0):
        return filename[end:]
    elif (start < end):
        return filename[end:]
    else:
        raise NotImplementedError()

def only_directory(file_path: str) -> str:
    r"""
    Извлекает адрес директории из переданного адреса файла.
    - `r"C:\Users\user\Documents"` вернёт `r"C:\Users\user"` хотя `Documents` - это папка.
    
    ### Примеры вызова:
    ```
    only_directory("")  # ""
    only_directory("filename.txt")  # ""
    only_directory(r"C:\Users\user\Documents\1.txt")  # "C:\Users\user\Documents"
    only_directory(r"C:\Users\user\Documents")  # "C:\Users\user"
    only_directory(r"C:\Users\user\Documents\1.")  # "C:\Users\user\Documents"
    only_directory(r"C:\Users\user\Documents\1.1.1.1")  # "C:\Users\user\Documents"
    only_directory("C:/Users/user/Documents/FiLeNaMe.TxT")  # "C:\Users\user\Documents"
    ```
    
    ### Пример использования:
    ```
    from os.path import isfile
    from os.path import join

    # Произвольное значение
    filename: str = "path/imsurefileexists.txt"

    # Импортируем библиотеку для получения текущей директории
    from os import getcwd

    # Если файл существует
    if isfile(filename):
        # Получаем директорию из переданного адреса файла
        directory: str = only_directory(filename) or getcwd()  # "path"

        # Создаём новый файл на основе имени существующего
        new_filename = join(directory, f"imsurefileexists (1).txt")
    ```
    
    ### Аргументы:
    :param file_path: Адрес файла с любыми разделителями.
    
    ### Вызываемые исключения:
    :raises TypeError: Если тип данных переданного адреса файла не является строковым.

    :rtype: str
    :return: Адрес директории из переданного адреса файла.
    - Если в адресе файла не указана директория, то будет возвращена пустая строка.
    - Результат будет содержать унифицированные разделители.
    """
    return dirname(normpath(file_path))

def only_filename(file_path: str) -> str:
    r"""
    Извлекает имя файла без расширения для переданного адреса файла.
    
    ### Примеры вызова:
    ```
    only_filename("")  # ""
    only_filename("filename")  # "filename"
    only_filename(r"1.txt")  # "1"
    only_filename(r"C:\Users\user\Documents\1.txt")  # "1"
    only_filename(r"C:\Users\user\Documents")  # "Documents"
    only_filename(r"C:\Users")  # "Users"
    only_filename(r"C:")  # ""
    only_filename(r"C:\U.sers\user\Documents\.gitignore")  # ".gitignore"
    only_filename(r"C:\Users\user\Documents\1.")  # "1"
    only_filename(r"C:\U.sers\user\Documents\1.")  # "1"
    only_filename(r"C:\Users\user\Documents\1.1.1.1")  # "1"
    only_filename("C:/Users/user/Documents/FiLeNaMe.TxT")  # "FiLeNaMe"
    only_filename("C:/Users/user/Documents/Кириллица.АбВ")  # "Кириллица"
    only_filename(None)  # raise TypeError
    only_filename(0)  # raise TypeError
    only_filename([])  # raise TypeError
    only_filename({})  # raise TypeError
    ```
    
    ### Пример использования:
    ```
    from os.path import isfile
    from os.path import join

    # Произвольное значение
    filename: str = "path/imsurefileexists.txt"

    # Если файл существует
    if isfile(filename):
        # Получаем имя файла без расширения
        fname: str = only_filename(filename)  # "myfile"

        # Создаём новый файл на основе имени существующего
        new_filename = join("path", f"{fname} (1).txt")
    ```
    
    ### Аргументы:
    :param file_path: Адрес файла с любыми разделителями.
    
    ### Вызываемые исключения:
    :raises TypeError: Если тип данных переданного адреса файла не является строковым.

    ### Требуемые модули:
    ```
    from os.path import basename, normpath
    ```

    :rtype: str
    :return: Имя файла без расширения и директории.
    - Если в пути только директории, то будет возвращена последняя.
    """
    if file_path == "":
        return ""
    
    filename: str = basename(normpath(file_path))
    start: int = filename.rfind("\\")
    end: int = filename[(start if start >= 0 else 0):].find('.')

    if (start < 0) and (end < 0):
        return filename
    elif (end < 1):
        return filename[start + 1:]
    elif (start < 0):
        return filename[:end]
    elif (start < end):
        return filename[start + 1:end]

def change_extension(file_path: str, new_extension: str) -> str:
    r"""
    Заменяет расширение файла на новое.

    ### Аргументы:
    :param file_path: исходный путь к файлу
    :param new_extension: новое расширение с точкой, например ".JPEG"

    ### Возвращает:
    Новый путь с заменённым расширением.

    ### Пример использования:
    ```
    change_extension("C:/folder/file.JPG", ".JPEG") # "C:/folder/file.JPEG"
    ```

    Вызываемые исключения:
    - TypeError if type(file_path) is not str
    - ValueError if new_extension не начинается с точки
    """
    if not isinstance(file_path, str):
        raise TypeError("file_path должен быть строкой")
    if not isinstance(new_extension, str) or not new_extension.startswith("."):
        raise ValueError("new_extension должен быть строкой, начинающейся с точки")

    base, _ = splitext(file_path)
    return f"{base}{new_extension}"

def create_filename(folder: str, filename: str):
    fname: str = only_filename(filename)
    ext: str = only_extension(filename)

    result: str = f"{fname}{ext}"
    i: int = 1

    while exists(join(folder, result)):
        i += 1
        result = f"{fname} ({i}){ext}"
    
    return join(folder, result)

def preceding(string: str):
    """
    Возвращает строку с экранированными символами для отправки в telebot MARKDOWN.
    """
    symbols: tuple[tuple[str, str]] = (
        # ("_", "\_"),
        # ("*", "\*"),
        ("[", "\["),
        ("]", "\]"),
        ("(", "\("),
        (")", "\)"),
        ("~", "\~"),
        ("`", "\`"),
        (">", "\>"),
        ("#", "\#"),
        ("+", "\+"),
        ("-", "\-"),
        ("=", "\="),
        ("|", "\|"),
        ("{", "\{"),
        ("}", "\}"),
        (".", "\."),
        ("!", "\!")
    )
        
    for before, after in symbols:
        string = string.replace(before, after)
        
    return string


class Bot():
    BOT_KEY: str = ""
    URL: str = "http://google.com/"
    
    """
    Максимальная дистанция на которой разделение слишком длинного сообщения на части будет искать пробелы или сносы строк.
    Если среди последних 100 символов таковых нет, то срез будет ровно по max_length.
    """
    MAX_SPLIT: int = 100
    class Attachment():
        ATTACHMENT_TYPE = dict[str, str | int]
        
        def __init__(self, attachment_id: int | str):
            self.id: int | str = ""
            self.filename: str = ""
            self.set_id(attachment_id)
            
            self.data: BytesIO | None = None

        def dumps(self) -> ATTACHMENT_TYPE:
            return {
                "id": self.get_id(),
                "filename": self.get_filename(),
                "classname": self.__class__.__name__
            }
            
        def compare(self, attachment: Bot.Attachment):
            return attachment.get_id() == self.get_id()
                
        def save_as(self, filename: str):
            if not self.check():
                raise ValueError(f"Некорректное значение атрибута {self.data=}. Перед сохранением необходимо загрузить файл методом download.")
            
            # print(f"save_as {filename=}")
            with open(filename, "wb") as file:
                self.data.seek(0)
                file.write(self.data.read())
            # print(f"saved {filename=}", isfile(filename))

        @abstractmethod
        def set_id(self, attachment_id: int | str) -> Never:
            raise NotImplementedError("Вместо используйте Vkbot.Attachment или Telebot.Attachment")

        def get_id(self) -> int | str:
            return self.id

        @abstractmethod
        def get_type(self) -> Never:
            raise NotImplementedError("Вместо используйте Vkbot.Attachment или Telebot.Attachment")
        

        def check_filename(self, filename: str) -> bool:
            return isinstance(filename, str) and (self.id or isfile(filename))

        def set_filename(self, filename: str):
            if self.check_filename(filename):
                self.filename = abspath(filename)
            elif isinstance(filename, str):
                raise FileNotFoundError(f"Некорректное значение аргумента {filename=}. Файл обязан сущестовать")
            else:
                raise ValueError(f"Некорректное значение аргумента {filename=}")

        def get_filename(self) -> str:
            if self.check_filename(self.filename):
                return self.filename
            elif isinstance(self.filename, str):
                raise FileNotFoundError(f"Некорректное значение атрибута {self.filename=}. Файл обязан сущестовать")
            else:
                raise ValueError(f"Некорректное значение атрибута {self.filename=}")
    

    class Event():
        EVENT_TYPE = str | int | None | dict | list[dict]
        
        @classmethod
        def loads(cls, data: EVENT_TYPE, parent: type[BOT]):
            owner_id: int = get_int(data, -1, "owner_id")
            chat_id: int = get_int(data, -1, "chat_id")
            isoformat: str = data.get("date", "")
            text: str = data.get("text", "")
            reply_data: Bot.Event.EVENT_TYPE | None = data.get("reply", {})
            forward_data: list[Bot.Event.EVENT_TYPE] = data.get("forward", "")
            
            date: datetime = datetime.fromisoformat(isoformat)
            reply: Bot.Event | None = None if reply_data is None else cls.loads(reply_data)
            
            forward_messages: list[Bot.Event] = []
            for event_data in forward_data:
                event: Bot.Event = cls.loads(event_data)
                forward_messages.append(event)
            
            attachments: list[Bot.Attachment] = []
            attachments_list: list[dict[str, str | int]] = get_from(data, "attachments")
            attachments_keys: dict[str, type[Bot.Attachment]] = {
                "Attachment": parent.Attachment,
                "PhotoAttachment": parent.PhotoAttachment,
                "VideoAttachment": parent.VideoAttachment,
                "AudioAttachment": parent.AudioAttachment,
                "DocAttachment": parent.DocAttachment,
            }
            
            for attachment_data in attachments_list:
                attachment_classname: str = attachment_data["classname"]
                attachment_class: type[Bot.Attachment] = attachments_keys[attachment_classname]
                attachment: Bot.Attachment = attachment_class.loads(attachment_data)
                attachments.append(attachment)
            
            result = cls(owner_id, chat_id, text, date, attachments, reply, forward_messages)
            first_name = data.get("first_name", "")
            last_name = data.get("last_name", "")
            result.set_name(first_name, last_name)
            return result
            
        
        def __init__(self, owner_id: int, chat_id: int, text: str, date: datetime, attachments: Iterable[Bot.Attachment] = [], reply: Bot.Message | None = None, forward: Iterable[Bot.Message] = []):
            """
            :param event: Объект события, полученный из listener.
            :param owner_id: Идентификатор отправителя события.
            :param chat_id: Идентификатор чата, в котором произошло событие.
            :param text: Текст сообытия (сообщения).
            :param date: Дата и время события.
            :param attachments: Список вложений (информации о вложениях).
            :param reply: Сообщение (событие), в ответ на которое получено текущее событие.
            :param forward: Включенные в событие пересылаемые сообщения (события сообщений).
            """
            self.events: list[VkBotMessageEvent | VkBotEvent | DotDict | dict | TelebotMessage | CallbackQuery | int] = []
            self.chat_id: int
            self.date: datetime
            self.text: str
            self.DEBUG_CALLBACK: bool = False
            
            self.reply: Bot.Event | None = None
            self.forward_messages: list[Bot.Event] = []
            self.attachments: list[Bot.Attachment] = []

            self.first_name: str = ""
            self.last_name: str = ""
            
            self.set_owner_id(owner_id)
            self.set_chat_id(chat_id)
            self.set_date(date)
            self.set_text(text)
            self.set_reply(reply)
            self.set_forward(forward)
            self.set_attachments(attachments)
                    
        def dumps(self) -> EVENT_TYPE:
            reply: Bot.Event | None = self.get_reply()
            return {
                "chat_id": self.get_chat_id(),
                "date": self.get_date().isoformat(),
                "text": self.get_text(),
                "reply": reply.dumps() if reply is not None else None,
                "forward": [event.dumps() for event in self.get_forward()],
                "attachments": [attachment.dumps() for attachment in self.get_attachments()],
                "first_name": str(self.first_name),
                "last_name": str(self.last_name)
            }
            
        def prev_for(self, event: Bot.Event) -> bool:
            """
            Возвращает является ли текущее событие (self) предыдущим для указанного (event:Event)
            Если событие является предыдущим для указанного, то они могут быть объединены в одно событие
            Событие является предыдущим для указанного, если между их датами разница не более EVENT_PERIOD (const) и дата текущего события была раньше, чем дата указанного события

            :param event: Событие для которого выполняется проверка
            """
            return abs(diff_sec(event.date, self.date)) < EVENT_PERIOD and self.date <= event.date and self is not event
            
        def get_username(self) -> str | Literal[""]:
            """@username"""
            for event in self.events:
                if Vkbot.check_event(event):
                    return f"@id{self.get_chat_id()}"
                elif Telebot.check_event(event):
                    return f"@{event.from_user.username}"
            return ""
        
        def get_name(self) -> str | Literal[""]:
            return "here!"
        
        
        def check_event(self, event: VkBotMessageEvent | VkBotEvent | DotDict | dict | TelebotMessage | CallbackQuery) -> bool:
            if Vkbot.check_event(event):
                return True
            elif Telebot.check_event(event):
                return True
            else:
                return False

        def set_events(self, events: list[VkBotMessageEvent | VkBotEvent | DotDict | dict | TelebotMessage | CallbackQuery]):
            if all(self.check_event(event) for event in events):
                self.events = list(events)
            else:
                raise ValueError(f"Некорректное значение аргумента {events=}")

        def get_events(self) -> list[VkBotMessageEvent | VkBotEvent | DotDict | dict | TelebotMessage | CallbackQuery]:
            if all(self.check_event(event) for event in self.events):
                return list(self.events)
            else:
                raise ValueError(f"Некорректное значение атрибута {self.events=}")
        
        
        def check_owner_id(self, owner_id: int) -> bool:
            return isinstance(owner_id, int)

        def set_owner_id(self, owner_id: int):
            if self.check_owner_id(owner_id):
                self.owner_id = owner_id
            else:
                raise ValueError(f"Некорректное значение аргумента {owner_id=}")

        def get_owner_id(self) -> int:
            if self.check_owner_id(self.owner_id):
                return self.owner_id
            else:
                raise ValueError(f"Некорректное значение атрибута {self.owner_id=}")


        def check_chat_id(self, chat_id: int) -> bool:
            return isinstance(chat_id, int) and chat_id >= 0

        def set_chat_id(self, chat_id: int):
            if self.check_chat_id(chat_id):
                self.chat_id = chat_id
            else:
                raise ValueError(f"Некорректное значение аргумента {chat_id=}")

        def get_chat_id(self) -> int | None:
            if self.check_chat_id(self.chat_id):
                return self.chat_id
            else:
                raise ValueError(f"Некорректное значение атрибута {self.chat_id=}")


        def check_date(self, date: datetime) -> bool:
            return isinstance(date, datetime)  # and date.tzinfo is not None

        def set_date(self, date: datetime):
            if self.check_date(date):
                self.date = date
            else:
                raise ValueError(f"Некорректное значение аргумента {date=}")

        def get_date(self) -> datetime:
            if self.check_date(self.date):
                return self.date
            else:
                raise ValueError(f"Некорректное значение атрибута {self.date=}")
        
        
        def check_text(self, text: str) -> bool:
            return isinstance(text, str)

        def set_text(self, text: str):
            if self.check_text(text):
                self.text = text
            else:
                raise ValueError(f"Некорректное значение аргумента {text=}")

        def get_text(self) -> str:
            if self.check_text(self.text):
                return self.text
            else:
                raise ValueError(f"Некорректное значение атрибута {self.text=}")
            
            
        def check_reply(self, reply: Bot.Event) -> bool:
            return isinstance(reply, Bot.Event) and reply.check()

        def set_reply(self, reply: Bot.Event | None):
            if reply is None:
                self.reply = None
            elif self.check_reply(reply):
                self.reply = reply
            else:
                raise ValueError(f"Некорректное значение аргумента {reply=}")

        def get_reply(self) -> Bot.Event | None:
            if self.reply is None:
                return None
            elif self.check_reply(self.reply):
                return self.reply
            else:
                raise ValueError(f"Некорректное значение атрибута {self.reply=}")


        def check_forward(self, forward: Iterable[Bot.Event]) -> bool:
            return is_iterable(forward) and all(isinstance(message, Bot.Event) for message in forward)

        def set_forward(self, forward: Iterable[Bot.Event]):
            if self.check_forward(forward):
                if forward and self.reply:
                    raise ValueError(f"Некорректное значение атрибута {self.reply=}. Невозможно пересылать сообщения в ответ на сообщение")
                else:
                    self.forward_messages = list(forward)
            else:
                raise ValueError(f"Некорректное значение аргумента {forward=}")

        def get_forward(self) -> list[Bot.Event]:
            if self.check_forward(self.forward_messages):
                if self.forward_messages and self.reply:
                    raise ValueError(f"Некорректное значение атрибута {self.reply=}. Невозможно пересылать сообщения в ответ на сообщение")
                else:
                    return self.forward_messages
            else:
                raise ValueError(f"Некорректное значение атрибута {self.forward_messages=}")


        def check_attachments(self, attachments: Iterable[Bot.Attachment]) -> bool:
            return is_iterable(attachments) and all(isinstance(attachment, Bot.Attachment) for attachment in attachments)

        def set_attachments(self, attachments: Iterable[Bot.Attachment]):
            if self.check_attachments(attachments):
                self.attachments = list(attachments)
            else:
                raise ValueError(f"Некорректное значение аргумента {attachments=}")

        def get_attachments(self) -> list[Bot.Attachment]:
            if self.check_attachments(self.attachments):
                return self.attachments
            else:
                raise ValueError(f"Некорректное значение атрибута {self.attachments=}")


        def set_name(self, first_name: str, last_name: str):
            if isinstance(first_name, str) and isinstance(last_name, str):
                self.first_name = first_name
                self.last_name = last_name
            else:
                raise ValueError(f"Некорректное значение аргумента {first_name=} или {last_name=}")

        def get_name(self) -> tuple[str, str]:
            if isinstance(self.first_name, str) and isinstance(self.last_name, str):
                return (self.first_name, self.last_name)
            else:
                raise ValueError(f"Некорректное значение атрибута {self.first_name=} или {self.last_name=}")


    class Keyboard():
        KEYBOARD_TYPE = dict[str, int | bool | list["Bot.Keyboard.Button.BUTTON_TYPE"]]
        MAX_BUTTON_LENGTH: int = 40
        
        class Button():
            BUTTON_TYPE = dict[str, str]
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
            
            def loads(data: BUTTON_TYPE) -> Bot.Keyboard.Button:
                text: str = get_from(data, "text")
                color: int = get_int(data, Bot.Keyboard.Button.DEFAULT_COLOR, "color")
                callback_data: str | None = get_from(data, "callback_data")
                url: str | None = get_from(data, "url")
                return Bot.Keyboard.Button(text, color = color, callback_data = callback_data, url = url)
            
            def __init__(self, text: str, color: Literal[0, 1, 2, 3] | str | VkKeyboardColor = DEFAULT_COLOR, callback_data: str | None = "", url: str | None = None):
                """
                :param text: Обязательно не пустой текст.
                :param url: По нажатию на кнопку будет открываться указанная ссылка, не совместимо с callback_data.
                :param callback_data: Если указано, то кнопка вместо text по нажатию вернёт указанное значение, не совместимо с url.
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
                return {
                    "text": self.get_text(),
                    "color": tuple(self.__class__.COLORS.values()).index(self.get_color()),
                    "type": self.type if self.type in ("text", "callback_data", "url") else self.__class__.DEFAULT_BUTTON_TYPE,
                    "callback_data": self.get_callback_data() if self.type == "callback_data" else None,
                    "url": self.get_url() if self.type == "url" else None
                }
                    
                    
            def check_text(self, text: str) -> bool:
                return isinstance(text, str) and str(text).strip()
            
            def set_text(self, text: str):
                if self.check_text(text):
                    self.text = text
                else:
                    raise ValueError(f"Некорректное значение аргумента {text=}")

            def get_text(self) -> str:
                if self.check_text(self.text):
                    return str(self.text).strip()
                else:
                    raise ValueError(f"Некорректное значение атрибута {self.text=}")
            

            def check_color(self, color: Literal[0, 1, 2, 3] | str | VkKeyboardColor) -> bool:
                if isinstance(color, str):
                    color = str(color).upper()
                    
                for keys in self.COLORS:
                    if color in keys:
                        return True
                    
                return False

            def set_color(self, color: Literal[0, 1, 2, 3] | str | VkKeyboardColor):
                if isinstance(color, str):
                    color = str(color).upper()
                    
                for keys, value in self.COLORS.items():
                    if color in keys:
                        self.color = value
                        return
                    
                raise ValueError(f"Некорректное значение аргумента {color=}")

            def get_color(self) -> VkKeyboardColor:
                if self.check_color(self.color):
                    return self.color
                else:
                    raise ValueError(f"Некорректное значение аргумента {getattr(self, 'color', None)=}")
                    
                    
            def check_callback_data(self, callback_data: str) -> bool:
                return isinstance(callback_data, str) and callback_data 
            
            def set_callback_data(self, callback_data: str | None):
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
                :raises ValueError: Если callback_data не установлен (предварительно проверьте, что button.type == "callback_data").
                """
                if self.type != "callback_data":
                    raise ValueError(f"Кнопка имеет callback_data только если её тип 'callback_data', не {self.type}")
                elif self.check_callback_data(self.callback_data):
                    return str(self.callback_data)
                else:
                    raise ValueError(f"Некорректное значение атрибута {self.callback_data=}")
                    
                    
            def check_url(self, url: str) -> bool:
                return isinstance(url, str) and url
            
            def set_url(self, url: str | None):
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
                if self.type != "url":
                    raise ValueError(f"Кнопка имеет ссылку только если её тип 'url', не {self.type}")
                elif self.check_url(self.url):
                    return str(self.url).strip()
                else:
                    raise ValueError(f"Некорректное значение атрибута {self.url=}")
                
                
            def check_type(self) -> bool:
                if self.check_callback_data(self.callback_data) and self.type == "callback_data":
                    return True
                elif self.check_url(self.url) and self.type == "url":
                    return True
                elif self.check_text(self.text) and self.type == self.__class__.DEFAULT_BUTTON_TYPE:
                    return True
                else:
                    return False

            def get_type(self) -> Literal["text", "callback_data", "url"]:
                if self.check_type():
                    return self.type
                else:
                    raise ValueError(f"Некорректное значение атрибута {self.type=}")
            
        def __init__(self, buttons: Iterable[str | Button], max_width: int, inline: bool):
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
            return {
                "buttons": [button.dumps() for button in self.buttons],
                "max_width": int(self.max_width),
                "inline": bool(self.inline)
            }
        
        def check_editable(self) -> bool:
            return self.inline
            
        def get_unused_buttons(self) -> list[Never]:
            """
            Функция всегда возвращает пустой список.
            """
            return []

        def check_inline(self) -> bool:
            """
            Метод проверяет является ли клавиатура линейной
            * Кнопки линейной клавиатуры прикреплены к сообщению;
            * Кнопки нелинейной расположены под вводом чата.
            """
            return bool(self.inline)


    class BaseMessage():
        """
        Родительский класс для Message и VoiceMessage с общими полями и методами.
        """
        MESSAGE_TYPE = dict[str, Union[str, int, "MESSAGE_TYPE", None, dict[Literal["MESSAGE_NEW", "SENT", "EDIT", "DELETE"], list["Bot.Event.EVENT_TYPE"]]]]
        CREATE_KEY: str = "MESSAGE_NEW"
        SENT_KEY: str = "SENT"
        EDIT_KEY: str = "EDIT"
        DELETE_KEY: str = "DELETE"
        KEYS: tuple[Literal["MESSAGE_NEW", "SENT", "EDIT", "DELETE"]] = (CREATE_KEY, SENT_KEY, EDIT_KEY, DELETE_KEY)
        
        def __init__(self, owner_id: int, text: str, reply: Bot.Message | None = None):
            """
            :param owner_id: Идентификатор отправителя сообщения (пользователя или администратора, а если отправил сообщение бот, то используйте bot.group_id).
            :param text: Текст сообщения.
            :param reply: Создаваемое сообщение будет отправлено в ответ с ссылкой на указанное сообщение.
            """
            # Текст сообщения
            self.text: str

            # ID пользователя или сообщества, которое отправило/отправит сообщение
            self.owner_id: int
            
            # В ответ на сообщение
            self.reply: Bot.BaseMessage | None = None

            # Идентификатор чата (пользователя), куда будет отправлено сообщение
            self.chat_id: int | None = None  # Устанавливается после отправки методом send

            # Идентификатор сообщения
            self.id: int | None = None  # Устанавливается после отправки методом send
            
            # Если сообщение создаётся из события, то событие хранится в этом поле
            self.events: dict[Literal["MESSAGE_NEW", "SENT", "EDIT", "DELETE"], list[Bot.Event]] = {
                # События, из которых было создано сообщение
                self.__class__.CREATE_KEY: [],
                # События отправки сообщения
                self.__class__.SENT_KEY: [],
                # Остальные события
                self.__class__.EDIT_KEY: [],
                self.__class__.DELETE_KEY: []
            }
            
            # Даты сообщения
            self.dates: dict[Literal["MESSAGE_NEW", "SENT", "EDIT", "DELETE"], list[datetime]] = {
                # Сообщение получено
                self.__class__.CREATE_KEY: [],
                # Сообщение отправлено
                self.__class__.SENT_KEY: [],
                # Сообщение отредактировано
                self.__class__.EDIT_KEY: [],
                # Сообщение удалено
                self.__class__.DELETE_KEY: []
            }
            
            self.set_owner_id(owner_id)
            self.set_text(text)
            self.set_reply(reply)

        def dumps(self) -> MESSAGE_TYPE:
            reply: Bot.BaseMessage | None = self.get_reply()
            
            return {
                "events": {
                    key: [
                        event.dumps() for event in events
                    ] for key, events in self.events.items()
                },
                "dates": {
                    key: [
                        date.isoformat() for date in dates
                    ] for key, dates in self.dates.items()
                },
                "text": self.get_text(),
                "owner_id": self.get_owner_id(),
                "reply": reply.dumps() if reply is not None else None,
                "chat_id": self.get_chat_id(),
                "id": self.get_id()
            }
        
        @abstractmethod
        def get_bot_key(self) -> BOT_KEY:
            raise NotImplementedError()
        
        def was_sent(self) -> bool:
            """
            Возвращает `True`, если сообщение уже было отправлено и ещё не было удалено из чата.
            """
            return (len(self.events[self.__class__.CREATE_KEY]) + len(self.events[self.__class__.SENT_KEY])) > len(self.events[self.__class__.DELETE_KEY])
        
        def check_editable(self) -> bool:
            """
            Возвращает `True`, если текущее сообщение можно редактировать или удалить.
            - Не проверяет было ли сообщение удалено ранее.
            """
            message = self
            # print(f"{message=}")
            # print(f"{len(self.events[self.__class__.SENT_KEY])} {self.events[self.__class__.SENT_KEY]=}")
            # print(f"{len(self.events[self.__class__.DELETE_KEY])} {self.events[self.__class__.DELETE_KEY]=}")
            return len(self.events[self.__class__.SENT_KEY]) > len(self.events[self.__class__.DELETE_KEY])
            
        @abstractmethod
        def send(self, chat_id: int) -> list[Bot.Message]:
            raise NotImplementedError("Вместо Bot.Message используйте Vkbot.Message или Telebot.Message")

        @abstractmethod
        def delete(self) -> Never:
            raise NotImplementedError("Вместо Bot.Message используйте Vkbot.Message или Telebot.Message")
        
        @abstractmethod
        def get_username(self) -> str | None:
            raise NotImplementedError("Вместо Bot.Message используйте Vkbot.Message или Telebot.Message")

        
        def check_event(self, event: Bot.Event) -> bool:
            return isinstance(event, Bot.Event)

        def add_event(self,  event: Bot.Event | Any, date: datetime, key: Literal["MESSAGE_NEW", "SENT", "EDIT", "DELETE"]):
            if not isinstance(event, Bot.Event):
                message_id: int | None = None
                
                if Bot.Message.check_id(None, event):
                    message_id = int(event)
                
                event = Bot.Event(self.get_owner_id(), self.get_chat_id(), key, date)
                
                if message_id is not None:
                    event.events.append(message_id)
            
            if self.check_event(event):
                if isinstance(date, datetime):
                    if key in self.__class__.KEYS:
                        self.events[key].append(event)
                        self.dates[key].append(date)
                    else:
                        raise ValueError(f"Некорректное значение аргумента {key=}")
                else:
                    raise ValueError(f"Некорректное значение аргумента {date=}")
            else:
                raise ValueError(f"Некорректное значение аргумента {event=}")
        
        
        def check_owner_id(self, owner_id: int) -> bool:
            return isinstance(owner_id, int) and owner_id >= 0

        def set_owner_id(self, owner_id: int):
            if self.check_owner_id(owner_id):
                self.owner_id = owner_id
            else:
                raise ValueError(f"Некорректное значение аргумента {owner_id=}")

        def get_owner_id(self) -> int:
            if self.check_owner_id(self.owner_id):
                return self.owner_id
            else:
                raise ValueError(f"Некорректное значение атрибута {self.owner_id=}")
                    
                    
        def check_text(self, text: str) -> bool:
            return isinstance(text, str) and str(text).strip()
        
        def set_text(self, text: str):
            if self.check_text(text):
                self.text = text
            else:
                raise ValueError(f"Некорректное значение аргумента {text=}")

        def get_text(self) -> str:
            if self.check_text(self.text):
                return str(self.text).strip()
            else:
                raise ValueError(f"Некорректное значение атрибута {self.text=}")
            
            
        def check_reply(self, reply: Bot.BaseMessage) -> bool:
            return isinstance(reply, Bot.BaseMessage) and reply.check()

        def set_reply(self, reply: Bot.BaseMessage | None):
            if reply is None:
                self.reply = None
            elif self.check_reply(reply):
                self.reply = reply
            else:
                raise ValueError(f"Некорректное значение аргумента {reply=}")

        def get_reply(self) -> Bot.BaseMessage | None:
            if self.reply is None:
                return None
            elif self.check_reply(self.reply):
                return self.reply
            else:
                raise ValueError(f"Некорректное значение атрибута {self.reply=}")


        def check_chat_id(self, chat_id: int) -> bool:
            return isinstance(chat_id, int) and chat_id >= 0

        def set_chat_id(self, chat_id: int):
            if self.check_chat_id(chat_id):
                self.chat_id = chat_id
            else:
                raise ValueError(f"Некорректное значение аргумента {chat_id=}")

        def get_chat_id(self) -> int | None:
            if self.chat_id is None:
                return None
            elif self.check_chat_id(self.chat_id):
                return self.chat_id
            else:
                raise ValueError(f"Некорректное значение атрибута {self.chat_id=}")
        
        
        def check_id(self, message_id: int) -> bool:
            return isinstance(message_id, int) and message_id >= 0

        def set_id(self, message_id: int):
            if self.check_id(message_id):
                self.id = message_id
            else:
                raise ValueError(f"Некорректное значение аргумента {message_id=}")

        def get_id(self) -> int | None:
            if self.id is None:
                return None
            elif self.check_id(self.id):
                return self.id
            else:
                raise ValueError(f"Некорректное значение атрибута {self.id=}")
        
        
        def get_date(self, key: Literal["MESSAGE_NEW", "SENT", "EDIT", "DELETE"] = "MESSAGE_NEW") -> datetime | None:
            if key in self.dates:
                if self.dates[key]:
                    return self.dates[key][-1]
                else:
                    return None
            else:
                raise ValueError(f"Некорректное значение аргумента {key=}")


    class Message(BaseMessage):
        """
        Хранит в себе информацию о содержимом одного сообщения (одного блока).
        Ограничения на вместимость одного сообщения хранятся в полях класса.
        """
        MESSAGE_TYPE = dict[str, Union[str, int, "MESSAGE_TYPE", None, dict[Literal["MESSAGE_NEW", "SENT", "EDIT", "DELETE"], list["Bot.Event.EVENT_TYPE"]], list["Bot.Attachment.ATTACHMENT_TYPE"], "Bot.Keyboard.KEYBOARD_TYPE", list["Bot.Message.MESSAGE_TYPE"]]]

        # Текст пустого сообщения
        EMPTY_TEXT: str = " "

        # Максимальная длина сообщения в символах
        MAX_LENGTH: int = 4096

        # Максимальное количество вложений в одном сообщении
        MAX_ATTACHMENTS: int = 10

        # Максимальное количество вложений в одной медиагруппе
        MAX_ATTACHMENTS_IN_GROUP: int = 10
        
        @classmethod
        def loads(cls, data: MESSAGE_TYPE, parent: type[BOT], bot: VkApi | TeleBot) -> Bot.Message:
            owner_id: int = get_int(data, -1, "owner_id")
            text: str = get_from(data, "text")
            
            keyboard_data: dict[str, int | bool| list[dict[str, str]]] | None = get_from(data, "keyboard")
            keyboard: Bot.Keyboard | None = None if keyboard_data is None else parent.Keyboard.loads(keyboard_data)
            
            reply_data: dict[str, str | int | dict | None] | None = get_from(data, "reply")
            reply: Bot.Message | None = None if reply_data is None else parent.Message.loads(reply_data, bot)

            forward: list[dict[str, str | int | dict | None]] = get_from(data, "forward")
            forward_messages: list[Bot.Message] = [parent.Message.loads(message, bot) for message in forward]
            
            attachments: list[Bot.Attachment] = []
            attachments_list: list[dict[str, str | int]] = get_from(data, "attachments")
            attachments_keys: dict[str, type[Bot.Attachment]] = {
                "Attachment": parent.Attachment,
                "PhotoAttachment": parent.PhotoAttachment,
                "VideoAttachment": parent.VideoAttachment,
                "AudioAttachment": parent.AudioAttachment,
                "DocAttachment": parent.DocAttachment,
            }
            
            for attachment_data in attachments_list:
                attachment_classname: str = attachment_data["classname"]
                attachment_class: type[Bot.Attachment] = attachments_keys[attachment_classname]
                attachment: Bot.Attachment = attachment_class.loads(attachment_data)
                attachments.append(attachment)
            
            message = cls(bot, owner_id, text, keyboard, forward_messages, reply, attachments)
            
            message_id: str | None = get_from(data, "id")
            if message_id:
                message.set_id(int(message_id))
            
            chat_id: str | None = get_from(data, "chat_id")
            
            if chat_id:
                message.set_chat_id(int(chat_id))
            
            events_data: dict[Literal["MESSAGE_NEW", "SENT", "EDIT", "DELETE"], list[Bot.Event.EVENT_TYPE]] = data.get("events", {})
            dates_data: dict[Literal["MESSAGE_NEW", "SENT", "EDIT", "DELETE"], list[str]] = data.get("dates", {})
            
            for key in cls.KEYS:
                events_list: list[Bot.Event.EVENT_TYPE] = events_data.get(key, [])
                dates_list: list[str] = dates_data.get(key, [])
                
                if len(events_list) == len(dates_list):
                    for i in range(len(dates_list)):
                        event_data: Bot.Event.EVENT_TYPE = events_list[i]
                        date_data: str = dates_list[i]
                        
                        event: Bot.Event = parent.Event.loads(event_data, parent)
                        date: datetime = datetime.fromisoformat(date_data)
                        message.add_event(event, date, key)            
            return message
        
        @classmethod
        def from_event(cls: type[Vkbot.Message | Telebot.Message], event: Bot.Event, bot: VkApi | TeleBot):
            forward: list[Vkbot.Message | Telebot.Message] = [cls.from_event(ev, bot) for ev in event.get_forward()]
            reply: Vkbot.Message | Telebot.Message | None = cls.from_event(event.get_reply(), bot) if event.reply is not None else None
            
            message: Vkbot.Message | Telebot.Message = cls(bot, event.get_chat_id(), event.get_text(), None, forward, reply, event.get_attachments())
            message.set_chat_id(event.chat_id)
            message.add_event(event, event.get_date(), cls.CREATE_KEY)
            # print(f"{event=} {message.events[cls.CREATE_KEY]=}")
            return message

        def __init__(self, owner_id: int, text: str, keyboard: Bot.Keyboard | None = None, forward: Iterable[Vkbot.Message] = [], reply: Vkbot.Message | None = None, attachments: Iterable[Bot.Attachment] = []):
            """
            :param owner_id: Идентификатор отправителя сообщения (пользователя или администратора, а если отправил сообщение бот, то используйте bot.group_id).
            :param text: Текст сообщения.
            :param keyboard: Vkbot.Keyboard | Telebot.Keyboard.
            :param forward: Список сообщений для пересылки вместе с создаваемым сообщением.
            :param reply: Создаваемое сообщение будет отправлено в ответ с ссылкой на указанное сообщение.
            :param attachments: См. документацию Vkbot.Message и Telebot.Message.
            """
            super().__init__(owner_id, text, reply)
            
            # Вложения объявляются раньше, так как проверяются в set_keyboard
            self.attachments: list[Bot.Attachment] = []

            # Клавиатура
            self.keyboard: Bot.Keyboard | None = None
            
            # Пересланные сообщения
            self.forward_messages: list[Bot.Message] = []
            
            # Сообщение изменилось после отправки
            self.changed: bool = False
            
            self.set_attachments(attachments)
            self.set_keyboard(keyboard)
            self.set_forward(forward)
            
            # Текст устанавливается в последнюю очередь, потому что если он пустой и других вложений/сообщений/клавитуры не передано, то будет вызвано исключение
            self.set_text(text)

        def get_remove_callback(self) -> str:
            if self.keyboard and len(self.keyboard.buttons) == 1:
               callback_data: str | None = self.keyboard.buttons[0].callback_data
               
               if callback_data and callback_data.startswith(CALLBACK_REMOVE):
                   return callback_data
               
            return ""
            
        def __repr__(self) -> str:
            classname: str = "Vkbot.Message" if hasattr(self, "vkbot") else "Telebot.Message"
            id: int = self.id
            chat_id: int = self.get_chat_id()
            owner_id: int = self.get_owner_id()
            keyboard = self.keyboard
            text: str = cut(self.text, 40)
            text: str = self.text
            return f"{classname}({id=} {chat_id=} {owner_id=} {text=})[{keyboard=}]" + "{" + f"attachments({len(self.attachments)})={repr(self.attachments)}" + "}"
        
        def dumps(self) -> MESSAGE_TYPE:
            result: "Bot.Message.MESSAGE_TYPE" = super().dumps()
            keyboard: Bot.Keyboard | None = self.get_keyboard()
            
            result.update({
                "attachments": [attachment.dumps() for attachment in self.get_attachments()],
                "keyboard": keyboard.dumps() if keyboard is not None else None,
                "forward": [message.dumps() for message in self.get_forward()]
            })
            
            return result
        
        def compare_attachments(self, message: Message) -> bool:
            """
            Возвращает True, если у указанного сообщения и текущего одинаковые вложения.
            """
            
            if len(self.attachments) != len(message.attachments):
                return False
            
            for i in range(len(self.attachments)):
                if not self.attachments[i].compare(message.attachments[i]):
                    return False
            
            return True
        
        def compare_messages(message1: Bot.BaseMessage | None, message2: Bot.BaseMessage  | None) -> bool:
            if int(bool(message1)) + int(bool(message2)) == 1:
                return False
            elif message1 is None and message2 is None:
                return True
            else:
                return isinstance(message1, type(message2)) and message1.get_id() == message2.get_id()
        
        def compare_reply(self, message: Bot.Message) -> bool:
            return self.__class__.compare_messages(self.get_reply(), message.get_reply())
        
        def compare_forward(self, message: Message) -> bool:
            if len(self.forward_messages) != len(message.forward_messages):
                return False
            
            for i in range(len(self.forward_messages)):
                message1: Bot.Message = self.forward_messages[i]
                message2: Bot.Message = message.forward_messages[i]
                
                if not self.__class__.compare_messages(message1, message2):
                    return False
            
            return True
        
        def compare(self, message: Message) -> bool:
            return self.compare_attachments(message) and self.compare_forward(message) and self.compare_reply(message)
        
        @abstractmethod
        def edit(self, prevent_resend: bool = False) -> Never:
            raise NotImplementedError("Вместо используйте Vkbot.Message или Telebot.Message")

        def set_changed(self, changed: bool):
            if self.was_sent():
                self.changed = bool(changed)
        
        def was_changed(self) -> bool:
            if self.was_sent():
                return bool(self.changed)
            else:
                return False
        

        def check_keyboard(self, keyboard: Bot.Keyboard) -> bool:
            return isinstance(keyboard, Bot.Keyboard)
        
        def set_keyboard(self, keyboard: Bot.Keyboard | None):
            if keyboard is None:
                self.set_changed(True)
                self.keyboard = None
            elif self.check_keyboard(keyboard):
                self.set_changed(True)
                self.keyboard = keyboard
            else:
                raise ValueError(f"Некорректное значение аргумента {keyboard=}")

        def get_keyboard(self) -> Bot.Keyboard | None:
            if self.keyboard is None:
                return None
            elif self.check_keyboard(self.keyboard):
                return self.keyboard
            else:
                raise ValueError(f"Некорректное значение атрибута {self.keyboard=}")
            
        def clear_keyboard(self):
            """
            Очищает callback_data и url всех кнопок клавиатуры
            """
            if self.keyboard:
                buttons: list[Bot.Keyboard.Button] = []

                for button in self.keyboard.buttons:
                    button.set_url(None)
                    button.set_callback_data(";")
                    buttons.append(button)
                
                self.keyboard.update(buttons)


        def check_attachments(self, attachments: Iterable[Bot.Attachment]) -> bool:
            return is_iterable(attachments) and all(isinstance(attachment, Bot.Attachment) and attachment.check() for attachment in attachments)

        def set_attachments(self, attachments: Iterable[Bot.Attachment]):
            if self.check_attachments(attachments):
                self.set_changed(True)
                self.attachments = list(attachments)
            else:
                raise ValueError(f"Некорректное значение аргумента {attachments=}")

        def get_attachments(self) -> list[Bot.Attachment]:
            if self.check_attachments(self.attachments):
                return self.attachments
            else:
                raise ValueError(f"Некорректное значение атрибута {self.attachments=}")


        def check_reply(self, reply: Bot.BaseMessage) -> bool:
            return isinstance(reply, Bot.BaseMessage) and reply.check()

        def set_reply(self, reply: Bot.BaseMessage | None):
            if reply is None:
                self.set_changed(True)
                self.reply = None
            elif self.forward_messages:
                raise ValueError(f"Некорректное значение атрибута {self.forward_messages=}. Невозможно отвечать на сообщение, если уже включены пересланные сообщения")
            elif self.check_reply(reply):
                self.set_changed(True)
                self.reply = reply
            else:
                raise ValueError(f"Некорректное значение аргумента {reply=}")

        def get_reply(self) -> Bot.BaseMessage | None:
            if self.reply is None:
                return None
            elif self.forward_messages:
                raise ValueError(f"Некорректное значение атрибута {self.forward_messages=}. Невозможно отвечать на сообщение, если уже включены пересланные сообщения")
            elif self.check_reply(self.reply):
                return self.reply
            else:
                raise ValueError(f"Некорректное значение атрибута {self.reply=}")


        def check_forward(self, forward: Iterable[Bot.BaseMessage]) -> bool:
            return is_iterable(forward) and all(isinstance(message, Bot.BaseMessage) for message in forward)

        def set_forward(self, forward: Iterable[Bot.BaseMessage]):
            if self.check_forward(forward):
                if forward and self.reply:
                    raise ValueError(f"Некорректное значение атрибута {self.reply=}. Невозможно пересылать сообщения в ответ на сообщение")
                else:
                    self.set_changed(True)
                    self.forward_messages = list(forward)
            else:
                raise ValueError(f"Некорректное значение аргумента {forward=} для\n{self}")

        def get_forward(self) -> list[Bot.BaseMessage]:
            if self.check_forward(self.forward_messages):
                if self.forward_messages and self.reply:
                    raise ValueError(f"Некорректное значение атрибута {self.reply=}. Невозможно пересылать сообщения в ответ на сообщение")
                else:
                    return self.forward_messages
            else:
                raise ValueError(f"Некорректное значение атрибута {self.forward_messages=}")


        def check_text(self, text: str) -> bool:
            return isinstance(text, str)
        
        def set_text(self, text: str):
            if self.check_text(text):
                self.set_changed(True)
                self.text = text
            elif isinstance(text, str):
                raise ValueError(f"Пустой текст сообщения не допускается, если нет кнопок или вложений")
            else:
                raise ValueError(f"Некорректное значение аргумента {text=}")

        def get_text(self) -> str:
            if self.check_text(self.text):
                return str(self.text).strip()
            elif isinstance(self.text, str):
                raise ValueError(f"Пустой текст сообщения не допускается, если нет кнопок или вложений")
            else:
                raise ValueError(f"Некорректное значение атрибута {self.text=}")


    class VoiceMessage(BaseMessage):
        MESSAGE_TYPE = dict[str, str | int | dict | None]
        
        def __init__(self, owner_id: int, text: str, audio_attachment: Vkbot.AudioAttachment | Telebot.AudioAttachment | None, reply: Bot.Message | None = None):
            """
            :param owner_id: Идентификатор отправителя сообщения (пользователя или администратора, а если отправил сообщение бот, то используйте bot.group_id).
            :param text: Текст сообщения.
            :param event: Сообщение можно создать из Bot.Event, тогда событие помещается это поле.
            """
            super().__init__(owner_id, text, reply)
            
            self.audio_attachment: Bot.AudioAttachment | None
            self.set_audio_attachment(audio_attachment)

        def dumps(self) -> MESSAGE_TYPE:
            result: "Bot.VoiceMessage.MESSAGE_TYPE" = super().dumps()
            
            result.update({
                "text": self.get_text(),
                "audio_attachment": self.get_audio_attachment().dumps() if self.audio_attachment is not None else None
            })
            
            return result
            
            
        def check_audio_attachment(self, audio_attachment: Bot.AudioAttachment) -> bool:
            return isinstance(audio_attachment, Bot.AudioAttachment)

        def set_audio_attachment(self, audio_attachment: Bot.AudioAttachment | None):
            if audio_attachment is None:
                self.audio_attachment = None
            elif self.check_audio_attachment(audio_attachment):
                self.audio_attachment = audio_attachment
            else:
                raise ValueError(f"Некорректное значение аргумента {audio_attachment=}")
            
        def get_audio_attachment(self) -> Bot.AudioAttachment | None:
            if self.audio_attachment is None:
                return None
            elif self.check_audio_attachment(self.audio_attachment):
                return self.audio_attachment
            else:
                raise ValueError(f"Некорректное значение атрибута {self.audio_attachment=}")


    @classmethod
    def check_attachment(cls, attachment: Bot.Attachment) -> bool:
        """
        Возвращает `True`, если указанное вложение создано в этом боте.
        """
        return type(attachment) in cls.__dict__.values()
    
    def __init__(self, token: str, name: str, group_id: int):
        """
        :param token: Токен доступа к API.
        :param name: Имя бота, уникально для одной платформы, например, `"@botname_bot"`. Два vkbot с одинаковым именем нельзя, vkbot и telebot с одинаковым именем можно.
        :param group_id: Идентификатор группы, в которой будет работать бот.
        """
        self.name: str = ""
        self.token: str = ""
        self.group_id: int = -1
        
        self.set_name(name)
        self.set_group_id(group_id)
        self.set_token(token)

        self.working: bool = True
        self.events: dict[int, list[Bot.Event]] = {}
    
    def __repr__(self) -> str:
        name = self.name
        group_id = self.group_id
        working = self.working
        bot_key: BOT_KEY = self.get_bot_key()
        return f"{self.__class__.__name__}({bot_key=} {name=} {group_id=} {working=} events={len(self.events)})"
        
    def get_bot_key(self) -> BOT_KEY:
        return self.__class__.BOT_KEY
    
    def check_working(self) -> bool:
        """
        Возвращает True, если ещё не был вызван метод stop
        """
        return not not self.working

    def stop(self):
        """
        Останавливает все циклы бота, которые зависят от поля working (while self.check_working())
        WARNING: Может не останавливать polling
        """
        self.working = False
    
    def get_matches(self, old_messages: Iterable[Bot.Message], new_messages: Iterable[Bot.Message]) -> list[Bot.Message]:
        """
        Возвращает список сообщений с совпадающими вложениями (которые можно изменять или не надо удалять при редактировании).
        """
        common_prefix_len: int = 0
        min_len: int = min(len(old_messages), len(new_messages))
        
        while common_prefix_len < min_len:
            old_message: Bot.Message = old_messages[common_prefix_len]
            new_message: Bot.Message = new_messages[common_prefix_len]
            # print("compare:", common_prefix_len)
            # print(1, old_message)
            # print(2, new_message)
            
            if old_message.compare(new_message) and old_message.owner_id == new_message.owner_id:
                # print("True ->",common_prefix_len)
                common_prefix_len += 1
            else:
                # print("False ->", common_prefix_len)
                break
        
        return old_messages[:common_prefix_len]
    
    # Методы работы с полями  
    
    
    @classmethod
    def check_group_id(cls, group_id: int) -> bool:
        return isinstance(group_id, int) and group_id >= 0

    def set_group_id(self, group_id: int):
        if self.__class__.check_group_id(group_id):
            self.group_id = group_id
        else:
            raise ValueError(f"Некорректное значение аргумента {group_id=}")

    def get_group_id(self) -> int:
        if self.__class__.check_group_id(self.group_id):
            return self.group_id
        raise ValueError(f"Некорректное значение атрибута {self.group_id=}")


    @classmethod
    def check_token(cls, token: str) -> bool:
        return isinstance(token, str) and len(token) >= 46
    
    def set_token(self, token: str):
        if self.__class__.check_token(token):
            self.token = token
        else:
            raise ValueError(f"Некорректное значение аргумента {token=}")

    def get_token(self) -> str:
        if self.__class__.check_token(self.token):
            return str(self.token).strip()
        else:
            raise ValueError(f"Некорректное значение атрибута {self.token=}")


    @classmethod
    def check_name(cls, name: str) -> bool:
        return isinstance(name, str) and name.startswith("@") and len(name) >= 5
    
    def set_name(self, name: str):
        if self.__class__.check_name(name):
            self.name = name
        else:
            raise ValueError(f"Некорректное значение аргумента {name=}")

    def get_name(self) -> str:
        if self.__class__.check_name(self.name):
            return str(self.name).strip()
        else:
            raise ValueError(f"Некорректное значение атрибута {self.name=}")
        
    
    # Методы работы с событиями
    
    
    def add_id(self, event_id: int):
        """
        Создаёт очередь событий для пользователя
        Если очередь уже была создана, то новая создана не будет, старая останется без изменений
        Очередь событий нужна для объединения событий, пришедших друг за другом за короткий промежуток времени, в одно событие
        """
        if event_id not in self.events:
            if isinstance(event_id, int) and event_id > 0:
                self.events[event_id] = []
            else:
                raise ValueError(f"Некорректное значение аргумента {event_id=}")

    def add_event(self, event: Event):
        """
        Добавляет событие в очередь событий
        WARNING: Предварительно должен был быть вызван метод add_id с тем же идентификатором!
        """
        if event.check_chat_id(event.chat_id):
            self.events[event.chat_id].append(event)
        else:
            raise ValueError(f"Некорректное значение атрибута {event.chat_id=}")

    def remove_event(self, event: Event):
        """
        Удаляет событие из очереди событий
        WARNING: Предварительно должен был быть вызван метод add_id с тем же идентификатором!
        """
        if event.check_chat_id(event.chat_id):
            if event in self.events[event.chat_id]:
                self.events[event.chat_id].remove(event)
        else:
            raise ValueError(f"Некорректное значение атрибута {event.chat_id=}")

    def wait_events(self):
        """
        Ожидание возможного появления событий для объединения
        """
        sleep(EVENT_TIMEOUT)

    def get_events(self, event_id: int) -> list[Event]:
        """
        Возвращает все события в очереди для указанного id, отсортированные по дате по возрастанию (сначала более старые события)
        """
        return sorted(self.events[event_id] if event_id in self.events else [], key = lambda event: event.date)

    def get_prev_events(self, last_event: Event) -> list[Event]:
        """
        Собирает цепочку событий
        Очередь представляет собой словарь, где каждому chat_id:int соотвествует список Event, отсортированный по возрастанию поля date:datetime
        Если в списке после event есть ещё события, то event будет обработан вместе с последним в списке, поэтому вернётся []
        Если в списке перед event есть события, то вернётся список событий, включающий event
        Если в списке больше нет событий, то вернётся []
        """
        events: list[Bot.Event] = self.get_events(last_event.chat_id)

        # Вся цепочка событий, предыдущих для last_event
        prev_events: list[Bot.Event] = []

        def check_previous(prev_event: Bot.Event) -> bool:
            """
            Возвращает истину, если указанное событие является предыдущим хотя бы для одного из цепочки событий 
            """
            return prev_event.prev_for(last_event)

        # Если текущее событие последнее в очереди
        if last_event in events and events.index(last_event) == len(events) - 1:

            for event in events:
                # Проверяем является ли событие предыдущим для last_event
                if check_previous(event):
                    # Удаляем его из очереди
                    self.remove_event(event)

                    # Добавляем его в цепочку
                    prev_events.append(event)

            return prev_events + [last_event]

        return prev_events

    def combine_events(self, events: Iterable[Event]) -> Event:
        """
        Объединяет несколько событий в одно
        Если передано только одно событие, оно останется без изменений и будет возвращено в качестве результата
        Иначе будет изменено и возвращено последнее событие
        
        Совмещает текст событий и вложения
        """
        event: Bot.Event = events[-1]
        
        # Объединяем события
        event.set_events(list(chain.from_iterable(ev.events for ev in events)))
        
        # Объединяем текст через пробел
        event.set_text(" ".join([ev.get_text() for ev in events]))

        # Объединяем вложения
        event.set_attachments(list(chain.from_iterable(ev.attachments for ev in events)))

        # Возвращаем последнее событие, в которое были объединены все остальные события
        return event
    
    def check_callback(self, event: Event) -> bool:
        if event.DEBUG_CALLBACK:
            return True
        return False
    
    
    # Методы обработчики
    
    
    def listener(self, chat_id: int, text: str):
        """
        Замените этот метод на свою функцию, чтобы обрабатывать текст от пользователей
        """
        # Console.print(text, color = "yellow")
        pass

    def process_message(self, event: Event):
        """
        Замените этот метод на свою функцию, чтобы обрабатывать сообщения от пользователей
        """
        return self.listener(event.chat_id, event.get_text())

    def process_callback(self, event: Event):
        """
        Замените этот метод на свою функцию, чтобы обрабатывать события от пользователей
        """
        return self.listener(event.chat_id, event.get_text())

    def process_event__(self, event: Event):
        """
        Замените этот метод на свою функцию, чтобы обрабатывать события от пользователей
        """
        if self.check_callback(event):
            return self.process_callback(event)
        else:
            return self.process_message(event)

    def process_event_(self, event: Event):
        """
        Обрабатывает только что пришедшее событие
        Отправляет объединённое на обработку
        """

        # Добавляем событие в очередь событий
        self.add_event(event)

        # Ожидаем возможного появления следующих событий
        self.wait_events()

        # Получаем предыдущие события
        events: list[Bot.Event] = self.get_prev_events(
            event)  # Если есть последующие события, вернётся [], иначе вернётся список событий, включающий текущее событие

        # Объединяем события
        ev: Bot.Event | None = self.combine_events(events) if events else None

        # Удаляем событие из очереди
        self.remove_event(ev) if ev else None

        # Обрабатываем событие
        self.process_event__(ev) if ev else None

        """
        ### Если событие не было обработано
        Предыдущие события возвращают get_prev_events=[] если есть последующие события
        Но если событие не было обработано с последующими, оно обрабатывается здесь
        """

        # Ожидание возможной обработки события
        sleep(EVENT_INTERVAL)

        # Если событие не было обработано с последующими
        if event and event in self.events[event.chat_id]:
            # Удаляем событие из очереди
            self.remove_event(event)

            # Обрабатываем событие
            self.process_event__(event)

    def process_event(self, event: Event, combine_events: bool = True):
        """
        Обработчик событий из polling
        Запускает обработку события в отдельном потоке
        """
        def process_event():
            if combine_events:
                return self.process_event_(event)
            else:
                return self.process_event__(event)

        Thread(target = process_event).start()


    # Родительские методы
    
    
    def split_text(self, text: str) -> list[str]:
        """
        Разделитель текста сообщения
        Если текст сообщения слишком длинный и не помещается в одно сообщение (один блок), то его надо разделить
        Сначала выполняется попытка найти пробел или снос строки (далее - разделитель) с конца текста, но не далее чем на MAX_SPLIT с конца, чтобы не делить сообщение где попало
        Если разделитель найти не удалось, сообщение делится ровно по MAX_LENGTH
        """
        max_length: int = self.__class__.Message.MAX_LENGTH
        texts: list[str] = []
        text: str = str(text).strip()

        while text:
            part: str = text[:max_length].rstrip()
            last_space: int = part.rfind(" ")
            last_demolition: int = part.rfind("\n")

            last_splitter = max(last_space, last_demolition)
            last_splitter = max_length if last_splitter == -1 else last_splitter
            last_splitter = last_splitter if max_length - last_splitter < self.__class__.MAX_SPLIT else max_length

            part = text[:last_splitter]
            
            if part.strip():
                texts.append(part)
                
            text = text[last_splitter:].strip()

        return texts

    def split_attachments(self, attachments: Iterable[Bot.Attachment]) -> list[tuple[Bot.Attachment]]:
        """
        Делит список из имён файлов на несколько кортежей из имён файлов так, чтобы в одном кортеже было не более MAX_ATTACHMENTS имён файлов
        """
        max_attachments: int = self.__class__.Message.MAX_ATTACHMENTS
        return [tuple(attachments[i:i + max_attachments]) for i in range(0, len(attachments), max_attachments)]


class Vkbot(Bot):
    BOT_KEY: Literal["vkbot"] = "vkbot"
    URL: str = "http://vk.com/"
    
    def check_event(event: VkBotMessageEvent | VkBotEvent | DotDict) -> bool:
        """
        Возвращает True, если это событие из vkbot.
        """
        return isinstance(event, VkBotMessageEvent) or isinstance(event, VkBotEvent) or isinstance(event, DotDict) or isinstance(event, dict)
    
    
    class Attachment(Bot.Attachment):
        """
        Хранит информацию о загруженном на сервера вложении для повторной отправки без повторной загрузки.
        """
        ATTACHMENT_TYPE = dict[str, int | str]
        DEFAULT_ATTACHMENT_TYPE: Literal["doc"] = "doc"
        
        EXTENSIONS: dict[str, tuple[str]] = {
            "photo": PHOTO_EXTENSIONS,
            "video": VIDEO_EXTENSIONS,
            "doc": DOC_EXTENSIONS,
            "audio_message": AUDIO_EXTENSIONS
        }
        
        @classmethod
        def loads(cls: type[Vkbot.Attachment | Vkbot.PhotoAttachment | Vkbot.VideoAttachment | Vkbot.AudioAttachment | Vkbot.DocAttachment], data: ATTACHMENT_TYPE) -> Vkbot.Attachment | Vkbot.PhotoAttachment | Vkbot.VideoAttachment | Vkbot.AudioAttachment | Vkbot.DocAttachment:
            attachment_type: str | int = get_from(data, "type")
            owner_id: int = get_int(data, -1, "owner_id")
            attachment_id: int = get_int(data, -1, "id")
            access_key: str = get_from(data, "access_key")
            filename: str = get_from(data, "filename")

            type_key: str = attachment_type

            if is_int(type_key):
                type_key = "doc"
            
            attachment: Vkbot.Attachment | Vkbot.PhotoAttachment | Vkbot.VideoAttachment | Vkbot.AudioAttachment | Vkbot.DocAttachment = cls(
                {
                    type_key: {
                        "owner_id": owner_id,
                        "id": attachment_id,
                        "access_key": access_key,
                        "type": attachment_type
                    }
                }
            )
            
            if filename:
                attachment.set_filename(filename)
                
            return attachment
        
        def from_filename(filename: str, vkbot: VkApi) -> NoReturn:
            raise VkbotException("Vkbot не поддерживает загрузку вложений кроме PhotoAttachment")
    
        @classmethod
        def get_extension(cls, attachment_type: Literal["photo", "video", "doc", "audio_message"]) -> str:
            match attachment_type:
                case "photo":
                    return PHOTO_EXTENSIONS[0]
                case "video":
                    return VIDEO_EXTENSIONS[0]
                case "audio_message":
                    return AUDIO_EXTENSIONS[0]
                case "doc":
                    return DOC_EXTENSIONS[0]  # .bin
                case _:
                    raise ValueError(f"Некорректное значение аргумента {attachment_type=}")

        @classmethod
        def create_filename(cls, folder: str, attachment_type: Literal["photo", "video", "doc", "audio_message"], attachment_id: int):
            ext: str = cls.get_extension(attachment_type)
            return create_filename(folder, f"{attachment_type}_{attachment_id}{ext}")

        def __init__(self, attachment_type: Literal["photo", "video", "doc", "audio_message"], owner_id: int, attachment_id: int, access_key: str):
            """
            :param attachment_type: Тип вложения, должен быть в Vkbot.EXTENSIONS.
            :param owner_id: Идентификатор владельца вложения, который загрузил его на сервер, можно получить в Vkbot.upload_attachment.
            :param attachment_id: Идентификатор загруженного вложения можно получить в Vkbot.upload_attachment.
            :param access_key: Ключ доступа к вложению, можно получить в Vkbot.upload_attachment.
            """
            super().__init__(attachment_id)
            self.id: int
            self.type: Literal["photo", "video", "doc", "audio_message"] = self.__class__.DEFAULT_ATTACHMENT_TYPE
            self.owner_id: int = -1
            self.access_key: str = ""
            
            self.set_type(attachment_type)
            self.set_owner_id(owner_id)
            self.set_access_key(access_key)
            
        def dumps(self) -> ATTACHMENT_TYPE:
            result: "Vkbot.Attachment.ATTACHMENT_TYPE" = super().dumps()
            
            result.update({
                "owner_id": self.get_owner_id(),
                "access_key": self.get_access_key(),
                "type": self.get_type()
            })

            # print(f"dumps {result=}")
            
            return result

        def __str__(self) -> str:
            """
            type-ownerId_attachmentId_accessKey
            photo-225421698_457239018_009eebb3138c0e130b
            """
            return f"{self.type}{self.owner_id}_{self.id}_{self.access_key}"
        
        def check(self) -> bool:
            """
            Проверяет корректность полей вложения перед отправкой
            """
            return self.check_type(self.type) and self.check_owner_id(self.owner_id) and self.check_id(self.id) and self.check_access_key(self.access_key)
        
        def compare(self, attachment: Vkbot.Attachment) -> bool:
            if self.filename or attachment.filename:
                return self.get_filename() == attachment.get_filename()
            elif attachment.get_id() != self.get_id():
                return False
            elif attachment.get_access_key() != self.get_access_key():
                return False
            elif attachment.get_owner_id() != self.get_owner_id():
                return False
            else:
                return True
        
        @abstractmethod
        def download_attachments(self, vkbot: Vkbot) -> list[dict]:
            raise NotImplementedError()

        def get_max_size(self, attachments: list[dict]) -> dict:
            return attachments[0]
        
        @abstractmethod
        def get_url(self, attachment: dict) -> str:
            raise NotImplementedError()
            
        def download(self, vkbot: Vkbot) -> str:
            if self.data is not None:
                raise ValueError(f"Некорректное значение атрибута {self.data=}. Скачивание уже выполнено, повторное скачивание невозможно.")

            attachments: list[dict] = self.download_attachments(vkbot)
            attachment: dict = self.get_max_size(attachments)
            url: str = self.get_url(attachment)
            # Скачиваем файл
            response = requests.get(url)
            response.raise_for_status()
            self.data = BytesIO(response.content)
            return attachment.get("title", "")
        
        def make_filename(self, vkbot: Vkbot, folder: str) -> str:
            filename: str = self.filename

            if self.filename:
                return self.get_filename()
            elif not self.data:
                filename = self.download(vkbot)
            
            if not isdir(folder):
                makedirs(folder)
            
            attachment_filename: str = self.__class__.create_filename(folder, self.get_type(), self.get_id())
            
            if filename:
                if len(only_extension(filename)) < 2:
                    filename = change_extension(filename, only_extension(attachment_filename))
                
                filename = create_filename(filename)
            else:
                filename = attachment_filename
            
            # WARNING:
            if only_extension(filename).upper() in ".JPG":
                filename = change_extension(filename, ".jpeg")

            self.save_as(filename)
            self.set_filename(filename)
            return filename


        # Методы, связанные с полями класса
        

        def check_type(self, type: Literal["photo", "video", "doc", "audio_message"]) -> bool:
            return type in Vkbot.Attachment.EXTENSIONS

        def set_type(self, attachment_type: Literal["photo", "video", "doc", "audio_message"]):
            if self.check_type(attachment_type):
                self.type = attachment_type
            else:
                raise ValueError(f"Некорректное значение аргумента {attachment_type=}")

        def get_type(self) -> Literal["photo", "video", "doc", "audio_message"]:
            if self.check_type(self.type):
                return self.type
            else:
                raise ValueError(f"Некорректное значение атрибута {self.type=}")
        
        
        def check_id(self, attachment_id: int) -> bool:
            return isinstance(attachment_id, int) and attachment_id > 0

        def set_id(self, attachment_id: int):
            if self.check_id(attachment_id):
                self.id = attachment_id
            else:
                raise ValueError(f"Некорректное значение аргумента {attachment_id=}")

        def get_id(self) -> int:
            if self.check_id(self.id):
                return self.id
            else:
                raise ValueError(f"Некорректное значение атрибута {self.id=}")
        
        
        def check_owner_id(self, owner_id: int) -> bool:
            return isinstance(owner_id, int)

        def set_owner_id(self, owner_id: int):
            if self.check_owner_id(owner_id):
                self.owner_id = owner_id
            else:
                raise ValueError(f"Некорректное значение аргумента {owner_id=}")

        def get_owner_id(self) -> int:
            if self.check_owner_id(self.owner_id):
                return self.owner_id
            else:
                raise ValueError(f"Некорректное значение атрибута {self.owner_id=}")
        
        
        def check_access_key(self, key: str) -> bool:
            return isinstance(key, str) and key.strip()

        def set_access_key(self, key: str):
            if self.check_access_key(key):
                self.access_key = key.strip()
            else:
                raise ValueError(f"Некорректное значение аргумента {key=}")

        def get_access_key(self) -> str:
            if self.check_access_key(self.access_key):
                return self.access_key
            else:
                raise ValueError(f"Некорректное значение атрибута {self.access_key=}")
    
    
    class UrlAttachment():
        ATTACHMENT_TYPE = dict[str, int | str | bool]
        
        def __init__(self, attachment: DotDict | dict):
            """
            Распаковка внутреннего вложения URL
            """
            self.height: int = get_int(attachment, -1, "height")
            self.width: int = get_int(attachment, -1, "width")
            self.url: str = get_from(attachment, "url", types = (str,), default = "")
            
            self.type: Literal["s", "m", "x", "o", "p", "r", "base"]  | str = get_from(attachment, "type", types = (str,), default = "")
            self.with_padding: bool | None = get_from(attachment, "video", "can_dislike", default = None)
            
            if type(self.with_padding) is int:
                self.with_padding = bool(self.with_padding)
            
            if not self.type:
                self.type = ""
            
            if self.height < 0:
                warn("Некорректное значение поля attachment.height или attachment['height']")
                self.height = 0
            
            if self.width < 0:
                warn("Некорректное значение поля attachment.width или attachment['width']")
                self.width = 0
            
            if not self.url:
                warn("Некорректное значение поля attachment.url или attachment['url']")
                self.url = ""
        
        def dumps(self) -> ATTACHMENT_TYPE:
            result: "Vkbot.UrlAttachment.ATTACHMENT_TYPE" = {}
            
            if isinstance(self.height, int) and self.height > 0:
                result["height"] = self.height

            if isinstance(self.width, int) and self.width > 0:
                result["width"] = self.width

            if isinstance(self.url, str) and self.url:
                result["url"] = self.url

            if isinstance(self.type, str) and self.type:
                result["type"] = self.type
                
            return result


    class PhotoAttachment(Attachment):
        ATTACHMENT_TYPE = dict[str, Union[int, str, bool, "Vkbot.UrlAttachment.ATTACHMENT_TYPE", list["Vkbot.UrlAttachment.ATTACHMENT_TYPE"]]]
        
        def from_filename(filename: str, vkbot: Vkbot) -> Vkbot.Attachment:
            """
            Метод загружает изображение из файла с указанным адресом.
            Возвращает вложение, готовое к отправке.
            """
            responses: list = vkbot.upload.photo_messages(filename)
            response: dict = responses[0]

            owner_id: int = get_int(response, -1, "owner_id")
            attachment_id = get_int(response, -1, "id")
            access_key: str = get_from(response, "access_key", types = (str,), default = "")

            attachment: Vkbot.Attachment = vkbot.__class__.Attachment("photo", owner_id, attachment_id, access_key)
            attachment.set_filename(filename)
            Console.success("uploaded", filename, "to", attachment)
            return attachment
        
        def __init__(self, attachment: dict | DotDict):
            """
            Распаковка вложения изображения
            """
            owner_id: str = get_from(attachment, "photo", "owner_id")
            attachment_id: str = get_from(attachment, "photo", "id")
            access_key: str = get_from(attachment, "photo", "access_key")
            
            super().__init__("photo", owner_id, attachment_id, access_key)
            
            self.date: datetime = get_date(attachment, "photo", "date")
            self.sizes: list[Vkbot.UrlAttachment] = []
            self.text: str = get_from(attachment, "photo", "text", types = (str,), default = None)
            self.web_view_token: str = get_from(attachment, "photo", "web_view_token", types = (str,), default = None)
            self.has_tags: bool = get_from(attachment, "photo", "has_tags", default = None)
            orig_photo: dict = get_from(attachment, "photo", "orig_photo", types = (dict,), default = {})
            self.orig_photo: Vkbot.UrlAttachment = Vkbot.UrlAttachment(orig_photo)
            
            album_id: int | None = get_from(attachment, "photo", "album_id", types = (int,), default = None)
            self.album_id: int = album_id if isinstance(album_id, int) else 0
            
            if album_id is None:
                warn(f"Некорректное значение атрибута {self.album_id=}")
            
            for size_dict in get_from(attachment, "photo", "sizes", types = (list,), default = []):
                size_attachment: Vkbot.UrlAttachment = Vkbot.UrlAttachment(size_dict)
                self.sizes.append(size_attachment)
            
            if not isinstance(self.text, str):
                warn(f"Некорректное значение атрибута {self.text=}")
                self.text = ""
            
            if not isinstance(self.web_view_token, str):
                warn(f"Некорректное значение атрибута {self.web_view_token=}")
                self.web_view_token = ""
            
            if self.has_tags is None:
                warn(f"Некорректное значение атрибута {self.has_tags=}")
                self.has_tags = False
            else:
                self.has_tags = bool(self.has_tags)
                
            if (not orig_photo) or not isinstance(orig_photo, dict):
                warn(f"Некорректное значение атрибута {self.orig_photo=}")
                
        def dumps(self) -> ATTACHMENT_TYPE:
            result: "Vkbot.PhotoAttachment.ATTACHMENT_TYPE" = super().dumps()
            
            result.update({
                "album_id": int(self.album_id),
                "text": str(self.text),
                "web_view_token": str(self.web_view_token),
                "has_tags": bool(self.has_tags),
                "orig_photo": self.orig_photo.dumps(),
                "sizes": [size.dumps() for size in self.sizes]
            })
            
            return result
        
        def download_attachments(self, vkbot: Vkbot) -> list[dict]:
            photos: list[dict] = vkbot.bot.method("photos.getById", {
                "photos": self.get_id(),
                "extended": 0
            })

            return photos
        
        def get_url(self, attachment: dict) -> str:
            sizes: list[dict] = attachment.get("sizes", [])

            # Ищем максимальный размер
            max_size: dict = max(sizes, key=lambda x: x.get("width", 0) * x.get("height", 0))
            url = max_size["url"]
            return url


    class VideoAttachment(Attachment):
        ATTACHMENT_TYPE = dict[str, int | str | bool | list[dict[str, int | str]]]
        
        def __init__(self, attachment: dict | DotDict):
            """
            Распаковка вложения видео
            """
            owner_id: str = get_from(attachment, "video", "owner_id")
            attachment_id: str = get_from(attachment, "video", "id")
            access_key: str = get_from(attachment, "video", "access_key")
            
            super().__init__("video", owner_id, attachment_id, access_key)
            
            self.date: datetime = get_date(attachment, "video", "date")
            self.can_edit: bool = get_from(attachment, "video", "can_edit", default = None)
            self.can_delete: bool = get_from(attachment, "video", "can_delete", default = None)
            self.can_add: bool = get_from(attachment, "video", "can_add", default = None)
            self.can_attach_link: bool = get_from(attachment, "video", "can_attach_link", default = None)
            self.can_edit_privacy: bool = get_from(attachment, "video", "can_edit_privacy", default = None)
            self.is_private: bool = get_from(attachment, "video", "is_private", default = None)
            self.processing: bool = get_from(attachment, "video", "processing", default = None)
            self.can_dislike: bool = get_from(attachment, "video", "can_dislike", default = None)
            
            self.is_author: bool = get_from(attachment, "video", "is_author", types = (bool,), default = None)
            self.is_favorite: bool = get_from(attachment, "video", "is_favorite", types = (bool,), default = None)
            
            self.response_type: Literal["min"] | str = get_from(attachment, "video", "response_type", types = (str,), default = None)
            self.description: str = get_from(attachment, "video", "description", types = (str,), default = None)
            self.title: str = get_from(attachment, "video", "title", types = (str,), default = None)
            self.track_code: str = get_from(attachment, "video", "track_code", types = (str,), default = None)
            
            # В секундах
            self.duration: int = get_int(attachment, -1, "video", "duration")
            self.width: int = get_int(attachment, -1, "video", "width")
            self.height: int = get_int(attachment, -1, "video", "height")
            self.views: int = get_int(attachment, -1, "video", "views")
            self.local_views: int = get_int(attachment, -1, "video", "local_views")

            self.image: list[Vkbot.UrlAttachment] = []
            self.first_frame: list[Vkbot.UrlAttachment] = []
            
            for image_dict in get_from(attachment, "video", "image", types = (list,), default = []):
                if isinstance(image_dict, dict) or isinstance(image_dict, DotDict):
                    image_attachment: Vkbot.UrlAttachment = Vkbot.UrlAttachment(image_dict)
                    self.image.append(image_attachment)
                else:
                    warn(f"Некорректное значение словаря с ключом image пропущено")
            
            for image_dict in get_from(attachment, "video", "first_frame", types = (list,), default = []):
                if isinstance(image_dict, dict) or isinstance(image_dict, DotDict):
                    image_attachment: Vkbot.UrlAttachment = Vkbot.UrlAttachment(image_dict)
                    self.first_frame.append(image_attachment)
                else:
                    warn(f"Некорректное значение словаря с ключом image пропущено")
            
            for key in ("can_edit", "can_delete", "can_add", "can_attach_link", "can_edit_privacy", "is_private", "processing", "can_dislike"):
                value: int | None = getattr(self, key)
                
                if value is None:
                    warn(f"Некорректное значение словаря с ключом {key}={repr(value)}")
                    setattr(self, key, False)
                else:
                    setattr(self, key, bool(value))
            
            if not isinstance(self.response_type, str):
                warn(f"Некорректное значение атрибута {self.response_type=}")
                self.response_type = ""
            
            if not isinstance(self.description, str):
                warn(f"Некорректное значение атрибута {self.description=}")
                self.description = ""
            
            if not isinstance(self.title, str):
                warn(f"Некорректное значение атрибута {self.title=}")
                self.title = ""
            
            if (not isinstance(self.track_code, str)) or not self.track_code.startswith("video_"):
                warn(f"Некорректное значение атрибута {self.track_code=}")
                self.track_code = ""
            
            if not isinstance(self.is_author, bool):
                warn(f"Некорректное значение атрибута {self.is_author=}")
                self.is_author = False
            
            if not isinstance(self.is_favorite, bool):
                warn(f"Некорректное значение атрибута {self.is_favorite=}")
                self.is_favorite = False
            
            if self.duration < 0:
                warn(f"Некорректное значение атрибута {self.duration=}")
                self.duration = 0
            
            if self.width < 0:
                warn(f"Некорректное значение атрибута {self.width=}")
                self.width = 0
            
            if self.height < 0:
                warn(f"Некорректное значение атрибута {self.height=}")
                self.height = 0
            
            if self.views < 0:
                warn(f"Некорректное значение атрибута {self.views=}")
                self.views = -1
            
            if self.local_views < 0:
                warn(f"Некорректное значение атрибута {self.local_views=}")
                self.local_views = -1
                
        def dumps(self) -> ATTACHMENT_TYPE:
            result: "Vkbot.VideoAttachment.ATTACHMENT_TYPE" = super().dumps()
            
            result.update({
                "can_edit": bool(self.can_edit),
                "can_delete": bool(self.can_delete),
                "can_add": bool(self.can_add),
                "can_attach_link": bool(self.can_attach_link),
                "can_edit_privacy": bool(self.can_edit_privacy),
                "is_private": bool(self.is_private),
                "processing": bool(self.processing),
                "can_dislike": bool(self.can_dislike),
                "is_author": bool(self.is_author),
                "is_favorite": bool(self.is_favorite),
                "response_type": str(self.response_type),
                "description": str(self.description),
                "title": str(self.title),
                "track_code": str(self.track_code),
                "duration": int(self.duration),
                "width": int(self.width),
                "height": int(self.height),
                "views": int(self.views),
                "local_views": int(self.local_views),
                "image": [img.dumps() for img in self.image],
                "first_frame": [frame.dumps() for frame in self.first_frame]
                # "date": int(self.date.timestamp()),
            })
            
            return result
        
        def download_attachments(self, vkbot: Vkbot) -> list[dict]:
            video: dict = vkbot.bot.method("video.get", {
                "videos": self.get_id(),
                "extended": 0
            })

            return video.get("items")
        
        def get_url(self, attachment: dict, size_key: Literal["mp4_1080", "mp4_720", "mp4_480", "mp4_360", "mp4_240"] | None = None) -> str:
            files: dict = attachment["files"]

            for key in ("mp4_1080", "mp4_720", "mp4_480", "mp4_360", "mp4_240"):
                if key == size_key:
                    return files[key]
                elif size_key is None and key in files:
                    return files[key]
            
            return list(files.values())[0]
    
    
    class DocAttachment(Attachment):
        ATTACHMENT_TYPE = dict[str, int | str | bool | list[int] | dict[str, int | str]]
        
        def __init__(self, attachment: dict | DotDict):
            """
            Распаковка вложения документа
            """
            owner_id: str = get_from(attachment, "doc", "owner_id")
            attachment_id: str = get_from(attachment, "doc", "id")
            access_key: str = get_from(attachment, "doc", "access_key")
            
            super().__init__("doc", owner_id, attachment_id, access_key)
            
            self.date: datetime = get_date(attachment, "doc", "date")
            self.title: str = get_from(attachment, "doc", "title", types = (str,), default = None)
            self.ext: str = get_from(attachment, "doc", "ext", types = (str,), default = None)
            self.url: str = get_from(attachment, "doc", "url", types = (str,), default = "")
            
            self.can_manage: bool = get_from(attachment, "doc", "can_manage", types = (bool,), default = None)
            
            self.is_unsafe: bool = get_from(attachment, "doc", "is_unsafe", default = None)
            
            self.size: int = get_int(attachment, -1, "doc", "size")
            self.doc_type: int = get_int(attachment, -1, "doc", "type")
            
            if not isinstance(self.title, str):
                warn(f"Некорректное значение атрибута {self.title=}")
                self.title = ""
                
            if self.size < 0:
                warn(f"Некорректное значение атрибута {self.size=}")
                self.size = 0
                
            if not isinstance(self.ext, str):
                warn(f"Некорректное значение атрибута {self.ext=}")
                self.ext = ""
                
            if self.doc_type < 0:
                warn(f"Некорректное значение атрибута {self.doc_type=}")
                self.doc_type = 0
                
            if not self.url:
                warn(f"Некорректное значение атрибута {self.url=}")
                self.url = ""
                
            if self.is_unsafe is None:
                warn(f"Некорректное значение атрибута {self.is_unsafe=}")
                self.is_unsafe = False
            else:
                self.is_unsafe = bool(self.is_unsafe)
                
            if self.can_manage is None:
                warn(f"Некорректное значение атрибута {self.can_manage=}")
                self.can_manage = False
                
        def dumps(self) -> ATTACHMENT_TYPE:
            result: "Vkbot.DocAttachment.ATTACHMENT_TYPE" = super().dumps()
            
            result.update({
                "title": str(self.title),
                "ext": str(self.ext),
                "url": str(self.url),
                "can_manage": bool(self.can_manage),
                "is_unsafe": bool(self.is_unsafe),
                "size": int(self.size),
                "type": int(self.doc_type),
                "type": int(self.doc_type)
                # "date": int(self.date.timestamp()),
            })
            
            return result
        
        def download_attachments(self, vkbot: Vkbot) -> list[dict]:
            docs: list[dict] = vkbot.bot.method("docs.getById", {
                "docs": self.get_id()
            })

            return docs
        
        def get_url(self, attachment: dict) -> str:
            return attachment["url"]

    
    class AudioAttachment(Attachment):
        ATTACHMENT_TYPE = dict[str, int | str | bool | list[int] | dict[str, int | str]]
        
        def __init__(self, attachment: dict | DotDict):
            """
            Распаковка вложения с аудио.
            Пришло голосовое сообщение с возможностью распознавания текста.
            """
            owner_id: int = get_from(attachment, "audio_message", "owner_id")
            attachment_id: int = get_from(attachment, "audio_message", "id")
            access_key: str = get_from(attachment, "audio_message", "access_key")
            
            super().__init__("audio_message", owner_id, attachment_id, access_key)
            
            self.date: datetime = datetime.now()
            self.duration: int = get_int(attachment, -1, "audio_message", "duration")
            self.link_mp3: str = get_from(attachment, "audio_message", "link_mp3", types = (str,), default = "")
            self.link_ogg: str = get_from(attachment, "audio_message", "link_ogg", types = (str,), default = "")
            self.waveform: list[int] = get_from(attachment, "audio_message", "waveform", type = (list,), default = [])
            
            if self.duration < 0:
                warn(f"Некорректное значение атрибута {self.duration=}")
                self.duration = 0
                
            if not self.link_mp3:
                warn(f"Некорректное значение атрибута {self.link_mp3=}")
                self.link_mp3 = ""
                
            if not self.link_ogg:
                warn(f"Некорректное значение атрибута {self.link_ogg=}")
                self.link_ogg = ""
                
            if not isinstance(self.waveform, list) or not all(isinstance(x, int) for x in self.waveform):
                warn(f"Некорректное значение атрибута {self.waveform=}")
                self.waveform = []
            
                
        def dumps(self) -> ATTACHMENT_TYPE:
            result: "Vkbot.AudioAttachment.ATTACHMENT_TYPE" = super().dumps()
            
            result.update({
                "duration": int(self.duration),
                "link_mp3": str(self.link_mp3),
                "link_ogg": str(self.link_ogg),
                "waveform": [int(elem) for elem in self.waveform]
            })
            
            return result
        
        def recognize(self) -> str | Literal[""]:
            """
            Распознавание голоса.
            """
            # Скачивание вложения, ответ в виде байтов
            response: Response = requests.get(self.link_mp3 or self.link_ogg)

            # Преобразование ответа в последовательность байтов
            audio_data: BytesIO = BytesIO(response.content)

            # Преобразование в аудио формат
            audio_segment: AudioSegment = AudioSegment.from_mp3(audio_data)

            # Преобразование mp3 в wav для распознавания
            audio_wav = audio_segment.export(format = "wav")

            # Распознавание текста голосового сообщения
            recognizer: Recognizer = Recognizer()
            
            with AudioFile(audio_wav) as source:
                audio: AudioData = recognizer.record(source)
                try:
                    # language="ru" не мешает распознавать английскую речь
                    recognized: str = recognizer.recognize_google(audio, language = "ru")
                except UnknownValueError as err:
                    recognized: UnknownValueError = err
            
            if isinstance(recognized, str) and recognized:
                return recognized
            else:
                return ""
        
        def download_attachments(self, vkbot: Vkbot) -> list[dict]:
            audios: list[dict] = vkbot.bot.method("audio.getById", {
                "audios": self.get_id()
            })

            return audios
        
        def get_url(self, attachment: dict) -> str:
            return attachment["url"]
    

    class Keyboard(Bot.Keyboard):
        """
        Может использоваться повторно
        """
        KEYBOARD_TYPE = dict[str, int | bool| list["Vkbot.Keyboard.Button.BUTTON_TYPE"]]
        MAX_BUTTON_LENGTH: int = 40
        
        class Button(Bot.Keyboard.Button):
            BUTTON_TYPE = dict[str, str | int]
            DEFAULT_MIN_WIDTH: int = 1
            DEFAULT_BUTTON_TYPE: str = "text"
            
            MIN_WIDTH_VALUES: dict[bool, tuple[int]] = {
                # inline=True
                True: (1, 2),
                # inline=False
                False: (1, 2, 3, 4)
            }
            
            def loads(data: BUTTON_TYPE) -> Vkbot.Keyboard.Button:
                text: str = get_from(data, "text")
                color: int = get_int(data, -1, "color")
                min_width: int = get_int(data, -1, "min_width")
                callback_data: str | None = get_from(data, "callback_data")
                url: str | None = get_from(data, "url")
                return Vkbot.Keyboard.Button(text, color, min_width, callback_data, url)
            
            def __init__(self, text: str, color: Literal[0, 1, 2, 3] | str | VkKeyboardColor = Bot.Keyboard.Button.DEFAULT_COLOR, min_width: Literal[1, 2, 3, 4] = DEFAULT_MIN_WIDTH, callback_data: str | None = None, url: str | None = None):
                """
                :param text: Обязательно не пустой текст.
                :param color: Цвет кнопки в виде индекса 0,1,2,3 или текстом RED,PRIMARY,#4BB34B,БЕЛЫЙ или конкретным VkKeyboardColor.
                :param min_width: Минимальная ширина кнопки, количество ячеек, которое будет занимать кнопка, в итоге кнопка может быть больше, но не меньше.
                :param url: По нажатию на кнопку будет открываться указанная ссылка, не совместимо с callback_data.
                :param callback_data: Если указано, то по нажатию на кнопку она заблокируется, а process_callback получит указанное значение, не совместимо с url.
                """
                super().__init__(text, color, callback_data, url)
                self.min_width: int = -1
                self.set_min_width(min_width)
                
            def dumps(self) -> BUTTON_TYPE:
                result: "Vkbot.Keyboard.Button.BUTTON_TYPE" = super().dumps()
                
                result.update({
                    "min_width": self.get_min_width()
                })
                
                return result
            

            def check_min_width(self, min_width: int) -> bool:
                return isinstance(min_width, int) and min_width > 0 and min_width < 5

            def set_min_width(self, min_width: int):
                if self.check_min_width(min_width):
                    self.min_width = min_width
                else:
                    raise ValueError(f"Некорректное значение аргумента {min_width=} при {self.inline=}")

            def get_min_width(self) -> int:
                if self.check_min_width(self.min_width):
                    return self.min_width
                else:
                    raise ValueError(f"Некорректное значение атрибута {self.min_width=} при {self.inline=}")
        
        def loads(data: KEYBOARD_TYPE) -> Vkbot.Keyboard:
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
            :param max_width: Максимальная ширина клавиатуры (количество кнопок в одном ряду).
            :param inline: True - кнопки, прикреплённые к сообщению; False - кнопки, закреплённые под клавиатурой.
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
            
            # print(f">>>{self.test}<<<")

        def dumps(self) -> KEYBOARD_TYPE:
            result: "Vkbot.Keyboard.KEYBOARD_TYPE" = super().dumps()
            
            result.update({
                "unused_buttons": [button.dumps() for button in self.unused_buttons]
            })
            
            return result
        
        def get_unused_buttons(self) -> list[Button]:
            """
            Метод возвращает кнопки, для которых не хватило ячеек в клавиатуре из-за ограничений vkbot.
            """
            # Проверка типа, в списке неиспользованных кнопок могут быть только кнопки или тексты
            for button in self.unused_buttons:
                if type(button) not in (str, self.__class__.Button):
                    raise ValueError(f"Некорректное значение поля Vkbot.Keyboard.unused_buttons, ожидался список строк или Vkbot.Keyboard.Button, а получено {type(button)}")

            return self.unused_buttons

        def get_keyboard(self) -> str:
            """
            Возвращает клавиатуру в том виде, в котором она отправляется vk_api.
            """
            if isinstance(self.keyboard, VkKeyboard):
                if self.buttons:
                    return self.keyboard.get_keyboard()
                else:
                    return VkKeyboard.get_empty_keyboard()
            else:
                raise ValueError(f"Некорректное значение атрибута {self.keyboard=}")
    
    
    class Message(Bot.Message):
        """
        Хранит информацию об одном сообщении для vk (один блок).
        """

        # Текст пустого сообщения (у пользователя текст не отображается, нужно для отправки кнопок без описания)
        EMPTY_TEXT: str = "ㅤ" # "&#00000013;"
        
        @classmethod
        def from_event(cls: type[Vkbot.Message], event: Bot.Event, bot: TeleBot):
            message: Vkbot.Message = super().from_event(event, bot)
            message_id: None = Vkbot.get_message_id(event)
            message.set_id(message_id) if message_id is not None else None
            return message

        def __init__(self, vkbot: VkApi, owner_id: int, text: str, keyboard: Vkbot.Keyboard | None = None, forward: Iterable[Vkbot.Message] = [], reply: Vkbot.Message | None = None, attachments: Iterable[Vkbot.Attachment] = []):
            """
            При создании сообщения указываются все поля кроме chat_id, message_id и random_id, они устанавливаются при отправке методом send.
            :param vkbot: Непосредственно бот, через который осуществляются запросы к API. Обязательно должен быть рабочим!
            :param owner_id: Идентификатор отправителя сообщения (сообщества или пользователя).
            :param text: Длина ограничена 4096 символами, текст может быть пустым.
            :param keyboard: Либо готовая клавиатура Vkbot.Keyboard либо нет клавиатуры (None).
            :param forward: Список сообщений Vkbot.Message для пересылки вместе с этим сообщением.
            :param reply: Одно сообщение Vkbot.Message, создаваемое сообщение будет отправлено в ответ (с ссылкой на reply сообщение).
            :param voice: Если True -> Сообщение будет отправляться в виде голосового, False -> в виде текстового.
            """
            super().__init__(owner_id, text, keyboard, forward, reply, attachments)
            self.reply: Vkbot.Message | None
            self.attachments: list[Vkbot.Attachment]
            self.keyboard: Vkbot.Keyboard | None
            self.forward_messages: list[Vkbot.Message]
            
            # Случайный идентификатор сообщения нужен для отправки сообщения, должен быть уникальным (не повторяться среди сообщений, отправляемых одному пользователю), иначе сообщение до пользователя не дойдёт
            self.random_id: int | None = None  # Устанавливается при отправке

            # Бот, который будет отправлять сообщение
            self.vkbot: VkApi
            self.set_vkbot(vkbot)
            
            self.kwargs: dict[str, str] = {}
        
        def get_bot_key(self) -> BOT_KEY:
            return "vkbot"
            
        def get_username(self) -> str | None:
            chat_id: int | None = self.get_chat_id()
            
            if chat_id is not None:
                return f"@id{chat_id}"
            else:
                return None
                

        def get_json_request(self, parse_mode: str = "") -> dict:
            """
            Формирует из сообщения JSON-словарь для отправки в vk_api.
            """
            format_data: str = ""
            text: str = self.get_text()
            
            if parse_mode:
                text, format_data = self.get_text_json()
            
            chat_id: int = self.get_chat_id()
            random_id: int = self.get_random_id()
            json_request: dict = {"user_id": chat_id, "message": text, "random_id": random_id}

            if format_data:
                json_request["format_data"] = format_data

            # Пересланные сообщения
            forward: dict = self.get_forward_json()

            # Ответ на сообщение
            reply: dict = self.get_reply_json()

            # Вложения
            attachments: dict = self.get_attachments_json()
            json_request.update(**attachments)
            
            # Кнопки
            keyboard: str = self.get_keyboard()

            if forward:
                json_request.update(**forward)
            elif reply:
                json_request.update(**reply)

            # Кнопки
            if keyboard:
                json_request.update(keyboard = self.get_keyboard_json())
            # print(f"KEYBOARD {keyboard=}")

            return json_request
        
        def send(self, chat_id: int, parse_mode: str = "") -> list[Vkbot.Message]:
            """
            Непосредственная отправка конечного текстового сообщения, вызывается только один раз!
            """
            self.kwargs = {
                "parse_mode": str(parse_mode)
            }
            
            # Сообщение может быть отправлено лишь единожды
            self.set_chat_id(chat_id)
            
            vkbot: VkApi = self.get_vkbot()

            # Формирование JSON
            json_request = self.get_json_request(parse_mode = parse_mode)
            
            try:
                # Отправка запроса
                response: int = vkbot.method("messages.send", json_request)
            except Exception as err:
                log_warn(f"Vkbot.Message.send {chat_id=} {err=}")
                return []

            # Распаковка ответа
            message_id: int = int(response)

            # Установка идентификатора сообщения после отправки
            self.set_id(message_id)
            
            self.set_changed(False)
            
            self.add_event(response, datetime.now(), self.__class__.SENT_KEY)

        def edit(self, prevent_resend: bool = False):
            """
            Непосредственное редактирование уже отправленного сообщения.
            :param prevent_resend: Не влияет на работу метода, нужно для унификации с `Telebot.Message.edit`.
            """
            if self.check_chat_id(self.chat_id):
                vkbot: VkApi = self.get_vkbot()
                message_id: int = self.get_id()
                chat_id: int = self.get_chat_id()

                json_request = self.get_json_request(**self.kwargs)
                json_request.update(peer_id = chat_id, message_id = message_id)

                if self.check_keyboard(self.keyboard) and not self.keyboard.check_editable():
                    raise ValueError(f"Некорректное значение атрибута {self.keyboard=}. Невозможно редактировать сообщение с не inline-клавиатурой. Удалите её прежде чем редактировать сообщение")

                self.set_changed(False)

                try:
                    response = vkbot.method("messages.edit", json_request)  # <class 'int'> 1
                except Exception as err:
                    log_warn(f"Vkbot.Message.edit {chat_id=} {message_id=} {err=}")
                    return
                # print(type(response), f"{response=}")
                self.add_event(response, datetime.now(), self.__class__.EDIT_KEY)
            else:
                raise ValueError(f"Некорректное значение атрибута {self.chat_id=}. Перед редактированием необходимо отправить сообщение.")
        
        def delete(self):
            """
            Удаление уже отправленного сообщения у пользователя.
            После удаления будет вновь доступна его отправка, но не редактирование.
            """
            vkbot: VkApi = self.get_vkbot()
            message_id: int = self.get_id()
            json_request: dict = {"message_ids": int(message_id), "delete_for_all": True}

            try:
                result: dict[str, int] = vkbot.method("messages.delete", json_request)  # <class 'dict'> {'34260': 1}
            except Exception as err:
                log_warn(f"Vkbot.Message.delete {message_id=} {err=}")
                return
            # print(f"{result=}")
            
            if result:
                if str(message_id) in result:
                    if result[str(message_id)] != 1:
                        log_warn(f"Не удалось удалить сообщение {message_id=}")
                        Debug.add_error(f"Не удалось удалить сообщение {message_id=}", [], Exception)

            self.add_event(result, datetime.now(), self.__class__.DELETE_KEY)
            self.id = None
            self.chat_id = None
            self.random_id = None

        def forward(self, chat_id: int, message: Vkbot.Message | None) -> Vkbot.Message:
            """
            Пересылает текущее сообщение в другой чат.
            :param message: Передайте сообщение для добавления комментария к пересылаемому сообщению, иначе сообщение будет переслано без комментариев.
            """
            vkbot: VkApi = self.get_vkbot()

            if message:
                message.set_forward([self])
            else:
                # WARNING: owner_id может отличаться
                message: Vkbot.Message = Vkbot.Message(vkbot, self.owner_id, Vkbot.Message.EMPTY_TEXT, forward = [self])

            message.send(chat_id)
            return message

        def reply(self, chat_id: int, message: Vkbot.Message):
            """
            Отправляет ответ на текущее сообщение.
            :param message: Передайте сообщение для добавления комментария ответу на сообщение, иначе ответ на сообщение будет без комментариев.
            """
            vkbot: VkApi = self.get_vkbot()
            message.set_reply(self)
            message.send(chat_id)

        
        # Методы работы с полями
        
        
        def check_vkbot(self, vkbot: VkApi) -> bool:
            return isinstance(vkbot, VkApi)

        def set_vkbot(self, vkbot: VkApi):
            if self.check_vkbot(vkbot):
                self.vkbot = vkbot
            else:
                raise ValueError(f"Некорректное значение аргумента {vkbot=}")

        def get_vkbot(self) -> VkApi:
            if self.check_vkbot(self.vkbot):
                return self.vkbot
            else:
                raise ValueError(f"Некорректное значение атрибута {self.vkbot=}")
        
        
        def set_random_id(self):
            """
            random_id устаналивается автоматически и только один раз для одного сообщения.
            """
            if self.random_id is None:
                self.random_id = get_random_id()
            else:
                raise ValueError(f"Поле self.random_id уже содержит значение и не может быть установлено повторно. Сообщение может быть отправлено только один раз.")

        def get_random_id(self) -> int | None:
            """
            Возвращает уникальный случайный идентификатор сообщения для его отправки.
            Если значение не было установлено, то сначала устанавливает значение, а затем возвращает его.
            Используйте `.get_chat_id() is not None` для проверки того, что сообщение уже было отправлено.
            """
            if self.random_id is None:
                self.set_random_id()
            return int(self.random_id)
        
        
        # Переопределённые методы работы с полями
        
        
        def check_id(self, message_id: int) -> bool:
            return isinstance(message_id, int)
        
        
        def get_text_json(self) -> tuple[str, str]:
            """
            Преобразует markdown-разметку в plain-текст и format_data для VK API.

            Поддерживаемые форматирования:
            ```
            - *жирный* → "bold"
            - _курсив_ → "italic"
            - ```код``` → "code"
            ```

            Возвращает кортеж из двух элементов:
            - `plain_text` — текст без символов форматирования (*, _, ```)
            - `format_data` — JSON-строка в готовом виде для отправки в vk_api.

            :param text: Текст с markdown-разметкой.

            :rtype: tuple[str, str]
            :return: (plain_text, format_data)
            """
            format_items: list[dict[str, str | int]] = []
            plain_text: str = self.get_text()

            # Улучшенные регулярные выражения
            bold_pattern: re.Pattern = re.compile(r'\*(?P<text>[^*]+)\*')
            italic_pattern: re.Pattern = re.compile(r'_(?P<text>[^_]+)_')
            code_pattern: re.Pattern = re.compile(r'```(?P<text>[^`]+)```')

            def extract_spans(pattern: re.Pattern, fmt_type: str, s: str) -> tuple[str, list[dict[str, str | int]]]:
                items: list[dict[str, str | int]] = []
                result: str = ""
                last_idx: int = 0

                for match in pattern.finditer(s):
                    start, end = match.span()
                    inner_text: str = match.group("text")

                    result += s[last_idx:start]
                    item_offset: int = len(result)
                    result += inner_text
                    item_length: int = len(inner_text)

                    items.append({
                        "offset": item_offset,
                        "length": item_length,
                        "type": fmt_type
                    })
                    last_idx = end

                result += s[last_idx:]
                return result, items

            # Измененный порядок обработки: сначала код, потом курсив, затем жирный
            plain_text, code_items = extract_spans(code_pattern, "code", plain_text)
            plain_text, italic_items = extract_spans(italic_pattern, "italic", plain_text)
            plain_text, bold_items = extract_spans(bold_pattern, "bold", plain_text)

            format_items = code_items + italic_items + bold_items
            format_items.sort(key=lambda x: x["offset"])

            format_data: dict[str, str | list[dict[str, str | int]]] = {
                "version": "1",
                "items": format_items
            }

            return plain_text, json.dumps(format_data)


        def check_reply(self, reply: Vkbot.Message) -> bool:
            return super().check_reply(reply)

        def set_reply(self, reply: Vkbot.Message | None):
            return super().set_reply(reply)

        def get_reply(self) -> Vkbot.Message | None:
            return super().get_reply()

        def get_reply_json(self) -> dict[str, int]:
            """
            Возвращает сообщение (в ответ на которое будет отправлено текущее) в готовом виде для отправки в vk_api.
            """
            if self.reply is None:
                return {}
            elif self.forward_messages:
                raise ValueError(f"Некорректное значение атрибута {self.forward_messages=}. Невозможно отвечать на сообщение, если уже включены пересланные сообщения")
            elif self.check_reply(self.reply):
                return {
                    "peer_id": self.reply.get_owner_id(),
                    "reply_to": self.reply.get_id()
                }
            else:
                raise ValueError(f"Некорректное значение атрибута {self.reply=}")
        

        def check_attachments(self, attachments: Iterable[Vkbot.Attachment]) -> bool:
            return super().check_attachments(attachments) and len(attachments) <= self.__class__.MAX_ATTACHMENTS

        def set_attachments(self, attachments: Iterable[Vkbot.Attachment]):
            return super().set_attachments(attachments)

        def get_attachments(self) -> list[Vkbot.Attachment]:
            return super().get_attachments()

        def get_attachments_json(self) -> dict[str, str]:
            """
            Возвращает вложения в готовом виде для отправки в vk_api.
            """
            if self.check_attachments(self.attachments):
                if self.attachments:
                    return {"attachment": ",".join(tuple(map(str, self.attachments)))}
                else:
                    return {}
            else:
                raise ValueError(f"Некорректное значение атрибута {self.attachments=}")
        

        def check_forward(self, forward: Iterable[Vkbot.Message]) -> bool:
            return super().check_forward(forward)

        def set_forward(self, forward: Iterable[Vkbot.Message]):
            return super().set_forward(forward)

        def get_forward(self) -> list[Vkbot.Message]:
            return super().get_forward()

        def get_forward_json(self) -> dict[str, int | str]:
            """
            Возвращает пересланные сообщения в готовом виде для отправки в vk_api.
            """
            if self.forward_messages == []:
                return {}
            elif self.check_forward(self.forward_messages):
                return {
                    "peer_id": self.forward_messages[0].get_owner_id(),
                    "forward_messages": ",".join(str(message.get_id()) for message in self.forward_messages)
                }
            else:
                raise ValueError(f"Некорректное значение атрибута {self.forward_messages=}")
        

        def check_keyboard(self, keyboard: Vkbot.Keyboard) -> bool:
            return super().check_keyboard(keyboard)
        
        def set_keyboard(self, keyboard: Vkbot.Keyboard | None):
            return super().set_keyboard(keyboard)
        
        def get_keyboard(self) -> Vkbot.Keyboard | None:
            return super().get_keyboard()

        def get_keyboard_json(self) -> str | Literal[""]:
            """
            Возвращает клавиатуру в готовом виде для отправки в vk_api.
            """
            if self.keyboard is None:
                return ""
            elif self.check_keyboard(self.keyboard):
                return self.keyboard.get_keyboard()
            else:
                raise ValueError(f"Некорректное значение атрибута {self.keyboard=}")
    
    
    class VoiceMessage(Bot.VoiceMessage):
        
        def __init__(self, vkbot: VkApi, owner_id: int, text: str, audio_attachment: Vkbot.AudioAttachment | None, reply: Bot.Message | None = None):
            """
            При создании сообщения указываются все поля кроме chat_id, message_id и random_id, они устанавливаются при отправке методом send.
            :param vkbot: Непосредственно бот, через который осуществляются запросы к API. Обязательно должен быть рабочим!
            :param owner_id: Идентификатор отправителя сообщения (сообщества или пользователя).
            :param text: Длина ограничена 4096 символами, текст может быть пустым.
            :param audio_attachment: Вложение аудио.
            :param reply: Одно сообщение Vkbot.Message, создаваемое сообщение будет отправлено в ответ (с ссылкой на reply сообщение).
            """
            super().__init__(owner_id, text, audio_attachment, reply)
            self.vkbot : VkApi
            self.set_vkbot(vkbot)
        
        def send(self, chat_id: int):
            raise VkbotException("Vkbot не поддерживает загрузку вложений кроме PhotoAttachment")

        
        # Методы работы с полями
        
        
        def check_vkbot(self, vkbot: VkApi) -> bool:
            return isinstance(vkbot, VkApi)

        def set_vkbot(self, vkbot: VkApi):
            if self.check_vkbot(vkbot):
                self.vkbot = vkbot
            else:
                raise ValueError(f"Некорректное значение аргумента {vkbot=}")

        def get_vkbot(self) -> VkApi:
            if self.check_vkbot(self.vkbot):
                return self.vkbot
            else:
                raise ValueError(f"Некорректное значение атрибута {self.vkbot=}")
        
        
        # Переопределённые методы работы с полями
        
        
        def check_audio_attachment(self, audio_attachment: Vkbot.AudioAttachment) -> bool:
            return isinstance(audio_attachment, Vkbot.AudioAttachment)

        def set_audio_attachment(self, audio_attachment: Vkbot.AudioAttachment | None):
            return super().set_audio_attachment(audio_attachment)
            
        def get_audio_attachment(self) -> Vkbot.AudioAttachment | None:
            return super().set_audio_attachment()
        
        
    def get_message_id(event: Bot.Event) -> int | None:
        for elem in event.events:
            if Vkbot.Message.check_id(None, elem):
                return int(elem)
        return None
    
    def __init__(self, token: str, name: str, group_id: int):
        """
        :param token: Токен доступа к API.
        :param name: Имя бота, уникально для одной платформы, например, `"@botname_bot"`. Два vkbot с одинаковым именем нельзя, vkbot и telebot с одинаковым именем можно.
        :param group_id: Идентификатор группы, в которой будет работать бот.
        """
        super().__init__(token, name, group_id)

        # Бот
        self.bot: VkApi

        # Загрузчик вложений
        self.upload: VkUpload

        self.initAPI()

        # Список загруженных вложений для предотвращения повторной загрузки
        self.attachments: dict[Vkbot.Attachment] = []

    def initAPI(self):
        """
        Инициализирует бота и загрузчика.
        Может быть вызван повторно для перезагрузки бота.
        """
        self.bot: VkApi = VkApi(token = self.token)
        self.upload: VkUpload = VkUpload(self.bot)
    
    def check_callback(self, event: Bot.Event) -> bool:
        if event.DEBUG_CALLBACK:
            return True
        
        for ev in event.events:
            if isinstance(ev, VkBotEvent) and not isinstance(ev, VkBotMessageEvent):
                return True
        
        return False
                    
    
    def split_buttons(self, buttons: Iterable[Keyboard.Button], max_width: int) -> list[Keyboard]:
        keyboards: list[Vkbot.Keyboard] = []
        
        while buttons:
            keyboard: Vkbot.Keyboard = self.__class__.Keyboard(buttons, max_width = max_width, inline = True)
            buttons = keyboard.get_unused_buttons()
            keyboards.append(keyboard)
        
        return keyboards
    
    def split(self, text: str, buttons: Iterable[Keyboard.Button], attachments: Iterable[Attachment], reply: Message | None, forward: Iterable[Message], max_width: int, inline: bool) -> list[Message]:
        attachments_groups: list[tuple[Vkbot.Attachment]] = self.split_attachments(attachments)
        texts: list[str] = self.split_text(text)
        keyboards: list[Vkbot.Keyboard] = self.split_buttons(buttons, max_width) if inline else [self.__class__.Keyboard(buttons, max_width = max_width, inline = inline)]
        messages: list[Vkbot.Message] = []
        
        for attachments in attachments_groups:
            message: Vkbot.Message = self.__class__.Message(self.bot, self.group_id, "", attachments = attachments)
            messages.append(message)
        
        for i, text in enumerate(texts):
            if i == 0 and messages:
                messages[-1].set_text(text)
            else:
                message: Vkbot.Message = self.__class__.Message(self.bot, self.group_id, text)
                messages.append(message)
        
        for i, keyboard in enumerate(keyboards):
            if i == 0 and messages:
                messages[-1].set_keyboard(keyboard)
            else:
                message: Vkbot.Message = self.__class__.Message(self.bot, self.group_id, self.__class__.Message.EMPTY_TEXT, keyboard = keyboard)
                messages.append(message)
        
        if forward:
            if messages:
                messages[0].set_forward(forward)
            else:
                message: Vkbot.Message = self.__class__.Message(self.bot, self.group_id, self.__class__.Message.EMPTY_TEXT, forward = forward)
                messages.append(message)
        elif reply:
            if messages:
                messages[0].set_reply(reply)
            else:
                message: Vkbot.Message = self.__class__.Message(self.bot, self.group_id, self.__class__.Message.EMPTY_TEXT, reply = reply)
                messages.append(message)
        
        return messages
    
    
    # Методы API
    
    
    def send(self, chat_id: int, text: str, buttons: Iterable[str] = [], filenames: Iterable[str] = [], compression: bool = True, inline: bool = True, max_width: int = 2, reply: Message | None = None, forward: Iterable[Message] = [], parse_mode: str = "") -> list[Message]:
        keyboard: Vkbot.Keyboard | None = None
        
        if buttons:
            keyboard = self.__class__.Keyboard(buttons, max_width = max_width, inline = inline)
        
        attachments: list[Vkbot.Attachment | Vkbot.PhotoAttachment | Vkbot.VideoAttachment | Vkbot.DocAttachment] = self.get_attachments(filenames, compression = compression)
        message: Vkbot.Message = Vkbot.Message(self.bot, self.group_id, text, keyboard, forward, reply, attachments)
        message.send(chat_id, parse_mode = parse_mode)
        return [message]
    
    def typing(self, chat_id: int):
        """
        На несколько секунд показывает "печатает..." в чате с пользователем
        Чтобы печатать непрерывно реализуйте цикл с вызовом метода раз в несколько секунд
        """
        self.bot.method("messages.setActivity", {"peer_id": chat_id, "type": "typing"})
    
    
    def get_attachment(self, filename: str, compression: bool = True) -> Vkbot.Attachment:
        """
        Возвращает вложение готовое для отправки.
        :param filename: Приводится к нормальному виду внутри метода.
        :param compression: Если compression=True -> attachment_type="photo" compression=False -> filename.jpg -> "doc".
        """
        if not self.get_bot_key:
            raise RuntimeError("Метод get_attachments доступен только для дочерних классов")
        
        def get_attachment_type(extension: str) -> Literal["photo", "video", "doc"]:
            """
            Возвращает тип вложения основываясь на указанном расширении файла
            Сопоставление расширений и типов вложений хранится в словаре EXTENSIONS
            :param extension: Обязательно в нижнем регистре и с точкой ".jpg"
            Иначе возвращает тип вложения по умолчанию, который хранится в DEFAULT_ATTACHMENT_TYPE
            """
            for attachment_type, extensions in self.__class__.Attachment.EXTENSIONS.items():
                if extension in extensions:
                    return attachment_type

            return self.__class__.Attachment.DEFAULT_ATTACHMENT_TYPE

        # Методы загрузки на сервер для разных типов вложений
        uploads: dict[str, Callable] = {
            "photo": self.__class__.PhotoAttachment.from_filename,
            "video": self.__class__.VideoAttachment.from_filename,
            "doc": self.__class__.DocAttachment.from_filename,
        }

        # Значение по умолчанию
        attachment_type: str = self.__class__.Attachment.DEFAULT_ATTACHMENT_TYPE

        # Значение по расширению файла только если загрузка со сжатием, без сжатия всегда "doc"
        if compression:
            extension: str = only_extension(filename).lower()
            attachment_type = get_attachment_type(extension)

        # Вызов соответствующего метода загрузки вложения
        attachment_type = str(attachment_type).lower()
        upload: Callable = uploads[attachment_type]
        attachment: Vkbot.Attachment = upload(filename, self)
        return attachment
        
    def get_attachments(self, filenames: Iterable[str], compression: bool = True) -> list[Vkbot.Attachment]:
        attachments: list[Vkbot.Attachment] = []
        
        for filename in filenames:
            attachment: Vkbot.Attachment = self.get_attachment(filename, compression)
            attachments.append(attachment)

        return attachments
    
    
    # Обработчики
    
    
    def extract_name(self, event: Bot.Event, chat_id: int) -> tuple[str, str]:
        first_name: str = ""
        last_name: str = ""

        try:
            vk = self.bot.get_api()
            user_info = vk.users.get(user_ids=chat_id, fields="first_name,last_name")[0]
            first_name = user_info["first_name"]
            last_name = user_info["last_name"]
            event.set_name(first_name, last_name)
        except Exception as err:
            log_warn(f"Ошибка при получении данных пользователя {chat_id=} {err=}")
        
        return (first_name, last_name)

    def parse_message(self, message: DotDict | dict, date: datetime, owner_id: int | None = None) -> Bot.Event:
        """
        Создаёт событие из сообщения, полученного из longpoll.
        """
        chat_id: int = get_int(message, -1, "from_id")
        _owner_id: int | None = owner_id
        owner_id: int = chat_id if owner_id is None else owner_id
        
        if chat_id < 0:
            # Только для reply_message и fwd_messages
            chat_id = get_int(message, -1, "peer_id")

        if chat_id < 0:
            raise ValueError(f"Некорректное значение словаря с ключом from_id или peer_id={repr(chat_id)}")
        
        self.add_id(chat_id)

        text: str = get_from(message, "text", types = (str,), default = "")
        date: datetime = get_date(message, "date")
        
        # reply
        reply: DotDict | None = get_from(message, "reply_message")
        reply_event: Bot.Event | None = None
        
        if reply:
            reply_event = self.parse_message(reply, date, _owner_id)
            reply_event.set_events([reply])
            
        # fwd_messages
        forward_events: list[Bot.Event] = []
        fwd_messages: list[dict] = get_from(message, "fwd_messages") or []
        
        for fwd in fwd_messages:
            fwd_date: datetime = get_date(fwd, "date")
            fwd_event: Bot.Event = self.parse_message(fwd, fwd_date, _owner_id)
            fwd_event.set_events([fwd])
            forward_events.append(fwd_event)

        # Обработка вложений
        attachments_list: list[dict | DotDict] = get_from(message, "attachments", types = (list,), default = [])
        attachments: list[Vkbot.Attachment] = []
        
        for attachment_data in attachments_list:
            attachment_type: Literal["photo", "video", "doc", "audio_message"] = attachment_data.type if "type" in dir(attachment_data) else attachment_data.get("type", None)
            attachment: Vkbot.PhotoAttachment | Vkbot.VideoAttachment | Vkbot.DocAttachment | Vkbot.AudioAttachment
            
            match attachment_type:
                case "photo":
                    attachment = self.__class__.PhotoAttachment(attachment_data)
                    attachments.append(attachment)
                case "video":
                    attachment = self.__class__.VideoAttachment(attachment_data)
                    attachments.append(attachment)
                case "doc":
                    attachment = self.__class__.DocAttachment(attachment_data)
                    attachments.append(attachment)
                case "audio_message":
                    attachment = self.__class__.AudioAttachment(attachment_data)
                    attachments.append(attachment)
                case _:
                    warn(f"Некорректное значение словаря с ключом type={repr(attachment_type)} во вложении сообщения")
                    continue
            

        event: Bot.Event = self.__class__.Event(owner_id, chat_id, text, date, attachments = attachments, reply = reply_event, forward = forward_events)
        event.set_events([message])
        self.extract_name(event, chat_id)
        return event
    
    
    def process_message(self, event: VkBotMessageEvent, date: datetime):
        """
        Обработчик событий от polling
        Определяет тип события и отправляет в соответствующий обработчик
        Примечание: голосовые и текстовые сообщения разделяются не здесь, а в parse_message
        """
        match event.type:
            case VkBotEventType.MESSAGE_NEW:
                ev: Bot.Event = self.parse_message(event.message, date)
                ev.set_events([event])
                return self.process_event(ev)
    
    
    def process_payload(self, event: VkBotEvent, date: datetime):
        match event.type:
            case VkBotEventType.MESSAGE_EVENT:
                payload: Any = get_from(event, "object", "payload")
                callback_data: str = ""
                
                if isinstance(payload, str):
                    callback_data = payload
                elif isinstance(payload, dict):
                    if "type" in payload:
                        callback_data = payload["type"]
                    else:
                        callback_data = json.dumps(event.object["payload"])
                elif payload:
                    callback_data = json.dumps(event.object["payload"])
                
                user_id: int = get_int(event, -1, "object", "peer_id")
                ev: Bot.Event = self.__class__.Event(user_id, user_id, callback_data, datetime.now())
                ev.set_events([event])
                self.extract_name(ev, user_id)
                return self.process_event(ev, combine_events = False)

    def polling(self, skip: float = 0, warning: bool = True):
        """
        Обработчик событий.
        Может быть вызван повторно, но предварительно остановите предыдущий обработчик.
        
        :param skip: Количество секунд, в течение которых бот не будет обрабатывать сообщения при запуске.
        Это нужно, чтобы не обрабатывать старые события, которые сервер отправляет при старте.
        
        :raises Exception: дублирует исключения, возникающие в vk_api кроме одной конкретной TypeError (см. ниже).
        """
        
        from_date: datetime = datetime.now()
        
        if skip > 0:
            from_date += timedelta(seconds = skip)
            
        def check():
            return skip <= 0 or datetime.now() >= from_date
        
        def show_warn():
            if warning:
                Console.warning("Пропущено событие", datetime.now())

        def polling():
            """
            Непосредственный обработчик событий
            """
            longpoll: VkBotLongPoll = VkBotLongPoll(self.bot, self.group_id)
            
            for event in longpoll.listen():
                event: VkBotEvent | VkBotMessageEvent = event
                
                if self.check_working():
                    if check():
                        message: DotDict | None = get_from(event, "message")
                        
                        if message:
                            date: datetime = get_date(message, "date")
                            # Обработка события в отдельном потоке
                            return self.process_message(event, date)
                        elif "object" in dir(event) and isinstance(event.object, DotDict) and "payload" in event.object:
                            return self.process_payload(event, datetime.now())
                    else:
                        show_warn()
                else:
                    return   # Выход из polling
                

        while self.check_working():
            try:
                polling() 
            # Перехват конкретной ошибки TypeError после удаления сообщения
            except TypeError as err:
                # После bot.method("messages.delete",{}) прилетает event и вместе с ним TypeError
                if not str(err) == "'<' not supported between instances of 'NoneType' and 'int'":
                    raise err
    
    
    # Переопределённые методы для работы с полями класса
    
    
    @classmethod
    def check_token(cls, token: str) -> bool:
        return super().check_token(token) and len(token) >= 220 and token.startswith("vk")
    
    def set_token(self, token: str):
        return super().set_token(token)

    def get_token(self) -> str:
        return super().get_token()


class Telebot(Bot):
    BOT_KEY: Literal["telebot"] = "telebot"
    URL: str = "http://t.me/"
    
    def check_event(event: TelebotMessage | CallbackQuery) -> bool:
        """
        Возвращает True, если это событие из telebot.
        """
        return isinstance(event, TelebotMessage) or isinstance(event, CallbackQuery)
    
    
    class Attachment(Bot.Attachment):
        ATTACHMENT_TYPE = dict[str, str | int]
        DEFAULT_ATTACHMENT_TYPE: type[InputMediaDocument] = InputMediaDocument
        
        EXTENSIONS: dict[type[InputMediaPhoto] | type[InputMediaVideo] | type[InputMediaDocument], tuple[str]] = {
            InputMediaPhoto: PHOTO_EXTENSIONS,
            InputMediaVideo: VIDEO_EXTENSIONS,
            InputMediaAudio: AUDIO_EXTENSIONS,
            InputMediaDocument: DOC_EXTENSIONS
        }
        
        def __init__(self, attachment: PhotoSize | Video | Document | Audio | Voice):
            super().__init__(attachment.file_id)
            self.id: str
            self.size: int = int((attachment.file_size if hasattr(attachment, "file_size") else None) or 0)
                        
        @abstractmethod
        def get_media_type(self) -> Never:
            raise NotImplementedError("Вместо Attachment используйте PhotoAttachment, VideoAttachment, AudioAttachment или DocumentAttachment")
            
        def dumps(self) -> ATTACHMENT_TYPE:
            result: "Telebot.Attachment.ATTACHMENT_TYPE" = super().dumps()
            
            result.update({
                "size": int(self.size)
            })
            
            return result
                
        def check(self) -> bool:
            return self.data is not None
                
        def get(self) -> BytesIO:
            if not self.check():
                raise ValueError(f"Некорректное значение атрибута {self.data=}. Перед получением необходимо загрузить файл методом download.")
            
            self.data.seek(0)
            return self.data
        
        def compare(self, attachment: Telebot.Attachment) -> bool:
            if self.filename or attachment.filename:
                return self.get_filename() == attachment.get_filename()
            elif self.id or attachment.id:
                return self.get_id() == attachment.get_id()
            elif self.data or attachment.data:
                return self.get() == attachment.get()
            else:
                # Два пустых вложения
                return True
                
        def download(self, telebot: Telebot) -> str:
            if self.data is not None:
                raise ValueError(f"Некорректное значение атрибута {self.data=}. Скачивание уже выполнено, повторное скачивание невозможно.")
                
            file_info: File = telebot.bot.get_file(self.id)
            response: Response = requests.get(f"https://api.telegram.org/file/bot{telebot.token}/{file_info.file_path}")
            response.raise_for_status()
            self.data = BytesIO(response.content)
            return file_info.file_path
        
        def make_filename(self, telebot: Telebot, folder: str) -> str:
            if self.filename:
                return self.get_filename()
            elif not self.data:
                filename: str = self.download(telebot)
                filename = create_filename(folder, filename)
            else:
                file_info: File = telebot.bot.get_file(self.id)
                filename = create_filename(folder, file_info.file_path)
            
            if not isdir(folder):
                makedirs(folder)
            
            # WARNING:
            if only_extension(filename).upper() in ".JPG":
                filename = change_extension(filename, ".jpeg")

            self.save_as(filename)
            self.set_filename(filename)
            return filename
            
        def load_from(self, filename: str):
            with open(filename, "rb") as file:
                self.data = BytesIO(file.read())
                self.data.seek(0)
        
        
        def check_id(self, attachment_id: str) -> bool:
            return isinstance(attachment_id, str)

        def set_id(self, attachment_id: str):
            if self.check_id(attachment_id):
                self.id = attachment_id
            else:
                raise ValueError(f"Некорректное значение аргумента {attachment_id=}")

        def get_id(self) -> str:
            if self.check_id(self.id):
                return self.id
            else:
                raise ValueError(f"Некорректное значение атрибута {self.id=}")
        
        
        def check(self) -> bool:
            return self.check_id(self.id) or self.check_filename(self.filename)

    
    class PhotoAttachment(Attachment):
        ATTACHMENT_TYPE = dict[str, str | int | list["Telebot.PhotoAttachment.ATTACHMENT_TYPE"]]
        
        def from_filename(filename: str) -> Telebot.PhotoAttachment:
            class Sentinel():
                file_id: Literal[""] = ""
                file_size: Literal[0] = 0
                width: Literal[0] = 0
                height: Literal[0] = 0
            
            attachment: Telebot.PhotoAttachment = Telebot.PhotoAttachment(Sentinel)
            attachment.set_filename(filename)
            Console.success("uploaded", filename, "to")
            return attachment
        
        def from_bytes(data: BytesIO) -> Telebot.PhotoAttachment:
            class Sentinel():
                file_id: Literal[""] = ""
                file_size: Literal[0] = 0
                width: Literal[0] = 0
                height: Literal[0] = 0

            attachment: Telebot.PhotoAttachment = Telebot.PhotoAttachment(Sentinel)
            attachment.data = data
            return attachment
        
        def loads(data: ATTACHMENT_TYPE) -> Telebot.PhotoAttachment:
            class Sentinel():
                
                def __init__(self, data: dict[str, str | int]):
                    self.file_id: str = get_from(data, "id")
                    self.size: int = get_int(data, -1, "size")
                    self.width: int = get_int(data, -1, "width")
                    self.height: int = get_int(data, -1, "height")
            
            filename: str = get_from(data, "filename")
            
            attachments_list: list[dict[str, str | int]] = get_from(data, "attachments")
            attachments: list[Sentinel] = [Sentinel(attachment) for attachment in attachments_list]
            
            sentinel = Sentinel(data)
            attachment: Telebot.PhotoAttachment = Telebot.PhotoAttachment(sentinel, attachments)
            if filename:
                attachment.set_filename(filename)
            return attachment

        def __init__(self, attachment: PhotoSize, sizes: Iterable[PhotoSize] = []):
            super().__init__(attachment)
            self.width: int = int(attachment.width)
            self.height: int = int(attachment.height)
            self.attachments: list[Telebot.PhotoAttachment] = []
            
            for photo in sizes:
                attachment: Telebot.PhotoAttachment = self.__class__(photo)
                self.attachments.append(attachment)
            
            """
            saved_files['photo']: int = file_id
            bot.send_photo(message.chat.id, saved_files['photo'], caption="Вот ваше сохраненное фот
            """
        
        def get_media_type(self) -> type[InputMediaPhoto]:
            return InputMediaPhoto

        def dumps(self) -> ATTACHMENT_TYPE:
            result: "Telebot.PhotoAttachment.ATTACHMENT_TYPE" = super().dumps()
            
            result.update({
                "width": int(self.width),
                "height": int(self.height),
                "attachments": [attachment.dumps() for attachment in self.attachments]
            })

            return result
                
        def get_image(self) -> Image:
            if not self.check():
                raise ValueError(f"Некорректное значение атрибута {self.data=}. Перед получением необходимо загрузить файл методом download.")
                
            self.data.seek(0)
            return Image.open(self.data)
                
        def save_as(self, filename: str, img_format: Literal["jpeg", "jpg", "png", "bmp", "gif"] = ""):
            if not self.check():
                raise ValueError(f"Некорректное значение атрибута {self.data=}. Перед сохранением необходимо загрузить файл методом download.")
            
            if not img_format:
                extension: str = only_extension(filename).lower()
                
                if extension in (".jpeg", ".jpg", ".png", ".bmp", ".gif"):
                    img_format = extension[1:]
                else:
                    img_format = ".jpeg"
            
            if img_format not in ("jpeg", "jpg", "png", "bmp", "gif"):
                raise ValueError(f"Некорректное значение аргумента {img_format=}. Поддерживаются только форматы jpeg, jpg, png, bmp и gif.")

            self.data.seek(0)
            
            with Image.open(self.data) as img:
                img.save(filename, format = img_format)
            
        def load_from(self, filename: str):
            with Image.open(filename) as img:
                self.data = BytesIO()
                img.save(self.data, format = img.format)
                self.data.seek(0)
    
    
    class VideoAttachment(Attachment):
        ATTACHMENT_TYPE = dict[str, Union[str, int, None, "Telebot.PhotoAttachment.ATTACHMENT_TYPE"]]

        def from_filename(filename: str) -> Telebot.VideoAttachment:
            class Sentinel():
                file_id: Literal[""] = ""
                file_size: Literal[0] = 0
                width: Literal[0] = 0
                height: Literal[0] = 0
                duration: Literal[0] = 0
                thumb: None = None
            
            attachment: Telebot.VideoAttachment = Telebot.VideoAttachment(Sentinel)
            attachment.set_filename(filename)
            return attachment
        
        def from_bytes(data: BytesIO) -> Telebot.VideoAttachment:
            class Sentinel():
                file_id: Literal[""] = ""
                file_size: Literal[0] = 0
                width: Literal[0] = 0
                height: Literal[0] = 0
                duration: Literal[0] = 0
                thumb: Literal[None] = None

            attachment: Telebot.VideoAttachment = Telebot.VideoAttachment(Sentinel)
            attachment.data = data
            return attachment

        def loads(data: ATTACHMENT_TYPE) -> Telebot.VideoAttachment:
            attachment: "Telebot.VideoAttachment.ATTACHMENT_TYPE" = get_from(data, "attachment")
            
            class SentinelThumb():
                file_id: str = get_from(attachment, "id")
                size: int = get_int(attachment, -1, "size")
                width: int = get_int(attachment, -1, "width")
                height: int = get_int(attachment, -1, "height")
            
            class Sentinel():
                file_id: str = get_from(data, "id")
                size: int = get_int(data, -1, "size")
                width: int = get_int(data, -1, "width")
                height: int = get_int(data, -1, "height")
                duration: int = get_int(data, -1, "height")
                thumb: SentinelThumb = SentinelThumb
            
            filename: str = get_from(data, "filename")
            
            attachment: Telebot.VideoAttachment = Telebot.VideoAttachment(Sentinel)
            if filename:
                attachment.set_filename(filename)
            return attachment

        def __init__(self, attachment: Video):
            super().__init__(attachment)
            self.width: int = int(attachment.width)
            self.height: int = int(attachment.height)
            self.duration: int = int(attachment.duration)
            self.thumb: Telebot.PhotoAttachment | None = None
            
            thumb: PhotoSize | None = attachment.thumb
            if thumb is None or isinstance(thumb, PhotoSize):
                if thumb:
                    self.attachment = Telebot.PhotoAttachment(thumb)
            
        def get_media_type(self) -> type[InputMediaVideo]:
            return InputMediaVideo

        def dumps(self) -> ATTACHMENT_TYPE:
            result: "Telebot.VideoAttachment.ATTACHMENT_TYPE" = super().dumps()
            
            result.update({
                "width": int(self.width),
                "height": int(self.height),
                "duration": int(self.duration),
                "attachment": self.attachment.dumps() if self.attachment is not None else None
            })

            return result
                
        def get_video(self, temp_filename: str) -> VideoCapture:
            if not self.check():
                raise ValueError(f"Некорректное значение атрибута {self.data=}. Перед получением необходимо загрузить файл методом download.")
            
            self.data.seek(0)
            with open(temp_filename, "wb") as file:
                file.write(self.data.read())
            
            return VideoCapture(temp_filename)  # .isOpened()
    
    
    class DocAttachment(Attachment):
        ATTACHMENT_TYPE = dict[str, Union[str, None, "Telebot.PhotoAttachment.ATTACHMENT_TYPE"]]

        def from_filename(filename: str) -> Telebot.DocAttachment:
            class Sentinel():
                file_id: Literal[""] = ""
                file_size: Literal[0] = 0
                file_name: Literal[None] = None
                thumb: Literal[None] = None
            
            attachment: Telebot.DocAttachment = Telebot.DocAttachment(Sentinel)
            attachment.set_filename(filename)
            return attachment
        
        def from_bytes(data: BytesIO) -> Telebot.DocAttachment:
            class Sentinel():
                file_id: Literal[""] = ""
                file_size: Literal[0] = 0
                file_name: Literal[None] = None
                thumb: Literal[None] = None

            attachment: Telebot.DocAttachment = Telebot.DocAttachment(Sentinel)
            attachment.data = data
            return attachment

        def loads(data: ATTACHMENT_TYPE) -> Telebot.DocAttachment:
            attachment: "Telebot.DocAttachment.ATTACHMENT_TYPE" = get_from(data, "attachment")
            
            class SentinelThumb():
                file_id: str = get_from(attachment, "id")
                id: str = get_from(attachment, "id")
                size: int = get_int(attachment, -1, "size")
                width: int = get_int(attachment, -1, "width")
                height: int = get_int(attachment, -1, "height")
            
            class Sentinel():
                file_id: str = get_from(data, "id")
                id: str = get_from(data, "id")
                size: int = get_int(data, -1, "size")
                file_name: str = get_from(data, "original_filename")
                thumb: SentinelThumb = SentinelThumb
            
            filename: str = get_from(data, "filename")
            
            attachment: Telebot.DocAttachment = Telebot.DocAttachment(Sentinel)
            if filename:
                attachment.set_filename(filename)
            return attachment

        def __init__(self, attachment: Document):
            super().__init__(attachment)
            self.original_filename: str = attachment.file_name or ""
            self.attachment: Telebot.PhotoAttachment | None = None
            
            thumb: PhotoSize | None = attachment.thumb
            if thumb is None or isinstance(thumb, PhotoSize):
                if thumb:
                    self.attachment = Telebot.PhotoAttachment(thumb)
            
        def get_media_type(self) -> type[InputMediaDocument]:
            return InputMediaDocument

        def dumps(self) -> ATTACHMENT_TYPE:
            result: "Telebot.DocAttachment.ATTACHMENT_TYPE" = super().dumps()
            
            result.update({
                "original_filename": str(self.original_filename),
                "attachment": self.attachment.dumps() if self.attachment is not None else None
            })

            return result
    
    
    class AudioAttachment(Attachment):
        """
        Общий класс для вложений аудио и голоса.
        """
        ATTACHMENT_TYPE = dict[str, Union[str, int, None, "Telebot.PhotoAttachment.ATTACHMENT_TYPE"]]

        def from_filename(filename: str) -> Telebot.AudioAttachment:
            class Sentinel():
                file_id: Literal[""] = ""
                file_size: Literal[0] = 0
                duration: Literal[0] = 0
            
            attachment: Telebot.AudioAttachment = Telebot.AudioAttachment(Sentinel)
            attachment.set_filename(filename)
            return attachment
        
        def from_bytes(data: BytesIO) -> Telebot.AudioAttachment:
            class Sentinel():
                file_id: Literal[""] = ""
                file_size: Literal[0] = 0
                duration: Literal[0] = 0

            attachment: Telebot.AudioAttachment = Telebot.AudioAttachment(Sentinel)
            attachment.data = data
            return attachment

        def loads(data: ATTACHMENT_TYPE) -> Telebot.AudioAttachment:
            attachment: "Telebot.AudioAttachment.ATTACHMENT_TYPE" = get_from(data, "attachment", default = None)
            
            if attachment:
                class SentinelThumb():
                    file_id: str = get_from(attachment, "id")
                    size: int = get_int(attachment, -1, "size")
                    width: int = get_int(attachment, -1, "width")
                    height: int = get_int(attachment, -1, "height")
            else:
                SentinelThumb = None
            
            class Sentinel():
                file_id: str = get_from(data, "id")
                size: int = get_int(data, -1, "size")
                text: str = get_from(data, "text")
                duration: int = get_int(data, -1, "height")
                title: str = get_from(data, "title", default = "")
                file_name: str = get_from(data, "original_filename", default = "")
                thumbnail: SentinelThumb | None = SentinelThumb
            
            filename: str = get_from(data, "filename")
            
            attachment: Telebot.AudioAttachment = Telebot.AudioAttachment(Sentinel)
            if filename:
                attachment.set_filename(filename)
            return attachment

        def __init__(self, attachment: Voice | Audio):
            super().__init__(attachment)
            self.text: str = ""
            self.duration: int = int(attachment.duration)
            
            # Уникальные поля Audio
            
            self.title: str = getattr(attachment, "title", "")
            self.original_filename: str = getattr(attachment, "file_name", "")
            self.attachment: Telebot.PhotoAttachment | None = None
            
            thumbnail: PhotoSize | None = getattr(attachment, "thumbnail", None)
            if thumbnail is None or isinstance(thumbnail, PhotoSize):
                if thumbnail:
                    self.attachment = Telebot.PhotoAttachment(thumbnail)
            
        def get_media_type(self) -> type[InputMediaAudio]:
            return InputMediaAudio

        def dumps(self) -> ATTACHMENT_TYPE:
            result: "Telebot.AudioAttachment.ATTACHMENT_TYPE" = super().dumps()
            
            # Voice | Audio
            result.update({
                "text": str(self.text),
                "duration": int(self.duration)
            })
            
            # Audio
            if self.title or self.original_filename or self.attachment:
                result.update({
                    "original_filename": str(self.original_filename),
                    "title": str(self.title),
                    "attachment": self.attachment.dumps() if self.attachment is not None else None
                })

            return result

        def download(self, telebot: Telebot) -> str:
            if self.check():
                raise ValueError(f"Некорректное значение атрибута {self.data=}. Скачивание уже выполнено, повторное скачивание невозможно.")
            
            file_info: File = telebot.bot.get_file(self.id)
            response: Response = requests.get(f"https://api.telegram.org/file/bot{telebot.token}/{file_info.file_path}")
            response.raise_for_status()

            extension: Literal[".wav", ".mp3", ".ogg", ".oga"] = only_extension(file_info.file_path).lower()
            
            if extension == "." or not extension:
                extension = ".ogg"
            
            audio_format: Literal["wav", "mp3", "ogg"] = "ogg"
            
            if extension in (".wav", ".mp3", ".ogg"):
                audio_format = extension[1:]
            
            sound = AudioSegment.from_file(BytesIO(response.content), format = audio_format)
            self.data = BytesIO()
            sound.export(self.data, format = "wav")
            self.data.seek(0)
            return file_info.file_path

        def recognize(self) -> str | Literal[""]:
            if not self.check():
                raise ValueError(f"Некорректное значение атрибута {self.data=}. Перед сохранением необходимо загрузить файл методом download.")
            
            self.data.seek(0)  # Перемещаем указатель в начало файла
            recognized: Any | str = ""
            rec: Recognizer = Recognizer()
            
            with WavFile(self.data) as source:
                audio = rec.record(source)
                try:
                    # language="ru" не мешает распознавать английскую речь
                    recognized = rec.recognize_google(audio, language = "ru-RU").lower()
                except LookupError as err:
                    recognized = err
                
            if isinstance(recognized, str) and recognized:
                return recognized
            else:
                return ""
                

        def save_as(self, filename: str, audio_format: Literal["wav", "mp3", "ogg"] = ""):
            if not self.check():
                raise ValueError(f"Некорректное значение атрибута {self.data=}. Перед сохранением необходимо загрузить файл методом download.")
            
            self.data.seek(0)
            sound = AudioSegment.from_wav(self.data)
            
            if not audio_format:
                extension: Literal[".wav", ".mp3", ".ogg"] = only_extension(filename).lower()
            
                if extension == "." or not extension:
                    extension = ".mp3"
                elif extension not in (".wav", ".mp3", ".ogg"):
                    extension = ".mp3"
                
                audio_format = extension[1:]
            
            sound = AudioSegment.from_wav(self.data)
            sound.export(filename, format = audio_format)

        def load_from(self, filename: str):
            if not self.check():
                raise ValueError(f"Некорректное значение атрибута {self.data=}. Поле уже содержит данные, повторная загрузка невозможна.")
            
            extension: Literal[".wav", ".mp3", ".ogg"] = only_extension(filename).lower()
            
            if extension == "." or not extension:
                extension = ".mp3"
            
            if extension not in (".wav", ".mp3", ".ogg"):
                raise ValueError(f"Некорректное значение аргумента {filename=}. Поддерживаются только форматы wav, mp3 и ogg.")
            
            sound = AudioSegment.from_file(filename, format = extension[1:])
            self.data = BytesIO()
            sound.export(self.data, format = "wav")
            self.data.seek(0)  # Перемещаем указатель в начало файла
        
        
        def check_text(self, text: str) -> bool:
            return isinstance(text, str)

        def set_text(self, text: str):
            if self.check_text(text):
                self.text = text
            else:
                raise ValueError(f"Некорректное значение аргумента {text=}")

        def get_text(self) -> str:
            if self.check_text(self.text):
                return self.text
            else:
                raise ValueError(f"Некорректное значение атрибута {self.text=}")
    
    
    class Keyboard(Bot.Keyboard):
        """
        Может использоваться повторно.
        """
                
        class Button(Bot.Keyboard.Button):
            BUTTON_TYPE = dict[str, str]

            def loads(data: BUTTON_TYPE) -> Telebot.Keyboard.Button:
                text: str = get_from(data, "text")
                callback_data: str = get_from(data, "callback_data")
                url: str = get_from(data, "url")
                return Telebot.Keyboard.Button(text, callback_data = callback_data, url = url)
            
            def __init__(self, text: str, callback_data: str | None = None, url: str | None = None):
                """
                :param text: Обязательно не пустой текст.
                :param url: По нажатию на кнопку будет открываться указанная ссылка, не совместимо с callback_data.
                :param callback_data: Если указано, то кнопка вместо text по нажатию вернёт указанное значение, не совместимо с url.
                """
                super().__init__(text, callback_data = callback_data, url = url)
                
            def dumps(self) -> BUTTON_TYPE:
                return {
                    "text": self.get_text(),
                    "type": self.get_type(),
                    **self.get_kwarg()
                }
            
            def get_kwarg(self) -> dict[str, str]:
                """
                Возвращает тип кнопки и содержимое для передачи в API создания кнопки.
                """
                match self.get_type():
                    case "url":
                        return {"url": self.url}
                    case "callback_data":
                        return {"callback_data": self.callback_data}
                    case _:
                        return {"callback_data": self.get_text()}
            
            def set_color(self, color: Literal[0, 1, 2, 3] | str | VkKeyboardColor):
                pass
        
        
        def loads(data: "Telebot.Keyboard.KEYBOARD_TYPE") -> Telebot.Keyboard:
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
            :param buttons: Длина больше 50 не тестировалась.
            :param max_width: Максимальная ширина клавиатуры (количество кнопок в одном ряду).
            :param inline: Если True -> клавиатура, прикреплённая к сообщению, False -> кнопки под клавиатурой.
            """
            super().__init__(buttons, inline = inline, max_width = max_width)
            
            # Поле с клавиатурой
            self.keyboard: InlineKeyboardMarkup | ReplyKeyboardMarkup = None

            self.update(buttons)
        
        def update(self, buttons: Iterable[str | Telebot.Keyboard.Button]):
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
            Ограничения telebot не тестировались, поэтому метод всегда возвращает пустой список (все кнопки были использованы).
            """
            return []

        def get_keyboard(self) -> str:
            """
            Возвращает клавиатуру в том виде, в котором она отправляется в API.
            """
            if isinstance(self.keyboard, InlineKeyboardMarkup | ReplyKeyboardMarkup):
                return self.keyboard
            else:
                raise TypeError()
    
    
    class Message(Bot.Message):
        """
        Хранит информацию об одном сообщении для telebot (один блок)
        """

        # Максимальное количество вложений в одном сообщении
        MAX_ATTACHMENTS: int = 1
        
        @classmethod
        def from_event(cls: type[Telebot.Message], event: Bot.Event, bot: TeleBot):
            message: Telebot.Message = super().from_event(event, bot)
            message_id: int | None = Telebot.get_message_id(event)
            message.set_id(message_id) if message_id is not None else None
            message.set_chat_id(event.chat_id)
            return message

        def __init__(self, telebot: TeleBot, owner_id: int, text: str, keyboard: Telebot.Keyboard | None = None, forward: Iterable[Telebot.Message] = [], reply: Telebot.Message | None = None, attachments: Iterable[Telebot.Attachment] = []):
            """
            При создании сообщения указываются все поля кроме chat_id, message_id и random_id, они устанавливаются при отправке методом send.
            :param telebot: Непосредственно бот, через который осуществляются запросы к API. Обязательно должен быть рабочим!
            :param owner_id: Идентификатор отправителя сообщения (сообщества или пользователя).
            :param text: Длина ограничена 4096 символами, текст может быть пустым.
            :param keyboard: Либо готовая клавиатура Telebot.Keyboard либо нет клавиатуры (None).
            :param forward: Список сообщений Telebot.Message для пересылки вместе с этим сообщением.
            :param reply: Одно сообщение Telebot.Message, создаваемое сообщение будет отправлено в ответ (с ссылкой на reply сообщение).
            :param voice: Если True -> Сообщение будет отправляться в виде голосового, False -> в виде текстового.
            """
            super().__init__(owner_id, text, keyboard, forward, reply, attachments)
            self.attachments: Telebot[Telebot.Attachment]
            self.reply: Telebot.Message | None
            self.keyboard: Telebot.Keyboard | None
            self.forward_messages: list[Telebot.Message]

            # Бот, который будет отправлять сообщение
            self.telebot: TeleBot
            self.set_telebot(telebot)
            
            self.kwargs: dict[str, str | bool | int | None] = {}
        
        def get_username(self) -> str | None:
            for event in self.events[self.__class__.CREATE_KEY]:
                for ev in event.get_events():
                    return ev.from_user.username
            return None
        
        def get_bot_key(self) -> BOT_KEY:
            return "telebot"
        
        def send(self, chat_id: int, parse_mode: str = "", forward_after: bool = False, single_caption: bool = True, has_spoiler: bool = False, show_caption_above_media: bool = False, disable_notification: bool | None = None, protect_content: bool | None = None, reply_to_message_id: int | None = None, timeout: int | None = None, allow_sending_without_reply: bool | None = None, message_thread_id: int | None = None, business_connection_id: str | None = None, message_effect_id: str | None = None, allow_paid_broadcast: bool | None = None) -> dict[str, list[TelebotMessage]]:
            """
            Непосредственная отправка конечного сообщения, вызывается только один раз!
            :param forward_after: Если сообщение содержит пересылаемые, то они будут отправлены перед текущим (если `True`) или после текущего (если `False`).
            :param single_caption: Если сообщение содержит вложения, то текст сообщения будет добавлен только к первому вложению (если `True`) или ко всем (если `False`).
            """
            # here
            # return {}

            # Сообщение может быть отправлено лишь единожды
            self.set_chat_id(chat_id)

            telebot: TeleBot = self.get_telebot()
            
            self.kwargs = {
                "parse_mode": str(parse_mode) if parse_mode is not None else None,
                "forward_after": bool(forward_after) if forward_after is not None else None,
                "single_caption": bool(single_caption) if single_caption is not None else None,
                "has_spoiler": bool(has_spoiler) if has_spoiler is not None else None,
                "show_caption_above_media": bool(show_caption_above_media) if show_caption_above_media is not None else None,
                "disable_notification": bool(disable_notification) if disable_notification is not None else None,
                "protect_content": bool(protect_content) if protect_content is not None else None,
                "reply_to_message_id": int(reply_to_message_id) if reply_to_message_id is not None else None,
                "timeout": int(timeout) if timeout is not None else None,
                "allow_sending_without_reply": bool(allow_sending_without_reply) if allow_sending_without_reply is not None else None,
                "message_thread_id": int(message_thread_id) if message_thread_id is not None else None,
                "business_connection_id": str(business_connection_id) if business_connection_id is not None else None,
                "message_effect_id": str(message_effect_id) if message_effect_id is not None else None,
                "allow_paid_broadcast": bool(allow_paid_broadcast) if allow_paid_broadcast is not None else None,
            }
            
            kwargs: dict[str, str] = {
                key: value for key, value in {
                    "disable_notification": disable_notification,
                    "protect_content": protect_content,
                    "reply_to_message_id": reply_to_message_id,
                    "timeout": timeout,
                    "allow_sending_without_reply": allow_sending_without_reply,
                    "message_thread_id": message_thread_id,
                    "business_connection_id": business_connection_id,
                    "message_effect_id": message_effect_id,
                    "allow_paid_broadcast": allow_paid_broadcast
                }.items() if value is not None
            }

            if parse_mode:
                kwargs["parse_mode"] = parse_mode
                
            if self.keyboard:
                kwargs["reply_markup"] = self.keyboard.get_keyboard()
            # print(f"KEYBOARD {kwargs.get('reply_markup')=}")
            
            # Вложения
            filenames: list[str] = []
            attachments: list[Telebot.Attachment] = self.get_attachments()
            responses: list[TelebotMessage] = []
            forward_responses: list[TelebotMessage] = []
            attachments_responses: list[TelebotMessage] = []
            
            if self.keyboard and attachments:
                raise TelebotException("Telebot не поддерживает отправку вложений вместе с клавиатурой")
            
            if not forward_after:
                # Отправка пересланных сообщений
                for message in self.get_forward():
                    response: TelebotMessage = message.forward(chat_id)
                    forward_responses.append(response)
            
            # В ответ на сообщение
            reply: Telebot.Message | None = self.get_reply()
            
            # if self.text == "Некорректный ответ":
            #     if Debug.flag:
            #         Debug.flag = False
            #     else:
            #         raise Exception()

            # Отправка этого сообщения
            if attachments:
                files: list[BufferedReader] = []
                media_group: list[InputMediaPhoto | InputMediaVideo | InputMediaAudio | InputMediaDocument] = []
                text: str = self.get_text(parse_mode)
                
                for attachment in attachments:
                    media_type: type[InputMediaPhoto | InputMediaVideo | InputMediaAudio | InputMediaDocument] = attachment.get_media_type()
                    content: str | BufferedReader | BytesIO
                    file_id: str = attachment.get_id()
                    
                    if file_id:
                        # Вложение уже на серверах Telegram - берём file_id
                        content = file_id
                        
                        # У значений под ключами filenames и attachments в результирующем словаре должна быть одинаковая длина (один response соответствует одному имени файла)
                        filenames.append("")
                    elif attachment.check_filename(attachment.filename):
                        # Файл ещё не загружен на сервера - открываем файл и не забываем закрыть
                        filename: str = attachment.get_filename()
                        content = open(filename, "rb")
                        files.append(content)
                        filenames.append(filename)
                    else:
                        # У вложения нет файла, но его можно передать и байтами
                        content = attachment.get()
                        
                        # У значений под ключами filenames и attachments в результирующем словаре должна быть одинаковая длина (один response соответствует одному имени файла)
                        filenames.append("")
                        
                    caption: dict[str, str] = {}
                    
                    if text:
                        caption["caption"] = cut(text, Bot.Message.MAX_LENGTH)

                    if single_caption:
                        text = ""
                        
                    media: InputMediaPhoto | InputMediaVideo | InputMediaAudio | InputMediaDocument = media_type(
                        content, **caption)
                    media_group.append(media)
                
                if reply:
                    kwargs["reply_to_message_id"] = reply.get_id()
                
                if "parse_mode" in kwargs:
                    del kwargs["parse_mode"]

                try:
                    attachments_responses = telebot.send_media_group(self.get_chat_id(), media_group, **kwargs)
                except Exception as err:
                    log_warn(f"Telebot.Message.send send_media_group {chat_id=} {err=}")
                    attachments_responses = []
                
                for file in files:
                    file.close()

            elif reply:
                try:
                    response: TelebotMessage = telebot.reply_to(self.get_chat_id(), self.get_text(parse_mode), **kwargs)
                except Exception as err:
                    log_warn(f"Telebot.Message.send reply_to {chat_id=} {err=}")
                    responses = []
                else:
                    responses = [response]
            else:
                try:
                    response: TelebotMessage = telebot.send_message(self.get_chat_id(), self.get_text(parse_mode), **kwargs)
                except Exception:
                    try:
                        response: TelebotMessage = telebot.send_message(self.get_chat_id(), self.get_text(parse_mode).replace("_", ""), **kwargs)
                    except Exception as err:
                        log_warn(f"Telebot.Message.send send_message {chat_id=} {err=}")
                        responses = []
                    else:
                        responses = [response]
                else:
                    responses = [response]
            
            if forward_after:
                # Отправка пересланных сообщений
                for message in self.get_forward():
                    response: TelebotMessage = message.forward(chat_id)

                    if response:
                        forward_responses.append(response)
            
            if len(responses) == 1:
                response: TelebotMessage = responses[0]
                message_id: int = int(response.message_id)
                self.set_id(message_id)
            else:
                self.id = None
                
            for response in responses:
                event: Bot.Event = Bot.Event(self.get_owner_id(), chat_id, "", datetime.now())
                event.set_events([response])
                self.add_event(event, datetime.fromtimestamp(response.date), self.__class__.SENT_KEY)
            
            self.set_chat_id(chat_id)
            self.set_changed(False)
            
            if len(filenames) != len(attachments_responses):
                log_warn("По неизвестной причине Telegram API количество ответов не соответствует количеству указанных вложений. Это приведёт к исключению в Telebot.parse_responses")
            
            return {
                "attachments": attachments_responses,
                "filenames": filenames,
                "forward": forward_responses
            }
        
        deleted: dict[int, list[int]] = {}
        
        def add_deleted(self, chat_id: int, message_id: int):
            if chat_id in self.__class__.deleted:
                self.__class__.deleted[chat_id].append(message_id)
            else:
                self.__class__.deleted[chat_id] = [message_id]
        
        def check_deleted(self, chat_id: int, message_id: int):
            return message_id in self.__class__.deleted.get(chat_id, [])

        def delete(self):
            """
            Удаляет сообщение у пользователя, что позволяет отправить его заново.
            """
            telebot: TeleBot = self.get_telebot()
            chat_id: int = self.get_chat_id()
            message_id: int = self.get_id()
            
            if self.check_deleted(chat_id, message_id):
                raise ValueError(f"Некорректное значение атрибута {self.id=}. Невозможно повторно удалить сообщение.")
            
            if self.check_chat_id(chat_id) and self.check_id(message_id):
                try:
                    response: bool = telebot.delete_message(chat_id = chat_id, message_id = message_id)
                except Exception as err:
                    log_warn(f"Telebot.Message.delete {chat_id=} {message_id=} {err=}")
                    response = err
            else:
                response = ValueError(f"Некорректное значение атрибута {self.chat_id=} или {self.id=}. Перед удалением необходимо отправить сообщение.")
                raise response

            # print(f"delete {chat_id=} {message_id=} {response=}")
            self.add_deleted(chat_id, message_id)
            self.add_event(response, datetime.now(), self.__class__.DELETE_KEY)
            self.id = None
            self.chat_id = None
            
            chat_id: int = self.get_chat_id()
            message_id: int = self.get_id()
        
        def edit(self, prevent_resend: bool = False) -> dict[str, TelebotMessage]:
            # self.telebot.edit_message_text(chat_id = self.get_chat_id(),message_id = self.get_message_id(),text = self.get_text())
            if self.check_chat_id(self.chat_id) and not self.check_id(self.id):
                raise ValueError(f"Некорректное значение атрибута {self.id=}. Используйте экземпляры из результатов вызова метода Telebot.parse_responses(message, responses).")
            elif self.check_editable():
                if prevent_resend:
                    # print(f"prevent_resend!")
                    return {}
                else:
                    chat_id: int = self.get_chat_id()
                    message_id: int | None = self.id
                    self.delete()
                    return self.send(chat_id, **self.kwargs)
            else:
                raise ValueError(f"Некорректное значение атрибута {self.id=} или {self.chat_id=}. Перед редактированием необходимо отправить сообщение.")

        def forward(self, chat_id: int) -> TelebotMessage | None:
            """
            Пересылает это сообщение в указанный чат.
            """
            telebot: TeleBot = self.get_telebot()
            from_chat_id: int = self.get_chat_id()
            message_id: int = self.get_id()
            try:
                response: TelebotMessage = telebot.forward_message(chat_id, from_chat_id, message_id)
            except Exception as err:
                log_warn(f"Telebot.Message.forward forward_message {from_chat_id=} {message_id=} {err=}")
                return None
            return response

        def reply(self, chat_id: int, message: Telebot.Message):
            """
            Отправляет ответ на это сообщение.
            """
            message.set_reply(self)
            message.send(chat_id)
        
        
        # Методы работы с полями


        def get_text(self, parse_mode: str = "") -> str:
            if self.check_text(self.text):
                if parse_mode:
                    return preceding(str(self.text).strip())
                else:
                    return str(self.text).strip()
            elif isinstance(self.text, str):
                raise ValueError(f"Пустой текст сообщения не допускается, если нет кнопок или вложений")
            else:
                raise ValueError(f"Некорректное значение атрибута {self.text=}")
        
        
        def check_telebot(self, telebot: TeleBot) -> bool:
            return isinstance(telebot, TeleBot)

        def set_telebot(self, telebot: TeleBot):
            if self.check_telebot(telebot):
                self.telebot = telebot
            else:
                raise ValueError(f"Некорректное значение аргумента {telebot=}")

        def get_telebot(self) -> TeleBot:
            if self.check_telebot(self.telebot):
                return self.telebot
            else:
                raise ValueError(f"Некорректное значение атрибута {self.telebot=}")


        def check_reply(self, reply: Telebot.Message) -> bool:
            return super().check_reply(reply)

        def set_reply(self, reply: Telebot.Message | None):
            return super().set_reply(reply)

        def get_reply(self) -> Telebot.Message | None:
            return super().get_reply()
        

        def check_attachments_types(self, attachments: Iterable[Telebot.Attachment]) -> bool:
            if not attachments:
                return True
            
            media_types: list[type[InputMediaPhoto | InputMediaVideo | InputMediaAudio | InputMediaDocument]] = []
            
            for attachment in attachments:
                media_type: type[InputMediaPhoto | InputMediaVideo | InputMediaAudio | InputMediaDocument] = attachment.get_media_type()
                media_types.append(media_type)
                
            if InputMediaDocument in media_types and any(media_type in media_types for media_type in [InputMediaPhoto, InputMediaVideo, InputMediaAudio]):
                return False
            
            return True
        
        def check_attachments(self, attachments: Iterable[Telebot.Attachment]) -> bool:
            return super().check_attachments(attachments) and self.check_attachments_types(attachments)

        def set_attachments(self, attachments: Iterable[Telebot.Attachment]):
            if not self.check_attachments(attachments):
                raise ValueError(f"Некорректное значение аргумента {attachments=}")
            elif attachments and self.keyboard:
                raise TelebotException("Telebot не поддерживает отправку вложений вместе с клавиатурой")
            elif not self.check_attachments_types(attachments):
                raise TelebotException("Telebot не поддерживает отправку файлов и других вложений одним сообщением")
            else:
                return super().set_attachments(attachments)

        def get_attachments(self) -> list[Telebot.Attachment]:
            if not self.check_attachments(self.attachments):
                raise ValueError(f"Некорректное значение атрибута {self.attachments=}")
            elif self.attachments and self.keyboard:
                raise TelebotException("Telebot не поддерживает отправку вложений вместе с клавиатурой")
            elif not self.check_attachments_types(self.attachments):
                raise TelebotException("Telebot не поддерживает отправку файлов и других вложений одним сообщением")
            else:
                return super().get_attachments()
        

        def check_forward(self, forward: Iterable[Telebot.Message]) -> bool:
            return super().check_forward(forward)

        def set_forward(self, forward: Iterable[Telebot.Message]):
            return super().set_forward(forward)

        def get_forward(self) -> list[Telebot.Message]:
            return super().get_forward()


        def check_keyboard(self, keyboard: Telebot.Keyboard) -> bool:
            return super().check_keyboard(keyboard)
        
        def set_keyboard(self, keyboard: Telebot.Keyboard | None):
            if keyboard is None:
                self.keyboard = None
            elif self.check_keyboard(keyboard):
                if self.attachments:
                    raise TelebotException("Telebot не поддерживает отправку вложений вместе с клавиатурой")
                else:
                    self.set_changed(True)
                    self.keyboard = keyboard
            else:
                raise ValueError(f"Некорректное значение аргумента {keyboard=}")

        def get_keyboard(self) -> Telebot.Keyboard | None:
            if self.keyboard is None:
                return None
            elif self.check_keyboard(self.keyboard):
                if self.attachments:
                    raise TelebotException("Telebot не поддерживает отправку вложений вместе с клавиатурой")
                else:
                    return self.keyboard
            else:
                raise ValueError(f"Некорректное значение атрибута {self.keyboard=}")


    class VoiceMessage(Bot.VoiceMessage):
        
        def __init__(self, telebot: TeleBot, owner_id: int, text: str, audio_attachment: Telebot.AudioAttachment | None, event: Bot.Event = None, reply: Bot.Message | None = None):
            """
            :param owner_id: Идентификатор отправителя сообщения (пользователя или администратора, а если отправил сообщение бот, то используйте bot.group_id).
            :param text: Текст сообщения.
            :param event: Сообщение можно создать из Bot.Event, тогда событие помещается это поле.
            """
            super().__init__(owner_id, text, audio_attachment, event, reply)
            self.telebot: TeleBot
            self.set_telebot(telebot)
                    
        def send(self, chat_id: int) -> Telebot.Event:
            audio_attachment: Telebot.AudioAttachment | None = self.get_audio_attachment()
            telebot: TeleBot = self.get_telebot()
            content: str | BufferedReader | BytesIO
            files: list[BufferedReader] = []
            
            if not audio_attachment:
                self.synthesize()
            
            file_id: str = audio_attachment.get_id()
            if file_id:
                content = file_id
            elif audio_attachment.check_filename(audio_attachment.filename):
                filename: str = audio_attachment.get_filename()
                content = open(filename, "rb")
                files.append(content)
            else:
                content = audio_attachment.get()
                
            response: TelebotMessage = telebot.send_voice(chat_id, content)
            message_id: int = int(response.message_id)
            event: Bot.Event = self.__class__.Event(chat_id, "", datetime.now(), [audio_attachment])
            event.set_events([response])
            self.add_event(event, datetime.fromtimestamp(response.date), self.__class__.SENT_KEY)
            self.set_id(message_id)
            self.set_chat_id(chat_id)
            
            for file in files:
                file.close()
            
            return event
        
        def synthesize(self):
            """
            self.text -> self.audio_attachment
            """
            text: str = self.get_text()
            audio: BytesIO = Voice().synthesize(text)
            audio_attachment: Telebot.AudioAttachment = Telebot.AudioAttachment.from_bytes(audio)
            self.set_audio_attachment(audio_attachment)
        
        def recognize(self):
            audio_attachment: Telebot.AudioAttachment | None = self.get_audio_attachment()
            
            if audio_attachment:
                text: str = audio_attachment.recognize()
                self.set_text(text)
        
        
        # Методы работы с полями
        
        
        def check_telebot(self, telebot: TeleBot) -> bool:
            return isinstance(telebot, TeleBot)

        def set_telebot(self, telebot: TeleBot):
            if self.check_telebot(telebot):
                self.telebot = telebot
            else:
                raise ValueError(f"Некорректное значение аргумента {telebot=}")

        def get_telebot(self) -> TeleBot:
            if self.check_telebot(self.telebot):
                return self.telebot
            else:
                raise ValueError(f"Некорректное значение атрибута {self.telebot=}")
        
        
        # Переопределённые методы работы с полями
        
        
        def check_audio_attachment(self, audio_attachment: Telebot.AudioAttachment) -> bool:
            return isinstance(audio_attachment, Telebot.AudioAttachment)

        def set_audio_attachment(self, audio_attachment: Telebot.AudioAttachment | None):
            return super().set_audio_attachment(audio_attachment)
            
        def get_audio_attachment(self) -> Telebot.AudioAttachment | None:
            return super().set_audio_attachment()
        
        
    def get_message_id(event: Bot.Event) -> int:
        for ev in event.get_events():
            if isinstance(ev, TelebotMessage):
                return ev.message_id
            elif isinstance(ev, CallbackQuery):
                return ev.message.message_id
            else:
                raise ValueError(f"Некорректное значение поля {event.event=}. Ожидался telebot.types.Message или telebot.types.CallbackQuery")
    
    def __init__(self, token: str, name: str, group_id: int):
        """
        :param token: Токен доступа к API.
        :param name: Имя бота, уникально для одной платформы, например, `"@botname_bot"`. Два vkbot с одинаковым именем нельзя, vkbot и telebot с одинаковым именем можно.
        :param group_id: Идентификатор группы, в которой будет работать бот.
        """
        super().__init__(token, name, group_id)
        self.bot: TeleBot = self.initAPI()

        self.attachments: dict[Telebot.Attachment] = []

    def initAPI(self) -> TeleBot:
        return TeleBot(self.token)

    def check_callback(self, event: Bot.Event) -> bool:
        if event.DEBUG_CALLBACK:
            return True
        
        for ev in event.events:
            if isinstance(ev, CallbackQuery):
                return True
            
        return False
    
    def split(self, text: str, buttons: Iterable[Keyboard.Button], attachments: Iterable[Attachment], reply: Message | None, forward: Iterable[Message], max_width: int, inline: bool) -> list[Message]:
        attachments_groups: list[tuple[Telebot.Attachment]] = self.split_attachments(attachments)
        texts: list[str] = self.split_text(text)
        messages: list[Telebot.Message] = []
        
        for attachments in attachments_groups:
            message: Telebot.Message = self.__class__.Message(self.bot, self.group_id, "", attachments = attachments)
            messages.append(message)
        
        for i, text in enumerate(texts):
            if i == 0 and messages and ((not messages[-1].attachments) or (not buttons)):
                messages[-1].set_text(text)
            else:
                message: Telebot.Message = self.__class__.Message(self.bot, self.group_id, text)
                messages.append(message)
        
        if buttons:
            keyboard: Telebot.Keyboard = self.__class__.Keyboard(buttons, max_width = max_width, inline = inline)
            
            if messages and not messages[-1].attachments:
                messages[-1].set_keyboard(keyboard)
            else:
                message: Telebot.Message = self.__class__.Message(self.bot, self.group_id, "", keyboard = keyboard)
                messages.append(message)
        
        if forward:
            if messages:
                messages[0].set_forward(forward)
            else:
                message: Telebot.Message = self.__class__.Message(self.bot, self.group_id, self.__class__.Message.EMPTY_TEXT, forward = forward)
                messages.append(message)
        elif reply:
            if messages:
                messages[0].set_reply(reply)
            else:
                message: Telebot.Message = self.__class__.Message(self.bot, self.group_id, self.__class__.Message.EMPTY_TEXT, reply = reply)
                messages.append(message)

        return messages

    
    # 
    

    def typing(self, chat_id: int):
        self.bot.send_chat_action(chat_id, "typing")
    
    
    def get_attachment(self, filename: str, compression: bool = True) -> Telebot.Attachment:
        """
        Возвращает вложение готовое для отправки.
        :param filename: Приводится к нормальному виду внутри метода.
        :param compression: Если compression=True -> attachment_type="photo" compression=False -> filename.jpg -> "doc".
        """
        if not self.get_bot_key:
            raise RuntimeError("Метод get_attachments доступен только для дочерних классов")
        
        def get_attachment_type(extension: str) -> type[InputMediaPhoto] | type[InputMediaVideo] | type[InputMediaVideo] | type[InputMediaAudio] | type[InputMediaDocument]:
            """
            Возвращает тип вложения основываясь на указанном расширении файла
            Сопоставление расширений и типов вложений хранится в словаре EXTENSIONS
            :param extension: Обязательно в нижнем регистре и с точкой ".jpg"
            Иначе возвращает тип вложения по умолчанию, который хранится в DEFAULT_ATTACHMENT_TYPE
            """
            for attachment_type, extensions in self.__class__.Attachment.EXTENSIONS.items():
                if extension in extensions:
                    return attachment_type

            return self.__class__.Attachment.DEFAULT_ATTACHMENT_TYPE

        # Методы загрузки на сервер для разных типов вложений
        uploads: dict[type[InputMediaPhoto] | type[InputMediaVideo] | type[InputMediaVideo] | type[InputMediaAudio] | type[InputMediaDocument], Callable] = {
            InputMediaPhoto: self.__class__.PhotoAttachment.from_filename,
            InputMediaVideo: self.__class__.VideoAttachment.from_filename,
            InputMediaVideo: self.__class__.AudioAttachment.from_filename,
            InputMediaDocument: self.__class__.DocAttachment.from_filename
        }

        # Значение по умолчанию
        attachment_type: type[InputMediaPhoto] | type[InputMediaVideo] | type[InputMediaVideo] | type[InputMediaAudio] | type[InputMediaDocument] = self.__class__.Attachment.DEFAULT_ATTACHMENT_TYPE

        # Значение по расширению файла только если загрузка со сжатием, без сжатия всегда "doc"
        if compression:
            extension: str = only_extension(filename).lower()
            attachment_type = get_attachment_type(extension)

        # Вызов соответствующего метода загрузки вложения
        upload: Callable = uploads[attachment_type]
        attachment: Telebot.Attachment = upload(filename)
        return attachment 
        
    def get_attachments(self, filenames: Iterable[str], compression: bool = True) -> list[Telebot.Attachment]:
        attachments: list[Telebot.Attachment] = []
        
        for filename in filenames:
            attachment: Telebot.Attachment = self.get_attachment(filename, compression)
            attachments.append(attachment)

        return attachments

    def split_attachments(self, attachments: Iterable[Attachment]) -> list[tuple[Attachment]]:
        max_attachments: int = self.__class__.Message.MAX_ATTACHMENTS_IN_GROUP
        result: list[tuple[Telebot.Attachment, ...]] = []
        current_batch: list[Telebot.Attachment] = []
        current_media_types: set[type[InputMediaPhoto | InputMediaVideo | InputMediaAudio | InputMediaDocument]] = set()
        
        for attachment in attachments:
            media_type = attachment.get_media_type()
            
            if (len(current_batch) >= max_attachments or
                (InputMediaDocument in current_media_types and media_type != InputMediaDocument) or
                (current_media_types and InputMediaDocument not in current_media_types and media_type == InputMediaDocument)):
                
                result.append(current_batch)
                current_batch = [attachment]
                current_media_types = {media_type}
            else:
                current_batch.append(attachment)
                current_media_types.add(media_type)
        
        if current_batch:
            result.append(current_batch)
        
        return result

    def send(self, chat_id: int, text: str, buttons: Iterable[str] = [], filenames: Iterable[str] = [], inline: bool = True, max_width: int = 2, compression: bool = True, reply: Message | None = None, forward: Iterable[Message] = [], parse_mode: str = "") -> list[Message]:
        keyboard: Telebot.Keyboard | None = None
        
        if buttons:
            keyboard = self.__class__.Keyboard(buttons, max_width = max_width, inline = inline)
            
        attachments: list[Telebot.PhotoAttachment | Telebot.VideoAttachment | Telebot.AudioAttachment | Telebot.DocAttachment] = self.get_attachments(filenames, compression = compression)
        message: Telebot.Message = Telebot.Message(self.bot, self.group_id, text, keyboard, forward, reply, attachments)
        responses: dict[str, list[TelebotMessage]] = message.send(chat_id, parse_mode = parse_mode)
        messages: list[Telebot.Message] = self.parse_responses(responses, datetime.now(), self.group_id)
        return messages

    def send_voice(self, chat_id: int, text: str, reply: Message | None = None) -> list[Message]:
        message: Telebot.VoiceMessage = Telebot.VoiceMessage(self.bot, self.group_id, text, None, reply)
        message.synthesize()
        message.send(chat_id)
    
    
    # Обработчики
    
    
    def parse_responses(self, responses: dict[str, list[TelebotMessage]], date: datetime, owner_id: int | None) -> list[Telebot.Message]:
        attachments_responses: list[TelebotMessage] = responses.get("attachments", [])
        attachments_filenames: list[str] = responses.get("filenames", [])
        forward_responses: list[TelebotMessage] = responses.get("forward", [])
        messages: list[Telebot.Message] = []
        
        for response in forward_responses:
            message_id: str = response.id
            chat_id: int = response.chat.id
            event: Bot.Event = self.parse_message(response, get_date(response, "date", default = date), owner_id)
            
            mes: Telebot.Message = Telebot.Message.from_event(event, self.bot)
            mes.set_id(message_id)
            mes.set_chat_id(chat_id)
            messages.append(mes)
        
        for i, response in enumerate(attachments_responses):
            if i >= len(attachments_filenames):
                raise IndexError(f"Некорректное значение аргумента {responses=}. Словарь обязан содержать идентичное количество элементов в значениях с ключами 'attachments' и 'filenames'.")
            
            message_id: str = response.id
            chat_id: int = response.chat.id
            event: Bot.Event = self.parse_files(response, get_date(response, "date", default = date), owner_id)
            
            message: Telebot.Message = Telebot.Message.from_event(event, self.bot)
            message.set_id(message_id)
            message.set_chat_id(chat_id)
            try:
                message.attachments[0].set_filename(attachments_filenames[i])  # После отправки сообщения (загрузки вложения) в responses должно быть ровно 1 вложение на 1 сообщение
            except IndexError:
                pass
            messages.append(message)
        
        return messages
    
    
    def parse_message(self, message: TelebotMessage, date: datetime, owner_id: int | None = None) -> Bot.Event:
        chat_id: int = message.from_user.id
        owner_id: int = chat_id if owner_id is None else owner_id
        text: str = message.text or ""
        self.add_id(chat_id)
        
        event: Bot.Event = self.__class__.Event(owner_id, chat_id, text, date)
        event.set_events([message])

        first_name = message.from_user.first_name
        last_name = message.from_user.last_name or ""
        event.set_name(first_name, last_name)

        return event

    def parse_callback(self, callback: CallbackQuery, date: datetime, owner_id: int | None = None) -> Bot.Event:
        chat_id: int = callback.message.chat.id
        owner_id: int = chat_id if owner_id is None else owner_id
        text: str = callback.data or ""
        self.add_id(chat_id)
        
        event: Bot.Event = self.__class__.Event(owner_id, chat_id, text, date)
        event.set_events([callback])

        first_name = callback.message.from_user.first_name
        last_name = callback.message.from_user.last_name or ""
        event.set_name(first_name, last_name)

        return event

    def parse_voice(self, message: TelebotMessage, date: datetime, owner_id: int | None = None) -> Bot.Event:
        chat_id: int = message.chat.id
        owner_id: int = chat_id if owner_id is None else owner_id
        self.add_id(chat_id)
        attachment: Telebot.AudioAttachment = self.__class__.AudioAttachment(message.voice)
        
        event: Bot.Event = self.__class__.Event(owner_id, chat_id, "", date, attachments = [attachment])
        event.set_events([message])

        first_name = message.from_user.first_name
        last_name = message.from_user.last_name or ""
        event.set_name(first_name, last_name)

        return event

    def parse_files(self, message: TelebotMessage, date: datetime, owner_id: int | None = None):
        chat_id: int = message.from_user.id
        owner_id: int = chat_id if owner_id is None else owner_id
        text: str = message.caption or ""
        self.add_id(chat_id)
        attachments: list[Telebot.Attachment] = []
        
        if message.photo:
            photo: PhotoSize = message.photo[-1]
            sizes: list[PhotoSize] = message.photo[:-1]
            attachment: Telebot.PhotoAttachment = Telebot.PhotoAttachment(photo, sizes)
            attachments.append(attachment)

        if message.video:
            attachment: Telebot.VideoAttachment = Telebot.VideoAttachment(message.video)
            attachments.append(attachment)

        if message.audio:
            attachment: Telebot.AudioAttachment = Telebot.AudioAttachment(message.audio)
            attachments.append(attachment)

        if message.document:
            attachment: Telebot.DocAttachment = Telebot.DocAttachment(message.document)
            attachments.append(attachment)

        event: Bot.Event = self.__class__.Event(owner_id, chat_id, text, date, attachments = attachments)
        event.set_events([message])

        first_name = message.from_user.first_name
        last_name = message.from_user.last_name or ""
        event.set_name(first_name, last_name)

        return event
        

    def process_message(self, message: TelebotMessage, date: datetime):
        event = self.parse_message(message, date)
        return self.process_event(event)

    def process_callback(self, callback: CallbackQuery, date: datetime):
        event = self.parse_callback(callback, date)
        return self.process_event(event, combine_events = False)

    def process_voice(self, message: TelebotMessage, date: datetime):
        event = self.parse_voice(message, date)
        return self.process_event(event)

    def process_file(self, message: TelebotMessage, date: datetime):
        event = self.parse_files(message, date)
        return self.process_event(event)

    def polling(self, skip: float = 0, warning: bool = True):
        """
        Обработчик событий.
        Может быть вызван повторно, но предварительно остановите предыдущий обработчик.
        
        :param skip: Количество секунд, в течение которых бот не будет обрабатывать сообщения при запуске.
        Это нужно, чтобы не обрабатывать старые события, которые сервер отправляет при старте.
        
        :raises Exception: дублирует исключения, возникающие в API.
        """
        
        from_date: datetime = datetime.now()
        
        if skip > 0:
            from_date += timedelta(seconds = skip)
            
        def check():
            return skip <= 0 or datetime.now() >= from_date
        
        def show_warn():
            if warning:
                Console.warning("Пропущено событие", datetime.now())
        
        def polling():
            # Обработчик текстовых сообщений
            @self.bot.message_handler(content_types = ["text"])
            def message_handler(message: TelebotMessage):
                return self.process_message(message, get_date(message.date)) if check() else show_warn()

            # Обработчик нажатий на кнопки
            @self.bot.callback_query_handler(func = lambda call: True)
            def callback_query_handler(callback: CallbackQuery):
                return self.process_callback(callback, datetime.now()) if check() else show_warn()

            # Обработчик голосовых сообщений
            @self.bot.message_handler(content_types = ["voice"])
            def voice_message_handler(voice: TelebotMessage):
                return self.process_voice(voice, get_date(voice.date)) if check() else show_warn()

            # Обработчик файлов
            @self.bot.message_handler(content_types = ["photo", "video", "audio", "document"])
            def file_handler(message):
                return self.process_file(message, get_date(message.date)) if check() else show_warn()
            
            return self.bot.polling(none_stop = True, interval = 0)

        while self.check_working():
            polling()
    
    
    # Переопределённые методы работы с полями
    

    @classmethod
    def check_name(cls, name: str) -> bool:
        return super().check_name(name) and name.endswith("bot")
    
    def set_name(self, name: str):
        return super().set_name(name)

    def get_name(self) -> str:
        return super().get_name()
    
    
    @classmethod
    def check_group_id(cls, group_id: int) -> bool:
        if isinstance(group_id, str):
            raise Exception()
        return isinstance(group_id, int) and group_id >= 0

    def set_group_id(self, group_id: int):
        if self.__class__.check_group_id(group_id):
            token_group_id: int = self.token[:self.token.find(":")]
            
            if group_id != token_group_id and self.token:
                warn(f"Значение аргумента {group_id=} не совпадает с идентификатором группы в поле self.token")
            
            self.group_id = group_id
        else:
            raise ValueError(f"Некорректное значение аргумента {group_id=}")

    def get_group_id(self) -> int:
        if self.__class__.check_group_id(self.group_id):
            token_group_id: str | int = self.token[:self.token.find(":")]
            
            if token_group_id and is_int(token_group_id):
                token_group_id = int(token_group_id)
            else:
                self.get_token()
                raise NotImplementedError("Недостижимый код: get_token должен вызвать исключение")
            
            if self.group_id == token_group_id:
                return self.group_id
            else:
                raise ValueError(f"Значение атрибута {self.group_id=} не совпадает с идентификатором группы в поле self.token")
        else:
            raise ValueError(f"Некорректное значение атрибута {self.group_id=}")


    @classmethod
    def check_token(cls, token: str) -> bool:
        return super().check_token(token) and ":" in token and is_int(token[:token.find(":")])
    
    def set_token(self, token: str):
        if self.__class__.check_token(token):
            group_id: int = int(token[:token.find(":")])
            
            if self.__class__.check_group_id(group_id):
                if group_id != self.group_id:
                    warn(f"Идентификатор группы в поле {token=} не совпадает с идентификатором группы в поле group_id")
                
                self.token = token
                return
            
        raise ValueError(f"Некорректное значение аргумента {token=}")

    def get_token(self) -> str:
        if self.__class__.check_token(self.token):
            group_id: int = self.token[:self.token.find(":")]
            
            if is_int(group_id) and self.__class__.check_group_id(int(group_id)):
                group_id = int(group_id)
                
                if group_id == self.group_id:
                    return str(self.token).strip()
                else:
                    raise ValueError(f"Идентификатор группы в поле {self.token=} не совпадает с идентификатором группы в поле self.group_id")
            else:
                raise ValueError(f"Некорректное значение атрибута {self.token=}. Идентификатор группы в поле не прошёл проверку")
        else:
            raise ValueError(f"Некорректное значение атрибута {self.token=}")


class Message():
    MESSAGE_TYPE = dict[str, int | str | list[str] | list[Union["Bot.Keyboard.Button.BUTTON_TYPE", "Vkbot.Keyboard.Button.BUTTON_TYPE", "Telebot.Keyboard.Button.BUTTON_TYPE"]] | bool | dict[str, dict[int, list["Message.MessagesGroup.GROUP_TYPE"]]]]
    
    class MessagesGroup():
        GROUP_TYPE = dict[str, str | int | bool | list[Union["Vkbot.Message.MESSAGE_TYPE", "Telebot.Message.MESSAGE_TYPE"]]]
        
        def loads(data: GROUP_TYPE, bot: BOT) -> Message.MessagesGroup:
            chat_id: int = get_int(data, -1, "chat_id")
            owner_id: int = get_int(data, -1, "owner_id")
            compression: bool = get_from(data, "inline")
            messages: list[dict[str, str | int | dict | list[dict] | None]] = get_from(data, "messages")
            
            group: Message.MessagesGroup = Message.MessagesGroup(bot, chat_id, owner_id, 
                [bot.__class__.Message.loads(message, bot.__class__, bot.bot) for message in messages], get_from(data, "username"), get_date(data, "date"), compression
            )
            return group
            
        def __init__(self, bot: BOT, chat_id: int, owner_id: int, messages: Iterable[Bot.Message], username: str, date: datetime, compression: bool = True):
            self.bot: BOT = None
            self.chat_id: int | None = None
            self.owner_id: int | None = None
            self.messages: list[Bot.Message] = list(messages)
            self.compression: bool = bool(compression)
            self.username: str = username
            self.date: datetime = date
            
            self.set_bot(bot)
            self.set_chat_id(chat_id)
            self.set_owner_id(owner_id)
        
        def __repr__(self) -> str:
            bot_key: BOT_KEY = self.bot.get_bot_key()
            chat_id: int = self.chat_id
            owner_id: int = self.owner_id
            messages: int = len(self.messages)
            username: str | None = self.username
            date: datetime | None = self.date
            result: str = f"MessagesGroup({bot_key} {chat_id=} {owner_id=} {username=} {date=} {messages=})["
            
            if self.messages:
                for message in self.messages:
                    result += f"\n\t{repr(message)}"
                    
                return f"{result}\n]"
            else:
                return f"{result}]"
            
        
        def dumps(self) -> GROUP_TYPE:
            return {
                "bot_key": self.bot.get_bot_key(),
                "chat_id": int(self.chat_id),
                "owner_id": int(self.owner_id),
                "compression": bool(self.compression),
                "messages": [message.dumps() for message in self.messages],
                "username": self.username,
                "date": get_timestamp(self.date) if self.date is not None else None
            }
        
        def get_text(self) -> str:
            return "\n".join(message.get_text() for message in self.messages)
        
        
        # Методы работы с полями
        
        
        def check_bot(self, bot: BOT) -> bool:
            return isinstance(bot, Vkbot) or isinstance(bot, Telebot)

        def set_bot(self, bot: BOT):
            if self.check_bot(bot):
                self.bot = bot
            else:
                raise ValueError(f"Некорректное значение аргумента {bot=}")

        def get_bot(self) -> BOT:
            if self.check_bot(self.bot):
                return self.bot
            else:
                raise ValueError(f"Некорректное значение атрибута {self.bot=}")


        def check_chat_id(self, chat_id: int) -> bool:
            return isinstance(chat_id, int) and chat_id >= 0

        def set_chat_id(self, chat_id: int):
            if self.chat_id is not None:
                raise ValueError(f"Поле self.chat_id уже содержит значение и не может быть установлено повторно. Сообщение может быть отправлено только один раз.")
            elif self.check_chat_id(chat_id):
                self.chat_id = chat_id
            else:
                raise ValueError(f"Некорректное значение аргумента {chat_id=}")

        def get_chat_id(self) -> int | None:
            if self.chat_id is None:
                return None
            elif self.check_chat_id(self.chat_id):
                return self.chat_id
            else:
                raise ValueError(f"Некорректное значение атрибута {self.chat_id=}")
        
        
        def check_owner_id(self, owner_id: int) -> bool:
            return isinstance(owner_id, int) and owner_id >= 0

        def set_owner_id(self, owner_id: int):
            if self.check_owner_id(owner_id):
                self.owner_id = owner_id
            else:
                raise ValueError(f"Некорректное значение аргумента {owner_id=}")

        def get_owner_id(self) -> int:
            if self.check_owner_id(self.owner_id):
                return self.owner_id
            else:
                raise ValueError(f"Некорректное значение атрибута {self.owner_id=}")
    
    def loads(data: MESSAGE_TYPE, get_bot: Callable) -> Message:
        id: int = get_int(data, -1, "id")
        
        text: str = get_from(data, "text")
        buttons_list: list[dict[str, str]] = get_from(data, "buttons", types = (list,), default = [])
        buttons: list[Bot.Keyboard.Button] = [Bot.Keyboard.Button.loads(button_data) for button_data in buttons_list]
        
        max_width: int = get_int(data, -1, "max_width")
        inline: bool = get_from(data, "inline")
        filenames: list[str] = get_from(data, "filenames")
        
        message: Message = Message(id, text, buttons, max_width, inline, filenames)
        
        messages: dict[str, dict[int, list["Message.MessagesGroup.GROUP_TYPE"]]] = get_from(data, "messages")
        for bot_key, messages_groups in messages.items():
            for chat_id, groups in messages_groups.items():
                for group in groups:
                    messages_group: Message.MessagesGroup = Message.MessagesGroup.loads(group, get_bot(bot_key))
                    message.add_group(bot_key, messages_group.get_chat_id(), messages_group)

        return message
    
    def __init__(self, message_id: int, text: str = "", buttons: Iterable[str | Bot.Keyboard.Button] = [], max_width: int = 2, inline: bool = True, filenames: Iterable[str] = []):
        self.id: int = -1
        self.text: str = ""
        self.filenames: list[str] = []

        self.buttons: list[Bot.Keyboard.Button] = []
        self.max_width: int = None
        self.inline: bool = None
        
        self.messages: dict[BOT_KEY, dict[int, list[Message.MessagesGroup]]] = {}
        self.set_id(message_id)
        self.set_text(text)
        self.set_keyboard(buttons, inline = inline, max_width = max_width)
        self.set_filenames(filenames)
    
    def __repr__(self) -> str:
        id: int = self.id
        text: str = self.text
        filenames: list[str] = self.filenames
        buttons: list[str] = self.buttons
        max_width: int = self.max_width
        inline: bool = self.inline
        messages: str = ""
        
        for bot_key, groups in self.messages.items():
            messages += f"\n  {bot_key=}"
            
            for chat_id, groups_list in groups.items():
                messages += f"\n    {chat_id=}"
                
                for group in groups_list:
                    string: str = repr(group)
                    
                    for s in string.split("\n"):
                        messages += f"\n      {s}"
                        
                messages += f"\n    <"
                
            messages += f"\n  <<"
        return f"Message({id=} {text=} {filenames=} {buttons=} {inline=} {max_width})[{messages}]"
    
    def dumps(self) -> MESSAGE_TYPE:
        return {
            "id": self.get_id(),
            "text": str(self.text),
            "filenames": [str(filename) for filename in self.filenames],
            "buttons": [button.dumps() for button in self.buttons],
            "max_width": int(self.max_width),
            "inline": bool(self.inline),
            "messages": {
                bot_key: {
                    chat_id: [
                        group.dumps() for group in groups
                    ] for chat_id, groups in messages_groups.items()
                } for bot_key, messages_groups in self.messages.items()
            }
        }
    
    @abstractmethod
    def get_header(message: Bot.Message, username: str, owner_id: int) -> str:
        return message.get_text()
    
    @abstractmethod
    def get_footer(attachments: list[Bot.Attachment], from_bot_key: BOT_KEY, to_bot_key: BOT_KEY) -> str:
        return ""
    
    @abstractmethod
    def get_remove_button(message: Bot.Message) -> Bot.Keyboard.Button:
        raise NotImplementedError()
    
    def check_sent(self, bot_key: BOT_KEY, chat_id: int) -> bool:
        if bot_key not in self.messages:
            # print(f"{bot_key=} {bot_key in self.messages=}")
            return False
        
        if chat_id not in self.messages[bot_key]:
            # print(f"{chat_id=} {chat_id in self.messages[bot_key]=}")
            return False

        # print(f"groups: {len(self.messages[bot_key][chat_id])}")
        for messages_group in self.messages[bot_key][chat_id]:
            existing_messages: list[Bot.Message] = messages_group.messages
            # print(f"{messages_group=}")
            
            for message in existing_messages:
                if message.was_sent():
                    return True
        
        return False
    
    def get_remove_callback(self, message: Bot.Message, bot_key: BOT_KEY, chat_id: int):
        """
        Возвращает callback для кнопки удаления указанного сообщения

        :param message: Сообщение, которое будет удалено по нажатию на кнопку.
        :param bot_key: В какой бот отправляется новое сообщение с кнопкой удаления указанного.
        :param chat_id: Идентификатор пользователя, которому отправляется новое сообщение с кнопкой удаления указанного.
        """
        remove_key: tuple = (bot_key, chat_id, message.get_bot_key(), message.get_owner_id(), message.get_chat_id(), message.get_id())
        return CALLBACK_SEPARATOR.join(tuple(map(str, remove_key)))
    
    def update_groups(self, groups: Iterable[MessagesGroup], bot: BOT, chat_id: int, owner_id: int, messages: Iterable[Bot.Message] = [], get_header: Callable = get_header, get_footer: Callable = get_footer, get_remove_button: Callable = get_remove_button) -> list[Bot.Message]:
        """
        Получает на вход сообщения в группах (группы могут быть от разных отправителей) и возвращает список сообщений для чата bot, chat_id.
        Функция старается оставить в результате старые сообщения из аргумента messages. Если список пуст, то все сообщения будут новыми.
        - Одинаковые сообщения (bot_key, owner_id, chat_id) будут оставлены без изменений (или отредактированы, если сообщения отличаются compare(text, attachments, forward, reply)).
        - Сообщения из той же соцсети (bot_key) будут пересланы через forward группами из подряд идущих сообщений (даже из разных групп массива `groups`), но могут быть разделены следующей категорией:
        - Остальные сообщения будут отправлены как новые.
        
        :param groups: Группы с сообщениями из чата, которые нужно будет отправить.
        :param bot: Бот, через который нужно будет отправить сообщения.
        :param chat_id: Чат, в который нужно будет отправить сообщения.
        :param owner_id: Идентификатор группы (бота), от лица которого нужно будет отправить сообщения.
        :param messages: Сообщения, которые уже есть в чате и их можно использовать для редактирования, чтобы не отправлять новые.
        :param get_header: Функция должна принимать аргументы (message: Bot.Message, username: str, owner_id: int) и возвращать новый текст сообщения str, текст будет заменён у новых сообщений, отредактированных и у заголовка пересланных сообщений, сообщения оставленные без изменений не будут отредактированы.
        :param get_footer: Функция должна принимать аргументы (attachments: list[Bot.Attachment], from_bot_key: BOT_KEY, to_bot_key: BOT_KEY) и возвращать дополниение к тексту сообщения str, текст будет добавлен к новым сообщениям, отредактированным и к заголовкам пересланных сообщений.
        :param get_remove_button: Функция должна принимать аргументы (message: Bot.Message) и возвращать кнопку `Bot.Keyboard.Button` с `callback_data`.
        """
        # print(f"split_groups {bot=} {chat_id=}")
        old_messages = list(messages)
        messages_list: list[Bot.Message] = []
        forward_list: list[tuple[Bot.Message, str, int]] = []

        to_bot_key: BOT_KEY = bot.get_bot_key()
        
        def chain_broken():
            """
            Цепочка подряд идущих сообщений распалась.
            При разделении группы на сообщения, функция старается оставить уже имеющиеся в чате сообщения либо без изменений, либо отредактировать их, чтобы не отправлять новые сообщения.
            """
            old_messages.clear()
        
        def forward():
            """
            Формирует результирующий список, добавляя туда пересылаемые сообщения с подписью.
            """
            if forward_list:
                username: str = ""
                owner_id: int = -1
                forward_messages: list[Bot.Message] = []
                # print(f"forward {len(forward_messages)} messages from {username=} {owner_id=}")
                
                for mes, username, owner_id_ in forward_list:
                    forward_messages.append(mes)
                
                message: Bot.Message = bot.__class__.Message(bot.bot, owner_id, "", forward = forward_messages)
                message.set_text(get_header(message, username, owner_id))
                messages_list.append(message)
                forward_list.clear()
        
        def add_forward(message: Bot.Message, username: str, owner_id: int):
            """
            Формирует список сообщений для пересылки, но не добавляет их в результирующий список.
            
            :param username: Отправитель сообщения берётся из группы.
            :param owner_id: Отправитель сообщения берётся из группы.
            """
            forward_list.append((message, username, owner_id))
        
        def add_message(new_message: Bot.Message, username: str, owner_id: int, from_bot_key: BOT_KEY, old_mes: Bot.Message | None = None):
            """
            Формирует результирующий список на основе существующих сообщений.
            Если цепочка распадётся, то следующие сообщения будут только новыми (пересланными или созданными).
            Цепочка распадается если встречается сообщение, которое нельзя отредактировать или оставить без изменений.
            
            :param username: Отправитель сообщения берётся из группы.
            :param owner_id: Отправитель сообщения берётся из группы.
            """
            # print(f"{new_message=} old_messages={len(old_messages)}")
            
            if len(messages_list) < len(old_messages):
                old_message: Bot.Message = old_messages[len(messages_list)]
                old_mes = old_message
                # print(f"{old_message=}")
                
                if isinstance(old_message, bot.__class__.Message):
                    # print("same type", bot.__class__.Message)
                    if old_message.get_owner_id() in (owner_id, new_message.get_owner_id()):
                        # print("same owner", old_message.owner_id, f"was_sent={old_message.was_sent()}")
                        if old_message.was_sent() and old_message.get_chat_id() == chat_id:
                            if old_message.compare(new_message):
                                # print("Оставляем без изменений")
                                messages_list.append(old_message)
                                return
                            elif old_message.check_editable():

                                # print("Редактируем")
                                if old_message.get_text() != new_message.get_text():
                                    old_message.set_text(get_header(new_message, username, owner_id))

                                if old_message.get_keyboard() != new_message.get_keyboard():
                                    old_message.set_keyboard(new_message.keyboard)
                                
                                messages_list.append(old_message)
                                return
                            
                    #     else:
                    #         print(f"was_sent={old_message.was_sent()} {chat_id=} != {old_message.chat_id=}")
                    # else:
                    #     print(f"{old_message.owner_id=}")
            
                    chain_broken()
                    
                    if old_message.check_editable():
                        add_forward(old_message, username, owner_id)
                        # print("-> forward", len(forward_list))
                        return
            
            chain_broken()
            # forward()
            # print("Отправляем")
            header: str = get_header(new_message, group.username, group.owner_id)

            if header != new_message.text and old_mes:
                keyboard: Bot.Keyboard = bot.__class__.Keyboard([
                    get_remove_button(old_mes)
                ], max_width = 2, inline = True)
                new_message.set_keyboard(keyboard)
            else:
                new_message.clear_keyboard()

            new_message.set_text(header)
            messages_list.append(new_message)
        
        i = 10
        for group in groups:
            # print(f"Группа №{groups.index(group)+1} из {len(groups)} с {len(group.messages)} сообщениями")
            # print(f"{group.bot.get_bot_key()} -> {bot.get_bot_key()}")
            # print(f"{group.get_chat_id()} -> {chat_id}")
            # print(group)
            from_bot_key: BOT_KEY = group.bot.get_bot_key()
            
            for message in group.messages:
                attachments_list: list[Bot.Attachment] = list(message.attachments)
                footer: str = ""
                
                if from_bot_key != to_bot_key:
                    footer = get_footer(attachments_list, from_bot_key, to_bot_key)

                text: str = message.get_text() + footer
                keyboard: Bot.Keyboard | None = None
                
                if message.keyboard:
                    buttons: list[Bot.Keyboard.Button] = []
                    
                    for button in message.keyboard.buttons:
                        # Дублируем кнопки для отслеживания ответов бота, но кнопки не кликабельны
                        buttons.append(bot.__class__.Keyboard.Button(button.get_text(), callback_data = ""))
                    
                    keyboard: Bot.Keyboard = bot.__class__.Keyboard(buttons, max_width = message.keyboard.max_width, inline = message.keyboard.inline)

                attachments: list[Bot.Attachment] = []

                for mes_att in attachments_list:
                    attachment: Vkbot.PhotoAttachment | Vkbot.VideoAttachment | Vkbot.AudioAttachment | Vkbot.DocAttachment | Telebot.PhotoAttachment | Telebot.VideoAttachment | Telebot.AudioAttachment | Telebot.DocAttachment = mes_att

                    if bot.__class__.check_attachment(attachment):
                        attachments.append(attachment)
                    else:
                        # here
                        try:
                            filename: str = attachment.make_filename(group.bot, ATTACHMENTS_FOLDER)
                        except Exception as err:
                            log_warn(err)
                            exc_type, exc_value, exc_traceback = sys.exc_info()
                            formatted_traceback: list[str] = traceback.format_exception(exc_type, exc_value, exc_traceback)

                            try:
                                dumps = mes_att.dumps()
                            except Exception as err:
                                dumps = err
                            
                            try:
                                bot_key = bot.get_bot_key()
                            except Exception as err:
                                bot_key = err

                            Debug.add_error(f"Ошибка при отправке вложения {mes_att=} получателю {bot_key=} {chat_id=} {dumps=}", formatted_traceback, err)
                        else:
                            att = bot.get_attachment(filename, compression = True)
                            attachments.append(att)

                new_message: Bot.Message = bot.__class__.Message(bot.bot, owner_id, text, keyboard = keyboard, attachments = attachments)

                old_mes: Bot.Message | None = None

                if len(group.messages) == 1:
                    old_mes = group.messages[0]

                    if not old_mes.check_editable():
                        old_mes = None

                add_message(new_message, group.username, group.owner_id, group.bot.get_bot_key(), old_mes = old_mes)
        
        # forward()
        return messages_list
    
    def send_groups(self, groups: Iterable[MessagesGroup], bot: BOT, chat_id: int, owner_id: int, messages: Iterable[Bot.Mesage] = [], compression: bool = True, get_header: Callable = get_header, get_footer: Callable = get_footer, get_remove_button: Callable = get_remove_button):
        """
        Получает на вход сообщения в группах (группы могут быть от разных отправителей) и отправляет список сообщений для чата bot, chat_id.
        Функция старается оставить в результате старые сообщения из аргумента messages. Если список пуст, то все сообщения будут новыми.
        - Одинаковые сообщения (bot_key, owner_id, chat_id) будут оставлены без изменений (или отредактированы, если сообщения отличаются compare(text, attachments, forward, reply)).
        - Сообщения из той же соцсети (bot_key) будут пересланы через forward группами из подряд идущих сообщений (даже из разных групп массива `groups`), но могут быть разделены следующей категорией:
        - Остальные сообщения будут отправлены как новые.
        
        :param groups: Группы с сообщениями из чата, которые нужно отправить.
        :param bot: Бот, через который нужно отправить сообщения.
        :param chat_id: Чат, в который нужно отправить сообщения.
        :param owner_id: Идентификатор группы (бота), от лица которого нужно отправить сообщения.
        :param messages: Сообщения, которые уже есть в чате и их можно использовать для редактирования, чтобы не отправлять новые.
        :param get_header: Функция должна принимать аргументы (message: Bot.Message, username: str, owner_id: int) и возвращать новый текст сообщения str, текст будет заменён у новых сообщений, отредактированных и у заголовка пересланных сообщений, сообщения оставленные без изменений не будут отредактированы.
        :param get_footer: Функция должна принимать аргументы (attachments: list[Bot.Attachment], from_bot_key: BOT_KEY, to_bot_key: BOT_KEY) и возвращать дополниение к тексту сообщения str, текст будет добавлен к новым сообщениям, отредактированным и к заголовкам пересланных сообщений.
        :param get_remove_button: Функция должна принимать аргументы (message: Bot.Message) и возвращать кнопку `Bot.Keyboard.Button` с `callback_data`.
        """
        # Получаем цепочку сообщений
        messages: list[Bot.Message] = self.update_groups(groups, bot, chat_id, owner_id, messages = messages, get_header = get_header, get_footer = get_footer, get_remove_button = get_remove_button)
        messages_list: list[Bot.Message] = []
        username: str = ""
        removable_messages: list[Bot.Message] = []
        
        # Отправляем сообщения и сохраняем ответ сервера
        for message in messages:
            kwargs: dict[str, bool] = {}
            
            if isinstance(message, Telebot.Message):
                kwargs["forward_after"] = True
                kwargs["parse_mode"] = MARKDOWN
            elif isinstance(message, Vkbot.Message):
                kwargs["parse_mode"] = MARKDOWN
            
            was_sent: bool = message.was_sent()
            # print(type(message), f"{message.text=}", kwargs, f"{was_sent=}")
            
            if not message.was_sent():
                responses: dict[str, TelebotMessage] | None = message.send(chat_id, **kwargs)
                
                # Отправка одного сообщения ничего не вернёт
                # Но отправка группы вложений вернёт сразу несколько событий, которые надо обработать
                if responses:
                    parsed: list[Telebot.Message] = bot.parse_responses(responses, datetime.now(), bot.group_id)
                    
                    if parsed:
                        username = parsed[0].get_username()
                        messages_list += parsed
                    else:
                        username = message.get_username()
                        messages_list.append(message)
                else:
                    username = message.get_username()
                    messages_list.append(message)
                
                if message.get_remove_callback():
                    removable_messages.append(message)
        
        # print("send_groups result:")
        # for message in messages_list:
        #     print("\t", message)
        # print("<<<")
        
        # Сохраняем сообщения для редактирования в дальнейшем
        self.add_messages(bot, chat_id, bot.group_id, messages_list, compression, username, datetime.now())

        bot_key: BOT_KEY = bot.get_bot_key()
        # print(f"after send_groups={len(self.messages[bot_key][chat_id])} {bot_key=} {chat_id=}:")
        # for group in self.messages[bot_key][chat_id]:
        #     print(f"{group=}")
        # print("<<<")
        return removable_messages

    def get_groups(self, bot_key: BOT_KEY, chat_id: int) -> list[Message.MessagesGroup]:
        if bot_key in self.messages and chat_id in self.messages[bot_key] and self.messages[bot_key][chat_id]:
            return self.messages[bot_key][chat_id]
        else:
            raise RuntimeError(f"Сообщение не было отправлено на адрес {chat_id=}. Перед редактированием сначала отправьте его.")

    def edit_groups(self, groups: Iterable[MessagesGroup], get_header: Callable = get_header, get_footer: Callable = get_footer, get_remove_button: Callable = get_remove_button):
        """
        Получает на вход сообщения в группах (группы могут быть от разных отправителей) и обновляет сообщения во всех чатах.
        Функция старается оставить в результате старые сообщения (которые уже есть в чате), сохранённые после вызова метода send_groups.
        - Одинаковые сообщения (bot_key, owner_id, chat_id) будут оставлены без изменений (или отредактированы, если сообщения отличаются compare(text, attachments, forward, reply)).
        - Сообщения из той же соцсети (bot_key) будут пересланы через forward группами из подряд идущих сообщений (даже из разных групп массива `groups`), но могут быть разделены следующей категорией:
        - Остальные сообщения будут отправлены как новые.
        
        :param groups: Группы с сообщениями из чата, которые нужно отправить.
        :param get_header: Функция должна принимать аргументы (message: Bot.Message, username: str, owner_id: int) и возвращать новый текст сообщения str, текст будет заменён у новых сообщений, отредактированных и у заголовка пересланных сообщений, сообщения оставленные без изменений не будут отредактированы.
        :param get_footer: Функция должна принимать аргументы (attachments: list[Bot.Attachment], from_bot_key: BOT_KEY, to_bot_key: BOT_KEY) и возвращать дополниение к тексту сообщения str, текст будет добавлен к новым сообщениям, отредактированным и к заголовкам пересланных сообщений.
        :param get_remove_button: Функция должна принимать аргументы (message: Bot.Message) и возвращать кнопку `Bot.Keyboard.Button` с `callback_data`.
        """
        removable_messages: list[Bot.Message] = []

        for bot_key in self.messages:
            for chat_id in self.messages[bot_key]:
                messages_group: Message.MessagesGroup = self.get_last_group(bot_key, chat_id)
                # print(f"edit_groups {bot_key=} {chat_id=} {messages_group=}")
                bot: BOT = messages_group.bot
                # print(f"{bot=}")
                compression: bool = messages_group.compression
                existing_messages: list[Bot.Message] = []

                for group in self.get_groups(bot_key, chat_id):
                    existing_messages += group.messages

                expected_messages: list[Bot.Message] = self.update_groups(groups, bot, chat_id, bot.group_id, messages = existing_messages, get_header = get_header, get_footer = get_footer, get_remove_button = get_remove_button)
                result_messages: list[Bot.Message] = []
                
                for message in expected_messages:
                    responses: dict[str, TelebotMessage] | None = None
                    
                    was_sent = message.was_sent()
                    was_changed = message.was_changed()
                    check_editable = message.check_editable()
                    # print(message, f"{was_sent=} {was_changed=} {check_editable=}")
                    
                    if message.get_text().strip() or message.get_attachments():
                        if message.check_editable():
                            if message.was_changed():
                                responses = message.edit()
                            #     print("Редактируем")
                            # else:
                            #     print("Оставляем без изменений")
                        elif was_sent and (not was_changed) and (not check_editable) and chat_id == message.get_owner_id():
                            # print("Пропускаем")
                            pass
                        else:
                            # print("Отправляем", chat_id)
                            responses = message.send(chat_id)
                    
                    if responses:
                        parsed: list[Telebot.Message] = bot.parse_responses(responses, datetime.now(), bot.group_id)
                    
                        if parsed:
                            result_messages += parsed
                        else:
                            result_messages.append(message)
                    else:
                        result_messages.append(message)
                
                    if message.get_remove_callback():
                        removable_messages.append(message)
                
                # print(f"messages_group.messages={len(messages_group.messages)}")
                # for message in messages_group.messages:
                #     print("\t", message)
                
                all_messages: list[Bot.Message] = messages_group.messages + result_messages
                result_messages = []

                for message in all_messages:
                    if message not in result_messages:
                        if message.chat_id is not None:
                            result_messages.append(message)
                
                result_messages.sort(key = lambda message: message.get_date("SENT") or message.get_date("MESSAGE_NEW"))

                messages_group.messages = result_messages
                
                # print(f"edit_groups result={len(result_messages)}:")
                # for message in result_messages:
                #     print("\t", message)
                # print("<<<")

                self.messages[bot_key][chat_id] = [messages_group]

                # bot_key: BOT_KEY = bot.get_bot_key()
                # print(f"after edit_groups={len(self.messages[bot_key][chat_id])} {bot_key=} {chat_id=}:")
                # for group in self.messages[bot_key][chat_id]:
                #     print(f"{group=}")
                # print("<<<")
        return removable_messages

    def delete_groups(self, bot_key_filter: str | Any = Any, chat_id_filter: int | Any = Any):
        deleting: list[tuple[str, int]] = []
        
        for bot_key in self.messages:
            if bot_key_filter is Any or bot_key == bot_key_filter:
                for chat_id in self.messages[bot_key]:
                    if chat_id_filter is Any or chat_id == chat_id_filter:
                        messages_group: Message.MessagesGroup = self.get_last_group(bot_key, chat_id)
                        
                        for message in messages_group.messages:
                            # print(f"{message=} {message.check_editable()=}")
                            try:
                                if message.check_editable():
                                    message.delete()
                            except ValueError as err:
                                log_warn(f"delete_groups {bot_key_filter=} {chat_id_filter=} {err=}")
                        
                        deleting.append((bot_key, chat_id))

        for bot_key, chat_id in deleting:
            del self.messages[bot_key][chat_id]

    
    def update(self, bot: BOT, messages: list[Bot.Message], compression: bool = True) -> list[Bot.Message]:
        attachments: list[Bot.Attachment] = bot.get_attachments(self.filenames, compression = compression)
        old_messages: list[Bot.Message] = list(messages)
        new_messages: list[Bot.Message] = bot.split(self.text, self.buttons, attachments, max_width = self.max_width, inline = self.inline, reply = None, forward = [])
        messages_list: list[Bot.Message] = bot.get_matches(old_messages, new_messages)
        
        # Удаляем лишние сообщения
        for message in old_messages:
            if message not in messages_list:
                message.delete()
        
        # Редактируем оставшиеся сообщения
        for i, old_message in enumerate(messages_list):
            new_message: Bot.Message = new_messages[i]
            
            if old_message.get_text() != new_message.get_text():
                old_message.set_text(new_message.get_text())

            if old_message.get_keyboard() != new_message.get_keyboard():
                old_message.set_keyboard(new_message.keyboard)
        
        # Добавляем новые сообщения
        return messages_list + new_messages[len(messages_list):]
        
    def send(self, bot: BOT, chat_id: int, compression: bool = True, parse_mode: str = ""):
        username: str = ""
        
        # Получаем цепочку сообщений
        messages: list[Bot.Message] = self.update(bot, messages = [], compression = compression)
        messages_list: list[Bot.Message] = []

        # Отправляем сообщения и сохраняем ответ сервера
        for message in messages:
            message: Vkbot.Message | Telebot.Message
            responses: dict[str, TelebotMessage] | None = message.send(chat_id, parse_mode = parse_mode)
            
            # Отправка одного сообщения ничего не вернёт
            # Но отправка группы вложений вернёт сразу несколько событий, которые надо обработать
            if responses:
                parsed: list[Telebot.Message] = bot.parse_responses(responses, datetime.now(), bot.group_id)
                
                if parsed:
                    username = parsed[0].get_username()
                    messages_list += parsed
                else:
                    username = message.get_username()
                    messages_list.append(message)
            else:
                username = message.get_username()
                messages_list.append(message)
            
            message.set_owner_id(bot.group_id)
        
        # Сохраняем сообщения для редактирования в дальнейшем
        # print(f"{messages_list=}")
        self.add_messages(bot, chat_id, bot.group_id, messages_list, compression, username, datetime.now())

    def edit(self, force_resend: bool = False, prevent_resend: bool = False):
        """
        Изменяет сообщение в чате у пользователя. Отправляет новые, если старых не хватает.
        :param force_resend: Если `True`, то переотправляет сообщение вместо редактирования, чтобы оно было последним в очереди.
        :param prevent_resend: Если `True`, то ни в коем случае не переотправляет сообщение, только редактирует.
        """
        for bot_key in self.messages:
            for chat_id in self.messages[bot_key]:
                messages_group: Message.MessagesGroup = self.get_last_group(bot_key, chat_id)
                bot: BOT = messages_group.bot
                compression: bool = messages_group.compression
                existing_messages: list[Bot.Message] = messages_group.messages
                expected_messages: list[Bot.Message] = self.update(bot, messages = existing_messages, compression = compression)
                result_messages: list[Bot.Message] = []
                
                for message in expected_messages:
                    responses: dict[str, TelebotMessage] | None = None
                    
                    if message.check_editable():
                        if force_resend:
                            message.delete()
                            responses = message.send(chat_id)
                        elif message.was_changed():
                            responses = message.edit(prevent_resend = prevent_resend)
                    else:
                        responses = message.send(chat_id)
                    
                    if responses:
                        parsed: list[Telebot.Message] = bot.parse_responses(responses, datetime.now(), bot.group_id)
                    
                        if parsed:
                            result_messages += parsed
                        else:
                            result_messages.append(message)
                    else:
                        result_messages.append(message)
                
                messages_group.messages = result_messages
    
    def delete(self, bot_key_filter: str | Any = Any, chat_id_filter: int | Any = Any):
        # print(f"deleting from {bot_key_filter=} {chat_id_filter=}",self)
        deleting: dict[str, list[int]] = {}
        
        for bot_key in self.messages:
            if bot_key_filter is Any or bot_key == bot_key_filter:
                for chat_id in self.messages[bot_key]:
                    if chat_id_filter is Any or chat_id == chat_id_filter:
                        messages_group: Message.MessagesGroup = self.get_last_group(bot_key, chat_id)
                        for message in messages_group.messages:
                            # print(f"deleting {message=} {message.check_editable()=}")
                            if message.check_editable():
                                message.delete()
                                
                                if bot_key in deleting:
                                    deleting[bot_key].append(chat_id)
                                else:
                                    deleting[bot_key] = [chat_id]
        
        for bot_key, chat_ids in deleting.items():
            for chat_id in chat_ids:
                del self.messages[bot_key][chat_id]
                
        # print(f"DELETED {bot_key_filter=} {chat_id_filter=} >>>", self.messages.get(bot_key_filter, {}).get(chat_id_filter, None))
    
    def resend(self, parse_mode: str = ""):
        recipients: dict[str, dict[int, BOT]] = {}
        
        for bot_key, chat_ids in self.messages.items():
            for chat_id, groups in chat_ids.items():
                if groups:
                    bot: BOT = groups[-1].bot
                    
                    if bot_key in recipients:
                        recipients[bot_key][chat_id] = bot
                    else:
                        recipients[bot_key] = {chat_id: bot}
        
        self.delete()
        self.messages.clear()
        
        for bot_key, bots in recipients.items():
            for chat_id, bot in bots.items():
                self.send(bot, chat_id, parse_mode = parse_mode)
                # print(f"resend {bot_key=} {chat_id=}", self.messages[bot_key][chat_id])

    def was_sent(self, bot_key: BOT_KEY, chat_id: int) -> bool:
        return bot_key in self.messages and chat_id in self.messages[bot_key]
    
    # Методы работы с полями
        
    def check_id(self, message_id: int) -> bool:
        return isinstance(message_id, int) and message_id >= 0

    def set_id(self, message_id: int):
        if self.check_id(message_id):
            self.id = message_id
        else:
            raise ValueError(f"Некорректное значение аргумента {message_id=}")

    def get_id(self) -> int:
        if self.check_id(self.id):
            return self.id
        else:
            raise ValueError(f"Некорректное значение атрибута {self.id=}")
    
    
    def set_text(self, text: str):
        """
        Устанавливает значение атрибута. Не изменяет сообщение в чате у пользователя.
        """
        self.text = text
    

    def add_recipient(self, bot_key: BOT_KEY, chat_id: int):
        bot_key: BOT_KEY = str(bot_key)
        chat_id: int = int(chat_id)
        
        if bot_key not in self.messages:
            self.messages[bot_key] = {}
        
        if chat_id not in self.messages[bot_key]:
            self.messages[bot_key][chat_id] = []

    def add_group(self, bot_key: BOT_KEY, chat_id: int, messages_group: MessagesGroup):
        self.add_recipient(bot_key, chat_id)

        # print(f"add_group {bot_key=} {chat_id=} {messages_group=}")
        
        if isinstance(messages_group, self.__class__.MessagesGroup):
            self.messages[bot_key][chat_id].append(messages_group)
        else:
            raise TypeError(f"Некорректное значение аргумента {messages_group=}")
    
    def add_messages(self, bot: BOT, chat_id: int, owner_id: int, messages: Iterable[Bot.Message], compression: bool, username: str, date: datetime):
        messages_group = self.__class__.MessagesGroup(bot, chat_id, owner_id, messages, username, date, compression)
        bot_key: BOT_KEY = bot.get_bot_key()
        # print(f"add_messages {bot_key=} {chat_id=} {messages=}")
        return self.add_group(bot_key, chat_id, messages_group)


    def has_groups(self, bot_key: BOT_KEY, chat_id: int) -> bool:
        return bot_key in self.messages and chat_id in self.messages[bot_key] and self.messages[bot_key][chat_id]
        
    def get_last_group(self, bot_key: BOT_KEY, chat_id: int) -> Message.MessagesGroup:
        if bot_key in self.messages and chat_id in self.messages[bot_key] and self.messages[bot_key][chat_id]:
            return self.messages[bot_key][chat_id][-1]
        else:
            raise RuntimeError(f"Сообщение не было отправлено на адрес {chat_id=}. Перед редактированием сначала отправьте его.")

    def set_filenames(self, filenames: Iterable[str]):
        self.filenames.clear()

        for filename in filenames:
            filename = abspath(normpath(str(filename)))
            if isfile(filename):
                self.filenames.append(filename)
            else:
                raise FileNotFoundError(filename)
    
    
    def check_keyboard(self, buttons: Iterable[str | Bot.Keyboard.Button], max_width: int, inline: bool) -> bool:
        if not isinstance(inline, bool):
            return False
        
        if (not isinstance(max_width, int)) or max_width < 1:
            return False
        
        return all(buttons, lambda button: isinstance(button, str) or isinstance(button, Bot.Keyboard.Button))
    
    def get_keyboard(self, bot: BOT, buttons: Iterable[str | Bot.Keyboard.Button]) -> Bot.Keyboard:
        if not isinstance(self.inline, bool):
            raise ValueError(f"Некорректное значение атрибута {self.inline=}")
        elif (not isinstance(self.max_width, int)) or self.max_width < 1:
            raise ValueError(f"Некорректное значение атрибута {self.max_width=}")
        else:
            buttons_list: list[Bot.Keyboard.Button] = []
            
            for button in buttons:
                if isinstance(button, Bot.Keyboard.Button):
                    pass
                elif isinstance(button, str):
                    button: Bot.Keyboard.Button = bot.__class__.Keyboard.Button(button)
                else:
                    raise ValueError(f"Некорректное значение атрибута {self.buttons=}")
                
                buttons_list.append(button)
            
            return bot.__class__.Keyboard(buttons_list, max_width = self.max_width, inline = self.inline)
        
    def set_keyboard(self, buttons: Iterable[str | Bot.Keyboard.Button] = [], inline: bool | None = None, max_width: int | None = None):
        """
        Устанавливает значение атрибута. Не изменяет сообщение в чате у пользователя.

        :param buttons: Список кнопок или пустой список
        :param inline: True - кнопки, прикреплённые к сообщению; False - кнопки, закреплённые под клавиатурой; None - по умолчанию (True).
        :param max_width: Максимальная ширина клавиатуры (количество кнопок в одном ряду); None - по умолчанию (2).
        """
        if inline is None:
            inline = self.inline
        
        if max_width is None:
            max_width = self.max_width
        
        if not isinstance(inline, bool):
            raise ValueError(f"Некорректное значение аргумента {inline=}")
        elif (not isinstance(max_width, int)) or max_width < 1:
            raise ValueError(f"Некорректное значение аргумента {max_width=}")
        elif not all(isinstance(button, str) or isinstance(button, Bot.Keyboard.Button) for button in buttons):
            raise ValueError(f"Некорректное значение аргумента {buttons=}")
        else:
            self.buttons = [Bot.Keyboard.Button(button) if isinstance(button, str) else button for button in buttons]
            self.max_width = int(max_width)
            self.inline = bool(inline)


    def get_last(self) -> tuple[BOT_KEY, datetime] | None:
        """
        Функция определяет последнее сообщение из всех групп и возвращает информацию о том, от какого бота и когда
        """
        dates: dict[BOT_KEY, list[datetime]] = {
            "vkbot": [],
            "telebot": []
        }

        for bot_key, groups in self.messages.items():
            if groups:
                group: Message.MessagesGroup = groups[-1]

                if group.messages:
                    for message in group.messages:
                        for key in Bot.BaseMessage.KEYS:
                            date: datetime | None = message.get_date(key)

                            if date:
                                if bot_key in dates:
                                    dates[bot_key].append(date)
                                else:
                                    dates[bot_key] = [date]
        
        if len(dates) == 1:
            bot_key: BOT_KEY = tuple(dates.keys())[0]
            return (bot_key, max(dates[bot_key]))
        elif not dates:
            return None
        
        max_date: datetime | None = None
        result: BOT_KEY | None = None

        for bot_key, dates_list in dates.items():
            date: datetime = max(dates_list)

            if max_date is None or date > max_date:
                max_date = date
                result = bot_key
        
        return (result, max_date)
