"""
Настраивает `pydub.AudioSegment` для обработки голосовых и аудио-вложений.
Модуль относится к utility-части transport-layer `bots`. Сначала он ищет
локальные `ffmpeg` и `ffprobe` в `modules/ffmpeg/bin`; на Windows ожидаются
имена `ffmpeg.exe` и `ffprobe.exe`. Если локальных файлов нет, используется
системный путь из `which`, а затем стандартные имена программ.

Найденные пути назначаются в `AudioSegment.converter`, `AudioSegment.ffmpeg`
и `AudioSegment.ffprobe`, чтобы Telegram/VK voice/audio conversion работала
без повторной настройки в transport-классах. Если итоговые пути не указывают
на локальные файлы, модуль выводит предупреждения, но оставляет системный
поиск `ffmpeg` доступным.
"""

from __future__ import annotations

from bots.compat import (
    AudioSegment,
    getcwd,
    isfile,
    join,
    os_name,
    warn,
    which,
)

AudioSegment_directory: str = join(getcwd(), "modules", "ffmpeg", "bin")
ffmpeg_program_name: str = "ffmpeg.exe" if os_name == "nt" else "ffmpeg"
ffprobe_program_name: str = "ffprobe.exe" if os_name == "nt" else "ffprobe"
local_converter_filename: str = join(AudioSegment_directory, ffmpeg_program_name)
local_ffprobe_filename: str = join(AudioSegment_directory, ffprobe_program_name)
converter_filename: str = (
    local_converter_filename
    if isfile(local_converter_filename)
    else which("ffmpeg") or "ffmpeg"
)
ffmpeg_filename: str = converter_filename
ffprobe_filename: str = (
    local_ffprobe_filename
    if isfile(local_ffprobe_filename)
    else which("ffprobe") or "ffprobe"
)

AudioSegment.converter = converter_filename
AudioSegment.ffmpeg = ffmpeg_filename
AudioSegment.ffprobe = ffprobe_filename

if not isfile(converter_filename):
    warn(converter_filename)

if not isfile(ffmpeg_filename):
    warn(ffmpeg_filename)

if not isfile(ffprobe_filename):
    warn(ffprobe_filename)
