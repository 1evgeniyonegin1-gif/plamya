# Changelog 3 февраля 2026

## Обзор

Масштабный день разработки. Добавлена система нагрузочного тестирования, тестирование на галлюцинации, Partner Panel архитектура, улучшения куратора и деплой Traffic Engine.

---

## Новые компоненты

### 1. Система нагрузочного тестирования

**Папка:** `tests/load_testing/`

Полная система эмуляции 100+ параллельных пользователей:

- `load_runner.py` — главный orchestrator
- `user_simulator.py` — эмуляция поведения пользователей
- `mocks/` — 4 smart mock компонента (AI, DB, Telegram, RAG)
- `fixtures/` — 100 виртуальных пользователей с реалистичными профилями
- `metrics/` — сбор метрик в реальном времени и HTML отчёты

**Тесты:** `tests/stress/test_100_users.py`
- Smoke test (10 users, ~10 сек)
- Load test (100 users, ~2-3 мин)
- Stress test (500 users, ~5-10 мин)

**Результаты:** `load_test_results/`
- CSV метрики (raw + aggregated)
- HTML отчёты с 6 интерактивными графиками
- PNG диаграммы

**Документация:**
- `RUN_LOAD_TESTS.md` — инструкция запуска
- `docs/LOAD_TESTING_SYSTEM.md` — полная документация
- `docs/LOAD_TESTING_SUMMARY.md` — итоги тестирования

**Статистика:** 14 файлов, ~4350 строк кода

---

### 2. Тестирование на галлюцинации

**Скрипт:** `scripts/run_hallucination_tests.py` (478 строк)

Автоматическая проверка AI на вымышленные продукты:

**Тестовые данные:**
- `tests/hallucination_tests.json` — 500+ вопросов
- `tests/hallucination_tests_part2.json`
- `tests/hallucination_tests_part3.json`
- `tests/hallucination_tests_part4.json`

**Категории:**
- `fake_product_lines` — несуществующие линейки
- `fake_products` — вымышленные продукты
- `confusion_perfume_cosmetics` — путаница Gentleman
- `wrong_prices` — неправильные цены
- `wrong_composition` — неправильный состав
- `real_products_validation` — проверка реальных

**Результаты:**
- 76.7% прошли (23 из 30)
- Выявлены проблемы: ED Smart PRO, Collagen ULTRA, Vitamin D FORTE

---

### 3. Partner Panel (Telegram Mini App)

**Папка:** `partner_panel/`

Telegram Mini App для управления Traffic Engine:

**Backend** (`partner_panel/backend/`):
- FastAPI + SQLAlchemy
- 18 API endpoints
- Модели: Partner, PartnerCredentials, PartnerChannel
- Telegram Mini App аутентификация (initData + JWT)

**Frontend** (`partner_panel/frontend/`):
- React 18 + TypeScript
- Vite — быстрая сборка
- TailwindCSS — стили
- TanStack Query — кэширование
- Zustand — state management

**Страницы:**
- Dashboard — быстрая статистика
- Connect — многошаговая форма подключения
- Channels — управление каналами (TODO)
- Stats — статистика и аналитика (TODO)

**Статус:** ~30% готовности (архитектура есть, TODO много)

---

### 4. Quality Testing система

**Папка:** `tests/quality/`

AI Judge для оценки качества ответов:

- `evaluators/ai_judge.py` — AI судья (430 строк)
- `reports/dialog_report.py` — отчёты о диалогах
- `runners/quality_runner.py` — runner тестов
- `scenarios/curator_scenarios.yaml` — 30+ сценариев куратора
- `scenarios/content_scenarios.yaml` — 40+ сценариев контента

**Результаты:** `quality_test_results/` — 20+ отчётов

---

## Улучшения существующих компонентов

### AI-Куратор (`curator_bot/ai/prompts.py`)

**Recurring Characters** — персонажи для сериальности:
- Артём (скептик)
- Валентина Петровна (успешная партнёрша)
- Маша (новичок)
- Олег (бизнесмен)

**Signature Phrases** — маячки для узнаваемости:
- attention_grabber: "Стоп. Это важно."
- frame_shift: "Это не про продажи. Это про..."
- mind_reading: "Да, я знаю что ты думаешь"
- call_to_action: "Ну что, погнали?"
- raw_honesty: "Честно? / Скажу как есть"

**Emotional Roller Coaster** — структура вовлечения:
- НИЗ → ЕЩЁ НИЖЕ → САМОЕ ДНО → ПОВОРОТ → ПОДЪЁМ → ПИК → РЕЛИЗ

---

### Traffic Engine

**Коммит:** `003d379` — APEXFLOW Traffic Engine — NL International

Задеплоен на VPS с модульной архитектурой:
- `traffic-engine/warmup/` — прогрев аккаунтов
- `traffic-engine/posting/` — автопостинг
- `traffic-engine/channels/` — auto_comments, story_viewer, chat_inviter

---

### Deepseek интеграция

**Коммит:** `d4e25a8` — Deepseek как основной AI для контент-менеджера

- Модель: `deepseek-chat`
- Цена: $0.14 / 1M input, $0.28 / 1M output
- Использование: генерация постов в Контент-Менеджере

---

### YandexGPT улучшения

**Коммит:** `5423e94` — Поддержка чтения ключа из файла

Теперь приватный ключ можно хранить в файле вместо .env.

---

## Обновлённая документация

| Файл | Изменение |
|------|-----------|
| `CLAUDE.md` | Обновлён статус до 3 февраля, добавлен Deepseek, обновлена структура |
| `docs/VPS_DEPLOY.md` | Исправлен путь `/root/apexflow` |
| `docs/LOAD_TESTING_SYSTEM.md` | Новый — полная документация |
| `docs/LOAD_TESTING_SUMMARY.md` | Новый — результаты тестирования |
| `RUN_LOAD_TESTS.md` | Новый — инструкция запуска |

**Удалено:**
- `MEDIA_LIBRARY_SUMMARY.md` — дублировал `docs/MEDIA_LIBRARY_OPTIMIZATION.md`

---

## Что НЕ доделано

### Из предыдущих планов:
- [ ] Исправить автопостинг (/schedule)
- [ ] Telethon API keys для мониторинга каналов
- [ ] Проставить даты в топ-20 документах RAG

### Новые задачи:
- [ ] Partner Panel: подключение к БД (сейчас mock'и)
- [ ] Partner Panel: Telethon интеграция
- [ ] Снизить hallucination rate (сейчас 23.3%)
- [ ] Доработать промпты для fake products

---

## Статистика дня

| Метрика | Значение |
|---------|----------|
| Новые файлы | 146+ |
| Строк кода | 22,370+ |
| Новые папки | 10+ |
| Документация | 2,000+ строк |
| Тестовые вопросы | 500+ |

---

## Коммиты

```
5423e94 fix: добавлена поддержка чтения YandexGPT ключа из файла
003d379 feat: APEXFLOW Traffic Engine — NL International
d4e25a8 feat: Deepseek как основной AI для контент-менеджера
5932215 feat: эмоциональные горки и качественное тестирование
c51c96c feat: recurring characters и фирменные фразы в куратора
```
