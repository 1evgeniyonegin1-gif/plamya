# Деплой на VPS (Timeweb Cloud)

## Текущий сервер

- **Провайдер:** Timeweb Cloud
- **IP:** 194.87.86.103
- **IPv6:** 2a03:6f00:a::1:988f
- **ОС:** Ubuntu 24.04 LTS
- **Тариф:** 1 vCPU, 1GB RAM, 15GB SSD

---

## Подключение к серверу

```bash
ssh root@194.87.86.103
```

Пароль: в панели Timeweb → Доступ → Root-пароль

---

## Структура на сервере

```
/root/apexflow/
├── venv/                    # Python виртуальное окружение
├── .env                     # Переменные окружения (токены, ключи)
├── curator_bot/             # AI-Куратор
├── content_manager_bot/     # AI-Контент-Менеджер
├── shared/                  # Общий код
└── run_bots.py              # Скрипт запуска обоих ботов
```

---

## Управление ботами

### Статус
```bash
systemctl status nl-bots
```

### Перезапуск
```bash
systemctl restart nl-bots
```

### Остановка
```bash
systemctl stop nl-bots
```

### Запуск
```bash
systemctl start nl-bots
```

### Логи (в реальном времени)
```bash
journalctl -u nl-bots -f
```

### Логи (последние 100 строк)
```bash
journalctl -u nl-bots -n 100
```

---

## Обновление кода

```bash
cd /root/apexflow
git pull
systemctl restart nl-bots
```

**Важно:** Если репозиторий приватный, нужно настроить SSH-ключ или использовать токен.

---

## База данных

- **СУБД:** PostgreSQL 16
- **База:** nl_international
- **Пользователь:** nlbot
- **Пароль:** nlbot123

### Подключение к БД
```bash
sudo -u postgres psql -d nl_international
```

### Расширения
- pgvector (для RAG/эмбеддингов)

---

## Переменные окружения (.env)

```env
CURATOR_BOT_TOKEN=токен_куратора
CONTENT_MANAGER_BOT_TOKEN=токен_контент_менеджера
CHANNEL_USERNAME=@nl_international_partners
ADMIN_TELEGRAM_IDS=756877849
GIGACHAT_AUTH_TOKEN=токен_gigachat
GIGACHAT_CLIENT_ID=client_id
ANTHROPIC_API_KEY=ключ_anthropic
DATABASE_URL=postgresql+asyncpg://nlbot:nlbot123@localhost:5432/nl_international
LOG_LEVEL=INFO
TIMEZONE=Europe/Moscow
```

---

## Systemd сервис

Файл: `/etc/systemd/system/nl-bots.service`

```ini
[Unit]
Description=NL International AI Bots
After=network.target postgresql.service

[Service]
Type=simple
User=root
WorkingDirectory=/root/apexflow
Environment=PATH=/root/apexflow/venv/bin:/usr/bin
ExecStart=/root/apexflow/venv/bin/python run_bots.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

---

## Установка с нуля

### 1. Обновление системы
```bash
apt update && apt upgrade -y
```

### 2. Установка зависимостей
```bash
apt install -y python3.12 python3.12-venv python3-pip git postgresql postgresql-contrib postgresql-16-pgvector
```

### 3. Клонирование проекта
```bash
cd /root
git clone https://github.com/1evgeniyonegin1-gif/nl-international-ai-bots.git
cd nl-international-ai-bots
```

### 4. Виртуальное окружение
```bash
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install sentence-transformers openai pgvector
```

### 5. База данных
```bash
sudo -u postgres psql -c "CREATE USER nlbot WITH PASSWORD 'nlbot123';"
sudo -u postgres psql -c "CREATE DATABASE nl_international OWNER nlbot;"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE nl_international TO nlbot;"
sudo -u postgres psql -d nl_international -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

### 6. Создание .env
```bash
cat > .env << 'EOF'
# Скопировать содержимое из секции "Переменные окружения"
EOF
```

### 7. Создание таблиц
```bash
python scripts/create_database.py
```

### 8. Настройка systemd
```bash
# Создать /etc/systemd/system/nl-bots.service (см. выше)
systemctl daemon-reload
systemctl enable nl-bots
systemctl start nl-bots
```

---

## Мониторинг

### Проверка что боты работают
1. Написать `/start` ботам в Telegram
2. Проверить статус: `systemctl status nl-bots`
3. Посмотреть логи: `journalctl -u nl-bots -f`

### Проверка PostgreSQL
```bash
systemctl status postgresql
```

### Место на диске
```bash
df -h
```

### Память
```bash
free -h
```

---

## Бэкапы

### База данных
```bash
pg_dump -U nlbot nl_international > backup_$(date +%Y%m%d).sql
```

### Восстановление
```bash
psql -U nlbot nl_international < backup_YYYYMMDD.sql
```

---

## Возможные проблемы

### Бот не отвечает
1. Проверить статус: `systemctl status nl-bots`
2. Посмотреть логи: `journalctl -u nl-bots -n 50`
3. Перезапустить: `systemctl restart nl-bots`

### Нет места на диске
```bash
pip cache purge
apt clean
journalctl --vacuum-size=100M
```

### Ошибка подключения к БД
```bash
systemctl status postgresql
systemctl restart postgresql
```
