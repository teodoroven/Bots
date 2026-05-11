"""
Содержит helper-функции для разбора путей и подбора свободного имени файла.
Модуль относится к архитектурной зоне: слой унификации транспортов `bots`, который скрывает различия Telegram и VK за общими объектами сообщений, клавиатур, вложений и событий.

### Публичные классы
- Публичные классы отсутствуют.

### Публичные функции
- `only_extension`: возвращает расширение файла.
- `only_directory`: возвращает директорию из пути файла.
- `only_filename`: возвращает имя файла из пути.
- `change_extension`: создаёт имя файла с новым расширением.
- `create_filename`: создаёт свободное имя файла рядом с существующими файлами.

### Связи
Используется транспортным слоем и wrapper-логикой, чтобы app-layer работал с `Message`, `Keyboard`, `Button`, `Attachment` и `Event` без привязки к конкретной соцсети.
"""

from __future__ import annotations

from bots.compat import (
    Literal,
    basename,
    dirname,
    exists,
    join,
    normpath,
    splitext,
)
from bots.types import Literal

def only_extension(file_path: str) -> str | Literal[""]:
    """
    Извлекает расширение с точкой из имени файла.

    ### Примеры вызова:
    ```
    only_extension("") # ""
    only_extension(r"C:\\Users\\user\\Documents\\1.txt") # ".txt"
    only_extension(r"C:\\Users\\user\\Documents\\1.TXT") # ".TXT"
    only_extension(r"C:\\Users\\user\\Documents\\1.tXt") # ".tXt"
    only_extension(r"C:\\Users\\user\\Documents") # ""
    only_extension(r"C:\\Users\\user\\Documents\\1.") # "."
    only_extension(r"C:\\Users\\user\\Documents\\1.1.1.1") # ".1.1.1"
    only_extension("C:/Users/user/Documents/FiLeNaMe.TxT") # ".TxT"
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
    """
    Извлекает путь к директории из переданного пути файла.
    Если передан путь без директории, возвращается пустая строка. Последний
    компонент всегда считается именем файла, поэтому `r"C:\\Users\\user\\Documents"`
    вернёт `r"C:\\Users\\user"`, даже если `Documents` является папкой.

    ### Аргументы:
    :param file_path: путь к файлу

    ### Примеры вызова:
    ```
    only_directory("") # "."
    only_directory("filename.txt") # ""
    only_directory(r"C:\\Users\\user\\Documents\\1.txt") # r"C:\\Users\\user\\Documents"
    only_directory("C:/Users/user/Documents/1.txt") # "C:/Users/user/Documents"
    ```

    :return: директория из нормализованного пути
    """
    return dirname(normpath(file_path))

def only_filename(file_path: str) -> str:
    """
    Извлекает имя файла без расширения из переданного пути.

    ### Аргументы:
    :param file_path: путь к файлу

    ### Примеры вызова:
    ```
    only_filename("") # ""
    only_filename("filename") # "filename"
    only_filename(r"1.txt") # "1"
    only_filename(r"C:\\Users\\user\\Documents\\1.txt") # "1"
    only_filename("C:/Users/user/Documents/FiLeNaMe.TxT") # "FiLeNaMe"
    only_filename(r"C:\\Users\\user\\Documents\\1.") # "1"
    ```

    :return: имя последнего компонента пути без расширения
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
    """
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
    """
    Подбирает свободное имя файла в `folder`.
    Если `filename` уже существует, добавляет к имени суффиксы ` (2)`, ` (3)`
    и так далее, сохраняя расширение.

    ### Аргументы:
    :param folder: директория, где проверяется занятость имени
    :param filename: желаемое имя файла или путь, из которого берутся имя и расширение

    ### Примеры вызова:
    ```
    create_filename("downloads", "photo.jpg") # "downloads/photo.jpg"
    create_filename("downloads", "photo.jpg") # "downloads/photo (2).jpg", если первый путь занят
    ```

    :return: путь к первому свободному имени файла
    """
    fname: str = only_filename(filename)
    ext: str = only_extension(filename)

    result: str = f"{fname}{ext}"
    i: int = 1

    while exists(join(folder, result)):
        i += 1
        result = f"{fname} ({i}){ext}"

    return join(folder, result)
