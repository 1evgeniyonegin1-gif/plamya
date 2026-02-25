# Deploy Telegram Job Monitor

## Шаги деплоя на VPS

### 1. Получить Session String

Используем существующий session от Traffic Engine:

```bash
ssh root@194.87.86.103

# Проверить что Traffic Engine работает
systemctl status apexflow-traffic

# Получить session_string из БД или .env
cd /root/apexflow
grep TELEGRAM_SESSION traffic_engine/config.py  # или cat .env
```

Если нужен новый session:

```bash
cd /root/apexflow
source venv/bin/activate
python -c "
from telethon.sync import TelegramClient
from telethon.sessions import StringSession

api_id = YOUR_API_ID
api_hash = 'YOUR_API_HASH'

with TelegramClient(StringSession(), api_id, api_hash) as client:
    print('Session string:', client.session.save())
"
```

### 2. Настроить переменные окружения

Отредактировать `deploy/telegram-job-monitor.service`:

```ini
Environment="TELEGRAM_SESSION_STRING=ВАША_SESSION_STRING"
Environment="TELEGRAM_API_ID=ВАШЕ_API_ID"
Environment="TELEGRAM_API_HASH=ВАШЕ_API_HASH"
```

### 3. Deploy на VPS

```bash
# На локальной машине - закоммитить изменения
cd c:\Users\mafio\OneDrive\Документы\projects\nl-international-ai-bots
git add freelance_engine/telegram_monitor.py
git add freelance_engine/job_analyzer.py
git add scripts/run_job_monitor.py
git add deploy/telegram-job-monitor.service
git add DEPLOY_JOB_MONITOR.md
git commit -m "feat: Telegram job channels monitor"
git push origin main

# На VPS - обновить код
ssh root@194.87.86.103
cd /root/apexflow
git pull origin main

# Установить зависимости (если нужны новые)
source venv/bin/activate
pip install -r requirements.txt

# Скопировать systemd сервис
cp deploy/telegram-job-monitor.service /etc/systemd/system/

# ВАЖНО: Отредактировать сервис и добавить credentials!
nano /etc/systemd/system/telegram-job-monitor.service
# Заполнить TELEGRAM_SESSION_STRING, API_ID, API_HASH

# Перезагрузить systemd
systemctl daemon-reload

# Запустить сервис
systemctl start telegram-job-monitor

# Проверить статус
systemctl status telegram-job-monitor

# Просмотр логов
journalctl -u telegram-job-monitor -f

# Включить автозапуск
systemctl enable telegram-job-monitor
```

### 4. Проверка работы

```bash
# Логи
journalctl -u telegram-job-monitor -n 50 --no-pager

# Проверить создание лидов в CRM
cd /root/apexflow
source venv/bin/activate
python -c "from freelance_engine.crm import get_new_leads; print(get_new_leads(10))"

# Проверить INBOX
cat ~/.plamya/shared/INBOX.md
```

### 5. Мониторинг

```bash
# Статус всех сервисов APEXFLOW
systemctl status nl-bots
systemctl status apexflow-traffic
systemctl status telegram-job-monitor

# RAM usage
free -m

# Disk space
df -h
```

## Troubleshooting

### Сервис не запускается

```bash
# Проверить логи
journalctl -u telegram-job-monitor -n 100 --no-pager

# Проверить permissions
ls -la /root/apexflow/scripts/run_job_monitor.py

# Запустить вручную для дебага
cd /root/apexflow
source venv/bin/activate
export TELEGRAM_SESSION_STRING="..."
export TELEGRAM_API_ID="..."
export TELEGRAM_API_HASH="..."
python scripts/run_job_monitor.py
```

### Session expired

Если session протух (FloodWaitError, AuthKeyUnregisteredError):

```bash
# Сгенерировать новый session
cd /root/apexflow
source venv/bin/activate
python -c "
from telethon.sync import TelegramClient
from telethon.sessions import StringSession

api_id = YOUR_API_ID
api_hash = 'YOUR_API_HASH'

with TelegramClient(StringSession(), api_id, api_hash) as client:
    print('New session string:', client.session.save())
"

# Обновить в systemd
nano /etc/systemd/system/telegram-job-monitor.service
systemctl daemon-reload
systemctl restart telegram-job-monitor
```

### Нет новых лидов

```bash
# Проверить что каналы доступны
cd /root/apexflow
source venv/bin/activate
python -c "
from telethon.sync import TelegramClient
from telethon.sessions import StringSession

session = 'YOUR_SESSION'
api_id = YOUR_ID
api_hash = 'YOUR_HASH'

with TelegramClient(StringSession(session), api_id, api_hash) as client:
    # Проверяем доступ к каналу
    entity = client.get_entity('@freelance_orders')
    print(f'Channel: {entity.title}, subscribers: {entity.participants_count}')
"
```

## Настройка каналов

Для добавления/удаления каналов отредактируйте:

`freelance_engine/telegram_monitor.py`:

```python
DEFAULT_CHANNELS = [
    "@freelance_orders",
    "@python_jobs",
    "@botjobs",
    "@fl_it",
    "@remotejob_it",
    # добавьте новые каналы здесь
]
```

После изменения:

```bash
git commit -am "feat: update monitored channels"
git push
# на VPS: git pull && systemctl restart telegram-job-monitor
```

## Performance

- RAM usage: ~50-100 MB (Telethon client)
- CPU: minimal (событийная модель)
- Network: ~1-5 MB/hour (зависит от активности каналов)

## Безопасность

⚠️ **НИКОГДА не коммитить session string в git!**

Session string даёт полный доступ к Telegram аккаунту.
Хранить только в:
- `/etc/systemd/system/telegram-job-monitor.service` (на VPS)
- Environment variables (не в коде!)
