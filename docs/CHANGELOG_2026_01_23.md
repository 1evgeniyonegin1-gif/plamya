# Changelog — 23 января 2026

## Выполнено сегодня

### 1. Обновлены ВСЕ воронки клиентов с реальными историями

**Файл:** `curator_bot/funnels/messages.py`

| Воронка | Было | Стало |
|---------|------|-------|
| Энергия | Вымышленная история Алексея | Реальный отзыв про Метабиотик |
| Иммунитет | Вымышленная история Анны | Реальный отзыв про Биодрон |
| Красота | Вымышленная история Ольги | Реальные отзывы про коллаген и крем |
| Дети | Вымышленная история Марии | История про дерматит (дочь 13 лет) + гель Smartum Max |
| Спорт | Вымышленная история | История Дмитрия-студента |
| Бизнес | Вымышленная Екатерина | Реальная история Елены из Екатеринбурга (45-55к/мес за 11 мес) |

**Источники историй:**
- `content/knowledge_base/success_stories/mama_v_dekrete_i_nl.md` — история Елены
- `content/knowledge_base/from_telegram/telegram_success_stories_evergreen_*.txt` — отзывы про продукты

### 2. Очистка проекта (49 файлов)

**Удалено из корня (18 файлов):**
- `create_database.py`, `analyze_catalog.py` (дубли)
- `SUMMARY.md`, `QUICK_SUMMARY.md`, `MEMO.md` (устаревшие)
- `WORK_LOG_2026-01-20.md`, `START_TOMORROW.md`
- `CHANGELOG_ANALYTICS.md`, `DEPLOY_ANALYTICS.md`
- `CATALOG_ANALYSIS_REPORT.md`, `MISSING_PRODUCT_INFO.md`, `PRODUCTS_WITHOUT_PRICES.md`
- `REFERENCE_IMAGES_IMPLEMENTATION.md`, `REFERENCE_IMAGES_QUICKSTART.md`
- `FAQ ,Training, о компании, реф ссылки.md`
- `fix_env.sh`, `fix_env_simple.sh`, `Procfile`, `railway.toml`, `setup_db.sql`

**Архивировано в scripts/archive/ (19 файлов):**
- `process_telegram_export*.py` (3 версии)
- `organize_*.py`, `categorize_*.py`, `map_*.py` и др.
- `scrape_*.py`, `find_nl_api.py`, `test_nl_access.py`
- `extract_pdf_text.py`, `update_market_intelligence.py`, `create_partner.py`

**Архивировано в docs/archive/ (12 файлов):**
- `ANALYTICS.md`, `DEPLOYMENT.md`, `MARKET_INTELLIGENCE.md`
- `DEVELOPMENT_TODO.md`, `IMPLEMENTATION_ROADMAP.md`
- `RAG_EXPANSION_PLAN.md`, `SALES_FUNNEL_*.md`
- `SCALING_POTENTIAL.md`, `YANDEX_CLOUD_MIGRATION.md`, `GOOGLE_FORM_STRUCTURE.md`

**Удалены неиспользуемые модули:**
- `shared/ai_clients/gemini_client.py`
- `content_manager_bot/scraper/` (пустой)
- `content/post_templates/`, `content/training_materials/` (пустые)

### 3. Деплой на VPS

```bash
git push  # 2 коммита
ssh root@194.87.86.103
cd /root/nl-international-ai-bots && git pull
systemctl restart nl-bots
```

**Статус:** Боты работают, память 650 MB

---

## Коммиты

1. `32374cb` — Improve: реальные истории из базы знаний во всех воронках
2. `86d2589` — Cleanup: очистка проекта от устаревших файлов

---

## Текущая структура проекта

```
nl-international-ai-bots/
├── CLAUDE.md              # Главная инструкция
├── README.md              # Описание проекта
├── requirements.txt       # Зависимости
├── run_bots.py           # Запуск обоих ботов
│
├── curator_bot/          # AI-Куратор (18 файлов)
├── content_manager_bot/  # Контент-Менеджер (16 файлов)
├── shared/               # Общий код (14 файлов)
│
├── content/
│   ├── knowledge_base/   # 106 документов RAG
│   ├── telegram_knowledge/
│   └── unified_products/ # 485 MB изображений (в .gitignore)
│
├── scripts/              # 8 активных скриптов
│   └── archive/          # 19 архивных скриптов
│
└── docs/                 # 11 актуальных документов
    └── archive/          # 12 архивных документов
```

---

## Что осталось сделать

### Важно
- [ ] Исправить автопостинг (кнопки /schedule)
- [ ] Решить проблему unified_products/ (485 MB в репозитории) — вынести на CDN

### Желательно
- [ ] Telethon API keys для мониторинга каналов
- [ ] Проставить даты в топ-20 документах RAG
- [ ] Закрыть TODO в коде (funnel_events)
