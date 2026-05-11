# relay

App-layer проекта.

Пакет `relay` содержит основную бизнес-логику чат-бота автошколы: обработку событий, пользовательские и административные сессии, доменную модель, GPT-настройки, уведомления, очереди и runtime-сборку приложения.

## Назначение

`relay` не должен знать детали Telegram Bot API или VK API. Он работает с унифицированными объектами из `bots`: `Message`, `Event`, `Keyboard`, `Button`, `Attachment`.

Главная ответственность слоя:

- принять событие от транспорта;
- найти пользователя и актуальный сценарий;
- обработать команду, callback или текст;
- обновить сессию, доменную модель, GPT-запрос или диалог;
- сохранить состояние через `db`;
- отправить ответ через wrapper/transport-layer.

## Основной поток события

```text
bots.Event
     ↓
relay.handlers.Context
     ↓
CommandsHandler / SessionsHandler / ChatGPTHandler
     ↓
relay.sessions / relay.domain / relay.gpt
     ↓
relay.runtime
     ↓
db.Storage + bots.wrapper.Message
```

## Ключевые зоны

- `relay.app.App` — главный app-layer класс, который собирает runtime-миксины и registry классов.
- `relay.handlers` — маршрутизация команд, callback-ов, сессий и GPT-запросов.
- `relay.sessions` — state-machine пользовательских и административных сценариев.
- `relay.domain` — дерево доменных элементов: филиалы, даты, вопросы, контексты, лимиты.
- `relay.gpt` — GPT wrapper, `Request`, `Response`, подсчёт и обработка токенов.
- `relay.conversations` — диалоги клиента и администратора через бота.
- `relay.notifications` — события и уведомления для администраторов.
- `relay.queues` — очереди сообщений и фоновых задач.
- `relay.runtime` — миксины, которые разделяют ответственность `App` по зонам.

## Context

`Context` — структура передачи параметров между обработчиками и сессиями. Она хранит только нужные ссылки: приложение, бот, пользователя, событие и текущий handler.

Такой подход снижает связанность:

- сессия получает доступ только к тому, что нужно её сценарию;
- callback-и проходят по цепочке обработчиков до нужного места;
- app-layer не смешивает transport details, storage details и бизнес-сценарии в одном объекте.

## Sessions

Сессии реализуют state-machine поверх сообщений и меню:

- `MainSession` — запись клиента на занятие;
- `ConvSession` — диалог клиента и администратора;
- `GPTSession` и связанные сессии — настройка GPT;
- `SessionUsers`, `UserSession`, `SessionAdmins`, `AdminSession` — административные сценарии;
- `MenuSession`, `LevelSession`, `ModeSession` — базовые механизмы меню, уровней и режимов.

Сессии используют преимущества `bots.wrapper.Message`: одно бизнес-сообщение может по-разному выглядеть и обновляться в Telegram и VK, но для app-layer остаётся единой сущностью.

## Runtime

Runtime-миксины разделяют `App` по зонам ответственности:

- пользователи и администраторы;
- боты и lifecycle;
- сообщения и очереди;
- диалоги;
- доменная модель;
- GPT-настройки, контент, лимиты и запросы;
- фоновые process tasks.

## Тесты

Публичные tests для app-layer находятся в `tests/relay`:

```bash
python -m unittest discover tests -p "*_test.py"
```

Они проверяют callback data, handlers, sessions, меню, пользователей, GPT debounce, очереди и уведомления без реальных Telegram/VK токенов.
