# Curator Mini App

Telegram Mini App для AI-Куратора (@nl_curator_bot).

## Разделы

### 🛒 Продукция
- Каталог 190 продуктов NL International
- Поиск и фильтр по категориям
- Фото продуктов
- Цены и PV
- Реферальные ссылки на nlstar.com

### 💼 Бизнес
- Сравнение моделей: "Ты один" vs "Ты + система APEXFLOW"
- Объяснение автоматизации
- CTA: Написать в Telegram (@DanilLysenkoNL)
- CTA: Регистрация партнёром (nlstar.com)

## Технологии

### Backend
- FastAPI
- SQLAlchemy (async)
- JWT аутентификация
- Telegram initData валидация

### Frontend
- React 18
- TypeScript
- Vite
- Tailwind CSS (космическая тема)
- TanStack Query
- Zustand

## Локальный запуск

### Backend
```bash
cd curator_miniapp
pip install -r requirements.txt
python -m curator_miniapp.backend.main
```
API: http://localhost:8002

### Frontend
```bash
cd curator_miniapp/frontend
npm install
npm run dev
```
UI: http://localhost:3001

## Структура

```
curator_miniapp/
├── backend/
│   ├── main.py              # FastAPI app
│   ├── config.py            # Настройки
│   ├── database.py          # DB session
│   ├── api/
│   │   ├── auth.py          # JWT auth
│   │   ├── products.py      # Каталог
│   │   └── business.py      # Бизнес-раздел
│   ├── models/
│   │   ├── user.py          # CuratorUser
│   │   └── analytics.py     # ProductView, BusinessInterest
│   └── services/
│       ├── telegram_auth.py # initData валидация
│       └── products_service.py
│
└── frontend/
    ├── src/
    │   ├── App.tsx          # Главный компонент
    │   ├── pages/
    │   │   ├── Products.tsx # Каталог
    │   │   └── Business.tsx # Бизнес
    │   ├── components/
    │   │   ├── ProductCard.tsx
    │   │   ├── ProductModal.tsx
    │   │   ├── Navigation.tsx
    │   │   ├── Loading.tsx
    │   │   └── Stars.tsx
    │   └── hooks/
    │       ├── useTelegram.ts
    │       └── useAuth.ts
    └── package.json
```

## API Endpoints

### Auth
- `POST /api/v1/auth/telegram` - Аутентификация через Telegram
- `GET /api/v1/auth/me` - Текущий пользователь

### Products
- `GET /api/v1/products` - Список продуктов
- `GET /api/v1/products/{key}` - Продукт по ключу
- `GET /api/v1/products/categories` - Категории
- `GET /api/v1/products/{key}/image` - Фото продукта
- `POST /api/v1/products/{key}/view` - Трекинг просмотра

### Business
- `GET /api/v1/business/presentation` - Контент бизнес-раздела
- `POST /api/v1/business/contact` - Трекинг CTA кликов
- `GET /api/v1/business/partner-status` - Статус партнёра

## Интеграция с ботом

В curator_bot добавлены команды:
- `/menu` - Показывает Mini App кнопки
- `/catalog` - Открывает каталог продуктов
- `/business` - Открывает бизнес-раздел

## Переменные окружения

```env
# Используется токен куратора
CURATOR_BOT_TOKEN=...

# URL Mini App (для кнопок в боте)
CURATOR_MINIAPP_URL=https://curator.apexflow.ru

# JWT секрет
CURATOR_MINIAPP_SECRET_KEY=...

# Контакт для CTA
BUSINESS_CONTACT_USERNAME=DanilLysenkoNL
```

## Деплой

1. Применить миграцию: `scripts/migrations/011_curator_miniapp.sql`
2. Собрать frontend: `npm run build`
3. Настроить Nginx
4. Создать systemd сервис

## Реферальные ссылки

| Назначение | URL |
|------------|-----|
| Регистрация | https://nlstar.com/ref/eiPusg/ |
| Каталог | https://nlstar.com/ref/q9zfpK/ |
