# Load Testing System - NL International AI Bots

Система нагрузочного тестирования для AI-Куратора и AI-Контент-Менеджера.

## Возможности

- **Параллельное выполнение** - контроль concurrency (одновременных запросов)
- **Ramp-up** - постепенное увеличение нагрузки
- **100 тестовых персон** - реалистичные профили пользователей
- **Smart Mocks** - эмуляция AI без реальных API вызовов
- **Real-time метрики** - прогресс, RPS, Response Time, Error Rate
- **Отчёты** - консоль, CSV, HTML с графиками (matplotlib)

## Структура

```
tests/load_testing/
├── fixtures/
│   ├── personas.py          # 100 тестовых пользователей
│   └── __init__.py
├── metrics/
│   ├── collector.py         # Сбор метрик в реальном времени
│   ├── reporter.py          # Консольный и HTML репорты
│   └── __init__.py
├── mocks/
│   ├── mock_ai_clients.py   # Mock Claude/YandexGPT
│   ├── mock_rag.py          # Mock RAG Engine
│   ├── mock_persona.py      # Mock Persona Manager
│   ├── mock_funnel.py       # Mock Funnel Manager
│   └── __init__.py
├── user_simulator.py        # VirtualUser, VirtualAdmin
├── load_runner.py           # Главный модуль для запуска тестов
├── example_test.py          # Примеры использования
└── README.md                # Эта документация
```

## Быстрый старт

### 1. Установка зависимостей

```bash
# Для HTML отчётов с графиками
pip install matplotlib
```

### 2. Запуск примера

```bash
cd tests/load_testing
python example_test.py
```

## Использование

### Пример 1: Быстрый тест AI-Куратора

```python
import asyncio
from load_runner import quick_curator_test

async def mock_bot_handler(message):
    """Mock handler для обработки сообщений"""
    from mocks.mock_ai_clients import MockAnthropicClient

    client = MockAnthropicClient(latency_ms=500)
    response = await client.generate_response(
        system_prompt="Ты AI-куратор",
        user_message=message.text
    )
    await message.answer(response)

# Запускаем тест
collector = await quick_curator_test(
    bot_handler=mock_bot_handler,
    users=10,          # 10 пользователей
    concurrent=5,      # 5 одновременных
    max_messages=5     # По 5 сообщений
)
```

### Пример 2: Тест Content Manager

```python
from load_runner import quick_content_manager_test

async def mock_content_generator(admin_id: int, post_type: str):
    """Mock generator для постов"""
    from mocks.mock_ai_clients import MockContentGenerator

    generator = MockContentGenerator(latency_ms=800)
    return await generator.generate_content(post_type=post_type)

# Запускаем тест
collector = await quick_content_manager_test(
    content_generator=mock_content_generator,
    admins=5,          # 5 админов
    concurrent=3,      # 3 одновременных
    posts_per_admin=10 # По 10 постов
)
```

### Пример 3: Стресс-тест

```python
from load_runner import stress_test

# Высокая нагрузка с ramp-up
collector = await stress_test(
    bot_handler=mock_bot_handler,
    users=50,          # 50 пользователей
    concurrent=20,     # 20 одновременных
    ramp_up_sec=10.0   # Выход на нагрузку за 10 сек
)
```

### Пример 4: Кастомная конфигурация

```python
from load_runner import LoadTestConfig, LoadTestRunner

config = LoadTestConfig(
    test_name="Мой тест",
    scenario="curator",              # curator | content_manager | mixed
    total_users=20,
    concurrent_users=10,
    max_messages_per_user=5,
    ramp_up_duration_sec=5.0,        # Постепенное увеличение нагрузки
    ramp_up_steps=5,
    delay_between_messages_sec=0.8,  # Задержка между сообщениями
    delay_variance_sec=0.3,          # Вариативность задержки
    export_csv=True,
    generate_html_report=True,
    output_dir="my_test_results"
)

runner = LoadTestRunner(config)
collector = await runner.run(bot_handler=mock_bot_handler)
```

## Тестовые персоны

Система включает 100 предгенерированных пользователей с разнообразными профилями:

### Сегменты (A-E)
- **A (25%)** - Амбициозные предприниматели (25-45 лет)
- **B (20%)** - Мамы в декрете (25-40 лет)
- **C (15%)** - Студенты (18-28 лет)
- **D (25%)** - Потребители продуктов (30-55 лет)
- **E (15%)** - Скептики (20-50 лет)

### Интенты
- **business (40%)** - Интересуются бизнесом
- **product (35%)** - Интересуются продуктами
- **curious (15%)** - Любопытные
- **skeptic (10%)** - Скептики

### Pain Points
- **weight (30%)** - Снижение веса
- **energy (20%)** - Энергия и бодрость
- **immunity (15%)** - Иммунитет
- **beauty (20%)** - Красота
- **money (15%)** - Дополнительный доход

### Поведение
- **active (40%)** - Активные, много вопросов
- **passive (35%)** - Пассивные, короткие ответы
- **skeptic (25%)** - Скептичные, критикуют

### Использование персон

```python
from fixtures.personas import get_test_personas, get_personas_by_segment

# Получить всех персон
personas = get_test_personas()  # 100 пользователей

# Фильтровать по сегменту
segment_a = get_personas_by_segment(personas, "A")

# Фильтровать по интенту
business_users = get_personas_by_intent(personas, "business")

# Пример персоны
persona = personas[0]
print(f"{persona.name}, {persona.age}, {persona.city}")
print(f"Сегмент: {persona.segment}")
print(f"Интент: {persona.intent}")
print(f"Сообщений: {len(persona.test_messages)}")
```

## Метрики

### Собираемые метрики

- **Response Time**: min, max, avg, median, P95, P99
- **Throughput**: requests per second
- **Error Rate**: процент ошибок
- **Распределение**: по интентам, сегментам, типам ошибок

### Экспорт метрик

```python
from metrics.collector import MetricsCollector

collector = MetricsCollector()

# Записываем метрику
collector.record_message(
    user_id=1,
    success=True,
    response_time_ms=500,
    intent="business",
    segment="A"
)

# Получаем сводку
summary = collector.get_summary()
print(summary)

# Экспорт в CSV
collector.export_to_csv("metrics.csv")
collector.export_aggregated_to_csv("metrics_aggregated.csv")
```

### Консольный репорт

```python
from metrics.reporter import ConsoleReporter

reporter = ConsoleReporter(collector)

# Заголовок теста
reporter.print_header("Мой тест", total_users=10, total_messages=50)

# Прогресс в реальном времени
reporter.print_progress(
    current=25,
    total=50,
    elapsed_sec=10.0,
    show_metrics=True
)

# Финальная сводка
reporter.print_summary(test_duration_sec=30.0)
```

### HTML отчёт с графиками

```python
from metrics.reporter import HTMLReporter

html_reporter = HTMLReporter(collector)
html_reporter.generate_report(
    output_path="report.html",
    test_name="Мой тест",
    test_config={
        "Пользователей": 10,
        "Сценарий": "curator",
    }
)
```

HTML отчёт включает:
- Основные метрики (красивые карточки)
- Response Time over Time (линейный график)
- Throughput over Time (линейный график)
- Error Rate over Time (линейный график)
- Response Time Distribution (гистограмма)
- Intent/Segment Distribution (круговая диаграмма)

## Mocks

### MockAnthropicClient

Эмулирует Claude Sonnet 3.5:

```python
from mocks.mock_ai_clients import MockAnthropicClient

client = MockAnthropicClient(
    latency_ms=500,           # Средняя задержка
    latency_variance_ms=200   # Вариативность
)

response = await client.generate_response(
    system_prompt="Ты AI-куратор",
    user_message="Привет!",
    temperature=0.7
)
```

Features:
- Smart Intent Detection (по ключевым словам)
- Персонализированные ответы
- Реалистичная задержка API
- Метрики calls/latency/intent distribution

### MockContentGenerator

Эмулирует генератор постов:

```python
from mocks.mock_ai_clients import MockContentGenerator

generator = MockContentGenerator(latency_ms=800)

post = await generator.generate_content(
    post_type="product",
    mood={"hook": "Слушай, вот интересная тема..."}
)
```

### MockRAGEngine

Эмулирует RAG без pgvector:

```python
from mocks.mock_rag import MockRAGEngine

rag = MockRAGEngine()

results = await rag.retrieve(
    query="Energy Diet",
    top_k=5,
    min_similarity=0.45
)
```

Features:
- Keyword search вместо vector search
- 100+ документов в базе знаний
- Быстрый поиск без нагрузки на БД

## Конфигурация

### LoadTestConfig параметры

| Параметр | Описание | По умолчанию |
|----------|----------|--------------|
| `test_name` | Название теста | - |
| `scenario` | Сценарий (curator/content_manager/mixed) | - |
| `total_users` | Количество пользователей | 10 |
| `concurrent_users` | Одновременных пользователей | 5 |
| `max_messages_per_user` | Максимум сообщений на пользователя | None |
| `ramp_up_duration_sec` | Время выхода на полную нагрузку | 0 |
| `ramp_up_steps` | Количество шагов ramp-up | 5 |
| `delay_between_messages_sec` | Задержка между сообщениями | 1.0 |
| `delay_variance_sec` | Вариативность задержки | 0.5 |
| `export_csv` | Экспортировать CSV | True |
| `generate_html_report` | Генерировать HTML отчёт | True |
| `output_dir` | Директория для результатов | "load_test_results" |

## Сценарии

### 1. Curator Scenario

Тестирование AI-Куратора:

```python
config = LoadTestConfig(
    test_name="Тест AI-Куратора",
    scenario="curator",
    total_users=20,
    concurrent_users=10,
)

runner = LoadTestRunner(config)
await runner.run(bot_handler=mock_bot_handler)
```

### 2. Content Manager Scenario

Тестирование Content Manager:

```python
config = LoadTestConfig(
    test_name="Тест Content Manager",
    scenario="content_manager",
    total_users=10,  # Количество админов
    concurrent_users=5,
)

runner = LoadTestRunner(config)
await runner.run(content_generator=mock_content_generator)
```

### 3. Mixed Scenario

Смешанный тест (curator + content_manager):

```python
config = LoadTestConfig(
    test_name="Смешанный тест",
    scenario="mixed",
    total_users=20,  # 10 curator + 10 content manager
    concurrent_users=8,
)

runner = LoadTestRunner(config)
await runner.run(
    bot_handler=mock_bot_handler,
    content_generator=mock_content_generator
)
```

## Результаты

После выполнения теста создаются файлы:

```
load_test_results/
├── test_name_20260203_143022.csv              # Все метрики
├── test_name_20260203_143022_aggregated.csv   # Агрегированные (по окнам)
├── test_name_20260203_143022.html             # HTML отчёт
└── charts/                                     # Графики
    ├── response_time.png
    ├── throughput.png
    ├── error_rate.png
    ├── rt_distribution.png
    └── intent_distribution.png
```

## Примеры результатов

### Консольный вывод

```
================================================================================
НАГРУЗОЧНЫЙ ТЕСТ: Быстрый тест AI-Куратора
================================================================================
Начало: 2026-02-03 14:30:22
Пользователей: 10
Ожидается запросов: 30
================================================================================

Конфигурация:
  Сценарий: curator
  Пользователей: 10
  Одновременных: 5
  Задержка между запросами: 0.5 сек

[████████████████████████████████████████] 100.0% | 30/30 | Прошло: 15s | RPS: 2.0
  └─ Метрики (5 сек): Успешно: 98.0% | Avg RT: 520ms | P95: 780ms

================================================================================
ИТОГОВАЯ СВОДКА
================================================================================

Длительность теста: 15s
Всего запросов: 30
Успешных: 29 (96.7%)
Ошибок: 1 (3.3%)

Response Time:
  Минимальный: 310.50 ms
  Максимальный: 890.20 ms
  Средний: 545.30 ms
  Медиана (P50): 520.00 ms
  P95: 780.00 ms
  P99: 850.00 ms

Throughput:
  Запросов в секунду: 2.00 req/sec

Распределение по интентам:
  business    :   12 ( 40.0%)
  product     :   10 ( 33.3%)
  curious     :    5 ( 16.7%)
  skeptic     :    3 ( 10.0%)
```

## FAQ

### Как протестировать реальные боты?

Замените mock handlers на реальные:

```python
from curator_bot.handlers.messages import handle_message
from content_manager_bot.ai.content_generator import ContentGenerator

# Реальный handler
await quick_curator_test(bot_handler=handle_message)

# Реальный generator
generator = ContentGenerator()
await quick_content_manager_test(
    content_generator=generator.generate_content
)
```

### Как изменить количество персон?

```python
from fixtures.personas import generate_test_personas

# Генерируем 200 персон
personas = generate_test_personas(count=200)
```

### Как добавить свои сообщения?

```python
from user_simulator import VirtualUser

user = VirtualUser(
    user_id=1,
    telegram_id=123456,
    name="Тестовый",
    age=30,
    city="Москва",
    segment="A",
    intent="business",
    pain_point="money",
    behavior="active",
    test_messages=[
        "Привет!",
        "Хочу зарабатывать с NL",
        "Сколько можно заработать?",
    ]
)
```

### Как настроить latency mocks?

```python
from mocks.mock_ai_clients import MockAnthropicClient

# Быстрый API (200ms ±100ms)
fast_client = MockAnthropicClient(latency_ms=200, latency_variance_ms=100)

# Медленный API (1000ms ±300ms)
slow_client = MockAnthropicClient(latency_ms=1000, latency_variance_ms=300)
```

### Как запустить тест без HTML?

```python
config = LoadTestConfig(
    test_name="Мой тест",
    scenario="curator",
    export_csv=True,
    generate_html_report=False  # Отключаем HTML
)
```

## Рекомендации

### Начните с малого

```python
# Первый тест: 5 пользователей, 3 сообщения
await quick_curator_test(users=5, concurrent=3, max_messages=3)
```

### Постепенно увеличивайте нагрузку

```python
# Тест с ramp-up
await stress_test(users=50, concurrent=20, ramp_up_sec=10.0)
```

### Анализируйте результаты

- Смотрите P95/P99 Response Time (не только average)
- Проверяйте Error Rate
- Анализируйте графики (спайки, тренды)
- Сравнивайте результаты разных тестов

### Используйте реалистичные задержки

```python
config = LoadTestConfig(
    delay_between_messages_sec=2.0,  # Пользователь думает 2 сек
    delay_variance_sec=1.0,          # ±1 сек вариативность
)
```

## Поддержка

Если возникли вопросы или проблемы, проверьте:

1. **Зависимости установлены**: `pip install matplotlib`
2. **Импорты работают**: `python -c "from load_runner import *"`
3. **Примеры запускаются**: `python example_test.py`

Для детальной отладки добавьте логирование:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

---

**Версия**: 1.0
**Дата**: 2026-02-03
**Автор**: Claude Code
