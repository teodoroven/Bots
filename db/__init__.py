"""
Открывает namespace storage-слоя `db`.
Модуль относится к архитектурной зоне: слой хранения `db`, который изолирует SQLAlchemy, репозитории и документы состояния от app-layer.

### Публичные классы
- Публичные классы отсутствуют.

### Публичные функции
- Публичные функции отсутствуют.

### Связи
Используется storage-слоем и runtime-логикой приложения для чтения, сохранения и миграции состояния без прямой зависимости app-layer от деталей SQLAlchemy.
"""

from db.base import Base
from db.session import SessionLocal
from db.session import get_db_session
from db.storage import SqlAlchemyStorage
from db.storage import Storage

__all__: list[str] = [
    "Base",
    "SessionLocal",
    "Storage",
    "SqlAlchemyStorage",
    "get_db_session",
]
