# Деплой Partner Panel (Telegram Mini App)

Пошаговая инструкция по деплою Partner Panel на VPS с доменом.

## Шаг 1: Купить домен

### Где купить:
- **reg.ru** — от 150 руб/год за .ru
- **timeweb.com/ru/services/domains** — от 179 руб/год
- **nic.ru** — от 199 руб/год

### Что купить:
Любой домен, например:
- `nl-partner.ru`
- `apexflow-panel.ru`
- `nlpartner.site` (дешевле)

### После покупки:
1. Перейди в DNS настройки домена
2. Добавь **A-запись**:
   - Имя: `@` (или пусто)
   - Тип: `A`
   - Значение: `194.87.86.103`
3. Добавь ещё одну A-запись для www:
   - Имя: `www`
   - Тип: `A`
   - Значение: `194.87.86.103`
4. Подожди 5-30 минут пока DNS обновится

### Проверить DNS:
```bash
# На своём компе или на VPS
ping твой-домен.ru
# Должен показать IP 194.87.86.103
```

---

## Шаг 2: Настройка на VPS

### 2.1. Подключись к серверу:
```bash
ssh root@194.87.86.103
```

### 2.2. Обнови код и установи зависимости:
```bash
cd /root/apexflow
git pull

# Установи nginx и certbot если ещё нет
apt update
apt install -y nginx certbot python3-certbot-nginx

# Установи зависимости для Partner Panel backend
source venv/bin/activate
pip install pydantic-settings pyjwt
```

### 2.3. Собери frontend:
```bash
cd /root/apexflow/partner_panel/frontend

# Установи Node.js если нет (нужна версия 18+)
# Проверь: node --version
# Если нет или старая версия:
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt install -y nodejs

# Установи зависимости и собери
npm install
npm run build
```

---

## Шаг 3: Настройка nginx

### 3.1. Создай конфиг:
```bash
nano /etc/nginx/sites-available/partner-panel
```

Вставь (замени `YOUR_DOMAIN.ru` на свой домен):

```nginx
server {
    listen 80;
    server_name YOUR_DOMAIN.ru www.YOUR_DOMAIN.ru;

    location / {
        return 301 https://$host$request_uri;
    }

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }
}

server {
    listen 443 ssl http2;
    server_name YOUR_DOMAIN.ru www.YOUR_DOMAIN.ru;

    # SSL сертификаты (пока закомментируй, добавим после certbot)
    # ssl_certificate /etc/letsencrypt/live/YOUR_DOMAIN.ru/fullchain.pem;
    # ssl_certificate_key /etc/letsencrypt/live/YOUR_DOMAIN.ru/privkey.pem;

    ssl_session_timeout 1d;
    ssl_session_cache shared:SSL:50m;
    ssl_protocols TLSv1.2 TLSv1.3;

    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml;

    root /root/apexflow/partner_panel/frontend/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api {
        proxy_pass http://127.0.0.1:8001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        proxy_read_timeout 90;
    }

    location /health {
        proxy_pass http://127.0.0.1:8001/health;
    }
}
```

### 3.2. Включи сайт:
```bash
ln -sf /etc/nginx/sites-available/partner-panel /etc/nginx/sites-enabled/
nginx -t  # Проверить конфиг
systemctl reload nginx
```

---

## Шаг 4: SSL сертификат (Let's Encrypt)

### 4.1. Получи сертификат:
```bash
# Замени YOUR_DOMAIN.ru на свой домен
certbot --nginx -d YOUR_DOMAIN.ru -d www.YOUR_DOMAIN.ru
```

Certbot спросит:
- Email — введи свой (для напоминаний об истечении)
- Agree to terms — `Y`
- Share email — можно `N`
- Redirect HTTP to HTTPS — `2` (да, редирект)

### 4.2. Проверь автообновление:
```bash
certbot renew --dry-run
```

---

## Шаг 5: Systemd сервис для backend

### 5.1. Создай сервис:
```bash
nano /etc/systemd/system/partner-panel.service
```

Вставь:
```ini
[Unit]
Description=NL Partner Panel Backend (FastAPI)
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=simple
User=root
WorkingDirectory=/root/apexflow
Environment="PATH=/root/apexflow/venv/bin"
Environment="PARTNER_PANEL_API_PORT=8001"
Environment="PARTNER_PANEL_DATABASE_URL=postgresql+asyncpg://postgres:UB8TG6@@IUYDGC@localhost:5432/nl_international"
Environment="PARTNER_PANEL_SECRET_KEY=сгенерируй-длинный-ключ-тут"
Environment="PARTNER_PANEL_BOT_TOKEN=токен-бота-из-botfather"
ExecStart=/root/apexflow/venv/bin/uvicorn partner_panel.backend.main:app --host 127.0.0.1 --port 8001 --workers 2
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=partner-panel

[Install]
WantedBy=multi-user.target
```

### 5.2. Сгенерируй секретный ключ:
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
# Скопируй результат в PARTNER_PANEL_SECRET_KEY
```

### 5.3. Запусти:
```bash
systemctl daemon-reload
systemctl enable partner-panel
systemctl start partner-panel
systemctl status partner-panel
```

### 5.4. Проверь логи если что-то не так:
```bash
journalctl -u partner-panel -f
```

---

## Шаг 6: Настройка Mini App в BotFather

### 6.1. Создай нового бота или используй существующего:
1. Открой @BotFather в Telegram
2. `/newbot` или выбери существующего через `/mybots`

### 6.2. Настрой Web App:
```
/mybots
→ Выбери бота
→ Bot Settings
→ Menu Button
→ Configure menu button
```

Введи:
- **URL**: `https://YOUR_DOMAIN.ru`
- **Title**: `Partner Panel` (или любое название)

### 6.3. Получи токен бота:
```
/mybots
→ Выбери бота
→ API Token
```

Скопируй токен и добавь в systemd сервис (PARTNER_PANEL_BOT_TOKEN).

### 6.4. Перезапусти сервис:
```bash
systemctl restart partner-panel
```

---

## Шаг 7: Проверка

### 7.1. Проверь что всё работает:
```bash
# Backend работает?
curl http://localhost:8001/health

# HTTPS работает?
curl https://YOUR_DOMAIN.ru/health
```

### 7.2. Открой Mini App:
1. Открой бота в Telegram
2. Нажми кнопку меню (внизу слева, рядом с полем ввода)
3. Должна открыться Partner Panel

---

## Troubleshooting

### Ошибка "502 Bad Gateway"
Backend не запущен:
```bash
systemctl status partner-panel
journalctl -u partner-panel -n 50
```

### Ошибка "SSL certificate problem"
Certbot не отработал:
```bash
certbot certificates  # Посмотреть сертификаты
certbot renew --force-renewal  # Обновить принудительно
```

### Mini App не открывается
1. Проверь что URL в BotFather правильный (с https://)
2. Проверь что DNS настроен (ping домен)
3. Проверь SSL (https://www.ssllabs.com/ssltest/)

### База данных не подключается
Проверь DATABASE_URL в сервисе:
```bash
systemctl cat partner-panel | grep DATABASE
```

---

## Команды для управления

```bash
# Перезапустить backend
systemctl restart partner-panel

# Логи backend
journalctl -u partner-panel -f

# Перезапустить nginx
systemctl restart nginx

# Обновить код и пересобрать
cd /root/apexflow
git pull
cd partner_panel/frontend && npm run build
systemctl restart partner-panel
systemctl restart nginx
```

---

## Переменные окружения

| Переменная | Описание |
|------------|----------|
| `PARTNER_PANEL_BOT_TOKEN` | Токен Telegram бота (из BotFather) |
| `PARTNER_PANEL_DATABASE_URL` | PostgreSQL connection string |
| `PARTNER_PANEL_SECRET_KEY` | Секретный ключ для JWT |
| `PARTNER_PANEL_API_PORT` | Порт API (8001) |
