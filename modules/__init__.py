import requests
import json
import logging
import traceback
import sys
from os import makedirs
from os.path import isdir
from os.path import isfile
from os.path import join
from os.path import dirname
from os.path import normpath
from typing import Any
from typing import Iterable
class Debug():
    flag = True
    errors: list[tuple[str, list[str], Exception]] = []
    sent_errors: list[tuple[str, list[str], Exception]] = []
    def add_error(title: str, formatted_traceback: list[str], exception: Exception):
        error = (title, formatted_traceback, exception)
        s = "Group authorization failed: method is unavailable with group auth"
        for err in Debug.sent_errors:
            if s in str(err[1]) and s in str(err[1]):
                return
            elif s in str(err[2]) and s in str(err[2]):
                return
            elif error == err:
                return
        Debug.errors.append(error)
def setup_logging_with_rotation(log_file: str = "main.log", max_size_mb: int = 10, backup_count: int = 5):
    import logging
    from logging.handlers import RotatingFileHandler
    handler = RotatingFileHandler(
        log_file,
        maxBytes = max_size_mb * 1024 * 1024,
        backupCount = backup_count
    )
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger = logging.getLogger()
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger
logger = setup_logging_with_rotation()
def example_function():
    print("1")
    logger.debug("Начало выполнения функции")
    try:
        result = 10 / 2
        logger.info(f"Результат: {result}")
        print("2")
    except Exception as e:
        logger.error(f"Ошибка: {e}", exc_info=True)
        print("3")
    logger.debug("Завершение функции")
    print("4")
USERS_FOLDER: str = "users"
USERS_EXTENSION: str = ".json"
CHATS_FOLDER: str = "chats"
ATTACHMENTS_FOLDER: str = "attachments"
JSON_FOLDER: str = "json"
GENERAL_COMMANDS_FILENAME: str = "general_commands.json"
COMMON_COMMANDS_FILENAME: str = "common_commands.json"
USERS_FILENAME: str = "users.json"
GPT_FILENAME: str = "gpt.json"
ROOT_FILENAME: str = "root.json"
LANG_FILENAME: str = "lang.json"
BOTS_FILENAME: str = "bots.json"
DATA_FILENAME: str = "data.json"
FILENAMES: dict[str, str] = {
    "users": (JSON_FOLDER, USERS_FILENAME),
    "gpt": (JSON_FOLDER, GPT_FILENAME),
    "root": (JSON_FOLDER, ROOT_FILENAME),
    "lang": (JSON_FOLDER, LANG_FILENAME),
    "bots": (JSON_FOLDER, BOTS_FILENAME),
    "data": (JSON_FOLDER, DATA_FILENAME)
}
def get_filenames(directory: str, filename: str) -> tuple[str, str]:
    result_filename: str = join(directory, filename)
    return result_filename, f"{result_filename}.backup"
def get_json_filenames(key: str) -> tuple[str, str]:
    directory, filename = FILENAMES[key]
    return get_filenames(directory, filename)
def only_directory(file_path: str) -> str:
    return dirname(normpath(file_path))
def readfile(filename: str) -> str | None:
    if not isfile(filename):
        return None
    with open(filename, "r", encoding = "UTF-8") as file:
        return file.read()
def readfiles(filenames: Iterable[str]) -> str | None:
    for filename in filenames:
        content: str | None = readfile(filename)
        if content is not None:
            return content
def loadfiles(filenames: Iterable[str]) -> dict:
    for filename in filenames:
        content: str | None = readfile(filename)
        if content is not None:
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                pass
    return {}
def writefile(filename: str, content: str) -> Exception | None:
    directory: str = only_directory(filename)
    if not isdir(directory):
        makedirs(directory)
    with open(filename, "w", encoding = "UTF-8") as file:
        file.write(content)
def writefiles(filenames: Iterable[str], content: str) -> dict[str, list[Exception]]:
    exceptions: dict[str, list[Exception]] = {}
    for filename in filenames:
        exception: Exception | None = writefile(filename, content)
        if exception is not None:
            if filename in exceptions:
                exceptions[filename].append(exception)
            else:
                exceptions[filename] = [exception]
    return exceptions
def savefiles(filenames: Iterable[str], data: dict) -> Exception | None:
    if not filenames:
        return ValueError("filenames must be not empty")
    try:
        content: str = json.dumps(data)
    except Exception as err:
        return err
    exceptions: dict[str, list[Exception]] = writefiles(filenames, content)
    if len(exceptions) == len(set(filenames)):
        return exceptions.values()[0][0]
def log_warn(message: str):
    import traceback
    tb_str = traceback.format_exc()
    logger.warning(f"{tb_str.rstrip()}\n{message}\n")
    Console.warning(f"{tb_str.rstrip()}\n{message}\n")
def combine(*strings: Iterable[Any], separator: str = " ", end: str = "") -> str:  
    result: str = str()
    for s in strings:
        result = f"{result}{str(separator)}{str(s)}" if result else str(s)
    return f"{result}{end}"
class Console():  
    colorized = True
    input_active = []
    def get_value_from(key, dictionary, miss = None):
        dict_key: str = str(key).lower()
        if dict_key in dictionary:
            return dictionary[dict_key]
        else:
            return miss
    def get_effect_code(effect):
        effects = {
            'reset': 0,
            'bold': 1,
            'faded': 2,
            'cursive': 3,
            'underline': 4,
            'blinking': 5,
            'flashing': 6,
            'color': 7,
        }
        return Console.get_value_from(effect, effects)
    def get_color_number(color):
        colors = {
            'black': 0,
            'red': 1,
            'green': 2,
            'yellow': 3,
            'blue': 4,
            'purple': 5,
            'lightblue': 6,
            'white': 7,
        }
        if color == 'rainbow':
            for color in colors:
                Console.print(color, color = color)
        return Console.get_value_from(color, colors)
    def get_color_code(decade, color):
        try:
            return decade + Console.get_color_number(color)
        except TypeError:
            return None
    def get_text_color(color):
        return Console.get_color_code(30, color)
    def get_background_color(color):
        return Console.get_color_code(40, color)
    def colorize(*strings, **config):
        get = config.get
        string = combine(*strings)
        if Console.colorized:
            for key in ('effect', 'color', 'background'):
                code = get(key)
                if code != None:
                    string = "\033[{}m{}".format(code, string)
            string += "\033[0m"
        return string
    def decorate(*strings, **config):
        get = config.get
        string = combine(*strings)
        effect = Console.get_effect_code(get('effect'))
        color = Console.get_text_color(get('color'))
        background = Console.get_background_color(get('background'))
        end = get('end') or "\n"
        return Console.colorize(string, effect = effect, color = color, background = background, end = end)
    def _output(*strings, **config):
        get = config.get
        string = combine(*strings)
        end = get('end', "\n")
        return print(string, end = end)
    def output(*strings, **config):
        get = config.get
        string = Console.colorize(combine(*strings), log = strings, **config)
        return Console._output(string)
    def print(*strings, **config):
        get = config.get
        string = Console.decorate(combine(*strings), **config)
        return Console._output(string, log = strings, **config)
    def success(*strings, **config):
        get = config.get
        string = combine(*strings)
        return Console.print(string, color = "green", end = get('end'))
    def info(*strings, **config):
        get = config.get
        string = combine(*strings)
        return Console.print(string, color = "blue", end = get('end'))
    def log(*elements, **config):
        get = config.get
        result = []
        for elem in elements:
            match elem:
                case None:
                    color = "purple"
                case bool(elem):
                    color = "purple"
                case int(elem) | float(elem):
                    color = "blue"
                case str(elem):
                    color = "green"
                case _:
                    color = "white"
            result.append(Console.decorate(str(elem), color = color))
        Console.print(*result, end = get('end'))
    def warning(*strings, **config):
        get = config.get
        string = combine(*strings)
        return Console.print(string, color = "yellow", end = get('end'))
    def error(*strings, **config):
        get = config.get
        string = combine(*strings)
        return Console.print(string, color = "red", end = get('end'))
    def loading(*strings, **config):
        get = config.get
        string = combine(*strings) + "..."
        return Console.print(string, color = "purple", end = get('end'))
    def change_colorize(enable):
        Console.colorized = enable
        return enable
    def disable_colors():
        return Console.change_color(False)
    def enable_colors():
        return Console.change_color(True)