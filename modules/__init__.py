"""
Открывает namespace пакета `modules`.
Модуль относится к архитектурной зоне: корневой compatibility-слой, который сохраняет общие настройки и файловые helper-функции.

### Публичные классы
- Публичные классы отсутствуют.

### Публичные функции
- `get_json_filenames`: возвращает основной и backup-путь JSON-документа.
- `readfile`: читает текстовый файл, если он существует.
- `readfiles`: читает первый существующий файл из списка.
- `only_directory`: возвращает директорию из пути файла.
- `log_warn`: записывает warning с traceback-контекстом.

### Публичные константы и типы
- Ключевые публичные значения: `ATTACHMENTS_FOLDER`, `JSON_FOLDER`, `GENERAL_COMMANDS_FILENAME`, `COMMON_COMMANDS_FILENAME`, `LANG_FILENAME`, `FILENAMES`.

### Связи
Используется соседними слоями проекта как корневой модуль запуска, compatibility exports или общий набор настроек.
"""

import logging
import traceback

from collections.abc import Iterable
from os import makedirs
from os.path import isdir
from os.path import isfile
from os.path import join
from os.path import dirname
from os.path import normpath


logger: logging.Logger = logging.getLogger("bot.storage")


ATTACHMENTS_FOLDER: str = "attachments"
JSON_FOLDER: str = "json"
GENERAL_COMMANDS_FILENAME: str = "general_commands.json"
COMMON_COMMANDS_FILENAME: str = "common_commands.json"
LANG_FILENAME: str = "lang.json"


FILENAMES: dict[str, tuple[str, str]] = {
    "lang": (JSON_FOLDER, LANG_FILENAME),
}


def get_json_filenames(key: str) -> tuple[str, str]:
    """
    Возвращает основной и резервный путь JSON-файла по ключу `FILENAMES`.

    ### Аргументы:
    :param key: ключ словаря `FILENAMES`

    :return: кортеж из имени JSON-файла и имени backup-файла
    """
    filename: str
    folder: str
    folder, filename = FILENAMES[key]
    result_filename: str = join(folder, filename)
    return result_filename, f"{result_filename}.backup"


def readfile(filename: str) -> str | None:
    """
    Читает текстовый файл с диска.
    Если файла нет, возвращает `None` и не создаёт новых файлов.

    ### Аргументы:
    :param filename: путь к файлу

    :return: содержимое файла или `None`
    """
    if isfile(filename):
        with open(filename, "r", encoding = "utf-8") as file:
            return file.read()

    return None


def readfiles(filenames: Iterable[str]) -> str | None:
    """
    Читает первый существующий файл из списка путей.
    Пути проверяются по порядку, что позволяет сначала пробовать основной файл,
    а затем backup.

    ### Аргументы:
    :param filenames: последовательность путей к файлам

    :return: содержимое первого найденного файла или `None`
    """
    filename: str

    for filename in filenames:
        content: str | None = readfile(str(filename))

        if content is not None:
            return content

    return None

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

    :return: Адрес директории из переданного адреса файла.
    - Если в адресе файла не указана директория, то будет возвращена пустая строка.
    - Результат будет содержать унифицированные разделители.
    """
    return dirname(normpath(file_path))


def log_warn(message: str):
    """
    Записывает warning вместе с текущим traceback-контекстом.

    ### Аргументы:
    :param message: сообщение, добавляемое после traceback
    """
    tb_str: str = traceback.format_exc()
    logger.warning(f"{tb_str.rstrip()}\n{message}\n")
