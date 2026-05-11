"""

from __future__ import annotations

from bots.utils.audio import AudioSegment_directory
from bots.utils.audio import converter_filename
from bots.utils.audio import ffmpeg_filename
from bots.utils.audio import ffmpeg_program_name
from bots.utils.audio import ffprobe_filename
from bots.utils.audio import ffprobe_program_name
from bots.utils.audio import local_converter_filename
from bots.utils.audio import local_ffprobe_filename
from bots.utils.dates import diff_sec
from bots.utils.dates import get_date
from bots.utils.dates import get_timestamp
from bots.utils.dates import strftime
from bots.utils.env import get_env_int
from bots.utils.env import get_env_int_set
from bots.utils.files import change_extension
from bots.utils.files import create_filename
from bots.utils.files import only_directory
from bots.utils.files import only_extension
from bots.utils.files import only_filename
from bots.utils.mapping import get_from
from bots.utils.mapping import get_int
from bots.utils.mapping import is_int
from bots.utils.mapping import is_iterable
from bots.utils.text import cut
from bots.utils.text import preceding

__all__: list[str] = [
    "AudioSegment_directory",
    "change_extension",
    "converter_filename",
    "create_filename",
    "cut",
    "diff_sec",
    "ffmpeg_filename",
    "ffmpeg_program_name",
    "ffprobe_filename",
    "ffprobe_program_name",
    "get_date",
    "get_env_int",
    "get_env_int_set",
    "get_from",
    "get_int",
    "get_timestamp",
    "is_int",
    "is_iterable",
    "local_converter_filename",
    "local_ffprobe_filename",
    "only_directory",
    "only_extension",
    "only_filename",
    "preceding",
    "strftime",
]
Открывает namespace утилит транспортного слоя.
Модуль относится к архитектурной зоне: слой унификации транспортов `bots`, который скрывает различия Telegram и VK за общими объектами сообщений, клавиатур, вложений и событий.

### Публичные классы
- Публичные классы отсутствуют.

### Публичные функции
- Публичные функции отсутствуют.

### Связи
Используется транспортным слоем и wrapper-логикой, чтобы app-layer работал с `Message`, `Keyboard`, `Button`, `Attachment` и `Event` без привязки к конкретной соцсети.
"""

