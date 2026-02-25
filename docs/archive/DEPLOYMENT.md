# Развёртывание ботов 24/7

Инструкция по запуску ботов на постоянной основе без необходимости держать терминал открытым.

---

## Текущий деплой (PRODUCTION)

**Боты развёрнуты на Timeweb Cloud VPS и работают 24/7!**

- **IP:** 194.87.86.103
- **Документация:** [VPS_DEPLOY.md](VPS_DEPLOY.md)

---

## Варианты хостинга

| Платформа | Стоимость | Сложность | Рекомендация |
|-----------|-----------|-----------|--------------|
| **Timeweb Cloud** | ~300₽/мес | Средне | ✅ Текущий выбор (оплата в рублях) |
| **Railway** | $5/мес | Легко | Нужна зарубежная карта |
| **Render** | $7/мес | Легко | Бот засыпает через 15 мин |
| **DigitalOcean** | $4-6/мес | Средне | Нужна зарубежная карта |
| **VPS (любой)** | $3-10/мес | Сложно | Максимум контроля |

---

## Вариант 1: Railway (Рекомендуется)

Railway - самый простой способ запустить ботов 24/7.

### Шаг 1: Регистрация

1. Перейди на [railway.app](https://railway.app)
2. Войди через GitHub
3. Получишь $5 бесплатного кредита в месяц

### Шаг 2: Создание PostgreSQL

1. Нажми **New Project** → **Provision PostgreSQL**
2. Дождись создания базы данных
3. Нажми на базу → **Variables** → скопируй `DATABASE_URL`

### Шаг 3: Деплой ботов

**Способ A: Через GitHub (автоматический)**

1. Загрузи проект на GitHub
2. В Railway: **New** → **GitHub Repo** → выбери репозиторий
3. Railway автоматически найдёт `Procfile` или `main.py`

**Способ B: Через CLI**

```bash
# Установить Railway CLI
npm install -g @railway/cli

# Войти
railway login

# Создать проект
railway init

# Задеплоить
railway up
```

### Шаг 4: Настройка переменных

В Railway Dashboard → **Variables** добавь:

```
CURATOR_BOT_TOKEN=ваш_токен
CONTENT_MANAGER_BOT_TOKEN=ваш_токен
GIGACHAT_AUTH_TOKEN=ваш_токен
DATABASE_URL=postgresql://... (уже есть от PostgreSQL)
ADMIN_TELEGRAM_IDS=ваш_id
CHANNEL_USERNAME=@ваш_канал
```

### Шаг 5: Создание Procfile

Создай файл `Procfile` в корне проекта:

```
curator: python -m curator_bot.main
content: python -m content_manager_bot.main
```

Или для одного процесса с обоими ботами создай `run_all.py`:

```python
import asyncio
from curator_bot.main import main as curator_main
from content_manager_bot.main import main as content_main

async def run_all():
    await asyncio.gather(
        curator_main(),
        content_main()
    )

if __name__ == "__main__":
    asyncio.run(run_all())
```

И `Procfile`:
```
web: python run_all.py
```

---

## Вариант 2: Render

### Шаг 1: Регистрация

1. Перейди на [render.com](https://render.com)
2. Зарегистрируйся через GitHub

### Шаг 2: Создание PostgreSQL

1. **New** → **PostgreSQL**
2. Выбери Free plan (для теста) или Starter ($7/мес)
3. Скопируй Internal Database URL

### Шаг 3: Деплой бота

1. **New** → **Background Worker** (не Web Service!)
2. Подключи GitHub репозиторий
3. Build Command: `pip install -r requirements.txt`
4. Start Command: `python -m curator_bot.main`

### Шаг 4: Второй бот

Создай ещё один Background Worker для контент-менеджера:
- Start Command: `python -m content_manager_bot.main`

### Шаг 5: Переменные окружения

В каждом сервисе добавь Environment Variables.

---

## Вариант 3: VPS (DigitalOcean, Hetzner, etc.)

Для тех, кто хочет полный контроль.

### Шаг 1: Создание сервера

1. Создай Droplet (DigitalOcean) или VPS
2. Выбери Ubuntu 22.04
3. Минимум: 1 CPU, 1GB RAM, 25GB SSD (~$4-6/мес)

### Шаг 2: Подключение

```bash
ssh root@your-server-ip
```

### Шаг 3: Установка зависимостей

```bash
# Обновить систему
apt update && apt upgrade -y

# Установить Python
apt install python3.11 python3.11-venv python3-pip -y

# Установить PostgreSQL
apt install postgresql postgresql-contrib -y

# Настроить PostgreSQL
sudo -u postgres createuser --interactive
sudo -u postgres createdb nl_bots
```

### Шаг 4: Клонирование проекта

```bash
cd /opt
git clone https://github.com/your-repo/nl-international-ai-bots.git
cd nl-international-ai-bots

# Создать виртуальное окружение
python3.11 -m venv venv
source venv/bin/activate

# Установить зависимости
pip install -r requirements.txt
```

### Шаг 5: Настройка .env

```bash
cp .env.example .env
nano .env
# Заполнить все переменные
```

### Шаг 6: Systemd сервисы

Создай файл `/etc/systemd/system/curator-bot.service`:

```ini
[Unit]
Description=NL Curator Bot
After=network.target postgresql.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/nl-international-ai-bots
Environment=PATH=/opt/nl-international-ai-bots/venv/bin
ExecStart=/opt/nl-international-ai-bots/venv/bin/python -m curator_bot.main
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Создай файл `/etc/systemd/system/content-bot.service`:

```ini
[Unit]
Description=NL Content Manager Bot
After=network.target postgresql.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/nl-international-ai-bots
Environment=PATH=/opt/nl-international-ai-bots/venv/bin
ExecStart=/opt/nl-international-ai-bots/venv/bin/python -m content_manager_bot.main
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Шаг 7: Запуск сервисов

```bash
# Перезагрузить systemd
systemctl daemon-reload

# Включить автозапуск
systemctl enable curator-bot
systemctl enable content-bot

# Запустить
systemctl start curator-bot
systemctl start content-bot

# Проверить статус
systemctl status curator-bot
systemctl status content-bot
```

### Шаг 8: Просмотр логов

```bash
# Логи куратора
journalctl -u curator-bot -f

# Логи контент-менеджера
journalctl -u content-bot -f
```

---

## Вариант 4: Docker

Для тех, кто предпочитает контейнеры.

### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "-m", "curator_bot.main"]
```

### docker-compose.yml

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: nl_user
      POSTGRES_PASSWORD: nl_password
      POSTGRES_DB: nl_bots
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: always

  curator:
    build: .
    command: python -m curator_bot.main
    depends_on:
      - postgres
    environment:
      DATABASE_URL: postgresql+asyncpg://nl_user:nl_password@postgres:5432/nl_bots
    env_file:
      - .env
    restart: always

  content_manager:
    build: .
    command: python -m content_manager_bot.main
    depends_on:
      - postgres
    environment:
      DATABASE_URL: postgresql+asyncpg://nl_user:nl_password@postgres:5432/nl_bots
    env_file:
      - .env
    restart: always

volumes:
  postgres_data:
```

### Запуск

```bash
docker-compose up -d
```

---

## Мониторинг и обслуживание

### Проверка работы ботов

```bash
# Railway
railway logs

# Render
# Смотри в Dashboard → Logs

# VPS
journalctl -u curator-bot -f
journalctl -u content-bot -f

# Docker
docker-compose logs -f
```

### Перезапуск при проблемах

```bash
# VPS
systemctl restart curator-bot
systemctl restart content-bot

# Docker
docker-compose restart
```

### Обновление кода

```bash
# VPS
cd /opt/nl-international-ai-bots
git pull
systemctl restart curator-bot
systemctl restart content-bot

# Railway/Render
# Автоматически при push в GitHub
```

---

## Бэкапы базы данных

### Railway

Railway делает автоматические бэкапы PostgreSQL.

### VPS

```bash
# Создать бэкап
pg_dump -U postgres nl_bots > backup_$(date +%Y%m%d).sql

# Восстановить
psql -U postgres nl_bots < backup_20260116.sql
```

### Автоматические бэкапы (cron)

```bash
crontab -e
# Добавить строку для ежедневного бэкапа в 3:00
0 3 * * * pg_dump -U postgres nl_bots > /backups/nl_bots_$(date +\%Y\%m\%d).sql
```

---

## Troubleshooting

### Бот не отвечает

1. Проверь логи на ошибки
2. Проверь что токен бота правильный
3. Проверь подключение к базе данных
4. Перезапусти сервис

### Ошибки подключения к БД

1. Проверь DATABASE_URL
2. Убедись что PostgreSQL запущен
3. Проверь firewall правила

### GigaChat ошибки

1. Проверь GIGACHAT_AUTH_TOKEN
2. Токен может истечь - обнови его
3. Проверь лимиты API

---

## Рекомендуемая конфигурация для продакшена

| Компонент | Минимум | Рекомендуется |
|-----------|---------|---------------|
| CPU | 1 core | 2 cores |
| RAM | 1 GB | 2 GB |
| Storage | 10 GB | 25 GB |
| PostgreSQL | Shared | Dedicated |

---

## Чеклист перед деплоем

- [ ] Все токены добавлены в переменные окружения
- [ ] База данных создана и доступна
- [ ] Бот добавлен администратором в канал (для контент-менеджера)
- [ ] Таблицы базы данных созданы (`python scripts/create_database.py`)
- [ ] База знаний проиндексирована (`python scripts/build_knowledge_base.py`)
- [ ] Тесты пройдены локально
- [ ] Логирование настроено

---

## Поддержка

При проблемах с деплоем:
1. Проверь логи
2. Проверь переменные окружения
3. Создай issue в репозитории
