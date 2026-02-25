# NL International AI Bots — Инструкции для Claude Code

## О проекте

Боты и движки для автоматизации сетевого бизнеса NL International.
**Это НЕ ядро всех проектов — это один из проектов в `projects/`.**

### Важно: Новые проекты — ОТДЕЛЬНО!
Если задача не связана с NL International — **создавай отдельный проект** в `projects/`.
Не клади сюда фриланс-движки, сканеры бизнесов, дашборды и прочее.

## Подход к разработке

### Старый подход (НЕ РАБОТАЕТ):
Скриптованные боты с жёстким поведением — ломаются на непредвиденных ситуациях.

### Новый подход (ЭКСПЕРИМЕНТ):
Автономные AI-агенты, которые сами учатся и действуют. Пример — Чаппи:
сам изучает продукты, сам решает что делать, сам проявляет инициативу.
AI учится быстрее человека — пусть сам создаёт базы, каналы, стратегии.

## Структура проекта

```
nl-international-ai-bots/
├── curator_bot/              — AI-куратор партнёров (Production)
├── content_manager_bot/      — Генерация контента (Production)  
├── traffic_engine/           — Автокомменты, сторис, инвайты (Production)
├── chappie_engine/           — AI-партнёр, автономный агент (Эксперимент)
├── discipline_bot/           — Бот-сержант привычек (Ready, не задеплоен)
├── sales_engine/             — Обработка возражений (Production)
├── infobiz_engine/           — Создание курсов (WIP, сломан)
├── partner_panel/            — Mini App для партнёров (WIP 60%)
├── curator_miniapp/          — Mini App куратора
├── content_manager_miniapp/  — Mini App контента
├── shared/                   — Общий код (AI клиенты, БД, RAG, медиа)
├── content/                  — База знаний + медиа NL International
├── scripts/                  — Утилиты и миграции
├── tests/                    — Тесты
├── deploy/                   — Конфиги деплоя
├── docs/                     — Документация
├── migrations/               — Alembic миграции
└── tenants/                  — Конфиги тенантов
```

## Инфраструктура

### VPS (Timeweb Cloud)
- **IP:** 194.87.86.103
- **SSH:** `ssh root@194.87.86.103`  
- **Путь:** `/root/apexflow`
- **Сервисы:** `nl-bots.service`, `apexflow-traffic.service`

### База данных
- PostgreSQL localhost:5432, db: nl_international
- pgvector для RAG

### AI Провайдеры
- **Claude Sonnet 3.5** — основной (куратор, контент)
- **Deepseek** — дешёвый fallback для контента (⚠️ баланс 0 на 21.02.2026)
- **YandexGPT** — резервный

### Telegram
- **Боты:** @nl_curator_bot, @nl_content_bot
- **Админ ID:** 756877849

## Выбор модели: Sonnet vs Opus

- **Opus** — архитектура, стратегия, сложный дебаг
- **Sonnet** — код, баги, фичи, рутина

## Команды

```bash
# Локальный запуск
cd "c:\Users\mafio\OneDrive\Документы\projects\nl-international-ai-bots"
venv\Scripts\activate
python run_bots.py

# Деплой
git add . && git commit -m "описание" && git push
ssh root@194.87.86.103 "cd /root/apexflow && git pull && systemctl restart nl-bots"

# Логи
ssh root@194.87.86.103 "journalctl -u nl-bots -f"
ssh root@194.87.86.103 "journalctl -u apexflow-traffic -f"
```

## Безопасность
- НЕ показывай API ключи, токены, пароли
- НЕ пуши в main без подтверждения
- НЕ делай DELETE/DROP в БД без спроса
