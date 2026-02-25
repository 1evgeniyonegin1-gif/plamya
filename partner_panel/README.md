# NL Partner Panel

Telegram Mini App для партнёров NL International. Позволяет подключать Traffic Engine и управлять каналами прямо из Telegram.

## Архитектура

```
partner_panel/
├── backend/                 # FastAPI Backend
│   ├── api/                # API endpoints
│   │   ├── auth.py        # Telegram WebApp авторизация
│   │   ├── credentials.py # Управление credentials
│   │   ├── channels.py    # Управление каналами
│   │   └── stats.py       # Статистика
│   ├── models/            # SQLAlchemy модели
│   ├── services/          # Бизнес-логика
│   │   ├── telegram_auth.py   # Валидация initData
│   │   └── auto_setup.py      # Автонастройка Traffic Engine
│   ├── config.py          # Настройки
│   └── main.py            # FastAPI приложение
│
└── frontend/               # React Mini App
    ├── src/
    │   ├── api/           # API клиент (axios)
    │   ├── components/    # UI компоненты
    │   ├── hooks/         # React hooks
    │   │   ├── useTelegram.ts  # Telegram WebApp API
    │   │   └── useAuth.ts      # Авторизация (zustand)
    │   ├── pages/         # Страницы
    │   │   ├── Dashboard.tsx   # Главная
    │   │   ├── Connect.tsx     # Подключение аккаунта
    │   │   ├── Channels.tsx    # Управление каналами
    │   │   └── Stats.tsx       # Статистика
    │   ├── App.tsx
    │   └── main.tsx
    ├── package.json
    └── vite.config.ts
```

## Функционал

### Для партнёра:
1. **Подключение аккаунта** — ввод session_string, прокси
2. **Создание канала** — выбор сегмента (ЗОЖ/Мамы/Бизнес)
3. **Управление каналами** — пауза/запуск, настройки
4. **Статистика** — подписчики, просмотры, лиды

### Автоматизация:
- Генерация персоны под сегмент
- Автопостинг контента
- Интеграция реферальных ссылок
- Трекинг лидов

## Технологии

### Backend:
- **FastAPI** — API фреймворк
- **SQLAlchemy** — ORM
- **PostgreSQL** — база данных
- **PyJWT** — JWT токены

### Frontend:
- **React 18** — UI фреймворк
- **TypeScript** — типизация
- **Vite** — сборка
- **TailwindCSS** — стили
- **TanStack Query** — кэширование запросов
- **Zustand** — state management
- **Telegram WebApp API** — интеграция с Telegram

## Запуск

### Backend:
```bash
cd partner_panel/backend

# Создать venv
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Установить зависимости
pip install fastapi uvicorn sqlalchemy asyncpg pydantic-settings pyjwt

# Запустить
python -m partner_panel.backend.main
# или
uvicorn partner_panel.backend.main:app --reload --port 8000
```

### Frontend:
```bash
cd partner_panel/frontend

# Установить зависимости
npm install

# Запустить dev сервер
npm run dev

# Собрать для production
npm run build
```

## Конфигурация

### Backend (.env):
```env
# Telegram Bot Token (для валидации initData)
PARTNER_PANEL_BOT_TOKEN=your_bot_token

# Database
PARTNER_PANEL_DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/nl_international

# Security
PARTNER_PANEL_SECRET_KEY=your-secret-key

# Telethon defaults
PARTNER_PANEL_DEFAULT_API_ID=12345678
PARTNER_PANEL_DEFAULT_API_HASH=abcdef123456
```

### Frontend (.env):
```env
VITE_API_URL=/api/v1
```

## Деплой

### 1. Собрать frontend:
```bash
cd frontend && npm run build
```

### 2. Настроить nginx:
```nginx
server {
    listen 443 ssl;
    server_name partner.yourdomain.com;

    # Frontend
    location / {
        root /path/to/partner_panel/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    # API
    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 3. Настроить Mini App в BotFather:
```
/mybots → @your_bot → Bot Settings → Menu Button
URL: https://partner.yourdomain.com
```

## API Endpoints

### Auth
- `POST /api/v1/auth/telegram` — авторизация через Telegram initData
- `GET /api/v1/auth/me` — текущий партнёр

### Credentials
- `GET /api/v1/credentials` — список credentials
- `POST /api/v1/credentials` — добавить credentials
- `POST /api/v1/credentials/validate` — проверить session_string
- `DELETE /api/v1/credentials/{id}` — удалить

### Channels
- `GET /api/v1/channels` — список каналов
- `POST /api/v1/channels` — создать канал
- `PATCH /api/v1/channels/{id}` — обновить настройки
- `POST /api/v1/channels/{id}/pause` — приостановить
- `POST /api/v1/channels/{id}/resume` — возобновить
- `GET /api/v1/channels/{id}/stats` — статистика канала

### Stats
- `GET /api/v1/stats/overview` — общая статистика
- `GET /api/v1/stats/daily` — по дням
- `GET /api/v1/stats/leads` — список лидов

## Интеграция с Traffic Engine

Partner Panel использует существующий Traffic Engine:

1. **При создании канала** вызывается `AutoSetupService`
2. Credentials сохраняются в таблицу `partner_credentials`
3. Канал создаётся через Telethon и сохраняется в `partner_channels`
4. Автопостинг запускается через существующий `ContentScheduler`
5. Статистика собирается из `traffic_sources` и `traffic_clicks`

## Безопасность

- initData валидируется по HMAC-SHA256
- JWT токены для API запросов
- Session strings хранятся зашифрованно (TODO)
- Rate limiting на API (TODO)
