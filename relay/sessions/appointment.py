"""
Описывает сценарии записи клиента на занятие.
Модуль относится к архитектурной зоне: прикладной слой `relay`, который связывает пользователей, сессии, доменную модель, GPT, уведомления и runtime-логику приложения.

### Публичные классы
- `MainSession`: сессия записи клиента на занятие.
- `SessionFilials`: сессия списка филиалов.
- `FilialSession`: сессия управления филиалом.
- `DateSession`: сессия управления датой.
- `SessionDates`: сессия списка дат.
- `ConfigureDateSession`: сессия настройки даты.

### Публичные функции
- Публичные функции отсутствуют.

### Связи
Используется app-layer сценариями, обработчиками, сессиями и runtime-миксинами для единого пользовательского потока между ботами, GPT и storage.
"""

from __future__ import annotations


from relay.common import BotTypes, abstractmethod
from relay.config import INPUT_LENGTH, get_phrase
from .level import Level, LevelSession
from .manage import ManageSession, Mode, ModeSession
from relay.utils import is_int, join_callback
from relay.callback_data import Callback


class MainSession(LevelSession):

    """
    Многошаговый сценарий записи клиента в автошколу.
    Сессия ведёт пользователя по цепочке: стартовое подтверждение, выбор
    филиала, выбор даты, телефон, имя и финальное подтверждение. Филиал может
    быть пропущен автоматически, если доступен ровно один включённый филиал с
    датами, кроме специального филиала `Теория онлайн`. Единственная дата или
    единственный филиал подтверждаются через кнопки `ACCEPT_CALLBACK` и
    `DECLINE_CALLBACK`; уже выбранные значения можно продолжить через
    `NEXT_CALLBACK`, а телефон и имя можно пропустить через `SKIP_CALLBACK`.

    Доступ к филиалам, датам и созданию заявки приходит из `context.autocenter`
    как зависимости `find_filial`, `find_element`, `get_filials_list`,
    `get_dates_list`, `get_month_dates`, `get_available_threshold` и
    `make_appointment`. Сессия сама хранит только progress уровней и значения
    пользовательского ввода; запись заявки выполняет runtime-зависимость
    `make_appointment`.
    """
    def __init__(self, session_id: int, context: Context, data: dict, message: Message):
        """
        Создаёт сценарий записи и связывает его с runtime-зависимостями.
        Метод настраивает уровни `ask_start -> ask_filial -> ask_date ->
        ask_phone -> ask_name -> ask_confirm`, затем восстанавливает их состояние
        из `data`.

        ### Аргументы:
        :param session_id: идентификатор сессии
        :param context: контекст обработки события
        :param data: сериализованный словарь
        :param message: сообщение проекта или сообщение конкретного транспорта

        ### Пример использования:
        ```py
        session = MainSession(session_id = session_id, context = context, data = data, message = message)
        ```
        """
        super().__init__(session_id, context, data, message)
        self.find_filial = context.autocenter.find_filial
        self.find_element = context.autocenter.find_element
        self.get_filials_list = context.autocenter.get_filials_list
        self.get_dates_list = context.autocenter.get_dates_list
        self.get_month_dates = context.autocenter.get_month_dates
        self.get_available_threshold = context.autocenter.get_available_threshold
        self.make_appointment = context.autocenter.make_appointment

        self.levels = [
            Level(self.ask_start),
            Level(self.ask_filial),
            Level(self.ask_date),
            Level(self.ask_phone),
            Level(self.ask_name),
            Level(self.ask_confirm)
        ]

        self.load_levels(data)


    @abstractmethod
    def find_filial(self, filial_id: int) -> Filial | None:
        """
        Ищет филиал автошколы в текущих данных объекта или storage.

        ### Аргументы:
        :param filial_id: filial id

        :return: филиал автошколы или None, если подходящей записи нет

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        session.find_filial(filial_id = filial_id)
        ```
        """
        raise NotImplementedError()

    @abstractmethod
    def find_element(self, element_id: int, element_class: type[Element]) -> Element | None:
        """
        Ищет доменный элемент в текущих данных объекта или storage.

        ### Аргументы:
        :param element_id: идентификатор доменного элемента
        :param element_class: element class

        :return: доменный элемент или None, если подходящей записи нет

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        session.find_element(element_id = element_id, element_class = element_class)
        ```
        """
        raise NotImplementedError()

    @abstractmethod
    def get_filials_list(self, enabled: bool | None = None, removed: bool | None = None, has_dates: bool | None = None) -> list[Filial]:
        """
        Возвращает список филиалов автошколы.

        ### Аргументы:
        :param enabled: нужное состояние включения элемента
        :param removed: список удалённых элементов
        :param has_dates: has dates

        :return: filials list

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        session.get_filials_list(enabled = enabled, removed = removed, has_dates = has_dates)
        ```
        """
        raise NotImplementedError()

    @abstractmethod
    def get_dates_list(self, filial: Filial | None, enabled: bool | None = None, removed: bool | None = None, future: bool | None = None) -> list[Date | MonthDate]:
        """
        Возвращает список дат расписания.

        ### Аргументы:
        :param filial: филиал автошколы
        :param enabled: нужное состояние включения элемента
        :param removed: список удалённых элементов
        :param future: Future объект фоновой операции

        :return: dates list

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        session.get_dates_list(filial = filial, enabled = enabled, removed = removed, future = future)
        ```
        """
        raise NotImplementedError()

    @abstractmethod
    def get_month_dates(self) -> list[MonthDate]:
        """
        Возвращает даты, сгруппированные по месяцам.

        :return: month dates

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        session.get_month_dates()
        ```
        """
        raise NotImplementedError()

    @abstractmethod
    def get_available_threshold(self) -> datetime:
        """
        Возвращает порог доступности ближайших дат.

        :return: available threshold

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        session.get_available_threshold()
        ```
        """
        raise NotImplementedError()

    @abstractmethod
    def make_appointment(self, context: Context, filial: Filial, date: Date | MonthDate, phone: str = "", name: str = "") -> bool:
        """
        Создаёт заявку на запись через runtime автоцентра.
        Реальная реализация приходит из `context.autocenter.make_appointment` и
        может отправлять уведомления администраторам, сохранять состояние через
        storage API и использовать transport API для сообщений.

        ### Аргументы:
        :param context: контекст обработки события
        :param filial: филиал автошколы
        :param date: выбранная дата или месяц записи
        :param phone: телефон пользователя
        :param name: имя

        :return: `True`, если заявка создана и сессию можно завершить; иначе `False`

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        session.make_appointment(context = context, filial = filial, date = date, phone = phone, name = name)
        ```
        """
        raise NotImplementedError()


    def get_back(self) -> Callback | None:
        """
        Возвращает callback для кнопки «назад» на текущем уровне.
        На стартовом подтверждении кнопка назад не нужна. Для `Теория онлайн`
        после выбора филиала возврат с шага телефона ведёт к выбору филиала,
        потому что дата пропускается.

        :return: callback возврата или `None`

        ### Пример использования:
        ```py
        session.get_back()
        ```
        """
        if self.level == 0:
            # Вместо кнопки НАЗАД работает кнопка НЕТ
            return None
        elif self.level == 3 and self.get_filial() and self.get_filial().name == "Теория онлайн":
            return lambda: self.change_level(1)
        else:
            return self.prev_level

    def get_filials(self) -> list[Filial]:
        """
        Возвращает включённые неудалённые филиалы, у которых есть доступные даты.

        :return: список филиалов для пользовательской записи

        ### Пример использования:
        ```py
        session.get_filials()
        ```
        """
        return self.get_filials_list(enabled = True, removed = False, has_dates = True)

    def get_dates(self, filial: Filial) -> list[Date | MonthDate]:
        """
        Возвращает включённые будущие даты выбранного филиала.

        ### Аргументы:
        :param filial: филиал автошколы

        :return: список дат или месячных дат для записи

        ### Пример использования:
        ```py
        session.get_dates(filial = filial)
        ```
        """
        return self.get_dates_list(filial, enabled = True, removed = False, future = True)

    def get_filial(self) -> Filial | None:
        """
        Возвращает выбранный филиал автошколы.

        :return: филиал автошколы

        ### Пример использования:
        ```py
        session.get_filial()
        ```
        """
        level: Level = self.levels[1]
        filial_id: int | None = self.get_value(level, int)

        if filial_id is not None:
            filial: Filial | None = self.find_filial(filial_id)
            return filial
        else:
            return None

    def get_date(self) -> Date | MonthDate | None:
        """
        Возвращает выбранную дату записи.

        :return: доменный объект даты или `None`, если дата ещё не выбрана

        ### Пример использования:
        ```py
        session.get_date()
        ```
        """
        level: Level = self.levels[2]
        date_id: int | None = self.get_value(level, int)

        if date_id is not None:
            return self.find_element(date_id, Date)
        else:
            return None


    def check_dates(self, filials: list[Filial]) -> bool:
        """
        Проверяет, есть ли доступные даты для переданных филиалов.
        Учитываются как общие месячные даты, так и даты внутри включённых
        филиалов.

        ### Аргументы:
        :param filials: филиалы автошколы для проверки или отображения

        :return: `True`, если есть хотя бы одна доступная дата; иначе `False`

        ### Пример использования:
        ```py
        session.check_dates(filials = filials)
        ```
        """
        return (self.get_month_dates() and any(filial.enabled for filial in filials)
            ) or any(filial.elements and filial.enabled for filial in filials)

    def prove_filials(self) -> bool:
        """
        Проверяет, что запись вообще возможна.
        Если включённых филиалов или доступных дат нет, показывает пользователю
        фразу `no_filials`, завершает сессию и запрещает дальнейшие шаги.

        :return: `True`, если можно продолжать сценарий; иначе `False`

        ### Пример использования:
        ```py
        session.prove_filials()
        ```
        """
        filials: list[Filial] = self.get_filials()

        if not any(filial.enabled for filial in filials):
            self.show_phrase("no_filials")
            self.finish()
            return False

        if not self.check_dates(filials):
            self.show_phrase("no_filials")
            self.finish()
            return False

        return True

    def prove_filial(self) -> bool:
        """
        Проверяет выбранный филиал перед переходом к следующим шагам.
        Если филиал исчез, отключён или больше не имеет дат, пользователь
        возвращается к выбору филиала, когда доступны другие варианты.

        :return: `True`, если выбранный филиал актуален; иначе `False`

        ### Пример использования:
        ```py
        session.prove_filial()
        ```
        """
        filial: Filial | None = self.get_filial()
        enabled: bool | None = filial.enabled if filial else None

        if (not filial) or (not filial.enabled):
            filial_id: int | None = self.get_value(self.levels[1])

            if is_int(filial_id) or (filial and not filial.enabled):
                self.show_phrase("filial_changed")
            else:
                self.show_phrase("filial_required")

            if self.prove_filials():
                self.change_level(1)

            return False

        if not self.check_dates([filial]):
            # Если в других филиалах есть даты доступные для записи
            if self.prove_filials():
                # То переходим к выбору филиала
                self.show_phrase("no_dates")
                self.change_level(1)
                return False
            else:
                return False

        return True

    def prove_date(self) -> bool:
        """
        Проверяет выбранную дату перед сбором телефона, имени и подтверждением.
        Для `Теория онлайн` дата не требуется. Для остальных филиалов дата
        должна быть включена, принадлежать выбранному филиалу или быть
        `MonthDate`, и быть позже `get_available_threshold`. При устаревшей
        дате пользователь возвращается к выбору даты или филиала.

        :return: `True`, если дата актуальна или не нужна; иначе `False`

        ### Пример использования:
        ```py
        session.prove_date()
        ```
        """
        filial: Filial | None = self.get_filial()
        date: Date | MonthDate | None = self.get_date()

        if not self.prove_filial():
            return False
        elif filial.name == "Теория онлайн":
            return True
        elif not date:
            self.show_phrase("date_required")
        elif (not date.enabled) or ((not filial.has_element(date)) and (not isinstance(date, MonthDate))) or (date.get_date() <= self.get_available_threshold()):
            self.show_phrase("date_changed")
        else:
            return True

        if self.check_dates([filial]):
            self.change_level(2)
        else:
            self.change_level(1)

        return False


    def skip_filial(self) -> bool:
        """
        Автоматически выбирает филиал, если доступен ровно один вариант.
        Филиал `Теория онлайн` не пропускается автоматически, потому что для
        него дальше действует особая ветка без выбора даты.

        :return: `True`, если филиал был выбран автоматически; иначе `False`

        ### Пример использования:
        ```py
        session.skip_filial()
        ```
        """
        level: Level = self.levels[1]
        filials: list[Filial] = self.get_filials_list(enabled = True)

        if len(filials) == 1 and filials[0].name != "Теория онлайн" and self.check_dates([filials[0]]):
            self.set_value(level, filials[0].id)
            self.set_confirmed(level, True)
            return True
        else:
            return False


    def ask_start(self, level: Level, context: Context | None):
        """
        Запускает сценарий записи и спрашивает стартовое подтверждение.
        При подтверждении пытается автопропустить филиал; если автопропущенный
        филиал имеет одну дату, переводит пользователя на подтверждение этого
        выбора. `DECLINE_CALLBACK` завершает сессию.

        ### Аргументы:
        :param level: уровень сценария
        :param context: контекст обработки события

        :return: результат перехода уровня или обновления input-сообщения

        ### Пример использования:
        ```py
        session.ask_start(level = level, context = context)
        ```
        """
        if not self.prove_filials():
            return
        elif self.check_confirmed(level):
            return self.next_level(context)
        elif self.check_confirming(level):
            if context and context.event:
                confirmed: bool | None = self.confirmed(context)

                if confirmed is None:
                    context.remove_handler()
                    return
                elif confirmed:
                    self.set_confirming(level, False)
                    self.set_confirmed(level, True)

                    skip_filial: bool = self.skip_filial()
                    if skip_filial:
                        return self.change_level(1, reset = False)
                    else:
                        return self.next_level(None)
                else:
                    self.finish()
                    return

        skip_filial: bool = self.skip_filial()
        if skip_filial and context:
            filial: Filial = self.get_filial()
            dates: list[Date | MonthDate] = self.get_dates(filial)

            if len(dates) == 1:
                return self.change_level(1, reset = False)

        self.set_confirming(level, True)
        self.set_confirmed(level, False)
        return self.input.ask_confirm(get_phrase("main_confirm"))

    def ask_filial(self, level: Level, context: Context | None):
        """
        Показывает выбор филиала и обрабатывает ответ пользователя.
        При нескольких филиалах пользователь выбирает из меню или вводит начало
        названия; уже выбранный филиал можно подтвердить через `NEXT_CALLBACK`.
        При единственном филиале сессия показывает подтверждение через
        `ACCEPT_CALLBACK`/`DECLINE_CALLBACK`. Если филиал был отключён или
        удалён между событиями, показывается `filial_changed`.

        ### Аргументы:
        :param level: уровень сценария
        :param context: контекст обработки события

        :return: результат перехода уровня или обновления input-сообщения

        ### Пример использования:
        ```py
        session.ask_filial(level = level, context = context)
        ```
        """
        if not self.prove_filials():
            return

        filials: list[Filial] = self.get_filials()

        def find_filial(name: str) -> Filial | None:
            name = str(name).strip()

            for filial in filials:
                if filial.get_name().strip().startswith(name):
                    return filial

            return None

        if self.check_confirmed(level):
            self.next_level(context)
            return
        elif context and context.event:
            if context.is_callback():
                callback_data: str = context.get_callback_string(1)

                if callback_data == NEXT_CALLBACK:
                    self.next_level(None)
                    return

            filial: Filial | None = None

            if self.check_confirming(level):
                if context.is_callback():
                    args: list[str] = context.get_callback_data()
                    callback_data: str = context.get_callback_string(1)

                    if callback_data == ACCEPT_CALLBACK or callback_data == DECLINE_CALLBACK:
                        if callback_data == ACCEPT_CALLBACK:
                            filial_id: int = int(args[2])

                            if any(filial.id == filial_id for filial in filials):
                                filial = self.find_element(filial_id, Filial)
                            else:
                                self.show_phrase("filial_changed")
                                # -> ask_filial
                        elif callback_data == DECLINE_CALLBACK:
                            if len(filials) == 1:
                                self.change_level(0)
                                return
                            else:
                                self.set_confirming(level, False)
                                # -> ask_filial
                        else:
                            context.remove_handler()
                            return
                    else:
                        context.remove_handler()
                        return
            elif self.check_asked(level):
                answer: str = context.event.text

                if context.is_callback():
                    args: list[str] = context.get_callback_data()
                    callback_data: str = context.get_callback_string()

                    if callback_data == ANSWER_CALLBACK:
                        answer = args[1]
                    else:
                        context.remove_handler()
                        return

                filial = find_filial(answer)

                if filial is None:
                    self.incorrect()
                    # return
            else:
                context.remove_handler()
                return

            if filial:
                self.set_asked(level, False)
                self.set_value(level, filial.id)
                self.set_confirmed(level, True)
                self.set_confirming(level, False)
                self.next_level(None)
                return

        question: str = get_phrase("ask_filial")
        answers: dict[str, JSONABLE] = {}
        actions: dict[str, JSONABLE] = {}
        highlighted: list[str] = []

        if len(filials) > 1:
            choosen_filial: Filial | None = self.get_filial()
            if choosen_filial:
                highlighted.append(choosen_filial.get_answer())
                actions.update({
                    "next": NEXT_CALLBACK
                })

            for filial in filials:
                answer: str = filial.get_answer()
                answers[answer] = filial.id

            self.input.update(question, answers = answers, actions = actions, choosen = highlighted, skip = False)
            self.set_asked(level, True)
        else:
            filial: Filial = filials[0]
            filial_string: str = filial.get_name()

            question: str = get_phrase("confirm_single_filial").format(filial_string)
            self.input.update(question, answers = [], actions = {
                "accept": join_callback(ACCEPT_CALLBACK, filial.id),
                "decline": DECLINE_CALLBACK
            }, choosen = [], skip = False)
            self.set_confirming(level, True)

    def ask_date(self, level: Level, context: Context | None):
        """
        Показывает выбор даты для выбранного филиала.
        Для филиала `Теория онлайн` шаг даты пропускается. При нескольких датах
        пользователь выбирает из меню, а уже выбранную дату может подтвердить
        через `NEXT_CALLBACK`. Единственная дата подтверждается через
        `ACCEPT_CALLBACK`/`DECLINE_CALLBACK`; если дата устарела, отключена или
        стала недоступной относительно `get_available_threshold`, пользователь
        возвращается к актуальному выбору.

        ### Аргументы:
        :param level: уровень сценария
        :param context: контекст обработки события

        ### Пример использования:
        ```py
        session.ask_date(level = level, context = context)
        ```
        """
        filial: Filial | None = self.get_filial()

        if not self.prove_filials():
            return
        elif not self.prove_filial():
            return
        elif filial.name == "Теория онлайн":
            self.next_level(context)
            return
        elif self.check_confirmed(level):
            self.next_level(context)
            return
        elif context and context.event:
            if context.is_callback():
                callback_data: str = context.get_callback_string(1)

                if callback_data == NEXT_CALLBACK:
                    self.next_level(None)
                    return

            date: Date | MonthDate | None = None

            if self.check_confirming(level):
                if context.is_callback():
                    args: list[str] = context.get_callback_data()
                    callback_data: str = context.get_callback_string(1)

                    if callback_data == ACCEPT_CALLBACK or callback_data == DECLINE_CALLBACK:
                        dates: list[Date | MonthDate] = self.get_dates(filial)

                        if callback_data == ACCEPT_CALLBACK:
                            date_id: int = int(args[2])

                            if any(date.id == date_id for date in dates):
                                date = self.find_element(date_id, Date)
                            else:
                                self.show_phrase("date_changed")
                                # -> ask_date
                        elif callback_data == DECLINE_CALLBACK:
                            if len(dates) == 1:
                                self.change_level(0)
                                return
                            else:
                                self.set_confirming(level, False)
                                # -> ask_date
                        else:
                            context.remove_handler()
                            return
                    else:
                        context.remove_handler()
                        return
            elif self.check_asked(level):
                answer: str = context.event.text

                if context.is_callback():
                    args: list[str] = context.get_callback_data()
                    callback_data: str = context.get_callback_string()

                    if callback_data == ANSWER_CALLBACK:
                        answer = args[1]
                    else:
                        context.remove_handler()
                        return

                date_id = self.input.get_answer(answer)
                date = self.find_element(date_id, Date)
            else:
                context.remove_handler()
                return

            if date:
                self.set_asked(level, False)
                self.set_value(level, date.id)
                self.set_confirming(level, False)
                self.set_confirmed(level, True)
                self.next_level(None)
                return

        dates: list[Date | MonthDate] = self.get_dates(filial)

        if len(dates) > 1:
            question: str = get_phrase("ask_date").format(filial.get_answer())
            answers: dict[str, JSONABLE] = {}
            highlighted: list[str] = []
            actions: dict[str, JSONABLE] = {}
            choosen_date: Date | None = self.get_date()

            if choosen_date and any(date.id == choosen_date.id for date in dates):
                highlighted.append(choosen_date.get_answer())
                actions.update({
                    "next": NEXT_CALLBACK
                })

            for date in dates:
                answer: str = date.get_answer()
                answers[answer] = date.id

            self.input.update(question, answers = answers, actions = actions, choosen = highlighted, skip = False)
            self.set_asked(level, True)
            self.set_confirming(level, False)
        else:
            date: Date | MonthDate = dates[0]
            filial_string: str = filial.get_name()
            date_string: str = date.get_answer(cut_string = False)

            question: str = get_phrase("confirm_single_date").format(filial_string, date_string)
            self.input.update(question, answers = [], actions = {
                "accept": join_callback(ACCEPT_CALLBACK, date.id),
                "decline": DECLINE_CALLBACK
            }, choosen = [], skip = False)
            self.set_confirming(level, True)

    def ask_phone(self, level: Level, context: Context | None):
        """
        Запрашивает телефон клиента.
        Текстовый ответ обрезается до `INPUT_LENGTH` и сохраняется в уровне.
        Callback `SKIP_CALLBACK` сохраняет пустую строку и переводит сценарий к
        следующему шагу.

        ### Аргументы:
        :param level: уровень сценария
        :param context: контекст обработки события

        ### Пример использования:
        ```py
        session.ask_phone(level = level, context = context)
        ```
        """
        if not self.prove_filials():
            return
        elif not self.prove_filial():
            return
        elif not self.prove_date():
            return
        elif context and context.event:
            if self.check_asked(level):
                content, is_callback = self.get_command(context)

                phone: str = ""
                next_level: bool = False

                if is_callback:
                    callback_data: str = context.get_callback_string()

                    if callback_data == SKIP_CALLBACK:
                        next_level = True
                        phone = ""
                    else:
                        context.remove_handler()
                        return
                elif content and str(content).strip():
                    phone = cut(str(content).strip(), INPUT_LENGTH)

                    if phone:
                        next_level = True
                    else:
                        self.incorrect()

                if next_level:
                    self.set_asked(level, False)
                    self.set_confirmed(level, True)
                    self.set_value(level, phone)
                    self.next_level(None)
                    return
            else:
                context.remove_handler()
                return

        self.set_asked(level, True)
        question: str = get_phrase("ask_phone")
        self.input.update(question, answers = {}, actions = {}, choosen = [], skip = True)

    def ask_name(self, level: Level, context: Context | None):
        """
        Запрашивает имя клиента.
        Текстовый ответ обрезается до `INPUT_LENGTH` и сохраняется в уровне.
        Callback `SKIP_CALLBACK` сохраняет пустую строку и переводит сценарий к
        финальному подтверждению.

        ### Аргументы:
        :param level: уровень сценария
        :param context: контекст обработки события

        ### Пример использования:
        ```py
        session.ask_name(level = level, context = context)
        ```
        """
        if not self.prove_filials():
            return
        elif not self.prove_filial():
            return
        elif not self.prove_date():
            return
        elif context and context.event:
            if self.check_asked(level):
                content, is_callback = self.get_command(context)

                name: str = ""
                next_level: bool = False

                if is_callback:
                    callback_data: str = context.get_callback_string()

                    if callback_data == SKIP_CALLBACK:
                        next_level = True
                        name = ""
                    else:
                        context.remove_handler()
                        return
                elif content and str(content).strip():
                    name = cut(str(content).strip(), INPUT_LENGTH)

                    if name:
                        next_level = True
                    else:
                        self.incorrect()

                if next_level:
                    self.set_asked(level, False)
                    self.set_confirmed(level, True)
                    self.set_value(level, name)
                    self.next_level(None)
                    return
            else:
                context.remove_handler()
                return

        self.set_asked(level, True)
        question: str = get_phrase("ask_name")
        self.input.update(question, answers = {}, actions = {}, choosen = [], skip = True)

    def ask_confirm(self, level: Level, context: Context | None):
        """
        Показывает финальное подтверждение записи.
        В тексте указываются выбранный филиал и дата, если дата есть. Callback
        `ACCEPT_CALLBACK` запускает `final_level`, а `DECLINE_CALLBACK`
        возвращает пользователя к старту сценария.

        ### Аргументы:
        :param level: уровень сценария
        :param context: контекст обработки события

        ### Пример использования:
        ```py
        session.ask_confirm(level = level, context = context)
        ```
        """
        if not self.prove_filials():
            return
        elif not self.prove_filial():
            return
        elif not self.prove_date():
            return
        elif self.check_confirmed(level) and context:
            self.final_level(context)
            return
        elif context and context.event:
            if self.check_confirming(level):
                if context.is_callback():
                    callback_data: str = context.get_callback_string(1)
                    self.set_confirming(level, False)
                    self.set_confirmed(level, callback_data == ACCEPT_CALLBACK)

                    if callback_data == ACCEPT_CALLBACK:
                        self.final_level(context)
                        return
                    elif callback_data == DECLINE_CALLBACK:
                        self.change_level(0)
                        return
                    else:
                        context.remove_handler()
                        return
                else:
                    context.remove_handler()
                    return

        filial: Filial = self.get_filial()
        date: Date | MonthDate = self.get_date()

        filial_string: str = filial.get_name()
        date_string: str | None = date.get_answer(cut_string = False) if date else ""

        if date_string:
            on_date: str = get_phrase("on_date")
            date_string = f"{on_date}{date_string}"

        question: str = get_phrase("ask_confirm").format(filial_string, date_string)
        self.input.ask_confirm(question)
        self.set_confirming(level, True)


    def final_level(self, context: Context):
        """
        Создаёт заявку и завершает сценарий при успешной записи.
        Метод показывает промежуточное «Записываем...», берёт выбранные филиал,
        дату, телефон и имя из уровней, затем вызывает зависимость
        `make_appointment`. При успехе сессия завершается, input/menu сообщения
        обновляются текстом `appointment_success`.

        ### Аргументы:
        :param context: контекст обработки события

        ### Пример использования:
        ```py
        session.final_level(context = context)
        ```
        """
        if not self.prove_filials():
            return
        elif not self.prove_filial():
            return
        elif not self.prove_date():
            return

        self.input.update("Записываем...", answers = {}, actions = {}, skip = False, back = False)

        filial: Filial = self.get_filial()
        date: Date | MonthDate | None = self.get_date()
        phone: str = self.get_value(self.levels[3], str) or ""
        name: str = self.get_value(self.levels[4], str) or ""

        if self.make_appointment(context, filial, date, phone, name):
            self.finish()

            filial_string: str = filial.get_name()
            date_string: str = date.get_answer(cut_string = False) if date else ""

            if date_string:
                on_date: str = get_phrase("on_date")
                date_string = f"{on_date}{date_string}"

            question: str = get_phrase("appointment_success").format(filial_string, date_string)
            self.input.update(question, answers = {}, actions = {}, skip = False, back = False)
            self.menu.reset_message()


class SessionFilials(ModeSession):
    """
    Описывает пользовательскую или административную сессию `SessionFilials`.
    Сессия хранит состояние текущего пользовательского сценария, обновляет сообщения и завершает себя через общий session lifecycle.

    ### Поля
    - `DESCRIPTION_KEY`: ключ сериализации или transport-события, по которому объект отличает один вариант данных от другого.
    - `ALREADY_EXISTS_KEY`: ключ сериализации или transport-события, по которому объект отличает один вариант данных от другого.
    - `folder_id`: идентификатор объекта или связанной сущности, по которому runtime восстанавливает связь между слоями.
    - `element_id`: идентификатор объекта или связанной сущности, по которому runtime восстанавливает связь между слоями.
    - `element_class`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `next_session`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `create_element`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `remove_element`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `enable_element`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `disable_element`: runtime-зависимость или поле, используемое текущим session-сценарием.

    ### Методы
    - `__init__`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `update_data`: Обновляет data с учётом текущего состояния объекта.
    - `check_content`: Проверяет название филиала перед сохранением.

    ### Жизненный цикл
    Создаётся app-layer кодом, участвует в обработке пользовательского события и сохраняет изменённое состояние через существующие runtime/storage механизмы.

    ### Пример использования
    ```py
    session: SessionFilials
    ```
    """
    DESCRIPTION_KEY: str = "filials_description"
    ALREADY_EXISTS_KEY: str = "repeated_filial"

    def __init__(self, session_id: int, context: Context, data: dict, message: Message):
        """
        Создаёт session-объект `SessionFilials` и сохраняет состояние пользовательского сценария между входящими событиями.

        ### Аргументы:
        :param session_id: идентификатор сессии
        :param context: контекст обработки события
        :param data: сериализованный словарь
        :param message: сообщение проекта или сообщение конкретного транспорта

        ### Пример использования:
        ```py
        sessionFilials = SessionFilials(session_id = session_id, context = context, data = data, message = message)
        ```
        """
        super().__init__(session_id, context, data, message)
        self.folder_id: int = context.autocenter.filials_folder.id
        self.element_id = context.autocenter.filials_folder.id
        self.element_class = FilialsFolder
        self.next_session = FilialSession
        self.create_element = context.autocenter.create_filial
        self.remove_element = context.autocenter.remove_filial
        self.enable_element = context.autocenter.enable_element
        self.disable_element = context.autocenter.disable_element

        self.set_mode(data.get("mode", ""))

    def update_data(self, data: dict[str, str]):
        """
        Обновляет data с учётом текущего состояния объекта.

        ### Аргументы:
        :param data: JSON-совместимые данные для соответствующего repository

        ### Пример использования:
        ```py
        session.update_data(data = data)
        ```
        """
        super().update_data(data)
        self.element_id = self.folder_id

    def check_content(self, filial_name: str):
        """
        Проверяет, можно ли сохранить строку как содержимое доменного элемента.

        ### Аргументы:
        :param filial_name: filial name

        :return: `True`, если строку можно сохранить как содержимое; иначе `False`

        ### Пример использования:
        ```py
        sessionFilials.check_content(filial_name = filial_name)
        ```
        """
        if len(filial_name) > INPUT_LENGTH:
            return False

        for filial in self.get_container():
            if filial.name == filial_name:
                return False

        return True


class FilialSession(ModeSession):
    """
    Описывает пользовательскую или административную сессию `FilialSession`.
    Сессия хранит состояние текущего пользовательского сценария, обновляет сообщения и завершает себя через общий session lifecycle.

    ### Поля
    - `DESCRIPTION_KEY`: ключ сериализации или transport-события, по которому объект отличает один вариант данных от другого.
    - `element_class`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `next_session`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `create_date`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `remove_date`: runtime-зависимость или поле, используемое текущим session-сценарием.

    ### Методы
    - `__init__`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `create_date`: Создаёт доступную дату записи и связывает результат с текущим app-layer состоянием.
    - `remove_date`: Удаляет доступную дату записи из внутреннего состояния или storage.
    - `create_element`: Создаёт элемент доменной модели и связывает результат с текущим app-layer состоянием.
    - `remove_element`: Удаляет элемент доменной модели из внутреннего состояния или storage.
    - `get_next_level`: Возвращает next level из текущего состояния `FilialSession`.

    ### Жизненный цикл
    Создаётся app-layer кодом, участвует в обработке пользовательского события и сохраняет изменённое состояние через существующие runtime/storage механизмы.

    ### Пример использования
    ```py
    session: FilialSession
    ```
    """
    DESCRIPTION_KEY: str = "filial_description"

    def __init__(self, session_id: int, context: Context, data: dict, message: Message):
        """
        Создаёт session-объект `FilialSession` и сохраняет состояние пользовательского сценария между входящими событиями.

        ### Аргументы:
        :param session_id: идентификатор сессии
        :param context: контекст обработки события
        :param data: сериализованный словарь
        :param message: сообщение проекта или сообщение конкретного транспорта

        ### Пример использования:
        ```py
        session = FilialSession(session_id = session_id, context = context, data = data, message = message)
        ```
        """
        super().__init__(session_id, context, data, message)
        self.element_class = Filial
        self.next_session = DateSession
        self.create_date = context.autocenter.create_date
        self.remove_date = context.autocenter.remove_date

        self.always_actions.update({
            "rename": CHANGE_CALLBACK
        })

        self.set_mode(data.get("mode", ""))

    @abstractmethod
    def create_date(self, date: str, filial_id: int | None) -> Date:
        """
        Создаёт время сообщения или события и связывает результат с текущим объектом.

        ### Аргументы:
        :param date: время сообщения или события
        :param filial_id: filial id

        :return: созданный объект: время сообщения или события

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        session.create_date(date = date, filial_id = filial_id)
        ```
        """
        raise NotImplementedError

    @abstractmethod
    def remove_date(self, date_id: int, filial_id: int | None) -> bool:
        """
        Удаляет дату из расписания филиала.

        ### Аргументы:
        :param date_id: date id
        :param filial_id: filial id

        :return: результат шага сессии

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        session.remove_date(date_id = date_id, filial_id = filial_id)
        ```
        """
        raise NotImplementedError

    def create_element(self, content: str) -> int:
        """
        Создаёт доменный элемент и связывает результат с текущим объектом.

        ### Аргументы:
        :param content: содержимое доменного элемента

        :return: созданный объект: доменный элемент

        ### Пример использования:
        ```py
        session.create_element(content = content)
        ```
        """
        return self.create_date(str(content).strip(), filial_id = self.element_id)

    def remove_element(self, date_id: int) -> bool:
        """
        Удаляет доменный элемент из текущего контейнера.

        ### Аргументы:
        :param date_id: date id

        :return: результат шага сессии

        ### Пример использования:
        ```py
        session.remove_element(date_id = date_id)
        ```
        """
        return self.remove_date(date_id, filial_id = self.element_id)

    def get_next_level(self, element_id: int) -> dict[str, int]:
        """
        Возвращает следующий шаг настройки филиалов.

        ### Аргументы:
        :param element_id: идентификатор доменного элемента

        :return: next level

        ### Пример использования:
        ```py
        session.get_next_level(element_id = element_id)
        ```
        """
        result: dict[str, int] = super().get_next_level(element_id)

        result.update({
            "filial_id": int(self.element_id),
        })

        return result


class DateSession(ManageSession):
    """
    Описывает пользовательскую или административную сессию `DateSession`.
    Сессия хранит состояние текущего пользовательского сценария, обновляет сообщения и завершает себя через общий session lifecycle.

    ### Поля
    - `DESCRIPTION_KEY`: ключ сериализации или transport-события, по которому объект отличает один вариант данных от другого.
    - `remove_date`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `element_class`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `filial_id`: идентификатор объекта или связанной сущности, по которому runtime восстанавливает связь между слоями.

    ### Методы
    - `__init__`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `remove_date`: Удаляет доступную дату записи из внутреннего состояния или storage.
    - `remove_element`: Удаляет элемент доменной модели из внутреннего состояния или storage.
    - `get_actions`: Возвращает действия меню из текущего состояния `DateSession`.

    ### Жизненный цикл
    Создаётся app-layer кодом, участвует в обработке пользовательского события и сохраняет изменённое состояние через существующие runtime/storage механизмы.

    ### Пример использования
    ```py
    session: DateSession
    ```
    """
    DESCRIPTION_KEY: str = "date_description"

    def __init__(self, session_id: int, context: Context, data: dict, message: Message):
        """
        Создаёт session-объект `DateSession` и сохраняет состояние пользовательского сценария между входящими событиями.

        ### Аргументы:
        :param session_id: идентификатор сессии
        :param context: контекст обработки события
        :param data: сериализованный словарь
        :param message: сообщение проекта или сообщение конкретного транспорта

        ### Пример использования:
        ```py
        session = DateSession(session_id = session_id, context = context, data = data, message = message)
        ```
        """
        super().__init__(session_id, context, data, message)
        self.remove_date = context.autocenter.remove_date
        self.element_class = Date
        filial_id: int = get_int(data, -1, "filial_id")

    @abstractmethod
    def remove_date(self, date_id: int, filial_id: int | None) -> bool:
        """
        Удаляет дату из расписания филиала.

        ### Аргументы:
        :param date_id: date id
        :param filial_id: filial id

        :return: результат шага сессии

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        session.remove_date(date_id = date_id, filial_id = filial_id)
        ```
        """
        raise NotImplementedError()

    def remove_element(self):
        """
        Удаляет элемент доменной модели из внутреннего состояния или storage.

        ### Примеры вызова:
        ```py
        session.remove_element()
        ```
        """
        element: Element | None = self.get_element()

        if element:
            self.remove_date(element.id, filial_id = element.parent_id)
        else:
            self.validate_element()

    def get_actions(self, answers: dict[str, JSONABLE] = {}) -> dict[str, str]:
        """
        Возвращает действия управления филиалом.

        ### Аргументы:
        :param answers: варианты ответа

        :return: actions

        ### Пример использования:
        ```py
        session.get_actions(answers = answers)
        ```
        """
        result: dict[str, JSONABLE] = super().get_actions(answers)
        element: Date | MonthDate | None = self.get_element()

        if not isinstance(element, MonthDate):
            result.update({
                "change": CHANGE_CALLBACK
            })

        return result


class SessionDates(ModeSession):
    """
    Описывает пользовательскую или административную сессию `SessionDates`.
    Сессия хранит состояние текущего пользовательского сценария, обновляет сообщения и завершает себя через общий session lifecycle.

    ### Поля
    - `DESCRIPTION_KEY`: ключ сериализации или transport-события, по которому объект отличает один вариант данных от другого.
    - `get_available_threshold`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `remove_date`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `enable_element`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `disable_element`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `folder_id`: идентификатор объекта или связанной сущности, по которому runtime восстанавливает связь между слоями.
    - `element_id`: идентификатор объекта или связанной сущности, по которому runtime восстанавливает связь между слоями.
    - `element_class`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `next_session`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `always_actions`: runtime-зависимость или поле, используемое текущим session-сценарием.

    ### Методы
    - `__init__`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `update_data`: Обновляет data с учётом текущего состояния объекта.
    - `get_available_threshold`: Возвращает available threshold из текущего состояния `SessionDates`.
    - `remove_element`: Удаляет элемент доменной модели из внутреннего состояния или storage.
    - `get_description`: Возвращает description из текущего состояния `SessionDates`.
    - `process_action`: Обрабатывает действие меню в текущем пользовательском или transport-layer потоке.

    ### Жизненный цикл
    Создаётся app-layer кодом, участвует в обработке пользовательского события и сохраняет изменённое состояние через существующие runtime/storage механизмы.

    ### Пример использования
    ```py
    session: SessionDates
    ```
    """
    DESCRIPTION_KEY: str = "month_dates_description"

    def __init__(self, session_id: int, context: Context, data: dict, message: Message):
        """
        Создаёт session-объект `SessionDates` и сохраняет состояние пользовательского сценария между входящими событиями.

        ### Аргументы:
        :param session_id: идентификатор сессии
        :param context: контекст обработки события
        :param data: сериализованный словарь
        :param message: сообщение проекта или сообщение конкретного транспорта

        ### Пример использования:
        ```py
        sessionDates = SessionDates(session_id = session_id, context = context, data = data, message = message)
        ```
        """
        super().__init__(session_id, context, data, message)
        self.get_available_threshold = context.autocenter.get_available_threshold
        self.remove_date = context.autocenter.remove_date
        self.enable_element = context.autocenter.enable_element
        self.disable_element = context.autocenter.disable_element

        self.folder_id: int = context.autocenter.dates_folder.id
        self.element_id = context.autocenter.dates_folder.id
        self.element_class = DatesFolder
        self.next_session = DateSession

        self.always_actions = {
            "configure": CONFIGURE_CALLBACK
        }
        # self.choosing_actions.clear()
        self.removed_actions[True].clear()

        self.set_mode(data.get("mode", ""))

    def update_data(self, data: dict[str, str]):
        """
        Обновляет data с учётом текущего состояния объекта.

        ### Аргументы:
        :param data: JSON-совместимые данные для соответствующего repository

        ### Пример использования:
        ```py
        session.update_data(data = data)
        ```
        """
        super().update_data(data)
        self.element_id = self.folder_id

    @abstractmethod
    def get_available_threshold(self) -> datetime:
        """
        Возвращает порог доступности ближайших дат.

        :return: available threshold

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        sessionDates.get_available_threshold()
        ```
        """
        raise NotImplementedError()

    def remove_element(self, date_id: int) -> bool:
        """
        Удаляет доменный элемент из текущего контейнера.

        ### Аргументы:
        :param date_id: date id

        :return: результат шага сессии

        ### Пример использования:
        ```py
        sessionDates.remove_element(date_id = date_id)
        ```
        """
        return self.remove_date(date_id, self.element_id)

    def get_description(self) -> str:
        """
        Возвращает описание даты записи для admin-меню.

        :return: description

        ### Пример использования:
        ```py
        sessionDates.get_description()
        ```
        """
        return super().get_description().format(self.get_available_threshold().strftime(r"%d.%m.%Y"))

    def process_action(self, bot_key: BOT_KEY, chat_id: int, action: str) -> bool:
        """
        Обрабатывает действие меню в текущем runtime-контексте.

        ### Аргументы:
        :param bot_key: ключ транспорта
        :param chat_id: идентификатор чата
        :param action: действие меню

        :return: результат шага сессии

        ### Пример использования:
        ```py
        sessionDates.process_action(bot_key = bot_key, chat_id = chat_id, action = action)
        ```
        """


        if action == CONFIGURE_CALLBACK:
            self._next_level(bot_key, chat_id, ConfigureDateSession, {})#, message = self.get_message())
            return True

        return super().process_action(bot_key, chat_id, action)


class ConfigureDateSession(ModeSession):

    """
    Описывает пользовательскую или административную сессию `ConfigureDateSession`.
    Сессия хранит состояние текущего пользовательского сценария, обновляет сообщения и завершает себя через общий session lifecycle.

    ### Поля
    - `get_settings`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `load_dates`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `element_class`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `changed`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `answers`: хранит варианты ответа для операций этого объекта.

    ### Методы
    - `__init__`: runtime-зависимость или поле, используемое текущим session-сценарием.
    - `get_settings`: Возвращает настройки пользователя или GPT из текущего состояния `ConfigureDateSession`.
    - `save_settings`: Сохраняет настройки пользователя или GPT в storage или во внутреннем состоянии объекта.
    - `dumps`: Возвращает JSON-совместимый снимок объекта для storage или callback payload.
    - `get_question`: Возвращает вопрос анкеты или GPT-контекста из текущего состояния `ConfigureDateSession`.
    - `get_answers`: Возвращает варианты ответа из текущего состояния `ConfigureDateSession`.
    - `get_actions`: Возвращает действия меню из текущего состояния `ConfigureDateSession`.
    - `process_answer`: Обрабатывает ответ пользователя в текущем пользовательском или transport-layer потоке.
    - `process_action`: Обрабатывает действие меню в текущем пользовательском или transport-layer потоке.
    - `mode_configure`: runtime-зависимость или поле, используемое текущим session-сценарием.

    ### Жизненный цикл
    Создаётся app-layer кодом, участвует в обработке пользовательского события и сохраняет изменённое состояние через существующие runtime/storage механизмы.

    ### Пример использования
    ```py
    session: ConfigureDateSession
    ```
    """
    def __init__(self, session_id: int, context: Context, data: dict, message: Message):
        """
        Создаёт session-объект `ConfigureDateSession` и сохраняет состояние пользовательского сценария между входящими событиями.

        ### Аргументы:
        :param session_id: идентификатор сессии
        :param context: контекст обработки события
        :param data: сериализованный словарь
        :param message: сообщение проекта или сообщение конкретного транспорта

        ### Пример использования:
        ```py
        session = ConfigureDateSession(session_id = session_id, context = context, data = data, message = message)
        ```
        """
        super().__init__(session_id, context, data, message)
        self.get_settings = context.autocenter.get_settings
        self.load_dates = context.autocenter.load_dates

        self.element_class = None
        self.changed: dict[str, int] = data.get("changed", {})
        self.answers: dict[str, str] = {}

        self.modes.clear()

        for key in self.get_settings("main"):
            self.modes.append(
                Mode(key, lambda context, k = key: self.mode_configure(context, k))
            )

        self.always_actions.clear()
        self.choosing_actions.clear()
        self.removed_actions.clear()

        self.set_mode(data.get("mode", ""))


    @abstractmethod
    def get_settings(self, key: Literal["call_admin", "new_appointment", "gpt", "main", "buttons"]) -> dict[str, int]:
        """
        Возвращает настройки пользователя.

        ### Аргументы:
        :param key: ключ записи или настройки

        :return: settings

        :raises NotImplementedError: если метод вызван у базового контракта без реализации в наследнике

        ### Пример использования:
        ```py
        session.get_settings(key = key)
        ```
        """
        raise NotImplementedError()

    def save_settings(self):
        """
        Сохраняет настройки пользователя или GPT в storage или во внутреннем состоянии объекта.

        ### Примеры вызова:
        ```py
        session.save_settings()
        ```
        """
        self.get_settings("main").update(self.changed)
        self.load_dates()
        self.finish()
        self.show_phrase("saved")


    def dumps(self) -> BotTypes.SESSION_TYPE:
        """
        Возвращает JSON-совместимый снимок объекта для storage или callback payload.

        :return: JSON-совместимый словарь для сохранения или передачи между слоями

        ### Пример использования:
        ```py
        session.dumps()
        ```
        """
        result: BotTypes.SESSION_TYPE = super().dumps()

        result.update({
            "changed": self.changed
        })

        return result

    def get_question(self, answers: Never = {}) -> str:
        """
        Возвращает краткое описание элемента для вывода в чат.

        ### Аргументы:
        :param answers: варианты ответа

        :return: строка вида `Филиал «Название»` или `Элемент «id»`

        ### Пример использования:
        ```py
        session.get_question(answers = answers)
        ```
        """
        return get_phrase("configure_dates")

    def get_answers(self) -> dict[str, str]:
        """
        Возвращает варианты ответа для текущего меню.

        :return: варианты ответа

        ### Пример использования:
        ```py
        session.get_answers()
        ```
        """
        answers: dict[str, str] = {}

        if not self.check_mode():
            self.input.set_choosen([])
            # self.input.lang_answers = True

        for key in self.get_settings("main"):
            answers[get_phrase(key)] = key

            if key in self.changed:
                self.input.choosen.append(get_phrase(key))

        return answers

    def get_actions(self, answers: Never = {}) -> dict[str, str]:
        """
        Возвращает действия управления датой записи.

        ### Аргументы:
        :param answers: варианты ответа

        :return: actions

        ### Пример использования:
        ```py
        session.get_actions(answers = answers)
        ```
        """
        actions: dict[str, str] = {}

        if self.changed:
            actions.update({
                "save": SAVE_CALLBACK
            })

        return actions

    def process_answer(self, bot_key: BOT_KEY, chat_id: int, answer: str) -> bool:
        """
        Обрабатывает ответ пользователя в текущем runtime-контексте.

        ### Аргументы:
        :param bot_key: ключ транспорта
        :param chat_id: идентификатор чата
        :param answer: ответ пользователя

        :return: результат шага сессии

        ### Пример использования:
        ```py
        session.process_answer(bot_key = bot_key, chat_id = chat_id, answer = answer)
        ```
        """
        if answer in self.get_settings("main"):
            self.start_mode(answer)
            return True
        else:
            return False

    def process_action(self, bot_key: BOT_KEY, chat_id: int, action: str) -> bool:
        """
        Обрабатывает действие меню в текущем runtime-контексте.

        ### Аргументы:
        :param bot_key: ключ транспорта
        :param chat_id: идентификатор чата
        :param action: действие меню

        :return: результат шага сессии

        ### Пример использования:
        ```py
        session.process_action(bot_key = bot_key, chat_id = chat_id, action = action)
        ```
        """


        if action == SAVE_CALLBACK:
            self.save_settings()
            return True
        else:
            return False

    def mode_configure(self, context: Context | None, key: str):
        """
        Переводит session-меню в режим `configure`.

        ### Аргументы:
        :param context: контекст обработки события
        :param key: ключ записи или настройки

        ### Пример использования:
        ```py
        session.mode_configure(context = context, key = key)
        ```
        """
        content, is_callback = self.get_command(context)

        if context:
            if is_callback:
                callback_data: str = context.get_callback_string(1)

                if callback_data == SAVE_CALLBACK:
                    self.save_settings()
                    return
                else:
                    context.remove_handler()
                    return
            elif is_int(content):
                self.changed[key] = int(content)
            elif content:
                self.incorrect()

        value: int | None = self.get_settings("main").get(key, None)
        actions: dict[str, str] = {}

        configure_question: str = get_phrase(key)
        configure_value: str = get_phrase("configure_value")
        configured_value: str = get_phrase("configured_value")

        if is_int(value):
            configure_question = f"{configure_question}\n{configure_value}: {value}"

        if key in self.changed:
            new_value: int = self.changed[key]
            configure_question = f"{configure_question}\n{configured_value}: {new_value}"
            actions.update({
                "save": SAVE_CALLBACK
            })

        self.input.update(configure_question, answers = [], choosen = [], actions = actions, cancel = True, back = True)
