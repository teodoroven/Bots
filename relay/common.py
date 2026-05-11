"""
Собирает общие импорты и type aliases, используемые прикладными модулями `relay`.
Модуль относится к архитектурной зоне: прикладной слой `relay`, который связывает пользователей, сессии, доменную модель, GPT, уведомления и runtime-логику приложения.

### Публичные классы
- Публичные классы отсутствуют.

### Публичные функции
- Публичные функции отсутствуют.

### Публичные константы и типы
- Ключевые публичные значения: `T`.

### Связи
Используется app-layer сценариями, обработчиками, сессиями и runtime-миксинами для единого пользовательского потока между ботами, GPT и storage.
"""

from __future__ import annotations

import bots.types as BotTypes
from db.storage import SqlAlchemyStorage
from db.storage import Storage
from models import MODELS
from models import Model
from phrases import Phrases
from logs import setup_logging

import argparse
import json
import logging
import re
import requests
import sys
import tiktoken
import traceback

from abc import abstractmethod
from collections.abc import Callable
from collections.abc import Iterable
from contextlib import contextmanager
from datetime import datetime
from os import listdir
from os import remove
from os import rename
from openai import OpenAI
from queue import Empty
from queue import PriorityQueue
from threading import Lock
from threading import Thread
from time import sleep
from typing import Any
from typing import Generic
from typing import Literal
from typing import Never
from typing import TypeVar
from typing import Union
from dateutil.relativedelta import relativedelta

T = TypeVar("T")
