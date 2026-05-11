"""
Создаёт SQLAlchemy engine, URL подключения и context manager для сессий базы данных.
Модуль относится к архитектурной зоне: слой хранения `db`, который изолирует SQLAlchemy, репозитории и документы состояния от app-layer.

### Публичные классы
- Публичные классы отсутствуют.

### Публичные функции
- `get_secret_value`: получает секретное значение из строки или файла.
- `build_postgres_url`: создаёт PostgreSQL URL из переменных окружения.
- `get_database_url`: возвращает URL базы данных приложения.
- `get_database_echo`: возвращает настройку SQLAlchemy echo.
- `create_db_engine`: создаёт SQLAlchemy engine приложения.
- `get_db_session`: создаёт context manager для `Session` базы данных.

### Публичные константы и типы
- Ключевые публичные значения: `DEFAULT_DATABASE_URL`.

### Связи
Используется storage-слоем и runtime-логикой приложения для чтения, сохранения и миграции состояния без прямой зависимости app-layer от деталей SQLAlchemy.
"""

from __future__ import annotations

from contextlib import contextmanager
from os import getenv
from urllib.parse import quote

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv


load_dotenv()


DEFAULT_DATABASE_URL: str = "sqlite:///autocenter_bot.db"


def get_secret_value(value_key: str, file_key: str) -> str:
    value: str = getenv(value_key, "").strip()

    if value:
        return value

    file_path: str = getenv(file_key, "").strip()

    if not file_path:
        return ""

    with open(file_path, "r", encoding = "utf-8") as file:
        return file.read().strip()


def build_postgres_url() -> str:
    host: str = getenv("DATABASE_HOST", "").strip()

    if not host:
        return ""

    driver: str = getenv("DATABASE_DRIVER", "postgresql+psycopg").strip()
    user: str = getenv("DATABASE_USER", "").strip()
    password: str = get_secret_value("DATABASE_PASSWORD", "DATABASE_PASSWORD_FILE")
    port: str = getenv("DATABASE_PORT", "5432").strip()
    name: str = getenv("DATABASE_NAME", "").strip()

    if not user or not password or not name:
        return ""

    encoded_user: str = quote(user, safe = "")
    encoded_password: str = quote(password, safe = "")

    return f"{driver}://{encoded_user}:{encoded_password}@{host}:{port}/{name}"


def get_database_url() -> str:
    value: str = getenv("DATABASE_URL", "").strip()
    return value or build_postgres_url() or DEFAULT_DATABASE_URL


def get_database_echo() -> bool:
    value: str = getenv("DATABASE_ECHO", "0").strip().lower()
    return value in ("1", "true", "yes", "on")


def create_db_engine(database_url: str | None = None, echo: bool | None = None) -> Engine:
    url: str = database_url or get_database_url()
    show_sql: bool = get_database_echo() if echo is None else bool(echo)
    return create_engine(
        url,
        echo = show_sql,
        future = True,
        pool_pre_ping = True,
    )


engine: Engine = create_db_engine()
SessionLocal: sessionmaker[Session] = sessionmaker(
    bind = engine,
    autoflush = False,
    autocommit = False,
    expire_on_commit = False,
)


@contextmanager
def get_db_session(session_factory: sessionmaker[Session] = SessionLocal):
    session: Session = session_factory()

    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
