"""
Описывает базовые сущности модуля.
Модуль относится к архитектурной зоне: слой хранения `db`, который изолирует SQLAlchemy, репозитории и документы состояния от app-layer.

### Публичные классы
- `Base`: базовый declarative-класс SQLAlchemy ORM.

### Публичные функции
- Публичные функции отсутствуют.

### Публичные константы и типы
- Ключевые публичные значения: `NAMING_CONVENTION`.

### Связи
Используется storage-слоем и runtime-логикой приложения для чтения, сохранения и миграции состояния без прямой зависимости app-layer от деталей SQLAlchemy.
"""

from __future__ import annotations

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase


NAMING_CONVENTION: dict[str, str] = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """
    `Base` описывает storage-объект, через который слой `db` работает с таблицами или репозиториями.

    ### Поля
    - `metadata`: SQLAlchemy metadata базовой declarative-модели.

    ### Жизненный цикл
    Объект создаётся на время storage-операции или описывает таблицу; внешние слои работают через storage API и не управляют SQLAlchemy-сессией напрямую.

    ### Пример использования
    ```py
    base: Base
    ```
    """
    metadata: MetaData = MetaData(naming_convention = NAMING_CONVENTION)
