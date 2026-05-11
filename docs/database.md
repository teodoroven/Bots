# Database

Проект хранит рабочее состояние в SQL-базе через `SQLAlchemy` и управляет схемой через `Alembic`.

Файлы `json/lang.json`, `json/general_commands.json`, `json/common_commands.json` остаются публичными ресурсами проекта: они содержат фразы и определения команд. Реальные пользовательские данные, логи, вложения и локальная история сообщений не публикуются.

## Локальный SQLite: Windows

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Минимальные значения в `.env`:

```env
DATABASE_URL=sqlite:///autocenter_bot.db
DATABASE_ECHO=0
STORAGE_BACKEND=sql
```

Подготовка базы:

```powershell
alembic upgrade head
```

Проверка запуска без polling:

```powershell
python main.py --check-startup
```

Команда ожидает уже сохранённые конфигурации ботов в storage. На пустой локальной
базе ошибка отсутствующей bot config считается нормальным результатом.

## Локальный SQLite: Linux/macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp .env.example .env
```

Минимальные значения в `.env`:

```env
DATABASE_URL=sqlite:///autocenter_bot.db
DATABASE_ECHO=0
STORAGE_BACKEND=sql
```

Подготовка базы:

```bash
alembic upgrade head
```

Проверка запуска без polling:

```bash
python main.py --check-startup
```

Команда ожидает уже сохранённые конфигурации ботов в storage. На пустой локальной
базе ошибка отсутствующей bot config считается нормальным результатом.

## PostgreSQL на сервере

Создайте пользователя и базу данных, подставив пароль только на сервере:

```bash
sudo -u postgres createuser autocenter_bot_user
sudo -u postgres createdb autocenter_bot --owner=autocenter_bot_user
sudo -u postgres psql -c "ALTER USER autocenter_bot_user WITH PASSWORD '<your-password>';"
```

В `.env` используйте отдельные поля, чтобы пароль не был частью URL:

```env
DATABASE_URL=
DATABASE_DRIVER=postgresql+psycopg
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=autocenter_bot
DATABASE_USER=autocenter_bot_user
DATABASE_PASSWORD=<your-password>
DATABASE_ECHO=0
STORAGE_BACKEND=sql
```

Применение миграций:

```bash
alembic upgrade head
```

## Docker Compose

Создайте `.env` и secret-файл:

```bash
cp .env.example .env
mkdir -p .secrets
printf '%s' '<your-postgres-password>' > .secrets/postgres_password
```

Для Docker оставьте `DATABASE_URL` пустым:

```env
DATABASE_URL=
DATABASE_ECHO=0
STORAGE_BACKEND=sql
```

Запуск:

```bash
docker compose up -d db
docker compose run --rm bot alembic upgrade head
docker compose up -d bot
```

## Новая миграция Alembic

Создание новой миграции:

```bash
alembic revision --autogenerate -m "message"
```

Применение миграций:

```bash
alembic upgrade head
```

## Проверки

```bash
git diff --check
python -m unittest discover tests -p "*_test.py"
```
