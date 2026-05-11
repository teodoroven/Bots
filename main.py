"""
Точка запуска чат-бота автошколы из корня проекта.
Модуль относится к архитектурной зоне: корневой слой проекта, который связывает запуск, compatibility exports и общие настройки приложения.

### Публичные классы
- Публичные классы отсутствуют.

### Публичные функции
- `run_bot`: запускает приложение с текущими настройками runtime.

### Связи
Используется соседними слоями проекта как корневой модуль запуска, compatibility exports или общий набор настроек.
"""

from __future__ import annotations


import relay.public as _relay_public
from relay.bootstrap import run_bot as _run_bot

Autocenter = _relay_public.Autocenter

for _name in _relay_public.__all__:
    if _name != "run_bot":
        globals()[_name] = getattr(_relay_public, _name)

__all__: list[str] = [*(_name for _name in _relay_public.__all__ if _name != "run_bot"), "run_bot"]

del _name
del _relay_public


def run_bot(argv: list[str] | None = None) -> int:
    return _run_bot(argv = argv, app_class = Autocenter)


if __name__ == "__main__":
    raise SystemExit(run_bot())
