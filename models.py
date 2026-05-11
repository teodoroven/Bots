"""
Описывает доступные GPT-модели и provider-specific настройки лимитов.
Модуль относится к архитектурной зоне: корневой слой проекта, который связывает запуск, compatibility exports и общие настройки приложения.

### Публичные классы
- `Model`: описание GPT-модели и её лимитов.
- `AnthropicModel`: описание модели провайдера Anthropic.
- `DeepSeekModel`: описание модели провайдера DeepSeek.
- `GoogleModel`: описание модели провайдера Google.
- `OpenAIModel`: описание модели провайдера OpenAI.

### Публичные функции
- Публичные функции отсутствуют.

### Публичные константы и типы
- Ключевые публичные значения: `MODELS`.

### Связи
Используется соседними слоями проекта как корневой модуль запуска, compatibility exports или общий набор настроек.
"""

class Model:
    """
    Хранит настройки GPT-модели для выбора провайдера, проверки лимитов и расчёта стоимости.

    Экземпляры используются app-layer как справочник: URL API, имя модели, размеры
    prompt/context, признаки возможностей и тарифы в рублях за миллион токенов.
    """
    def __init__(
        self,
        base_url: str,
        model: str,
        max_prompt: int,
        max_context: int,
        reasoning: bool = False,
        search: bool = False,
        audio: bool = False,
        price_per_request: float = 0.0,
        price_per_response: float = 0.0,
        cache_read_cost: float | None = None,
        cache_write_cost: float | None = None,
        economy_rating: int = 5, power_rating: int = 5,
    ):
        """
        Сохраняет описание модели для GPT runtime и административных меню.
        `base_url` и `model` используются при создании OpenAI-compatible client,
        `max_prompt` и `max_context` ограничивают запрос, capability-флаги
        показывают доступные сценарии, а цены и рейтинги нужны для расчёта
        стоимости и выбора модели.

        ### Аргументы:
        :param base_url: URL provider API для OpenAI-compatible клиента
        :param model: имя модели, передаваемое provider API
        :param max_prompt: максимум токенов в пользовательском prompt
        :param max_context: максимум токенов всего запроса с историей и system context
        :param reasoning: поддерживает ли модель reasoning-сценарии
        :param search: поддерживает ли модель поиск в интернете
        :param audio: поддерживает ли модель аудио-сценарии
        :param price_per_request: цена 1 млн input tokens в рублях
        :param price_per_response: цена 1 млн output tokens в рублях
        :param cache_read_cost: цена чтения cached input в рублях, если provider это поддерживает
        :param cache_write_cost: цена записи cached input в рублях, если provider это поддерживает
        :param economy_rating: оценка экономичности модели для UI и выбора
        :param power_rating: оценка мощности модели для UI и выбора
        """
        self.base_url: str = base_url
        self.model: str = model
        self.max_prompt: int = max_prompt
        self.max_context: int = max_context
        self.reasoning: bool = reasoning
        self.search: bool = search
        self.audio: bool = audio
        self.price_per_request: float = price_per_request
        self.price_per_response: float = price_per_response
        self.cache_read_cost: float | None = cache_read_cost
        self.cache_write_cost: float | None = cache_write_cost
        self.economy_rating: int = economy_rating
        self.power_rating: int = power_rating

    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """
        Считает стоимость запроса по тарифам входных и выходных токенов.
        """
        input_cost = (input_tokens / 1_000_000) * self.price_per_request
        output_cost = (output_tokens / 1_000_000) * self.price_per_response
        return input_cost + output_cost

    def calc_tokens(self, money_rub: float) -> int:
        """
        Оценивает общий объём токенов при равных долях prompt и response.
        """
        if self.price_per_request <= 0 or self.price_per_response <= 0:
            return 0

        # Для соотношения 1:1 (одинаковое количество токенов запроса и ответа)
        prompt_ratio = 1.0  # токены запроса
        response_ratio = 1.0  # токены ответа

        # Стоимость одной "пары" соотношения
        price_per_ratio_unit = (
            (self.price_per_request * prompt_ratio) +
            (self.price_per_response * response_ratio)
        ) / 1000000

        # Количество таких "пар" за указанную сумму
        ratio_units = money_rub / price_per_ratio_unit

        # Общее количество токенов = пары × (prompt + response)
        total_tokens = int(ratio_units * (prompt_ratio + response_ratio))

        return total_tokens


class AnthropicModel(Model):
    """
    Настройка модели Anthropic с API URL провайдера и поддержкой cached input.
    """
    def __init__(self, *, model: str, max_prompt: int, max_context: int, **kwargs):
        """
        Создаёт описание Anthropic-модели и включает признак поддержки кэша.
        """
        super().__init__(
            base_url="https://api.anthropic.com",
            model=model,
            max_prompt=max_prompt,
            max_context=max_context,
            **kwargs
        )
        self.cache_support = True


class DeepSeekModel(Model):
    """
    Настройка модели DeepSeek с API URL провайдера.
    """

    def __init__(self, *, model: str, max_prompt: int, max_context: int, **kwargs):
        """
        Создаёт описание DeepSeek-модели с заданными лимитами prompt и context.
        """
        super().__init__(
            base_url="https://api.deepseek.com",
            model=model,
            max_prompt=max_prompt,
            max_context=max_context,
            **kwargs
        )


class GoogleModel(Model):
    """
    Настройка модели Google Gemini с API URL Generative Language.
    """

    def __init__(self, *, model: str, max_prompt: int, max_context: int, **kwargs):
        """
        Создаёт описание Google-модели с заданными лимитами prompt и context.
        """
        super().__init__(
            base_url="https://generativelanguage.googleapis.com",
            model=model,
            max_prompt=max_prompt,
            max_context=max_context,
            **kwargs
        )


class OpenAIModel(Model):
    """
    Настройка OpenAI-совместимой модели через ProxyAPI и поддержку cached input.
    """

    def __init__(self, *, model: str, max_prompt: int, max_context: int, **kwargs):
        """
        Создаёт описание OpenAI-модели и включает признак поддержки кэша.
        """
        super().__init__(
            base_url="https://api.proxyapi.ru/openai/v1",
            model=model,
            max_prompt=max_prompt,
            max_context=max_context,
            **kwargs
        )
        self.cache_support = True


AnthropicClaudeOpus4_20250514 = AnthropicModel(
    model="claude-opus-4-20250514",
    max_prompt=200000,
    max_context=200000,
    reasoning=True,
    price_per_request=3672.0,
    price_per_response=18360.0,
    cache_read_cost=367.20,
    cache_write_cost=4590.0,
    economy_rating=9,
    power_rating=10,
)

AnthropicClaude3Opus20240229 = AnthropicModel(
    model="claude-3-opus-20240229",
    max_prompt=200000,
    max_context=200000,
    reasoning=True,
    price_per_request=3672.0,
    price_per_response=18360.0,
    cache_read_cost=367.20,
    cache_write_cost=4590.0,
    economy_rating=9,
    power_rating=10,
)

AnthropicClaude37Sonnet20250219 = AnthropicModel(
    model="claude-3-7-sonnet-20250219",
    max_prompt=200000,
    max_context=200000,
    price_per_request=734.40,
    price_per_response=3672.0,
    cache_read_cost=73.44,
    cache_write_cost=918.0,
    economy_rating=6,
    power_rating=7,
)

AnthropicClaude35Sonnet20241022 = AnthropicModel(
    model="claude-3-5-sonnet-20241022",
    max_prompt=200000,
    max_context=200000,
    price_per_request=734.40,
    price_per_response=3672.0,
    cache_read_cost=73.44,
    cache_write_cost=918.0,
    economy_rating=6,
    power_rating=7,
)

AnthropicClaude35Sonnet20240620 = AnthropicModel(
    model="claude-3-5-sonnet-20240620",
    max_prompt=200000,
    max_context=200000,
    price_per_request=734.40,
    price_per_response=3672.0,
    cache_read_cost=73.44,
    cache_write_cost=918.0,
    economy_rating=6,
    power_rating=7,
)

AnthropicClaude35Haiku20241022 = AnthropicModel(
    model="claude-3-5-haiku-20241022",
    max_prompt=200000,
    max_context=200000,
    price_per_request=244.80,
    price_per_response=1224.0,
    cache_read_cost=24.48,
    cache_write_cost=306.0,
    economy_rating=3,
    power_rating=5,
)

DeepSeekDeepseekChat = DeepSeekModel(
    model="deepseek-chat",
    max_prompt=128000,
    max_context=128000,
    price_per_request=66.10,
    price_per_response=269.28,
    economy_rating=2,
    power_rating=5,
)

GoogleGemini25ProPreview0605 = GoogleModel(
    model="gemini-2.5-pro-preview-06-05",
    max_prompt=128000,
    max_context=1000000,
    price_per_request=306.0,
    price_per_response=2448.0,
    economy_rating=7,
    power_rating=9,
)

GoogleGemini25ProPreview0506 = GoogleModel(
    model="gemini-2.5-pro-preview-05-06",
    max_prompt=128000,
    max_context=1000000,
    price_per_request=306.0,
    price_per_response=2448.0,
    economy_rating=7,
    power_rating=9,
)

GoogleGemini25ProPreview0325 = GoogleModel(
    model="gemini-2.5-pro-preview-03-25",
    max_prompt=128000,
    max_context=1000000,
    price_per_request=306.0,
    price_per_response=2448.0,
    economy_rating=7,
    power_rating=9,
)

GoogleGemini25FlashPreview0520 = GoogleModel(
    model="gemini-2.5-flash-preview-05-20",
    max_prompt=128000,
    max_context=1000000,
    price_per_request=36.72,
    price_per_response=146.88,
    economy_rating=3,
    power_rating=5,
)

GoogleGemini25FlashPreview0417 = GoogleModel(
    model="gemini-2.5-flash-preview-04-17",
    max_prompt=128000,
    max_context=1000000,
    price_per_request=36.72,
    price_per_response=146.88,
    economy_rating=3,
    power_rating=5,
)

GoogleGemini25FlashLitePreview0617 = GoogleModel(
    model="gemini-2.5-flash-lite-preview-06-17",
    max_prompt=128000,
    max_context=1000000,
    price_per_request=24.48,
    price_per_response=122.40,
    economy_rating=2,
    power_rating=4,
)

GoogleGemini25Flash = GoogleModel(
    model="gemini-2.5-flash",
    max_prompt=128000,
    max_context=1000000,
    price_per_request=73.44,
    price_per_response=612.0,
    economy_rating=4,
    power_rating=6,
)

GoogleGemini20FlashLite = GoogleModel(
    model="gemini-2.0-flash-lite",
    max_prompt=128000,
    max_context=1000000,
    price_per_request=18.36,
    price_per_response=73.44,
    economy_rating=1,
    power_rating=3,
)

GoogleGemini20Flash = GoogleModel(
    model="gemini-2.0-flash",
    max_prompt=128000,
    max_context=1000000,
    price_per_request=24.48,
    price_per_response=97.92,
    economy_rating=2,
    power_rating=4,
)

GoogleGemini15Pro = GoogleModel(
    model="gemini-1.5-pro",
    max_prompt=128000,
    max_context=1000000,
    price_per_request=856.80,
    price_per_response=1713.60,
    economy_rating=8,
    power_rating=8,
)

GoogleGemini15Flash = GoogleModel(
    model="gemini-1.5-flash",
    max_prompt=128000,
    max_context=1000000,
    price_per_request=18.36,
    price_per_response=73.44,
    economy_rating=1,
    power_rating=3,
)

OpenAIGpt35Turbo0125 = OpenAIModel(
    model="gpt-3.5-turbo-0125",
    max_prompt=16384,
    max_context=16384,
    reasoning=False,
    price_per_request=122.40,
    price_per_response=367.20,
    economy_rating=1,
    power_rating=2,
)

OpenAIO3Pro20250610 = OpenAIModel(
    model="o3-pro-2025-06-10",
    max_prompt=128000,
    max_context=128000,
    reasoning=True,
    price_per_request=2400.0,
    price_per_response=9600.0,
    economy_rating=10,
    power_rating=10,
)

OpenAIO3Mini20250131 = OpenAIModel(
    model="o3-mini-2025-01-31",
    max_prompt=128000,
    max_context=128000,
    price_per_request=269.28,
    price_per_response=1077.12,
    cache_read_cost=134.64,
    economy_rating=4,
    power_rating=6,
)

OpenAIO320250416 = OpenAIModel(
    model="o3-2025-04-16",
    max_prompt=128000,
    max_context=128000,
    price_per_request=576.0,
    price_per_response=1600.0,
    cache_read_cost=144.0,
    economy_rating=5,
    power_rating=7,
)

OpenAIO1Pro20250319 = OpenAIModel(
    model="o1-pro-2025-03-19",
    max_prompt=128000,
    max_context=128000,
    reasoning=True,
    price_per_request=15300.0,
    price_per_response=76500.0,
    economy_rating=10,
    power_rating=10,
)

OpenAIO1Preview20240912 = OpenAIModel(
    model="o1-preview-2024-09-12",
    max_prompt=128000,
    max_context=128000,
    price_per_request=2550.0,
    price_per_response=7650.0,
    cache_read_cost=1275.0,
    economy_rating=9,
    power_rating=9,
)

OpenAIO1Mini20240912 = OpenAIModel(
    model="o1-mini-2024-09-12",
    max_prompt=128000,
    max_context=128000,
    price_per_request=734.40,
    price_per_response=1530.0,
    cache_read_cost=367.20,
    economy_rating=6,
    power_rating=7,
)

OpenAIO120241217 = OpenAIModel(
    model="o1-2024-12-17",
    max_prompt=128000,
    max_context=128000,
    price_per_request=2550.0,
    price_per_response=7650.0,
    cache_read_cost=1275.0,
    economy_rating=9,
    power_rating=9,
)

OpenAIGpt4oSearchPreview20250311 = OpenAIModel(
    model="gpt-4o-search-preview-2025-03-11",
    max_prompt=128000,
    max_context=128000,
    search=True,
    price_per_request=612.0,
    price_per_response=2448.0,
    economy_rating=7,
    power_rating=8,
)

OpenAIGpt4oMiniSearchPreview20250311 = OpenAIModel(
    model="gpt-4o-mini-search-preview-2025-03-11",
    max_prompt=128000,
    max_context=128000,
    search=True,
    price_per_request=36.72,
    price_per_response=146.88,
    economy_rating=3,
    power_rating=5,
)

OpenAIGpt4oMiniAudioPreview20241217 = OpenAIModel(
    model="gpt-4o-mini-audio-preview-2024-12-17",
    max_prompt=128000,
    max_context=128000,
    audio=True,
    price_per_request=2448.0,
    price_per_response=4896.0,
    economy_rating=8,
    power_rating=7,
)

OpenAIGpt4oMini20240718 = OpenAIModel(
    model="gpt-4o-mini-2024-07-18",
    max_prompt=128000,
    max_context=128000,
    price_per_request=36.72,
    price_per_response=146.88,
    cache_read_cost=18.36,
    economy_rating=3,
    power_rating=5,
)

OpenAIGpt4oAudioPreview20241217 = OpenAIModel(
    model="gpt-4o-audio-preview-2024-12-17",
    max_prompt=128000,
    max_context=128000,
    audio=True,
    price_per_request=24480.0,
    price_per_response=48960.0,
    economy_rating=10,
    power_rating=9,
)

OpenAIGpt4oAudioPreview20241001 = OpenAIModel(
    model="gpt-4o-audio-preview-2024-10-01",
    max_prompt=128000,
    max_context=128000,
    audio=True,
    price_per_request=24480.0,
    price_per_response=48960.0,
    economy_rating=10,
    power_rating=9,
)

OpenAIGpt4o64kOutputAlpha = OpenAIModel(
    model="gpt-4o-64k-output-alpha",
    max_prompt=64000,
    max_context=64000,
    price_per_request=1468.80,
    price_per_response=4406.40,
    economy_rating=8,
    power_rating=8,
)

OpenAIGpt4o20241120 = OpenAIModel(
    model="gpt-4o-2024-11-20",
    max_prompt=128000,
    max_context=128000,
    price_per_request=612.0,
    price_per_response=2448.0,
    cache_read_cost=306.0,
    economy_rating=7,
    power_rating=8,
)

OpenAIGpt4o20240806 = OpenAIModel(
    model="gpt-4o-2024-08-06",
    max_prompt=128000,
    max_context=128000,
    price_per_request=612.0,
    price_per_response=2448.0,
    cache_read_cost=306.0,
    economy_rating=7,
    power_rating=8,
)

OpenAIGpt41Mini20250414 = OpenAIModel(
    model="gpt-4.1-mini-2025-04-14",
    max_prompt=128000,
    max_context=128000,
    price_per_request=97.92,
    price_per_response=391.68,
    cache_read_cost=24.48,
    economy_rating=2,
    power_rating=5,
)

OpenAIGpt4120250414 = OpenAIModel(
    model="gpt-4.1-2025-04-14",
    max_prompt=128000,
    max_context=128000,
    price_per_request=489.60,
    price_per_response=1958.40,
    cache_read_cost=122.40,
    economy_rating=6,
    power_rating=7,
)

OpenAIGpt4Turbo20240409 = OpenAIModel(
    model="gpt-4-turbo-2024-04-09",
    max_prompt=128000,
    max_context=128000,
    price_per_request=2448.0,
    price_per_response=7344.0,
    economy_rating=8,
    power_rating=9,
)

OpenAIGpt432k0613 = OpenAIModel(
    model="gpt-4-32k-0613",
    max_prompt=32000,
    max_context=32000,
    price_per_request=14688.0,
    price_per_response=29376.0,
    economy_rating=10,
    power_rating=9,
)

OpenAIGpt5Nano20250807 = OpenAIModel(
    model="gpt-5-nano-2025-08-07",
    max_prompt=128000,
    max_context=128000,
    price_per_request=12.24,
    price_per_response=97.92,
    cache_read_cost=1.22,
    economy_rating=1,
    power_rating=4,
)

OpenAIGpt5Mini20250807 = OpenAIModel(
    model="gpt-5-mini-2025-08-07",
    max_prompt=128000,
    max_context=128000,
    price_per_request=61.20,
    price_per_response=489.60,
    cache_read_cost=6.12,
    economy_rating=2,
    power_rating=5,
)

OpenAIGpt5Codex = OpenAIModel(
    model="gpt-5-codex",
    max_prompt=128000,
    max_context=128000,
    price_per_request=306.0,
    price_per_response=2448.0,
    cache_read_cost=30.60,
    economy_rating=5,
    power_rating=7,
)

OpenAIGpt5ChatLatest = OpenAIModel(
    model="gpt-5-chat-latest",
    max_prompt=128000,
    max_context=128000,
    price_per_request=306.0,
    price_per_response=2448.0,
    cache_read_cost=30.60,
    economy_rating=5,
    power_rating=7,
)

OpenAIGpt520250807 = OpenAIModel(
    model="gpt-5-2025-08-07",
    max_prompt=128000,
    max_context=128000,
    price_per_request=306.0,
    price_per_response=2448.0,
    cache_read_cost=30.60,
    economy_rating=5,
    power_rating=7,
)


MODELS: dict[str, list[Model]] = {
    "Anthropic": [
        AnthropicClaudeOpus4_20250514,
        AnthropicClaude3Opus20240229,
        AnthropicClaude37Sonnet20250219,
        AnthropicClaude35Sonnet20241022,
        AnthropicClaude35Sonnet20240620,
        AnthropicClaude35Haiku20241022,
    ],

    "DeepSeek": [
        DeepSeekDeepseekChat,
    ],

    "Google": [
        GoogleGemini25ProPreview0605,
        GoogleGemini25ProPreview0506,
        GoogleGemini25ProPreview0325,
        GoogleGemini25FlashPreview0520,
        GoogleGemini25FlashPreview0417,
        GoogleGemini25FlashLitePreview0617,
        GoogleGemini25Flash,
        GoogleGemini20FlashLite,
        GoogleGemini20Flash,
        GoogleGemini15Pro,
        GoogleGemini15Flash,
    ],

    "OpenAI": [
        OpenAIGpt35Turbo0125,
        OpenAIO3Pro20250610,
        OpenAIO3Mini20250131,
        OpenAIO320250416,
        OpenAIO1Pro20250319,
        OpenAIO1Preview20240912,
        OpenAIO1Mini20240912,
        OpenAIO120241217,
        # OpenAIGpt4oSearchPreview20250311,
        # OpenAIGpt4oMiniSearchPreview20250311,
        # OpenAIGpt4oMiniAudioPreview20241217,
        # OpenAIGpt4oMini20240718,
        # OpenAIGpt4oAudioPreview20241217,
        # OpenAIGpt4oAudioPreview20241001,
        # OpenAIGpt4o64kOutputAlpha,
        # OpenAIGpt4o20241120,
        # OpenAIGpt4o20240806,
        OpenAIGpt41Mini20250414,
        OpenAIGpt4120250414,
        OpenAIGpt4Turbo20240409,
        OpenAIGpt432k0613,
        OpenAIGpt5Nano20250807,
        OpenAIGpt5Mini20250807,
        OpenAIGpt5Codex,
        OpenAIGpt5ChatLatest,
        OpenAIGpt520250807,
    ]
}
