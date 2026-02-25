# Система нагрузочного тестирования

## Обзор

Полноценная система автоматизированного нагрузочного тестирования для AI-Куратора и AI-Контент-Менеджера. Эмулирует до 100 параллельных пользователей, собирает метрики, генерирует HTML-отчёты с графиками.

## Основные возможности

✅ **100 виртуальных пользователей** с реалистичными профилями
✅ **Smart Mock System** — эмуляция AI без реальных API вызовов
✅ **Параллельное выполнение** — asyncio + Semaphore
✅ **Ramp-up нагрузки** — плавное увеличение нагрузки
✅ **Real-time метрики** — сбор данных в реальном времени
✅ **HTML отчёты с графиками** — matplotlib charts
✅ **CSV экспорт** — детальные логи для анализа
✅ **pytest интеграция** — удобный запуск через pytest

---

## Структура проекта

```
tests/
├── load_testing/              # Система нагрузочного тестирования
│   ├── mocks/                 # Mock компоненты
│   │   ├── mock_ai_clients.py    # Smart mock AI с intent detection
│   │   ├── mock_rag.py           # Mock RAG engine (keyword search)
│   │   ├── mock_persona.py       # Mock Persona Manager
│   │   └── mock_funnel.py        # Mock Conversational Funnel
│   │
│   ├── fixtures/              # Тестовые данные
│   │   └── personas.py           # 100 виртуальных пользователей
│   │
│   ├── metrics/               # Сбор и отчёты
│   │   ├── collector.py          # Сбор метрик в real-time
│   │   └── reporter.py           # Console + HTML reporters
│   │
│   ├── user_simulator.py      # Эмуляция пользователей
│   ├── load_runner.py         # Главный orchestrator
│   ├── example_test.py        # Примеры использования
│   └── README.md              # Документация
│
├── stress/                    # pytest тесты
│   └── test_100_users.py      # Smoke, load, stress тесты
│
└── conftest.py                # pytest конфигурация
```

---

## Быстрый старт

### 1. Установка зависимостей

```bash
pip install pytest pytest-asyncio matplotlib Jinja2
```

### 2. Запуск smoke test (10 пользователей)

```bash
# Через pytest
pytest tests/stress/test_100_users.py::test_smoke_10_users -v

# Или напрямую
cd tests/load_testing
python example_test.py
```

### 3. Запуск полного теста (100 пользователей)

```bash
pytest tests/stress/test_100_users.py::test_100_parallel_users -v
```

### 4. Просмотр результатов

Отчёты сохраняются в `load_test_results/`:
- `{test_name}_raw_metrics.csv` — детальные метрики
- `{test_name}_aggregated.csv` — агрегированные данные
- `{test_name}_report.html` — HTML отчёт с графиками

Откройте HTML отчёт в браузере для просмотра графиков.

---

## Примеры использования

### Пример 1: Быстрый тест куратора

```python
from tests.load_testing.load_runner import quick_curator_test

async def my_handler(message):
    # Ваш handler
    await message.answer("Ответ бота")

# Запуск теста
metrics = await quick_curator_test(
    bot_handler=my_handler,
    users=10,
    concurrent=5,
    max_messages=5
)

print(f"Error rate: {metrics['summary']['error_rate']:.2%}")
print(f"Avg response time: {metrics['aggregated']['avg_response_time_ms']:.0f} ms")
```

### Пример 2: Настраиваемый тест

```python
from tests.load_testing.load_runner import LoadTestRunner, LoadTestConfig

# Конфигурация
config = LoadTestConfig(
    test_name="my_load_test",
    scenario="curator",
    total_users=50,
    concurrent_users=20,
    max_messages_per_user=7,
    delay_between_messages_sec=1.5,
    delay_variance_sec=1.0,
    ramp_up_duration_sec=10.0,  # Плавный рост
    export_csv=True,
    export_html=True,
)

# Запуск
runner = LoadTestRunner(config)
metrics = await runner.run(bot_handler=my_handler)
```

### Пример 3: Стресс-тест (500 пользователей)

```python
from tests.load_testing.load_runner import stress_test

metrics = await stress_test(
    bot_handler=my_handler,
    users=500,
    concurrent=100,
    max_messages=5
)
```

---

## Метрики и SLA

### Целевые метрики (SLA)

| Метрика | Целевое значение | Критическое |
|---------|------------------|-------------|
| Avg Response Time | < 1000 ms | < 2000 ms |
| P95 Response Time | < 1500 ms | < 3000 ms |
| P99 Response Time | < 2000 ms | < 5000 ms |
| Error Rate | < 0.1% | < 1% |
| Throughput | > 20 req/sec | > 10 req/sec |
| Concurrent Users | 100 | 50 |

### Собираемые метрики

**Response Time:**
- Min, Max, Avg, Median
- P50, P95, P99 перцентили

**Throughput:**
- Requests per second
- Total requests
- Successful / Failed requests

**Distribution:**
- Intent distribution (product, business, skeptic, etc.)
- Segment distribution (A, B, C, D, E)
- Error distribution (по типам)

**Time Windows:**
- Метрики по временным окнам (каждые 5 секунд)
- Позволяют отслеживать изменения нагрузки

---

## Mock System

### MockAnthropicClient

Smart mock с intent detection:
- Анализирует сообщения по ключевым словам
- Определяет intent (product, business, skeptic, etc.)
- Возвращает релевантные ответы из шаблонов
- Эмулирует задержку API (500ms ± 200ms)
- Собирает метрики calls/latency/intent_distribution

### MockRAGEngine

Keyword search вместо vector search:
- Быстрый поиск без нагрузки на БД
- Keyword matching + scoring
- Фильтрация по категориям
- 50+ документов в mock knowledge base

### MockPersonaManager

Детерминированный выбор персоны:
- Выбор на основе post_type
- 3 персоны: expert, friend, motivator
- Hooks для каждой персоны
- Temperature, tone, emoji

### MockConversationalFunnel

Упрощённая логика воронки:
- Intent detection (product, business, skeptic, curious)
- Temperature determination (HOT, WARM, COLD)
- Stage transitions (greeting → discovery → solution)
- Контекст в памяти (без БД)

---

## 100 виртуальных пользователей

### Сегменты аудитории

| Сегмент | Описание | % | Intents |
|---------|----------|---|---------|
| A | Мамы 30-45 лет | 25% | product, curious |
| B | Студенты 18-25 | 20% | business, product |
| C | Пенсионеры 55+ | 15% | product, curious |
| D | Специалисты 25-40 | 25% | business, product |
| E | Скептики | 15% | skeptic |

### Pain Points

- **weight** (30%) — снижение веса
- **energy** (20%) — энергия, бодрость
- **immunity** (15%) — иммунитет
- **beauty** (20%) — красота, кожа
- **money** (15%) — дополнительный доход

### Behaviour Types

- **active** (40%) — активные, много вопросов
- **passive** (35%) — пассивные, короткие ответы
- **skeptic** (25%) — скептики, сомневаются

### Генерация сообщений

Каждый пользователь генерирует 5-10 сообщений на основе:
- Intent (product, business, curious, skeptic)
- Pain point (weight, energy, immunity, etc.)
- Behaviour (active, passive, skeptic)

---

## HTML отчёты

HTML отчёт включает:

### Графики

1. **Response Time over Time** — линейный график
2. **Throughput over Time** — линейный график
3. **Error Rate over Time** — линейный график
4. **Response Time Distribution** — гистограмма
5. **Intent Distribution** — круговая диаграмма
6. **Segment Distribution** — круговая диаграмма

### Summary Cards

- Total Users
- Total Messages
- Avg Response Time (с цветовой индикацией)
- Error Rate (с цветовой индикацией)
- Throughput
- Total Duration

### Цветовая индикация

- 🟢 **Зелёный** — метрика в целевом диапазоне
- 🟡 **Жёлтый** — метрика в предупредительном диапазоне
- 🔴 **Красный** — метрика превышает критический порог

---

## pytest интеграция

### Запуск через pytest

```bash
# Smoke test (быстрый)
pytest tests/stress/test_100_users.py::test_smoke_10_users -v

# Load test (100 пользователей)
pytest tests/stress/test_100_users.py::test_100_parallel_users -v

# Stress test (500 пользователей, медленный)
pytest tests/stress/test_100_users.py::test_stress_500_users -v -m slow
```

### Маркеры pytest

- `@pytest.mark.asyncio` — для async тестов
- `@pytest.mark.slow` — для медленных тестов

### Assertions

Тесты проверяют SLA автоматически:

```python
assert summary["error_rate"] < 0.01  # Error rate < 1%
assert aggregated["avg_response_time_ms"] < 2000  # < 2000 ms
assert aggregated["p95_response_time_ms"] < 3000  # < 3000 ms
assert summary["throughput_req_per_sec"] > 10  # > 10 req/sec
```

---

## CI/CD интеграция

### GitHub Actions (пример)

```yaml
name: Load Tests

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  load-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt

      - name: Run smoke test
        run: |
          pytest tests/stress/test_100_users.py::test_smoke_10_users -v

      - name: Run load test (nightly only)
        if: github.event_name == 'schedule'
        run: |
          pytest tests/stress/test_100_users.py::test_100_parallel_users -v

      - name: Upload reports
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: load-test-reports
          path: load_test_results/
```

---

## Troubleshooting

### Проблема: ImportError при запуске тестов

**Решение:** Убедитесь что корневая директория проекта в PYTHONPATH:

```python
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
```

### Проблема: matplotlib charts не отображаются

**Решение:** Установите matplotlib:

```bash
pip install matplotlib
```

Если проблема сохраняется, проверьте backend:

```python
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
```

### Проблема: Высокий error rate в тестах

**Возможные причины:**
1. Handler вызывает исключения
2. Mock'и настроены неправильно
3. Слишком высокая concurrency (уменьшите concurrent_users)

**Решение:** Посмотрите детальные ошибки в CSV:

```bash
grep "False" load_test_results/*_raw_metrics.csv
```

### Проблема: Медленные тесты

**Оптимизация:**
1. Уменьшите `max_messages_per_user`
2. Уменьшите `total_users`
3. Увеличьте `concurrent_users` (если есть ресурсы)
4. Уменьшите `delay_between_messages_sec`

---

## Расширение системы

### Добавление новых mock'ов

1. Создайте файл в `tests/load_testing/mocks/`
2. Реализуйте mock класс с методами и метриками
3. Интегрируйте в `load_runner.py`

Пример:

```python
# tests/load_testing/mocks/mock_database.py
class MockDatabase:
    def __init__(self):
        self.queries_count = 0

    async def execute_query(self, query: str):
        self.queries_count += 1
        # Mock implementation
        return {"result": "ok"}

    def get_metrics(self):
        return {"queries_count": self.queries_count}
```

### Добавление новых метрик

Расширьте `MetricsCollector` в `metrics/collector.py`:

```python
@dataclass
class RequestMetric:
    # ... existing fields
    custom_metric: float = 0.0  # Новая метрика

# В collect()
self.records.append(RequestMetric(
    # ... existing
    custom_metric=custom_value
))
```

### Добавление новых сценариев

Расширьте `LoadTestRunner` в `load_runner.py`:

```python
async def run(self, bot_handler, custom_param=None):
    if self.config.scenario == "custom":
        await self._run_custom_scenario(bot_handler, custom_param)
```

---

## Best Practices

### 1. Начинайте с smoke test

Всегда проверяйте работоспособность на малой нагрузке:

```bash
pytest tests/stress/test_100_users.py::test_smoke_10_users -v
```

### 2. Используйте ramp-up

Не включайте всех пользователей сразу:

```python
config = LoadTestConfig(
    ramp_up_duration_sec=10.0,  # Постепенный рост
    # ...
)
```

### 3. Анализируйте распределение intents

Проверяйте что тесты покрывают все сценарии:

```python
print("Intent distribution:")
for intent, count in ai_metrics["intent_distribution"].items():
    print(f"  {intent}: {count}")
```

### 4. Экспортируйте результаты

Всегда включайте экспорт для последующего анализа:

```python
config = LoadTestConfig(
    export_csv=True,
    export_html=True,
    # ...
)
```

### 5. Мониторьте системные ресурсы

Параллельно с тестами следите за:
- CPU usage
- Memory usage
- Database connections
- Network I/O

---

## FAQ

**Q: Можно ли использовать реальную БД вместо SQLite?**

A: Да, раскомментируйте PostgreSQL fixtures в `tests/conftest.py` и измените TEST_DATABASE_URL.

**Q: Как тестировать реальный AI (не mock)?**

A: Замените mock clients на реальные в тесте, но учтите что это дорого ($$$ на API calls) и медленно.

**Q: Сколько пользователей можно эмулировать?**

A: Зависит от ресурсов. Mock система легко справляется с 500+ пользователями. Реальные боты — 50-100 максимум.

**Q: Как интегрировать с CI/CD?**

A: См. раздел "CI/CD интеграция" выше. Smoke test запускайте на каждый PR, full load test — nightly.

**Q: Где хранятся отчёты?**

A: В `load_test_results/` (создаётся автоматически).

---

## Полезные ссылки

- [План системы](./.claude/plans/elegant-baking-milner.md)
- [README load_testing](../tests/load_testing/README.md)
- [Примеры использования](../tests/load_testing/example_test.py)
- [pytest документация](https://docs.pytest.org/)
- [matplotlib charts](https://matplotlib.org/stable/gallery/index.html)

---

## Контакты и поддержка

При возникновении проблем:
1. Проверьте логи тестов
2. Посмотрите CSV отчёты на детальные ошибки
3. Проверьте что все зависимости установлены
4. Создайте issue с описанием проблемы

---

**Версия документа:** 1.0
**Дата создания:** 3 февраля 2026
**Авторы:** Claude Sonnet 4.5 + Mafio
