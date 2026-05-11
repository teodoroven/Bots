"""
Описывает runtime-операции для загрузки и проверки администраторов.
Модуль относится к архитектурной зоне: прикладной слой `relay`, который связывает пользователей, сессии, доменную модель, GPT, уведомления и runtime-логику приложения.

### Публичные классы
- `AdminsMixin`: runtime-логика администраторов.

### Публичные функции
- Публичные функции отсутствуют.

### Связи
Используется app-layer сценариями, обработчиками, сессиями и runtime-миксинами для единого пользовательского потока между ботами, GPT и storage.
"""

from __future__ import annotations



from relay.common import BotTypes
from relay.config import (
    DEFAULT_NOTIFICATIONS,
    DEFAULT_PERMISSIONS,
    NOTIFICATION_KEY,
    NOTIFICATION_KEYS,
    PERMISSION_KEY,
    PERMISSION_KEYS,
    SYSTEM_ADMIN_ACCESS_LEVEL,
    logger_admin,
)
from relay.users import Admin, User
from relay.utils import is_int
class AdminsMixin:
        """
        Добавляет `App` операции настройки администраторов без привязки к transport-layer.
        Mixin рассчитан на включение в `App` и работает с его registry, storage, пользователями, ботами и очередями.

        ### Методы
        - `load_admins`: Загружает настройки администраторов из storage.
        - `save_admins`: Сохраняет список администраторов и их права в storage.
        - `has_active_admins`: Проверяет наличие active admins.
        - `create_first_admin`: Создаёт first admin и связывает результат с текущим app-layer состоянием.
        - `get_admin_level`: Возвращает admin level из текущего состояния `AdminsMixin`.
        - `get_admin`: Возвращает администратора из текущего состояния `AdminsMixin`.
        - `can_promote_admin`: Сравнивает состояние объектов и возвращает флаг, который нужен перед отправкой или редактированием.
        - `can_promote_admin_by_chat`: Сравнивает состояние объектов и возвращает флаг, который нужен перед отправкой или редактированием.
        - `can_demote_admin`: Сравнивает состояние объектов и возвращает флаг, который нужен перед отправкой или редактированием.
        - `promote_admin`: Меняет уровень прав администратора и сохраняет обновлённое состояние пользователя.

        ### Жизненный цикл
        Создаётся app-layer кодом, участвует в обработке пользовательского события и сохраняет изменённое состояние через существующие runtime/storage механизмы.

        ### Пример использования
        ```py
        app: AdminsMixin
        ```
        """
        def load_admins(self):
            """
            Загружает настройки администраторов из storage.

            ### Примеры вызова:
            ```py
            app.load_admins()
            ```
            """
            data: BotTypes.ADMIN_FILE_TYPE = self.storage.load_admins() or {}

            self.admins_storage = {}

            for user_id, admin_data in data.items():

                if not is_int(user_id):

                    continue

                uid: int = int(user_id)

                access_level: int = int(admin_data.get("access_level") or 0)

                admin_permissions = dict(admin_data.get("permissions", {}))

                admin_notifications = dict(admin_data.get("notifications", {}))

                permissions: dict[PERMISSION_KEY, bool] = {

                    key: bool(admin_permissions.get(key, DEFAULT_PERMISSIONS[key]))

                    for key in PERMISSION_KEYS

                }

                notifications: dict[NOTIFICATION_KEY, bool] = {

                    key: bool(admin_notifications.get(key, DEFAULT_NOTIFICATIONS[key]))

                    for key in NOTIFICATION_KEYS

                }

                self.admins_storage[uid] = {

                    "access_level": access_level,

                    "permissions": permissions,

                    "notifications": notifications

                }

            logger_admin.info("Загружены настройки администраторов: count=%s", len(self.admins_storage))

        def save_admins(self):
            """
            Сохраняет список администраторов и их права в storage.

            ### Примеры вызова:
            ```py
            app.save_admins()
            ```
            """
            data: BotTypes.ADMIN_FILE_TYPE = {}

            for user_id, admin_data in self.admins_storage.items():

                permissions_data: dict[str, bool] = dict(admin_data.get("permissions", {}))

                notifications_data: dict[str, bool] = dict(admin_data.get("notifications", {}))

                permissions: dict[PERMISSION_KEY, bool] = {

                    key: bool(permissions_data.get(key, DEFAULT_PERMISSIONS[key]))

                    for key in PERMISSION_KEYS

                }

                notifications: dict[NOTIFICATION_KEY, bool] = {

                    key: bool(notifications_data.get(key, DEFAULT_NOTIFICATIONS[key]))

                    for key in NOTIFICATION_KEYS

                }

                data[str(user_id)] = {

                    "access_level": int(admin_data.get("access_level") or 0),

                    "permissions": permissions,

                    "notifications": notifications

                }

            self.storage.save_admins(data)

            logger_admin.info("Сохранены настройки администраторов: count=%s", len(data))

        def has_active_admins(self) -> bool:
            """
            Проверяет наличие active admins.

            :return: `True`, если наличие active admins; иначе `False`

            ### Пример использования:
            ```py
            adminsMixin.has_active_admins()
            ```
            """

            admin_data: dict[str, JSONABLE]

            for admin_data in self.admins_storage.values():

                if int(admin_data.get("access_level") or 0) > 0:

                    return True

            return False

        def create_first_admin(self, bot_key: BOT_KEY, chat_id: int) -> User:
            """
            Создаёт first admin и связывает результат с текущим объектом.

            ### Аргументы:
            :param bot_key: ключ транспорта
            :param chat_id: идентификатор чата

            :return: созданный объект: first admin

            :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

            ### Пример использования:
            ```py
            adminsMixin.create_first_admin(bot_key = bot_key, chat_id = chat_id)
            ```
            """

            bot: BOT = self.get_bot(bot_key)

            if not bot.check_chat_id(chat_id) or chat_id <= 0:

                raise ValueError(f"Некорректное значение аргумента {chat_id=}")

            user_id: int | None = self.find_user(bot_key, chat_id)

            if user_id is None:

                user: User = self.create_user(bot_key, chat_id)

            elif user_id in self.users:

                user = self.users[user_id]

            else:

                user = self.login_user(user_id, bot_key, chat_id)

            self.admins_storage[user.id] = {

                "access_level": SYSTEM_ADMIN_ACCESS_LEVEL,

                "permissions": {key: True for key in PERMISSION_KEYS},

                "notifications": dict(DEFAULT_NOTIFICATIONS)

            }

            user.access_level = SYSTEM_ADMIN_ACCESS_LEVEL

            user.save()

            self.save_admins()

            logger_admin.info(

                "Создан первый администратор: user_id=%s bot_key=%s access_level=%s",

                user.id,

                bot_key,

                SYSTEM_ADMIN_ACCESS_LEVEL,

            )

            return user

        def get_admin_level(self, user_id: int) -> int:
            """
            Возвращает уровень доступа администратора.

            ### Аргументы:
            :param user_id: user id

            :return: admin level

            ### Пример использования:
            ```py
            adminsMixin.get_admin_level(user_id = user_id)
            ```
            """
            return self.get_access_level(user_id)

        def get_admin(self, user_id: int) -> Admin:
            """
            Возвращает администратора по user id.

            ### Аргументы:
            :param user_id: user id

            :return: admin

            :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

            ### Пример использования:
            ```py
            adminsMixin.get_admin(user_id = user_id)
            ```
            """
            if user_id not in self.users:

                raise ValueError(f"Администратор с {user_id=} не найден среди активных пользователей")

            user: User = self.users[user_id]

            admin: Admin = Admin(user.id, user.chat_ids, self.get_admin_level(user_id))

            admin_data: dict[str, JSONABLE] = self.admins_storage.get(user_id, {})

            admin.permissions.update(dict(admin_data.get("permissions", {})))

            admin.notifications.update(dict(admin_data.get("notifications", {})))

            return admin

        def can_promote_admin(self, actor_id: int, target_id: int) -> bool:
            """
            Сравнивает состояние объектов и возвращает флаг, который нужен перед отправкой или редактированием.

            ### Аргументы:
            :param actor_id: actor id
            :param target_id: target id

            :return: значение, которое runtime использует для продолжения обработки события

            ### Пример использования:
            ```py
            adminsMixin.can_promote_admin(actor_id = actor_id, target_id = target_id)
            ```
            """
            actor_level: int = self.get_access_level(actor_id)

            target_level: int = self.get_access_level(target_id)

            return actor_level > 1 and target_level < actor_level - 1

        def can_promote_admin_by_chat(self, actor_id: int, bot_key: BOT_KEY, chat_id: int) -> bool:
            """
            Сравнивает состояние объектов и возвращает флаг, который нужен перед отправкой или редактированием.

            ### Аргументы:
            :param actor_id: actor id
            :param bot_key: ключ транспорта
            :param chat_id: идентификатор чата

            :return: значение, которое runtime использует для продолжения обработки события

            ### Пример использования:
            ```py
            adminsMixin.can_promote_admin_by_chat(actor_id = actor_id, bot_key = bot_key, chat_id = chat_id)
            ```
            """
            bot: BOT = self.get_bot(bot_key)

            if not bot.check_chat_id(chat_id) or chat_id <= 0:

                return False

            user_id: int | None = self.find_user(bot_key, chat_id)

            if user_id is None:

                actor_level: int = self.get_access_level(actor_id)

                return actor_level > 1

            return self.can_promote_admin(actor_id, user_id)

        def can_demote_admin(self, actor_id: int, target_id: int) -> bool:
            """
            Сравнивает состояние объектов и возвращает флаг, который нужен перед отправкой или редактированием.

            ### Аргументы:
            :param actor_id: actor id
            :param target_id: target id

            :return: значение, которое runtime использует для продолжения обработки события

            ### Пример использования:
            ```py
            adminsMixin.can_demote_admin(actor_id = actor_id, target_id = target_id)
            ```
            """
            actor_level: int = self.get_access_level(actor_id)

            target_level: int = self.get_access_level(target_id)

            return actor_level > 1 and 0 < target_level < actor_level

        def promote_admin(self, actor_id: int, user_id: int) -> bool:
            """
            Меняет уровень прав администратора и сохраняет обновлённое состояние пользователя.

            ### Аргументы:
            :param actor_id: actor id
            :param user_id: user id

            :return: значение, которое runtime использует для продолжения обработки события

            ### Пример использования:
            ```py
            adminsMixin.promote_admin(actor_id = actor_id, user_id = user_id)
            ```
            """
            old_level: int = self.get_access_level(user_id)

            self.set_access_level(user_id, old_level + 1, actor_id = actor_id)

            promoted: bool = self.get_access_level(user_id) > old_level

            logger_admin.info(

                "Повышение администратора: actor_id=%s target_user_id=%s old_level=%s new_level=%s changed=%s",

                actor_id,

                user_id,

                old_level,

                self.get_access_level(user_id),

                promoted,

            )

            return promoted

        def demote_admin(self, actor_id: int, user_id: int) -> bool:
            """
            Меняет уровень прав администратора и сохраняет обновлённое состояние пользователя.

            ### Аргументы:
            :param actor_id: actor id
            :param user_id: user id

            :return: значение, которое runtime использует для продолжения обработки события

            ### Пример использования:
            ```py
            adminsMixin.demote_admin(actor_id = actor_id, user_id = user_id)
            ```
            """
            old_level: int = self.get_access_level(user_id)

            self.set_access_level(user_id, old_level - 1, actor_id = actor_id)

            demoted: bool = self.get_access_level(user_id) < old_level

            logger_admin.info(

                "Понижение администратора: actor_id=%s target_user_id=%s old_level=%s new_level=%s changed=%s",

                actor_id,

                user_id,

                old_level,

                self.get_access_level(user_id),

                demoted,

            )

            return demoted

        def promote_admin_by_chat(self, actor_id: int, bot_key: BOT_KEY, chat_id: int) -> bool:
            """
            Меняет уровень прав администратора и сохраняет обновлённое состояние пользователя.

            ### Аргументы:
            :param actor_id: actor id
            :param bot_key: ключ транспорта
            :param chat_id: идентификатор чата

            :return: значение, которое runtime использует для продолжения обработки события

            :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

            ### Пример использования:
            ```py
            adminsMixin.promote_admin_by_chat(actor_id = actor_id, bot_key = bot_key, chat_id = chat_id)
            ```
            """
            bot: BOT = self.get_bot(bot_key)

            if not bot.check_chat_id(chat_id) or chat_id <= 0:

                raise ValueError(f"Некорректное значение аргумента {chat_id=}")

            user_id: int | None = self.find_user(bot_key, chat_id)

            if user_id is None:

                user: User = self.create_user(bot_key, chat_id, access_level = 0)

                user_id = user.id

            return self.promote_admin(actor_id, user_id)

        def can_change_permissions(self, actor_id: int, target_id: int) -> bool:
            """
            Сравнивает состояние объектов и возвращает флаг, который нужен перед отправкой или редактированием.

            ### Аргументы:
            :param actor_id: actor id
            :param target_id: target id

            :return: значение, которое runtime использует для продолжения обработки события

            ### Пример использования:
            ```py
            adminsMixin.can_change_permissions(actor_id = actor_id, target_id = target_id)
            ```
            """
            actor_level: int = self.get_access_level(actor_id)

            target_level: int = self.get_access_level(target_id)

            return actor_level > target_level

        def can_change_notifications(self, actor_id: int, target_id: int) -> bool:
            """
            Сравнивает состояние объектов и возвращает флаг, который нужен перед отправкой или редактированием.

            ### Аргументы:
            :param actor_id: actor id
            :param target_id: target id

            :return: значение, которое runtime использует для продолжения обработки события

            ### Пример использования:
            ```py
            adminsMixin.can_change_notifications(actor_id = actor_id, target_id = target_id)
            ```
            """
            actor_level: int = self.get_access_level(actor_id)

            target_level: int = self.get_access_level(target_id)

            if actor_id == target_id and actor_level > 0:

                return True

            return actor_level > target_level

        def toggle_admin_option(self, actor_id: int, user_id: int, category: Literal["notifications", "permissions"], key: str) -> bool:
            """
            Меняет флаг доступности или настройку объекта и оставляет остальное состояние без изменений.

            ### Аргументы:
            :param actor_id: actor id
            :param user_id: user id
            :param category: категория административной настройки
            :param key: ключ записи или настройки

            :return: значение, которое runtime использует для продолжения обработки события

            :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

            ### Пример использования:
            ```py
            adminsMixin.toggle_admin_option(actor_id = actor_id, user_id = user_id, category = category, key = key)
            ```
            """
            if category not in ("notifications", "permissions"):

                raise ValueError(f"Некорректная категория {category=}")

            if category == "permissions" and not self.can_change_permissions(actor_id, user_id):

                return False

            if category == "notifications" and not self.can_change_notifications(actor_id, user_id):

                return False

            user_data: dict[str, JSONABLE] = self.admins_storage.setdefault(user_id, {

                "access_level": 0,

                "permissions": dict(Admin(user_id, {}).permissions),

                "notifications": dict(Admin(user_id, {}).notifications)

            })

            options: dict[str, bool] = dict(user_data.get(category, {}))

            if key not in options:

                return False

            options[key] = not bool(options[key])

            user_data[category] = options

            self.admins_storage[user_id] = user_data

            self.save_admins()

            logger_admin.info(

                "Изменена настройка администратора: actor_id=%s target_user_id=%s category=%s key=%s enabled=%s",

                actor_id,

                user_id,

                category,

                key,

                options[key],

            )

            return True

        def set_access_level(self, user_id: int, access_level: int, actor_id: int | None = None):
            """
            Проверяет и записывает уровень доступа администратора.

            ### Аргументы:
            :param user_id: user id
            :param access_level: уровень доступа
            :param actor_id: actor id

            :raises ValueError: если значение нельзя привести к допустимому состоянию объекта

            :raises PermissionError: если нижележащий слой сообщает об ошибке операции

            ### Пример использования:
            ```py
            adminsMixin.set_access_level(user_id = user_id, access_level = access_level, actor_id = actor_id)
            ```
            """
            old_level: int = self.get_access_level(user_id)

            access_level = int(access_level)

            if actor_id is not None:

                if access_level > old_level:

                    if not self.can_promote_admin(actor_id, user_id):

                        raise PermissionError()

                    actor_level: int = self.get_access_level(actor_id)

                    access_level = min(access_level, actor_level - 1)

                elif access_level < old_level:

                    if not self.can_demote_admin(actor_id, user_id):

                        raise PermissionError()

                    access_level = max(0, access_level)

            access_level = max(0, int(access_level))

            if access_level >= 3:

                creators: list[int] = [uid for uid, data in self.admins_storage.items() if int(data.get("access_level") or 0) >= 3 and uid != user_id]

                if creators:

                    raise ValueError("В системе может быть только один Создатель")

            user_data: dict[str, JSONABLE] = self.admins_storage.setdefault(user_id, {

                "access_level": 0,

                "permissions": dict(Admin(user_id, {}).permissions),

                "notifications": dict(Admin(user_id, {}).notifications)

            })

            user_data["access_level"] = access_level

            self.admins_storage[user_id] = user_data

            user: User | None = self.users.get(user_id)

            if user:

                user.access_level = access_level

                user.save()

            self.save_admins()

            logger_admin.info(

                "Изменён уровень доступа администратора: actor_id=%s target_user_id=%s old_level=%s new_level=%s",

                actor_id,

                user_id,

                old_level,

                access_level,

            )

        def set_admin_level(self, user_id: int, access_level: int):
            """
            Проверяет и сохраняет значение `admin level` в `AdminsMixin`.

            ### Аргументы:
            :param user_id: внутренний идентификатор пользователя в app-layer
            :param access_level: уровень доступа пользователя или администратора

            ### Пример использования:
            ```py
            app.set_admin_level(user_id = user_id, access_level = access_level)
            ```
            """
            self.set_access_level(user_id, access_level)

        def check_access(self, context: Context):
            """
            Проверяет значение `access` перед сохранением или использованием.

            ### Аргументы:
            :param context: контекст обработки события

            :raises PermissionError: если нижележащий слой сообщает об ошибке операции

            ### Пример использования:
            ```py
            adminsMixin.check_access(context = context)
            ```
            """
            access_level: int = context.user.get_access_level()

            access_required: int = context.handler.access_level

            if access_level >= access_required:

                return

            else:

                raise PermissionError()
