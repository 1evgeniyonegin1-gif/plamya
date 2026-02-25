# Миграция на Yandex Cloud

**Дата:** 20 января 2026
**Причина:** Нестабильное SSH соединение на Timeweb VPS + оптимизация для YandexGPT/YandexART

---

## Преимущества Yandex Cloud

✅ **Стабильность** — инфраструктура уровня enterprise
✅ **Скорость** — YandexGPT/YandexART в той же облачной инфраструктуре (меньше latency)
✅ **Managed Services** — PostgreSQL, мониторинг, бэкапы из коробки
✅ **Интеграция** — единая консоль для VM, AI, БД
✅ **Безопасность** — security groups, IAM, audit logs
✅ **Оплата рублями** — как и YandexGPT

---

## План миграции

### Этап 1: Создание инфраструктуры в Yandex Cloud

#### 1.1. Создать виртуальную машину (Compute Cloud)

**Параметры VM:**
- **Платформа:** Intel Ice Lake
- **Конфигурация:** 2 vCPU, 4 GB RAM (достаточно для 2 ботов)
- **Диск:** 20 GB SSD
- **ОС:** Ubuntu 22.04 LTS
- **Публичный IP:** Да (для SSH и Telegram API)
- **Security Group:**
  - Входящий: SSH (22), исходящий: ALL

**Создание через CLI:**
```bash
yc compute instance create \
  --name nl-bots-vm \
  --zone ru-central1-a \
  --platform standard-v3 \
  --cores 2 \
  --memory 4 \
  --core-fraction 100 \
  --create-boot-disk size=20,type=network-ssd,image-folder-id=standard-images,image-family=ubuntu-2204-lts \
  --network-interface subnet-name=default-ru-central1-a,nat-ip-version=ipv4 \
  --ssh-key ~/.ssh/id_rsa.pub
```

**Или через консоль:**
https://console.cloud.yandex.ru/folders/<folder-id>/compute/instances

---

#### 1.2. Настроить PostgreSQL

**Вариант A: Managed PostgreSQL (рекомендуется)**

**Преимущества:**
- Автоматические бэкапы
- Репликация
- Мониторинг
- Автообновления

**Параметры:**
- **Версия:** PostgreSQL 15
- **Класс хоста:** s2.micro (2 vCPU, 8 GB RAM)
- **Диск:** 10 GB SSD
- **Расширения:** pgvector (для RAG)

**Создание через CLI:**
```bash
yc managed-postgresql cluster create \
  --name nl-bots-db \
  --environment production \
  --network-name default \
  --postgresql-version 15 \
  --resource-preset s2.micro \
  --disk-type network-ssd \
  --disk-size 10 \
  --user name=nlbot,password=<STRONG_PASSWORD> \
  --database name=nl_international,owner=nlbot \
  --host zone-id=ru-central1-a,assign-public-ip=true
```

**Вариант B: PostgreSQL на той же VM (бюджетный)**

```bash
# На VM
sudo apt update
sudo apt install -y postgresql postgresql-contrib
sudo -u postgres psql -c "CREATE USER nlbot WITH PASSWORD '<PASSWORD>';"
sudo -u postgres psql -c "CREATE DATABASE nl_international OWNER nlbot;"
```

---

### Этап 2: Настройка новой VM

#### 2.1. Подключиться к VM

```bash
ssh yc-user@<PUBLIC_IP>
```

#### 2.2. Установить зависимости

```bash
# Системные пакеты
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3-pip git postgresql-client

# Создать директорию проекта
mkdir -p /home/yc-user/nl-international-ai-bots
cd /home/yc-user/nl-international-ai-bots

# Клонировать репозиторий
git clone https://github.com/<YOUR_REPO>/nl-international-ai-bots.git .
# Или загрузить код вручную через scp

# Создать venv
python3.11 -m venv venv
source venv/bin/activate

# Установить зависимости
pip install -r requirements.txt
```

#### 2.3. Настроить .env

```bash
# Создать .env файл
nano .env
```

**Содержимое .env:**
```env
# Telegram
CURATOR_BOT_TOKEN=<ваш токен>
CONTENT_MANAGER_BOT_TOKEN=<ваш токен>
CHANNEL_USERNAME=@nl_international_partners
ADMIN_TELEGRAM_IDS=756877849

# Группа с Topics
GROUP_ID=-1003676349853
CURATOR_BOT_USERNAME=@nl_curator_bot
TOPIC_PRODUCTS=7
TOPIC_BUSINESS=6
TOPIC_TRAINING=5
TOPIC_NEWS=4
TOPIC_SUCCESS=3
TOPIC_FAQ=2

# YandexGPT (используем существующий сервисный аккаунт)
YANDEX_SERVICE_ACCOUNT_ID=aje76dc7i20078podfrc
YANDEX_KEY_ID=ajensd96tl0d2q9fqmp9
YANDEX_PRIVATE_KEY_FILE=/home/yc-user/nl-international-ai-bots/yandex_key.pem
YANDEX_FOLDER_ID=b1gibb3gjf11pjbu65r3
YANDEX_MODEL=yandexgpt-lite

# YandexART
YANDEX_ART_ENABLED=true
YANDEX_ART_WIDTH=1024
YANDEX_ART_HEIGHT=1024

# AI модели
CONTENT_MANAGER_AI_MODEL=YandexGPT
CURATOR_AI_MODEL=claude-3-5-sonnet-20241022

# База данных
# Если Managed PostgreSQL:
DATABASE_URL=postgresql+asyncpg://nlbot:<PASSWORD>@<DB_HOST>:6432/nl_international
# Если на той же VM:
DATABASE_URL=postgresql+asyncpg://nlbot:<PASSWORD>@localhost:5432/nl_international

# GigaChat (резерв)
GIGACHAT_AUTH_TOKEN=<ваш токен>
GIGACHAT_CLIENT_ID=<ваш client_id>

# Claude (для куратора)
ANTHROPIC_API_KEY=<ваш ключ>
```

#### 2.4. Загрузить приватный ключ YandexGPT

```bash
# Скопировать с локальной машины
scp yandex_key.pem yc-user@<PUBLIC_IP>:/home/yc-user/nl-international-ai-bots/

# Или создать на сервере
nano /home/yc-user/nl-international-ai-bots/yandex_key.pem
# Вставить содержимое ключа
chmod 600 yandex_key.pem
```

---

### Этап 3: Миграция данных

#### 3.1. Экспортировать данные из старой БД (Timeweb)

**На старом сервере (если SSH заработает):**
```bash
pg_dump -h localhost -U nlbot nl_international > /tmp/nl_dump.sql
```

**Или подключитесь к Timeweb через веб-консоль:**
```bash
pg_dump -h localhost -U postgres nl_international > /tmp/nl_dump.sql
```

#### 3.2. Скопировать дамп на локальную машину

```bash
# С вашего компьютера
scp root@194.87.86.103:/tmp/nl_dump.sql ./nl_dump.sql
```

#### 3.3. Загрузить дамп в новую БД

**Если Managed PostgreSQL:**
```bash
psql -h <DB_HOST> -p 6432 -U nlbot -d nl_international < nl_dump.sql
```

**Если PostgreSQL на VM:**
```bash
psql -h localhost -U nlbot -d nl_international < nl_dump.sql
```

#### 3.4. Включить pgvector расширение

```bash
psql -h <DB_HOST> -U nlbot -d nl_international -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

---

### Этап 4: Запуск ботов на Yandex Cloud

#### 4.1. Создать systemd сервис

```bash
sudo nano /etc/systemd/system/nl-bots.service
```

**Содержимое:**
```ini
[Unit]
Description=NL International AI Bots
After=network.target postgresql.service

[Service]
Type=simple
User=yc-user
WorkingDirectory=/home/yc-user/nl-international-ai-bots
Environment="PATH=/home/yc-user/nl-international-ai-bots/venv/bin"
ExecStart=/home/yc-user/nl-international-ai-bots/venv/bin/python run_bots.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

#### 4.2. Запустить сервис

```bash
sudo systemctl daemon-reload
sudo systemctl enable nl-bots
sudo systemctl start nl-bots

# Проверить статус
sudo systemctl status nl-bots

# Смотреть логи
sudo journalctl -u nl-bots -f
```

---

### Этап 5: Проверка и переключение

#### 5.1. Протестировать ботов

- Отправьте `/start` в @nl_curator_bot
- Отправьте `/generate` в @nl_content_bot
- Проверьте генерацию текста и картинок

#### 5.2. Остановить старые боты на Timeweb

**Через веб-консоль Timeweb (если SSH не работает):**
```bash
systemctl stop nl-bots
systemctl disable nl-bots
```

#### 5.3. Обновить документацию

Обновить [CLAUDE.md](../CLAUDE.md):
- Новый IP адрес VM
- Новый путь к проекту
- Новые команды управления

---

## Стоимость Yandex Cloud (примерная)

| Ресурс | Конфигурация | Цена/месяц |
|--------|--------------|------------|
| VM (Compute Cloud) | 2 vCPU, 4 GB RAM, 20 GB SSD | ~900 ₽ |
| Managed PostgreSQL | s2.micro, 10 GB SSD | ~1500 ₽ |
| YandexGPT API | Pay-as-you-go | ~500-2000 ₽ |
| YandexART API | Pay-as-you-go | ~500-1000 ₽ |
| **Итого** | | **~3400-5400 ₽/месяц** |

**Бюджетный вариант (PostgreSQL на VM):** ~1900-4000 ₽/месяц

---

## Команды управления на Yandex Cloud

### SSH подключение
```bash
ssh yc-user@<PUBLIC_IP>
```

### Управление ботами
```bash
# Перезапуск
sudo systemctl restart nl-bots

# Статус
sudo systemctl status nl-bots

# Логи
sudo journalctl -u nl-bots -f

# Обновить код
cd /home/yc-user/nl-international-ai-bots
git pull
sudo systemctl restart nl-bots
```

### Управление БД (Managed PostgreSQL)
```bash
# Подключиться к БД
psql -h <DB_HOST> -p 6432 -U nlbot -d nl_international

# Бэкап
pg_dump -h <DB_HOST> -p 6432 -U nlbot nl_international > backup.sql

# Восстановление
psql -h <DB_HOST> -p 6432 -U nlbot -d nl_international < backup.sql
```

---

## Troubleshooting

### VM не создаётся
- Проверьте квоты в Yandex Cloud
- Проверьте баланс

### Не подключается к Managed PostgreSQL
- Проверьте, что в настройках кластера включён "Публичный доступ"
- Проверьте Security Group (разрешить порт 6432)
- Используйте SSL: добавьте `?sslmode=require` к DATABASE_URL

### Боты не отвечают
- Проверьте логи: `sudo journalctl -u nl-bots -n 100`
- Проверьте .env файл: `cat .env | grep -v PASSWORD`
- Проверьте доступ к БД: `psql $DATABASE_URL -c "SELECT 1;"`

---

## Следующие шаги

1. **Создать VM в Yandex Cloud** (через консоль или CLI)
2. **Настроить PostgreSQL** (Managed или на VM)
3. **Перенести код и данные**
4. **Запустить боты**
5. **Протестировать**
6. **Обновить CLAUDE.md** с новыми инструкциями

---

**Ссылки:**
- [Yandex Compute Cloud](https://cloud.yandex.ru/docs/compute/)
- [Managed PostgreSQL](https://cloud.yandex.ru/docs/managed-postgresql/)
- [Yandex CLI](https://cloud.yandex.ru/docs/cli/)
