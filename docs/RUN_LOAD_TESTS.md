# Запуск нагрузочных тестов — Пошаговая инструкция

## Перед запуском

### 1. Установите зависимости (если ещё не установлены)

```bash
pip install matplotlib Jinja2
```

> **Примечание:** pytest и pytest-asyncio уже установлены из requirements.txt

---

## Smoke Test (10 пользователей, ~10 секунд)

**Рекомендуется начать с этого теста**

```bash
pytest tests/stress/test_100_users.py::test_smoke_10_users -v
```

### Что проверяет:
- ✅ Базовая работоспособность системы
- ✅ Mock компоненты работают корректно
- ✅ Метрики собираются
- ✅ Error rate < 5%
- ✅ Response time < 3000 ms

### Ожидаемый результат:
```
===== 1 passed in 10s =====
```

---

## Full Load Test (100 пользователей, ~2-3 минуты)

**Основной тест для проверки производительности**

```bash
pytest tests/stress/test_100_users.py::test_100_parallel_users -v
```

### Что проверяет:
- ✅ 100 параллельных пользователей
- ✅ 50 concurrent connections
- ✅ Ramp-up нагрузки (постепенный рост)
- ✅ Error rate < 1%
- ✅ Avg response time < 2000 ms
- ✅ P95 response time < 3000 ms
- ✅ Throughput > 10 req/sec

### Генерируемые отчёты:
- `load_test_results/100_parallel_users_report.html` — **Откройте в браузере!**
- `load_test_results/100_parallel_users_raw_metrics.csv`
- `load_test_results/100_parallel_users_aggregated.csv`

### Ожидаемый результат:
```
===== 1 passed in 180s =====

📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ
============================================================
Всего пользователей:     100
Отправлено запросов:     700
Успешных ответов:        700
Ошибок:                  0
Error rate:              0.00%
Среднее время ответа:    520 ms
P95 время ответа:        780 ms
P99 время ответа:        890 ms
Throughput:              12.50 req/sec
Общая длительность:      56.0 сек
============================================================

✅ Все SLA выполнены!
```

---

## Stress Test (500 пользователей, ~5-10 минут)

**Для выявления bottlenecks**

```bash
pytest tests/stress/test_100_users.py::test_stress_500_users -v -m slow
```

### Что проверяет:
- ✅ 500 параллельных пользователей
- ✅ 100 concurrent connections
- ✅ Выявление узких мест системы
- ✅ Error rate < 5% (допускается выше чем в обычном тесте)
- ✅ Avg response time < 5000 ms

### Ожидаемый результат:
```
===== 1 passed in 600s =====

💥 STRESS TEST пройден!
Система выдержала нагрузку 500 пользователей
```

---

## Просмотр HTML отчёта

### Windows:
```bash
start load_test_results\*_report.html
```

### macOS:
```bash
open load_test_results/*_report.html
```

### Linux:
```bash
xdg-open load_test_results/*_report.html
```

### HTML отчёт содержит:

1. **Summary Cards** — ключевые метрики с цветовой индикацией
2. **6 Графиков:**
   - Response Time over Time
   - Throughput over Time
   - Error Rate over Time
   - Response Time Distribution (histogram)
   - Intent Distribution (pie chart)
   - Segment Distribution (pie chart)

---

## Анализ CSV отчётов

### Raw Metrics (детальные логи)
```bash
cat load_test_results/*_raw_metrics.csv | grep "False"  # Найти ошибки
```

### Aggregated Metrics (сводка по временным окнам)
```bash
cat load_test_results/*_aggregated.csv
```

---

## Troubleshooting

### Ошибка: "ModuleNotFoundError: No module named 'matplotlib'"

**Решение:**
```bash
pip install matplotlib
```

### Ошибка: "ModuleNotFoundError: No module named 'jinja2'"

**Решение:**
```bash
pip install Jinja2
```

### Ошибка: "ImportError" при запуске тестов

**Решение:** Убедитесь что вы запускаете из корневой директории проекта:
```bash
cd c:\Users\mafio\OneDrive\Документы\projects\nl-international-ai-bots
pytest tests/stress/test_100_users.py::test_smoke_10_users -v
```

### Высокий error rate в тестах

**Причины:**
1. Mock'и настроены неправильно
2. Handler вызывает исключения
3. Слишком высокая concurrency

**Решение:** Проверьте детальные ошибки в CSV:
```bash
grep "False" load_test_results/*_raw_metrics.csv
```

### Медленные тесты

**Оптимизация:**
1. Уменьшите `total_users` в конфиге
2. Уменьшите `max_messages_per_user`
3. Увеличьте `concurrent_users` (если есть ресурсы)

---

## Запуск всех тестов сразу

```bash
# Smoke + Full Load (без stress)
pytest tests/stress/test_100_users.py -v -k "not stress"

# Все тесты включая stress
pytest tests/stress/test_100_users.py -v
```

---

## Кастомный тест (программный запуск)

Создайте файл `my_test.py`:

```python
import asyncio
from tests.load_testing.load_runner import quick_curator_test
from tests.load_testing.mocks.mock_ai_clients import MockAnthropicClient, CURATOR_RESPONSE_TEMPLATES
from tests.load_testing.mocks.mock_rag import MockRAGEngine, MOCK_KNOWLEDGE_BASE

async def mock_handler(message):
    await asyncio.sleep(0.5)
    await message.answer("Response from bot")

async def main():
    # Инициализация
    ai_client = MockAnthropicClient(CURATOR_RESPONSE_TEMPLATES, latency_ms=500)
    rag_engine = MockRAGEngine(MOCK_KNOWLEDGE_BASE)

    # Wrapper
    async def handler(msg):
        await mock_handler(msg)

    # Запуск
    metrics = await quick_curator_test(
        bot_handler=handler,
        users=20,
        concurrent=10,
        max_messages=5
    )

    print(f"\n✅ Test completed!")
    print(f"Error rate: {metrics['summary']['error_rate']:.2%}")
    print(f"Avg response time: {metrics['aggregated']['avg_response_time_ms']:.0f} ms")

if __name__ == "__main__":
    asyncio.run(main())
```

Запуск:
```bash
python my_test.py
```

---

## CI/CD интеграция

### GitHub Actions (пример)

Создайте `.github/workflows/load-tests.yml`:

```yaml
name: Load Tests

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 2 * * *'  # Nightly at 2 AM

jobs:
  smoke-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: pytest tests/stress/test_100_users.py::test_smoke_10_users -v

  load-test:
    if: github.event_name == 'schedule'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: pytest tests/stress/test_100_users.py::test_100_parallel_users -v
      - uses: actions/upload-artifact@v3
        if: always()
        with:
          name: load-test-reports
          path: load_test_results/
```

---

## Дополнительная документация

- [Полная документация системы](docs/LOAD_TESTING_SYSTEM.md)
- [Быстрый старт](tests/load_testing/QUICKSTART.md)
- [Итоговый отчёт](docs/LOAD_TESTING_SUMMARY.md)
- [README с примерами](tests/load_testing/README.md)
- [Примеры кода](tests/load_testing/example_test.py)

---

## Помощь

Вопросы? Проверьте:
1. ✅ Установлены ли все зависимости (matplotlib, Jinja2)
2. ✅ Запускаете ли из корневой директории проекта
3. ✅ Нет ли ошибок в логах pytest

Не помогло? Изучите [Troubleshooting](docs/LOAD_TESTING_SYSTEM.md#troubleshooting).

---

**Готово!** Теперь вы можете запускать нагрузочные тесты одной командой.

🚀 **Happy Testing!**
