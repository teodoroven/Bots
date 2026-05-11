"""
Описывает runtime-операции над доменным деревом автошколы.
Модуль относится к архитектурной зоне: прикладной слой `relay`, который связывает пользователей, сессии, доменную модель, GPT, уведомления и runtime-логику приложения.

### Публичные классы
- `DomainMixin`: runtime-логика доменной структуры.

### Публичные функции
- Публичные функции отсутствуют.

### Связи
Используется app-layer сценариями, обработчиками, сессиями и runtime-миксинами для единого пользовательского потока между ботами, GPT и storage.
"""

from __future__ import annotations



from relay.common import BotTypes, Iterable, datetime
from relay.domain import Date
from relay.domain import Element
from relay.domain import Filial
from relay.domain import Folder
from relay.domain import Limit
from relay.domain import NamedElement
from relay.domain import NamedFolder
from relay.domain import Question
from relay.domain import SystemContext
from relay.utils import get_month_date, get_month_string, log_warn
class DomainMixin:
        """
        Добавляет `App` операции domain без привязки к transport-layer.
        Mixin рассчитан на включение в `App` и работает с его registry, storage, пользователями, ботами и очередями.

        ### Методы
        - `create_id`: Создаёт id и связывает результат с текущим app-layer состоянием.
        - `find_element`: Ищет элемент доменной модели по данным, которые пришли из вызывающего слоя.
        - `restore_element`: Восстанавливает ранее удалённый или сериализованный объект в рабочее состояние.
        - `change_element`: Координирует runtime-состояние приложения между очередями, пользователями и transport-layer.
        - `extend_element`: Координирует runtime-состояние приложения между очередями, пользователями и transport-layer.
        - `enable_element`: Меняет флаг доступности или настройку объекта и оставляет остальное состояние без изменений.
        - `disable_element`: Меняет флаг доступности или настройку объекта и оставляет остальное состояние без изменений.
        - `remove_element`: Удаляет элемент доменной модели из внутреннего состояния или storage.
        - `add_element`: Привязывает доменный элемент к текущему контейнеру.
        - `load_classname`: Загружает classname из storage.

        ### Жизненный цикл
        Создаётся app-layer кодом, участвует в обработке пользовательского события и сохраняет изменённое состояние через существующие runtime/storage механизмы.

        ### Пример использования
        ```py
        app: DomainMixin
        ```
        """
        def create_id(self) -> int:
            """
            Создаёт id и связывает результат с текущим app-layer состоянием.

            :return: созданный объект для id

            ### Примеры вызова:
            ```py
            app.create_id()
            ```
            """
            if hasattr(self, "storage") and getattr(self, "persist_ids", True):

                self.element_id = self.storage.next_id("element")

            else:

                self.element_id += 1

            return self.element_id

        def find_element(self, element_id: int, element_class: type[Element] = Element) -> Element | None:
            """
            Ищет доменный элемент в текущих данных объекта или storage.

            ### Аргументы:
            :param element_id: идентификатор доменного элемента
            :param element_class: element class

            :return: доменный элемент или None, если подходящей записи нет

            :raises KeyError: если обязательный ключ отсутствует в registry или payload

            ### Пример использования:
            ```py
            domainMixin.find_element(element_id = element_id, element_class = element_class)
            ```
            """
            element: Element | None = self.elements.get(element_id, None)

            if element:

                if isinstance(element, element_class):

                    return element

                else:

                    id = element_id

                    raise KeyError(f"Идентификатор {id=} используется повторно. Ожидался элемент {element_class}, а получен {element=}")

            else:

                return None

        def restore_element(self, element_id: int) -> int | None:
            """
            Восстанавливает ранее удалённый или сериализованный объект в рабочее состояние.

            ### Аргументы:
            :param element_id: идентификатор доменного элемента

            :return: значение, которое runtime использует для продолжения обработки события

            ### Пример использования:
            ```py
            domainMixin.restore_element(element_id = element_id)
            ```
            """
            element: Element | None = self.find_element(element_id)

            if element.removed_from is not None:

                removed_from: int = int(element.removed_from)

                element.removed_from = None

                self.add_element(element, removed_from)

                self.save_root()

                return removed_from

            else:

                return None

        def change_element(self, element_id: int, content: str) -> bool:
            """
            Координирует runtime-состояние приложения между очередями, пользователями и transport-layer.

            ### Аргументы:
            :param element_id: идентификатор доменного элемента
            :param content: содержимое доменного элемента

            :return: значение, которое runtime использует для продолжения обработки события

            ### Пример использования:
            ```py
            domainMixin.change_element(element_id = element_id, content = content)
            ```
            """
            element: Element | None = self.find_element(element_id)

            result: bool = element.set_content(content)

            if result:

                self.save_root()

                if element_id in self.contexts or element_id in self.questions:

                    self.save_gpt()

            return result

        def extend_element(self, element_id: int, content: str) -> bool:
            """
            Координирует runtime-состояние приложения между очередями, пользователями и transport-layer.

            ### Аргументы:
            :param element_id: идентификатор доменного элемента
            :param content: содержимое доменного элемента

            :return: значение, которое runtime использует для продолжения обработки события

            ### Пример использования:
            ```py
            domainMixin.extend_element(element_id = element_id, content = content)
            ```
            """
            element: Element | None = self.find_element(element_id)

            result: bool = element.add_content(content)

            if result:

                self.save_root()

                if element_id in self.contexts or element_id in self.questions:

                    self.save_gpt()

            return result

        def enable_element(self, element_id: int) -> bool:
            """
            Меняет флаг доступности или настройку объекта и оставляет остальное состояние без изменений.

            ### Аргументы:
            :param element_id: идентификатор доменного элемента

            :return: значение, которое runtime использует для продолжения обработки события

            ### Пример использования:
            ```py
            domainMixin.enable_element(element_id = element_id)
            ```
            """
            element: InteractiveMixin | None = self.find_element(element_id, InteractiveMixin)

            was_enabled: bool = element.enabled

            element.enabled = True

            self.save_root()

            return was_enabled != element.enabled

        def disable_element(self, element_id: int) -> bool:
            """
            Меняет флаг доступности или настройку объекта и оставляет остальное состояние без изменений.

            ### Аргументы:
            :param element_id: идентификатор доменного элемента

            :return: значение, которое runtime использует для продолжения обработки события

            ### Пример использования:
            ```py
            domainMixin.disable_element(element_id = element_id)
            ```
            """
            element: InteractiveMixin | None = self.find_element(element_id, InteractiveMixin)

            was_enabled: bool = element.enabled

            element.enabled = False

            self.save_root()

            return was_enabled != element.enabled

        def remove_element(self, element_id: int, from_id: int | None = None) -> bool:
            """
            Удаляет доменный элемент из текущего контейнера.

            ### Аргументы:
            :param element_id: идентификатор доменного элемента
            :param from_id: id контейнера, из которого удалён элемент

            :return: значение, которое runtime использует для продолжения обработки события

            ### Пример использования:
            ```py
            domainMixin.remove_element(element_id = element_id, from_id = from_id)
            ```
            """
            removed: bool = False

            element: Element | None = self.find_element(element_id)

            if element:

                element.removed_from = from_id

                if from_id is None:

                    element.removed_from = -1

            if element_id in self.elements:

                del self.elements[element_id]

                removed = True

            if from_id is not None and element is not None:

                folder: Folder | None = self.find_element(from_id, Folder)

                if folder is not None:



                    r = folder.remove_id(element_id)


                    removed = removed or r

            self.save_root()

            # if element:


            # else:


            return removed

        def add_element(self, element: Element, container_id: int | None = None):
            """
            Привязывает доменный элемент к текущему контейнеру.

            ### Аргументы:
            :param element: доменный элемент
            :param container_id: container id

            :raises KeyError: если обязательный ключ отсутствует в registry или payload

            ### Пример использования:
            ```py
            domainMixin.add_element(element = element, container_id = container_id)
            ```
            """
            if element.id in self.elements and element is not self.elements[element.id]:

                id: int = element.id

                log_warn(f"Перезапись элемента с идентификатором {id=}\nБыло: {self.find_element(id)}\nСтало: {element}")


            self.elements[element.id] = element

            if container_id is not None:

                container: Folder | None = self.find_element(container_id, Folder)

                container.add_element(element)

            if element.id == self.filials_folder.id:

                if isinstance(element, FilialsFolder):

                    self.filials_folder = element

                else:

                    id = element.id

                    raise KeyError(f"Идентификатор {id=} используется повторно. Ожидался элемент {FilialsFolder}, а получен {type(element)}")

            elif element.id == self.contexts_folder.id:

                if isinstance(element, ContextsFolder):

                    self.contexts_folder = element

                else:

                    id = element.id

                    raise KeyError(f"Идентификатор {id=} используется повторно. Ожидался элемент {ContextsFolder}, а получен {type(element)}")

            elif element.id == self.questions_folder.id:

                if isinstance(element, QuestionsFolder):

                    self.questions_folder = element

                else:

                    id = element.id

                    raise KeyError(f"Идентификатор {id=} используется повторно. Ожидался элемент {QuestionsFolder}, а получен {type(element)}")

            elif element.id == self.limits_folder.id:

                if isinstance(element, LimitsFolder):

                    self.limits_folder = element

                else:

                    id = element.id

                    raise KeyError(f"Идентификатор {id=} используется повторно. Ожидался элемент {LimitsFolder}, а получен {type(element)}")

            elif element.id == self.dates_folder.id:

                if isinstance(element, DatesFolder):

                    self.dates_folder = element

                else:

                    id = element.id

                    raise KeyError(f"Идентификатор {id=} используется повторно. Ожидался элемент {DatesFolder}, а получен {type(element)}")

            elif isinstance(element, Filial):

                self.filials[element.id] = element

                if element.id == self.theory_online.id or element.name == "Теория онлайн":

                    self.theory_online = element

            elif isinstance(element, Date):

                self.dates[element.id] = element

            elif isinstance(element, SystemContext):

                self.contexts[element.id] = element

                system_context = element


            elif isinstance(element, Question):

                self.questions[element.id] = element

            elif isinstance(element, Limit):

                self.limits[element.id] = element

        def load_classname(self, element_class: type[Element], data: BotTypes.ELEMENT_TYPE) -> Element:
            """
            Загружает данные из storage или внешнего transport/API и приводит их к объектам проекта.

            ### Аргументы:
            :param element_class: element class
            :param data: сериализованный словарь

            :return: значение, которое runtime использует для продолжения обработки события

            ### Пример использования:
            ```py
            domainMixin.load_classname(element_class = element_class, data = data)
            ```
            """
            if element_class in self.__class__.FOLDERS:

                element = element_class.loads(data, self.load_element)

            else:

                element = element_class.loads(data)

            self.add_element(element)

            return element

        def load_element(self, data: BotTypes.ELEMENT_TYPE) -> Element | NamedFolder:
            """
            Загружает элемент доменной модели из storage.

            ### Аргументы:
            :param data: JSON-совместимые данные для соответствующего repository

            :return: сериализованные данные для элемент доменной модели

            :raises ValueError: если значение не проходит локальную проверку перед сохранением

            ### Пример использования:
            ```py
            app.load_element(data = data)
            ```
            """
            self.element_id += 1

            element_id: int | None = get_int(data, None, "id")

            if element_id is not None and element_id > self.element_id:

                self.element_id = int(element_id)

            classname: str = data.get("classname")


            if classname in self.ELEMENTS:

                element_class = self.ELEMENTS[classname]

                return self.load_classname(element_class, data)

            else:

                raise ValueError(f"Некорректное значение под ключом {classname=} аргумента {data=}")

        def load_root(self):
            """
            Загружает root из storage.

            ### Примеры вызова:
            ```py
            app.load_root()
            ```
            """
            data: BotTypes.ROOT_TYPE = self.storage.load_document("root") or {}

            self.load_classname(Root, data.get("root", {"id": 0}))

            self.root.add_element(self.filials_folder)

            self.root.add_element(self.contexts_folder)

            self.root.add_element(self.questions_folder)

            self.root.add_element(self.limits_folder)

            self.root.add_element(self.dates_folder)

            if self.theory_online in self.filials_folder.elements:

                if self.filials_folder.elements.index(self.theory_online) != 0:

                    self.filials_folder.elements.remove(self.theory_online)

                    self.filials_folder.elements.insert(0, self.theory_online)

            else:

                self.filials_folder.elements.insert(0, self.theory_online)

            self.load_dates()

        def get_available_threshold(self) -> datetime:
            """
            Возвращает порог доступности ближайших дат.

            :return: available threshold

            ### Пример использования:
            ```py
            domainMixin.get_available_threshold()
            ```
            """
            now_date: datetime = datetime.now()

            days_before_available: int = self.settings.main.get("days_before_available", 6)

            return now_date + timedelta(days = days_before_available)

        def load_dates(self):
            """
            Загружает доступные даты записи из storage.

            ### Примеры вызова:
            ```py
            app.load_dates()
            ```
            """
            folder: DatesFolder[MonthDate] = self.dates_folder

            future_dates: list[str] = []

            required_dates: int = self.settings.main.get("months_dates", 6)

            available_threshold: datetime = self.get_available_threshold()

            start_index: int = available_threshold.month - 1

            changed: bool = False

            for month_date in folder.elements:

                date: datetime = month_date.get_date()

                if date > available_threshold:

                    future_dates.append(get_month_string(date))

                else:

                    log_warn(f"{date=} из прошлого")


            for month_index in range(start_index, start_index + required_dates):

                date: datetime = get_month_date(available_threshold, month_index)

                month: str = get_month_string(date)


                if month not in future_dates:

                    month_date: MonthDate = self.create_month_date(available_threshold, month_index)

                    folder.add_element(month_date)

                    changed = True

            if changed:

                folder.elements.sort(key = lambda elem: elem.date)

                self.save_root()

        def save_root(self):
            """
            Сохраняет root в storage или во внутреннем состоянии объекта.

            ### Примеры вызова:
            ```py
            app.save_root()
            ```
            """
            data: BotTypes.ROOT_TYPE = {

                # Сохраняем вложенность элементов и их копии

                "root": self.root.dumps()

            }


            self.storage.save_document("root", data)

            self.storage.ensure_counters_at_least(element = int(self.element_id))

        def create_filial(self, filial_name: str) -> Filial:
            """
            Создаёт филиал автошколы и связывает результат с текущим объектом.

            ### Аргументы:
            :param filial_name: filial name

            :return: созданный объект: филиал автошколы

            ### Пример использования:
            ```py
            domainMixin.create_filial(filial_name = filial_name)
            ```
            """
            filial_id: int = self.create_id()

            filial: Filial = Filial(filial_id, filial_name)

            self.add_element(filial, container_id = self.filials_folder.id)

            self.save_root()

            return filial

        def remove_filial(self, filial_id: int) -> bool:
            """
            Удаляет филиал из доменного дерева автошколы.

            ### Аргументы:
            :param filial_id: filial id

            :return: значение, которое runtime использует для продолжения обработки события

            ### Пример использования:
            ```py
            domainMixin.remove_filial(filial_id = filial_id)
            ```
            """
            result: bool = self.remove_element(filial_id, from_id = self.filials_folder.id)

            self.save_root()

            return result

        def find_filial(self, filial_id: int) -> Filial | None:
            """
            Ищет филиал автошколы в текущих данных объекта или storage.

            ### Аргументы:
            :param filial_id: filial id

            :return: филиал автошколы или None, если подходящей записи нет

            ### Пример использования:
            ```py
            domainMixin.find_filial(filial_id = filial_id)
            ```
            """
            return self.filials.get(filial_id, None)

        def find_filial_id(self, date_id: int) -> int | None:
            """
            Ищет filial id в текущих данных объекта или storage.

            ### Аргументы:
            :param date_id: date id

            :return: filial id или None, если подходящей записи нет

            ### Пример использования:
            ```py
            domainMixin.find_filial_id(date_id = date_id)
            ```
            """
            for filial_id, filial in self.filials.items():

                for date in filial.elements:

                    if isinstance(date, Date) and date.id == date_id:

                        return filial_id

            return None

        def remove_date(self, date_id: int, filial_id: int | None) -> bool:
            """
            Удаляет дату из расписания филиала.

            ### Аргументы:
            :param date_id: date id
            :param filial_id: filial id

            :return: значение, которое runtime использует для продолжения обработки события

            ### Пример использования:
            ```py
            domainMixin.remove_date(date_id = date_id, filial_id = filial_id)
            ```
            """
            filial_id = filial_id or self.find_filial_id(date_id)

            result: bool = self.remove_element(date_id, from_id = filial_id)

            self.save_root()

            return result

        def create_date(self, date: str, filial_id: int | None) -> Date:
            """
            Создаёт время сообщения или события и связывает результат с текущим объектом.

            ### Аргументы:
            :param date: время сообщения или события
            :param filial_id: filial id

            :return: созданный объект: время сообщения или события

            ### Пример использования:
            ```py
            domainMixin.create_date(date = date, filial_id = filial_id)
            ```
            """
            date_id: int = self.create_id()

            date: Date = Date(date_id, datetime.strptime(date, Date.DATE_FORMAT))

            self.add_element(date, container_id = filial_id)

            self.save_root()

            return date

        def create_month_date(self, available_threshold: datetime, month_index: int) -> MonthDate:
            """
            Создаёт month date и связывает результат с текущим объектом.

            ### Аргументы:
            :param available_threshold: available threshold
            :param month_index: month index

            :return: созданный объект: month date

            ### Пример использования:
            ```py
            domainMixin.create_month_date(available_threshold = available_threshold, month_index = month_index)
            ```
            """
            date_id: int = self.create_id()

            date: datetime = get_month_date(available_threshold, month_index)

            date_month: MonthDate = MonthDate(date_id, date)

            return date_month

        def get_filials_list(self, enabled: bool | None = None, removed: bool | None = None, has_dates: bool | None = None) -> list[Filial]:
            """
            Возвращает список филиалов автошколы.

            ### Аргументы:
            :param enabled: нужное состояние включения элемента
            :param removed: список удалённых элементов
            :param has_dates: has dates

            :return: filials list

            ### Пример использования:
            ```py
            domainMixin.get_filials_list(enabled = enabled, removed = removed, has_dates = has_dates)
            ```
            """
            result: list[Filial] = []

            filials_list: Iterable[Filial] = self.filials.values() if removed == True else self.filials_folder.elements

            month_dates: bool = len(self.get_dates_list(None, future = True, enabled = True)) > 0

            for elem in filials_list:

                filial_id: int = elem.id

                filial: Filial | None = self.find_filial(filial_id)

                if not filial:

                    continue

                filial_dates: bool = month_dates or any(date.enabled for date in filial.elements)

                filial_removed: bool | None

                if filial.name == "Теория онлайн":

                    filial_dates = True

                if filial in self.filials_folder.elements:

                    filial_removed = False

                elif filial:

                    filial_removed = True

                else:

                    filial_removed = None

                    log_warn(f"Неизвестный филиал {filial_id=} {filial=} {filial_removed=}")

                if filial:

                    if enabled is not None and enabled != filial.enabled:

                        continue

                    elif removed is not None and removed != filial_removed:

                        continue

                    elif has_dates is not None and has_dates != filial_dates:

                        continue

                    result.append(filial)

            return result

        def get_month_dates(self) -> list[MonthDate]:
            """
            Возвращает даты, сгруппированные по месяцам.

            :return: month dates

            ### Пример использования:
            ```py
            domainMixin.get_month_dates()
            ```
            """
            return self.dates_folder.elements

        def get_dates_list(self, filial: Filial | None, enabled: bool | None = None, removed: bool | None = None, future: bool | None = None) -> list[Date | MonthDate]:
            """
            Возвращает список дат расписания.

            ### Аргументы:
            :param filial: филиал автошколы
            :param enabled: нужное состояние включения элемента
            :param removed: список удалённых элементов
            :param future: Future объект фоновой операции

            :return: dates list

            ### Пример использования:
            ```py
            domainMixin.get_dates_list(filial = filial, enabled = enabled, removed = removed, future = future)
            ```
            """
            result: list[Date | MonthDate] = []

            dates_list: Iterable[Date | MonthDate] = []

            month_dates: list[MonthDate] = self.get_month_dates()

            available_threshold: datetime = self.get_available_threshold()

            if removed:

                dates_list = self.dates.values()

            elif filial:

                dates_list = filial.elements + month_dates

            else:

                dates_list = month_dates

            for date in dates_list:

                date_id: int = date.id

                date: Date | MonthDate | None = self.find_element(date_id, Date)

                if not date:

                    continue

                date_removed: bool | None

                date_future: bool = date.get_date() > available_threshold

                if date in month_dates or (filial and date in filial.elements):

                    date_removed = False

                elif date.id in self.dates:

                    date_removed = True

                else:

                    date_removed = None

                    log_warn(f"Неизвестная дата {date_id=} {date=} {date_removed=}")

                if date:

                    if enabled is not None and enabled != date.enabled:

                        continue

                    elif removed is not None and removed != date_removed:

                        continue

                    elif future is not None and future != date_future:

                        continue

                    result.append(date)

            return result
