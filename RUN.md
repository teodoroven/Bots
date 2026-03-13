# Инструкция запуска

## 1) Подготовка окружения
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows
pip install --upgrade pip
pip install -r requirements.txt
```

## 2) Системные зависимости
Для корректной обработки аудио нужен `ffmpeg`:
- Linux: установить пакет `ffmpeg` через менеджер пакетов.
- Windows: установить `ffmpeg` и добавить в `PATH` или использовать локальные бинарники в `modules/ffmpeg/bin`.

## 3) Настройка токенов и параметров
Проект ожидает валидные токены API и идентификаторы групп/чатов для VK/Telegram.
Рекомендуется передавать секреты через переменные окружения или внешний конфиг, не коммитя их в репозиторий.

## 4) Запуск
В этом репозитории нет единой точки входа (`main.py`) с CLI-командой.
Обычно проект используется как модуль/библиотека из вашего прикладного скрипта.

Пример минимального smoke-импорта:
```bash
python -c "import callbacks; import modules; print('ok')"
```

## 5) Проверка работоспособности
```bash
python -m unittest discover -s tests -p "test_*.py"
```
