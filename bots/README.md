# bots

Transport-layer проекта.

Пакет `bots` содержит общие абстракции и конкретные реализации ботов для Telegram и VK. Его задача — скрыть различия внешних API и предоставить app-layer единый способ работать с событиями, сообщениями, клавиатурами, callback-ами и вложениями.

## Назначение

`bots` отделяет транспортную логику от бизнес-логики приложения.

Внешние API Telegram и VK отличаются:

- форматом событий;
- способом отправки сообщений;
- устройством inline-кнопок;
- форматом callback-ов;
- правилами загрузки вложений;
- поведением редактирования и удаления сообщений.

Пакет приводит эти различия к общей внутренней модели, чтобы слой `relay` мог работать с ботами одинаково.

## Архитектура пакета

```text
external Telegram/VK API
        ↓
bots.telegram / bots.vk
        ↓
bots.base
        ↓
bots.wrapper
        ↓
relay
```

Основные части:

- `bots/base` — transport-independent контракты: `Bot`, `Event`, `Message`, `Keyboard`, `Button`, `Attachment`, `VoiceMessage`.
- `bots/telegram` — адаптер Telegram поверх `pyTelegramBotAPI`.
- `bots/vk` — адаптер VK поверх `vk_api`.
- `bots/wrapper` — transport-independent `Message`, который хранит группы отправленных сообщений по ботам и чатам.
- `bots/utils` — общие helper-функции для дат, файлов, текста, окружения, аудио и mapping-операций.
- `bots/runtime.py` и `bindings.py` — связывают базовые и конкретные классы так, чтобы у транспортов был единый вложенный API.

## Основной поток данных

```text
Telegram/VK event
        ↓
bots.telegram или bots.vk
        ↓
bots.base.Event
        ↓
relay.handlers
        ↓
relay.sessions / relay.domain / relay.gpt
        ↓
bots.wrapper.Message
        ↓
Telegram/VK API
```

## Что даёт transport-layer

- App-layer не знает деталей `telebot` и `vk_api`.
- Сценарии меню и сессий переиспользуются между платформами.
- Callback data и кнопки приводятся к общему формату.
- Вложения сериализуются и загружаются через транспортные адаптеры.
- Wrapper-сообщение может воспринимать несколько platform-specific сообщений как одну бизнес-сущность.
- Новый транспорт можно добавить как отдельный пакет, не переписывая `relay`.

## Как добавить новый транспорт

Новый adapter должен повторить ответственность существующих `bots/telegram` и `bots/vk`:

1. Реализовать класс бота на базе общего контракта `bots.base.Bot`.
2. Описать platform-specific `Message`, `Event`, `Keyboard`, `Button` и `Attachment`.
3. Добавить bindings, чтобы app-layer мог обращаться к вложенным типам единообразно.
4. Поддержать отправку, редактирование, удаление и разбор callback/event payload.
5. Добавить тесты transport-layer без реальных токенов и сетевых вызовов.
