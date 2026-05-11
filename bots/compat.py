from __future__ import annotations

from callbacks import CALLBACK_REMOVE
from modules import ATTACHMENTS_FOLDER
from modules import makedirs
from modules import isdir
from modules import dirname
import bots.types as BotTypes

import re
import logging
import json
import requests
import traceback
from abc import abstractmethod
from requests import Response
from time import sleep
from threading import Thread
from datetime import datetime
from datetime import timedelta
from io import BufferedReader, BytesIO
from PIL import Image
from warnings import warn
from itertools import chain
from typing import Literal
from typing import Union
from typing import Any
from typing import NoReturn
from typing import Callable
from collections.abc import Iterable

try:
    from typing import Never
except ImportError:
    Never: Any = NoReturn

from os import getcwd
from os.path import basename
from os.path import join
from os.path import abspath
from os.path import normpath
from os.path import isfile
from os.path import exists
from os.path import splitext
from os import getenv
from os import name as os_name
from shutil import which

from vk_api import VkApi
from vk_api import VkUpload
from vk_api.utils import get_random_id
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType, DotDict, VkBotEvent
from vk_api.bot_longpoll import VkBotMessageEvent
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from vk_api.exceptions import ApiError

from telebot import TeleBot
from telebot.types import ReplyKeyboardMarkup
from telebot.types import KeyboardButton
from telebot.types import InlineKeyboardMarkup
from telebot.types import InlineKeyboardButton
from telebot.types import InputMediaPhoto
from telebot.types import InputMediaVideo
from telebot.types import InputMediaAudio
from telebot.types import InputMediaDocument
from telebot.types import Message as TelebotMessage
from telebot.types import CallbackQuery
from telebot.types import File
from telebot.types import Voice
from telebot.types import PhotoSize
from telebot.types import Video
from telebot.types import Document
from telebot.types import Audio
from telebot.apihelper import ApiTelegramException

from speech_recognition import Recognizer
from speech_recognition import AudioData
from speech_recognition import WavFile
from speech_recognition import AudioFile
from speech_recognition import UnknownValueError

from dotenv import load_dotenv
from pydub import AudioSegment

load_dotenv()
