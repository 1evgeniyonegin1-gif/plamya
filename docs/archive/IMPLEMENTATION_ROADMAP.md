# ROADMAP: Полная реализация автоворонки с масштабированием

**Дата создания:** 21 января 2026
**Цель:** Превратить бота в автоматическую машину продаж с дупликацией на партнёров
**Ожидаемый результат:** 600,000+ ₽/мес через 12 месяцев

---

## Обзор проекта

### Текущее состояние:
- AI-Куратор работает как справочник
- Отвечает на вопросы, но НЕ продаёт
- Нет воронки, нет сбора контактов, нет реферальных ссылок

### Целевое состояние:
- Автоматическая воронка продаж
- Каждый партнёр может использовать систему
- Масштабирование через команду

### Связанные документы:
- [SALES_FUNNEL_PLAN.md](SALES_FUNNEL_PLAN.md) — детали воронки продаж
- [SCALING_POTENTIAL.md](SCALING_POTENTIAL.md) — расчёт потенциала дохода

---

## Фазы реализации

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         ROADMAP РЕАЛИЗАЦИИ                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ФАЗА 1 (Недели 1-2)          ФАЗА 2 (Недели 3-4)                       │
│  ══════════════════           ══════════════════                        │
│  MVP Воронки                  Полная воронка                            │
│  • /start с кнопками          • Цепочки прогрева                        │
│  • Квалификация лида          • Автонапоминания                         │
│  • Реф. ссылки                • Сбор контактов                          │
│                               • Уведомления о лидах                     │
│         ↓                              ↓                                │
│                                                                          │
│  ФАЗА 3 (Недели 5-6)          ФАЗА 4 (Недели 7-8)                       │
│  ══════════════════           ══════════════════                        │
│  Мультипартнёрский режим      Обучение и запуск                         │
│  • Регистрация лидеров        • Материалы для партнёров                 │
│  • Персональные ссылки        • Онбординг 5 партнёров                   │
│  • Панель партнёра            • Тестирование                            │
│                                                                          │
│         ↓                              ↓                                │
│                                                                          │
│  ФАЗА 5 (Месяцы 3-6)          ФАЗА 6 (Месяцы 6-12)                      │
│  ══════════════════           ══════════════════                        │
│  Масштабирование              Полная сеть                               │
│  • 20-50 партнёров            • 100+ партнёров                          │
│  • Оптимизация конверсий      • AC1 квалификация                        │
│  • TOP квалификация           • 500,000+ ₽/мес                          │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

# ФАЗА 1: MVP Воронки (Недели 1-2)

## Цель фазы
Минимальная работающая воронка: лид приходит → квалифицируется → получает реф. ссылку

## Задачи

### 1.1 Новый /start с inline-кнопками
**Файл:** `curator_bot/handlers/commands.py`
**Время:** 3-4 часа

**Что делаем:**
```python
# Заменяем текущий /start на версию с кнопками

@router.message(CommandStart())
async def cmd_start(message: Message):
    # Регистрируем пользователя (как сейчас)
    # ...

    # Показываем кнопки выбора
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🍎 Хочу улучшить здоровье",
            callback_data="intent_client"
        )],
        [InlineKeyboardButton(
            text="💼 Интересует заработок",
            callback_data="intent_business"
        )],
        [InlineKeyboardButton(
            text="❓ Просто хочу узнать больше",
            callback_data="intent_curious"
        )]
    ])

    await message.answer(
        "Привет! Я Данил, AI-консультант NL International.\n\n"
        "Чем могу помочь?",
        reply_markup=keyboard
    )
```

**Результат:** Пользователь выбирает путь при старте

---

### 1.2 Обработчики выбора intent
**Файл:** `curator_bot/handlers/funnel_callbacks.py` (новый)
**Время:** 4-5 часов

**Что делаем:**
```python
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

router = Router(name="funnel_callbacks")

# === ВЫБОР INTENT ===

@router.callback_query(F.data == "intent_client")
async def handle_client_intent(callback: CallbackQuery):
    """Пользователь выбрал 'Здоровье'"""
    # Сохраняем в БД
    await save_user_intent(callback.from_user.id, "client")

    # Показываем выбор боли
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔥 Похудеть", callback_data="pain_weight")],
        [InlineKeyboardButton(text="⚡ Больше энергии", callback_data="pain_energy")],
        [InlineKeyboardButton(text="💪 Укрепить здоровье", callback_data="pain_health")],
        [InlineKeyboardButton(text="✨ Красота изнутри", callback_data="pain_beauty")],
    ])

    await callback.message.edit_text(
        "Отлично! Что тебя интересует больше всего?",
        reply_markup=keyboard
    )


@router.callback_query(F.data == "intent_business")
async def handle_business_intent(callback: CallbackQuery):
    """Пользователь выбрал 'Заработок'"""
    await save_user_intent(callback.from_user.id, "business")

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 10-30к/мес", callback_data="income_10_30")],
        [InlineKeyboardButton(text="📈 50-100к/мес", callback_data="income_50_100")],
        [InlineKeyboardButton(text="🚀 200к+ /мес", callback_data="income_200_plus")],
    ])

    await callback.message.edit_text(
        "Круто! Какой уровень дохода тебя интересует?",
        reply_markup=keyboard
    )


# === ВЫБОР БОЛИ (для клиентов) ===

@router.callback_query(F.data.startswith("pain_"))
async def handle_pain_selection(callback: CallbackQuery):
    """Обработка выбора боли"""
    pain = callback.data.replace("pain_", "")
    await save_user_pain(callback.from_user.id, pain)

    # Отправляем первое сообщение прогрева + рекомендацию
    recommendation = get_product_recommendation(pain)

    await callback.message.edit_text(
        recommendation["intro_message"],
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="📦 Хочу попробовать",
                callback_data=f"show_product_{pain}"
            )],
            [InlineKeyboardButton(
                text="❓ Есть вопросы",
                callback_data="ask_question"
            )]
        ])
    )


# === ПОКАЗ ПРОДУКТА С ССЫЛКОЙ ===

@router.callback_query(F.data.startswith("show_product_"))
async def show_product_with_link(callback: CallbackQuery):
    """Показывает продукт с реферальной ссылкой"""
    pain = callback.data.replace("show_product_", "")
    user_id = callback.from_user.id

    # Получаем реф. ссылку (владельца или партнёра)
    referral_link = await get_referral_link(user_id, pain)
    recommendation = get_product_recommendation(pain)

    await callback.message.edit_text(
        f"Для твоей цели идеально подойдёт:\n\n"
        f"🥤 **{recommendation['product']}**\n"
        f"{recommendation['description']}\n\n"
        f"💰 Цена: {recommendation['price']} (со скидкой 25%)\n\n"
        f"👉 Заказать: {referral_link}\n\n"
        f"После заказа напиши мне — помогу с программой!",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="🛒 Перейти к заказу",
                url=referral_link
            )],
            [InlineKeyboardButton(
                text="💬 Задать вопрос",
                callback_data="ask_question"
            )]
        ])
    )

    # Логируем событие воронки
    await log_funnel_event(user_id, "product_shown", {"pain": pain})
```

**Результат:** Полный путь от /start до реф. ссылки

---

### 1.3 Конфигурация реферальных ссылок
**Файл:** `curator_bot/config/referral.py` (новый)
**Время:** 2-3 часа

**Что делаем:**
```python
from shared.config.settings import settings

# Маппинг продуктов на ссылки
PRODUCT_LINKS = {
    "weight": {
        "product": "Energy Diet Smart",
        "description": "Контроль веса без голода. 15 порций разных вкусов.",
        "price": "3,490 ₽",
        "product_id": "ed-smart-starter",
    },
    "energy": {
        "product": "Greenflash Витамины + Адаптогены",
        "description": "Комплекс для энергии и работоспособности.",
        "price": "2,890 ₽",
        "product_id": "gf-energy-complex",
    },
    "health": {
        "product": "Greenflash Иммунитет",
        "description": "Поддержка иммунной системы. Витамины C, D, цинк.",
        "price": "1,990 ₽",
        "product_id": "gf-immunity",
    },
    "beauty": {
        "product": "Collagen Formula",
        "description": "Коллаген + гиалуроновая кислота для кожи и волос.",
        "price": "2,490 ₽",
        "product_id": "collagen-formula",
    },
}


def get_product_recommendation(pain: str) -> dict:
    """Возвращает рекомендацию продукта по боли"""
    return PRODUCT_LINKS.get(pain, PRODUCT_LINKS["health"])


def generate_referral_link(partner_id: str, product_id: str) -> str:
    """Генерирует реферальную ссылку"""
    base_url = settings.nl_shop_base_url or "https://nlstar.com"
    return f"{base_url}/shop/{product_id}?ref={partner_id}"


async def get_referral_link(user_telegram_id: int, pain: str) -> str:
    """
    Получает реферальную ссылку.
    Если пользователь пришёл от партнёра — ссылка партнёра.
    Иначе — ссылка владельца системы.
    """
    # Проверяем, есть ли у пользователя "родитель" (кто его привёл)
    parent_partner = await get_user_parent_partner(user_telegram_id)

    if parent_partner and parent_partner.nl_partner_id:
        partner_id = parent_partner.nl_partner_id
    else:
        # Используем ID владельца системы
        partner_id = settings.nl_referral_id

    product = PRODUCT_LINKS.get(pain, PRODUCT_LINKS["health"])
    return generate_referral_link(partner_id, product["product_id"])
```

**Результат:** Автоматическая генерация реферальных ссылок

---

### 1.4 Обновление модели User в БД
**Файл:** `curator_bot/database/models.py`
**Время:** 1-2 часа

**Добавляем поля:**
```python
class User(Base):
    __tablename__ = "users"

    # ... существующие поля ...

    # Новые поля для воронки
    user_intent = Column(String(50))        # client / business / curious
    pain_point = Column(String(50))         # weight / energy / health / beauty
    income_goal = Column(String(50))        # 10_30 / 50_100 / 200_plus
    funnel_step = Column(Integer, default=0)
    funnel_started_at = Column(DateTime)

    # Для мультипартнёрского режима (Фаза 3)
    is_partner_leader = Column(Boolean, default=False)
    nl_partner_id = Column(String(50))      # ID партнёра в NL
    parent_partner_id = Column(Integer, ForeignKey("users.id"))

    # Контакты (Фаза 2)
    phone = Column(String(20))
    email = Column(String(100))
    lead_status = Column(String(50), default="new")
    lead_score = Column(Integer, default=0)
```

---

### 1.5 Миграция БД
**Файл:** `scripts/migrate_funnel_phase1.py` (новый)
**Время:** 1 час

```python
"""
Миграция БД для Фазы 1: MVP Воронки
"""
import asyncio
from sqlalchemy import text
from shared.database.base import engine

async def migrate():
    async with engine.begin() as conn:
        print("🔄 Запуск миграции Фазы 1...")

        # Добавляем поля для воронки
        await conn.execute(text("""
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS user_intent VARCHAR(50),
            ADD COLUMN IF NOT EXISTS pain_point VARCHAR(50),
            ADD COLUMN IF NOT EXISTS income_goal VARCHAR(50),
            ADD COLUMN IF NOT EXISTS funnel_step INTEGER DEFAULT 0,
            ADD COLUMN IF NOT EXISTS funnel_started_at TIMESTAMP,
            ADD COLUMN IF NOT EXISTS is_partner_leader BOOLEAN DEFAULT FALSE,
            ADD COLUMN IF NOT EXISTS nl_partner_id VARCHAR(50),
            ADD COLUMN IF NOT EXISTS parent_partner_id INTEGER REFERENCES users(id)
        """))

        # Создаём таблицу событий воронки
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS funnel_events (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id),
                event_type VARCHAR(50) NOT NULL,
                event_data JSONB,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """))

        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_funnel_events_user
            ON funnel_events(user_id)
        """))

        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_funnel_events_type
            ON funnel_events(event_type)
        """))

        print("✅ Миграция Фазы 1 завершена!")

if __name__ == "__main__":
    asyncio.run(migrate())
```

---

### 1.6 Регистрация роутеров
**Файл:** `curator_bot/main.py`
**Время:** 30 минут

**Добавляем:**
```python
from curator_bot.handlers.funnel_callbacks import router as funnel_router

# В функции main():
dp.include_router(funnel_router)
```

---

## Чеклист Фазы 1

- [ ] Обновить `/start` с inline-кнопками
- [ ] Создать `funnel_callbacks.py` с обработчиками
- [ ] Создать `referral.py` с конфигурацией ссылок
- [ ] Добавить поля в модель User
- [ ] Создать и запустить миграцию
- [ ] Зарегистрировать роутер в main.py
- [ ] Добавить NL_REFERRAL_ID в .env
- [ ] Протестировать полный путь: /start → выбор → ссылка
- [ ] Задеплоить на VPS

**Время на Фазу 1:** 12-15 часов
**Результат:** Работающая MVP воронка

---

# ФАЗА 2: Полная воронка (Недели 3-4)

## Цель фазы
Добавить прогрев, напоминания, сбор контактов и уведомления

## Задачи

### 2.1 Цепочки прогрева
**Файл:** `curator_bot/funnels/warmup_sequences.py` (новый)
**Время:** 6-8 часов

**Структура:**
```python
"""
Цепочки прогревающих сообщений для разных путей воронки
"""

# === ЦЕПОЧКА ДЛЯ "ПОХУДЕНИЕ" ===

WEIGHT_SEQUENCE = [
    {
        "delay_hours": 0,  # Сразу после выбора
        "message": """
Окей, давай по факту про похудение.

Главное правило: дефицит калорий. Всё остальное — детали.

Но есть нюанс: если просто меньше есть — организм замедляет метаболизм и начинает "запасать" жир.

Нужен баланс:
• Достаточно белка (чтобы не терять мышцы)
• Контроль калорий (но не голодание!)
• Все нутриенты (чтобы метаболизм работал)

Сейчас расскажу, как это работает на практике...
""",
        "buttons": [
            {"text": "Продолжить →", "callback": "warmup_weight_2"}
        ]
    },
    {
        "delay_hours": 0,  # После клика
        "trigger": "warmup_weight_2",
        "message": """
Energy Diet — это не волшебная таблетка. Это инструмент контроля.

Одна порция = 200 ккал, при этом:
• 25г белка (сытость на 3-4 часа)
• Все витамины и минералы (метаболизм не замедляется)
• Клетчатка (нормальное пищеварение)
• Готовится за 2 минуты

Как использовать:
Заменяешь 1-2 приёма пищи → автоматический дефицит калорий.
Без голода, без срывов, без подсчёта.

Средний результат: -3-5 кг за первый месяц.
""",
        "buttons": [
            {"text": "Хочу попробовать", "callback": "show_product_weight"},
            {"text": "Сколько стоит?", "callback": "show_price_weight"}
        ]
    },
    {
        "delay_hours": 24,  # Через сутки, если не купил
        "auto": True,
        "message": """
{first_name}, вчера мы говорили о похудении.

Один факт, который многие не знают:
🔬 80% диет проваливаются потому, что люди недоедают белок.

Когда белка мало → организм "съедает" мышцы → метаболизм падает → вес возвращается.

Energy Diet решает эту проблему: 25г белка в каждой порции.

Кстати, сейчас действует скидка 25% на первый заказ 👇
""",
        "buttons": [
            {"text": "🛒 Заказать со скидкой", "callback": "show_product_weight"},
            {"text": "Есть вопрос", "callback": "ask_question"}
        ]
    },
    {
        "delay_hours": 72,  # Через 3 дня
        "auto": True,
        "message": """
{first_name}, финальное напоминание!

Скидка 25% на стартовый набор действует ещё 24 часа.

Это 15 порций разных вкусов — попробуешь и поймёшь, подходит тебе или нет.

После этого цена будет стандартная.

Решай сам, но если вопрос похудения актуален — это хороший момент попробовать.
""",
        "buttons": [
            {"text": "🛒 Успеть заказать", "callback": "show_product_weight"},
            {"text": "Не сейчас", "callback": "snooze_7_days"}
        ]
    }
]

# === ЦЕПОЧКА ДЛЯ "БИЗНЕС" ===

BUSINESS_SEQUENCE = [
    {
        "delay_hours": 0,
        "message": """
Отлично, что думаешь о дополнительном доходе!

Давай честно: в NL International нет "волшебных кнопок".
Это работа. Но работа с понятной математикой.

Вот как устроен доход:

1️⃣ Личный объём — продаёшь/потребляешь сам
2️⃣ Партнёрский бонус — за активность команды
3️⃣ Групповой объём — % от оборота всей структуры
4️⃣ Клубные бонусы — от оборота компании

Сейчас покажу конкретные цифры для твоей цели...
""",
        "buttons": [
            {"text": "Показать расчёт →", "callback": "warmup_business_2"}
        ]
    },
    {
        "delay_hours": 0,
        "trigger": "warmup_business_2",
        "message": """
{income_calculation}

Ключевой момент:
Ты не просто продаёшь, а строишь команду.

Каждый партнёр, которого ты обучишь — это пассивный доход.
Они работают → ты получаешь процент с их оборота.

И главное: у тебя будет инструмент — этот бот.
Он автоматически прогревает твоих лидов и закрывает на продукт.

Хочешь узнать, как начать?
""",
        "buttons": [
            {"text": "Да, расскажи", "callback": "warmup_business_3"},
            {"text": "Есть вопросы", "callback": "ask_question"}
        ]
    },
    {
        "delay_hours": 0,
        "trigger": "warmup_business_3",
        "message": """
Чтобы начать, нужно:

1️⃣ Зарегистрироваться (бесплатно)
   👉 {registration_link}

2️⃣ Сделать первый заказ 70 PV (~3,500 ₽)
   Это активирует твой контракт + получишь продукт

3️⃣ Я добавлю тебя в обучение
   Покажу как использовать бота для привлечения

После регистрации напиши мне — дам доступ к материалам и помогу с первыми шагами!
""",
        "buttons": [
            {"text": "📝 Зарегистрироваться", "url": "{registration_link}"},
            {"text": "Ещё вопросы", "callback": "ask_question"}
        ]
    }
]

# Функция выбора цепочки
def get_sequence(intent: str, pain: str = None, income_goal: str = None):
    if intent == "client":
        sequences = {
            "weight": WEIGHT_SEQUENCE,
            "energy": ENERGY_SEQUENCE,
            "health": HEALTH_SEQUENCE,
            "beauty": BEAUTY_SEQUENCE,
        }
        return sequences.get(pain, HEALTH_SEQUENCE)
    elif intent == "business":
        return BUSINESS_SEQUENCE
    return None
```

---

### 2.2 Scheduler для автонапоминаний
**Файл:** `curator_bot/scheduler/reminder_scheduler.py` (новый)
**Время:** 4-5 часов

```python
"""
Автоматические напоминания для воронки
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta
from sqlalchemy import select, and_
from aiogram import Bot

from shared.database.base import AsyncSessionLocal
from curator_bot.database.models import User, FunnelEvent
from curator_bot.funnels.warmup_sequences import get_sequence

scheduler = AsyncIOScheduler()


async def send_scheduled_reminders(bot: Bot):
    """Отправляет запланированные напоминания"""

    async with AsyncSessionLocal() as session:
        # Находим пользователей, которым нужно отправить напоминание
        now = datetime.now()

        # Пользователи в воронке, которые не завершили покупку
        result = await session.execute(
            select(User).where(
                and_(
                    User.funnel_step > 0,
                    User.lead_status.in_(["new", "warming"]),
                    User.funnel_started_at.isnot(None)
                )
            )
        )
        users = result.scalars().all()

        for user in users:
            # Получаем цепочку для этого пользователя
            sequence = get_sequence(
                user.user_intent,
                user.pain_point,
                user.income_goal
            )
            if not sequence:
                continue

            # Находим следующее автосообщение
            for i, step in enumerate(sequence):
                if not step.get("auto"):
                    continue

                delay_hours = step.get("delay_hours", 24)
                send_time = user.funnel_started_at + timedelta(hours=delay_hours)

                # Проверяем, пора ли отправлять
                if send_time <= now:
                    # Проверяем, не отправляли ли уже
                    already_sent = await check_if_sent(
                        session, user.id, f"auto_reminder_{i}"
                    )
                    if not already_sent:
                        await send_reminder(bot, user, step)
                        await mark_as_sent(session, user.id, f"auto_reminder_{i}")


async def send_reminder(bot: Bot, user: User, step: dict):
    """Отправляет одно напоминание"""
    message = step["message"].format(
        first_name=user.first_name or "Друг"
    )

    # Формируем клавиатуру
    keyboard = None
    if step.get("buttons"):
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        buttons = []
        for btn in step["buttons"]:
            if btn.get("url"):
                buttons.append([InlineKeyboardButton(
                    text=btn["text"],
                    url=btn["url"]
                )])
            else:
                buttons.append([InlineKeyboardButton(
                    text=btn["text"],
                    callback_data=btn["callback"]
                )])
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    try:
        await bot.send_message(
            chat_id=user.telegram_id,
            text=message,
            reply_markup=keyboard
        )
    except Exception as e:
        print(f"Ошибка отправки напоминания {user.telegram_id}: {e}")


def setup_reminder_scheduler(bot: Bot):
    """Настраивает расписание"""
    scheduler.add_job(
        send_scheduled_reminders,
        'interval',
        hours=1,  # Проверяем каждый час
        args=[bot],
        id='send_reminders'
    )
    scheduler.start()
```

---

### 2.3 Сбор контактов
**Файл:** `curator_bot/handlers/contact_collector.py` (новый)
**Время:** 3-4 часа

```python
"""
Сбор контактов (телефон, email) для дожима
"""
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

router = Router(name="contact_collector")


class ContactStates(StatesGroup):
    waiting_phone = State()
    waiting_email = State()


@router.callback_query(F.data == "collect_contact")
async def start_contact_collection(callback: CallbackQuery, state: FSMContext):
    """Начинаем сбор контакта"""
    await callback.message.edit_text(
        "📱 Оставь свой номер телефона — пришлю полезные материалы!\n\n"
        "Формат: +79XXXXXXXXX",
    )
    await state.set_state(ContactStates.waiting_phone)


@router.message(ContactStates.waiting_phone)
async def process_phone(message: Message, state: FSMContext):
    """Обработка введённого телефона"""
    phone = message.text.strip()

    # Простая валидация
    if not phone.startswith("+") or len(phone) < 10:
        await message.answer(
            "Похоже, номер введён неправильно.\n"
            "Попробуй в формате: +79XXXXXXXXX"
        )
        return

    # Сохраняем телефон
    await save_user_phone(message.from_user.id, phone)
    await state.clear()

    await message.answer(
        "✅ Отлично! Записал твой номер.\n\n"
        "В ближайшее время пришлю полезные материалы.\n"
        "А пока можешь задать мне любой вопрос!"
    )

    # Уведомляем владельца о горячем лиде
    await notify_owner_about_lead(message.from_user.id, phone)


async def notify_owner_about_lead(user_id: int, phone: str):
    """Уведомление владельца о новом лиде с контактом"""
    from shared.config.settings import settings
    from curator_bot.main import bot  # или передавать через контекст

    user = await get_user_by_telegram_id(user_id)

    message = f"""
🔥 НОВЫЙ ЛИД С КОНТАКТОМ!

👤 {user.first_name} (@{user.username})
📱 Телефон: {phone}

🎯 Интерес: {user.user_intent}
💊 Боль: {user.pain_point}
📊 Шаг воронки: {user.funnel_step}

👉 Telegram: tg://user?id={user.telegram_id}
"""

    for admin_id in settings.admin_telegram_ids:
        try:
            await bot.send_message(admin_id, message)
        except:
            pass
```

---

### 2.4 Уведомления о горячих лидах
**Файл:** `curator_bot/notifications/lead_alerts.py` (новый)
**Время:** 2-3 часа

```python
"""
Система уведомлений о горячих лидах
"""
from aiogram import Bot
from shared.config.settings import settings


async def notify_hot_lead(bot: Bot, user_data: dict, trigger: str):
    """
    Уведомляет владельца (или партнёра) о горячем лиде

    Триггеры:
    - contact_left: оставил телефон/email
    - link_clicked: кликнул на ссылку заказа
    - high_engagement: много взаимодействий
    - registration_started: начал регистрацию партнёра
    """

    trigger_labels = {
        "contact_left": "📱 ОСТАВИЛ КОНТАКТ",
        "link_clicked": "🛒 КЛИКНУЛ ЗАКАЗАТЬ",
        "high_engagement": "🔥 ВЫСОКАЯ АКТИВНОСТЬ",
        "registration_started": "📝 НАЧАЛ РЕГИСТРАЦИЮ",
    }

    message = f"""
{trigger_labels.get(trigger, "🔔 НОВЫЙ ЛИД")}

👤 Имя: {user_data.get('first_name', 'Неизвестно')}
📱 Username: @{user_data.get('username', 'нет')}
📞 Телефон: {user_data.get('phone', 'не оставил')}

🎯 Интерес: {user_data.get('user_intent', '?')}
💊 Боль: {user_data.get('pain_point', '?')}
💰 Цель дохода: {user_data.get('income_goal', '?')}

📊 Шагов воронки: {user_data.get('funnel_step', 0)}
⏰ Время в воронке: {user_data.get('time_in_funnel', '?')}

💬 Написать: tg://user?id={user_data.get('telegram_id')}
"""

    # Определяем кому отправлять
    # Если лид пришёл от партнёра — отправляем партнёру
    recipient_id = user_data.get('parent_partner_telegram_id')
    if not recipient_id:
        # Иначе — владельцу системы
        recipient_id = settings.admin_telegram_ids[0] if settings.admin_telegram_ids else None

    if recipient_id:
        try:
            await bot.send_message(recipient_id, message)
        except Exception as e:
            print(f"Ошибка отправки уведомления: {e}")
```

---

## Чеклист Фазы 2

- [ ] Создать цепочки прогрева для всех путей (weight, energy, health, beauty, business)
- [ ] Реализовать scheduler для автонапоминаний
- [ ] Добавить сбор контактов (телефон)
- [ ] Настроить уведомления о горячих лидах
- [ ] Создать миграцию для новых полей
- [ ] Протестировать полный цикл с напоминаниями
- [ ] Задеплоить на VPS

**Время на Фазу 2:** 15-20 часов
**Результат:** Полноценная автоворонка с дожимом

---

# ФАЗА 3: Мультипартнёрский режим (Недели 5-6)

## Цель фазы
Партнёры могут использовать бота со своими реферальными ссылками

## Задачи

### 3.1 Регистрация партнёра-лидера
**Файл:** `curator_bot/handlers/partner_registration.py` (новый)
**Время:** 5-6 часов

```python
"""
Регистрация партнёров-лидеров (тех, кто будет использовать бота для своей команды)
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

router = Router(name="partner_registration")


class PartnerRegStates(StatesGroup):
    waiting_nl_id = State()
    waiting_confirmation = State()


@router.message(Command("become_leader"))
async def cmd_become_leader(message: Message, state: FSMContext):
    """Команда для регистрации как партнёр-лидер"""

    # Проверяем, не является ли уже лидером
    user = await get_user(message.from_user.id)
    if user and user.is_partner_leader:
        await message.answer(
            "Ты уже зарегистрирован как партнёр-лидер!\n\n"
            "Используй /my_stats для просмотра статистики."
        )
        return

    await message.answer(
        "🎯 Регистрация партнёра-лидера\n\n"
        "Это даст тебе:\n"
        "• Все лиды с твоих Reels будут получать ТВОИ реферальные ссылки\n"
        "• Статистика по твоим лидам\n"
        "• Уведомления о горячих лидах\n\n"
        "Для регистрации мне нужен твой ID партнёра NL.\n"
        "Его можно найти в личном кабинете NL.\n\n"
        "Введи свой ID партнёра (например: 12345678):"
    )
    await state.set_state(PartnerRegStates.waiting_nl_id)


@router.message(PartnerRegStates.waiting_nl_id)
async def process_nl_id(message: Message, state: FSMContext):
    """Обработка введённого NL ID"""
    nl_id = message.text.strip()

    # Простая валидация
    if not nl_id.isdigit() or len(nl_id) < 5:
        await message.answer(
            "Похоже, ID введён неправильно.\n"
            "ID партнёра — это числовой код из личного кабинета NL.\n\n"
            "Попробуй ещё раз:"
        )
        return

    await state.update_data(nl_id=nl_id)

    await message.answer(
        f"ID партнёра: {nl_id}\n\n"
        f"Подтверждаешь регистрацию?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Да, подтверждаю", callback_data="confirm_partner_reg")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_partner_reg")]
        ])
    )
    await state.set_state(PartnerRegStates.waiting_confirmation)


@router.callback_query(F.data == "confirm_partner_reg", PartnerRegStates.waiting_confirmation)
async def confirm_registration(callback: CallbackQuery, state: FSMContext):
    """Подтверждение регистрации"""
    data = await state.get_data()
    nl_id = data.get("nl_id")

    # Сохраняем в БД
    await register_partner_leader(
        telegram_id=callback.from_user.id,
        nl_partner_id=nl_id
    )

    await state.clear()

    await callback.message.edit_text(
        "✅ Отлично! Ты зарегистрирован как партнёр-лидер!\n\n"
        "Теперь все лиды, которые придут по твоим ссылкам, "
        "будут получать реферальные ссылки с ТВОИМ ID.\n\n"
        "📊 Твои команды:\n"
        "/my_stats — статистика по лидам\n"
        "/my_leads — список твоих лидов\n"
        "/my_link — твоя ссылка на бота\n\n"
        "Используй эту ссылку в своих Reels!"
    )


async def register_partner_leader(telegram_id: int, nl_partner_id: str):
    """Регистрирует пользователя как партнёра-лидера"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()

        if user:
            user.is_partner_leader = True
            user.nl_partner_id = nl_partner_id
            await session.commit()
```

---

### 3.2 Привязка лида к партнёру
**Файл:** `curator_bot/handlers/commands.py` (обновление)
**Время:** 3-4 часа

```python
# Обновляем /start для поддержки deep links

@router.message(CommandStart(deep_link=True))
async def cmd_start_with_ref(message: Message, command: CommandObject):
    """
    /start с реферальной ссылкой
    Формат: /start ref_TELEGRAM_ID_ПАРТНЁРА
    """
    args = command.args

    if args and args.startswith("ref_"):
        partner_telegram_id = args.replace("ref_", "")

        # Привязываем лида к партнёру
        await link_lead_to_partner(
            lead_telegram_id=message.from_user.id,
            partner_telegram_id=int(partner_telegram_id)
        )

    # Дальше — обычная логика /start
    # ...


async def link_lead_to_partner(lead_telegram_id: int, partner_telegram_id: int):
    """Привязывает лида к партнёру"""
    async with AsyncSessionLocal() as session:
        # Находим партнёра
        partner_result = await session.execute(
            select(User).where(
                and_(
                    User.telegram_id == partner_telegram_id,
                    User.is_partner_leader == True
                )
            )
        )
        partner = partner_result.scalar_one_or_none()

        if not partner:
            return  # Партнёр не найден

        # Находим или создаём лида
        lead_result = await session.execute(
            select(User).where(User.telegram_id == lead_telegram_id)
        )
        lead = lead_result.scalar_one_or_none()

        if lead and not lead.parent_partner_id:
            # Привязываем только если ещё не привязан
            lead.parent_partner_id = partner.id
            await session.commit()
```

---

### 3.3 Панель партнёра
**Файл:** `curator_bot/handlers/partner_panel.py` (новый)
**Время:** 5-6 часов

```python
"""
Панель партнёра-лидера: статистика, лиды, ссылки
"""
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from datetime import datetime, timedelta

router = Router(name="partner_panel")


@router.message(Command("my_stats"))
async def cmd_my_stats(message: Message):
    """Статистика партнёра"""
    user = await get_user(message.from_user.id)

    if not user or not user.is_partner_leader:
        await message.answer(
            "Эта команда доступна только для партнёров-лидеров.\n"
            "Используй /become_leader для регистрации."
        )
        return

    # Получаем статистику
    stats = await get_partner_stats(user.id)

    await message.answer(f"""
📊 Твоя статистика

За сегодня:
├── Новых лидов: {stats['today']['leads']}
├── Выбрали продукт: {stats['today']['showed_product']}
├── Кликнули "Заказать": {stats['today']['clicked_order']}
└── Оставили контакт: {stats['today']['left_contact']}

За неделю:
├── Новых лидов: {stats['week']['leads']}
├── Конверсия в клик: {stats['week']['click_rate']}%
└── Оставили контакт: {stats['week']['left_contact']}

За всё время:
├── Всего лидов: {stats['total']['leads']}
├── Заказов (примерно): {stats['total']['estimated_orders']}
└── Потенциальный ГО: {stats['total']['estimated_pv']} PV

🔥 Горячие лиды (требуют внимания): {stats['hot_leads']}
""")


@router.message(Command("my_leads"))
async def cmd_my_leads(message: Message):
    """Список лидов партнёра"""
    user = await get_user(message.from_user.id)

    if not user or not user.is_partner_leader:
        await message.answer("Команда доступна только для партнёров-лидеров.")
        return

    leads = await get_partner_leads(user.id, limit=20)

    if not leads:
        await message.answer("У тебя пока нет лидов. Поделись своей ссылкой!")
        return

    text = "👥 Твои последние лиды:\n\n"

    for lead in leads:
        status_emoji = {
            "new": "🆕",
            "warming": "🔥",
            "contacted": "📞",
            "ordered": "✅",
            "partner": "🤝"
        }.get(lead.lead_status, "❓")

        text += f"{status_emoji} {lead.first_name or 'Без имени'}"
        if lead.username:
            text += f" (@{lead.username})"
        if lead.phone:
            text += f" 📱"
        text += f" — {lead.pain_point or lead.user_intent or '?'}\n"

    text += f"\n📊 Всего лидов: {await count_partner_leads(user.id)}"

    await message.answer(text)


@router.message(Command("my_link"))
async def cmd_my_link(message: Message):
    """Ссылка партнёра на бота"""
    user = await get_user(message.from_user.id)

    if not user or not user.is_partner_leader:
        await message.answer("Команда доступна только для партнёров-лидеров.")
        return

    bot_username = (await message.bot.get_me()).username
    ref_link = f"https://t.me/{bot_username}?start=ref_{user.telegram_id}"

    await message.answer(f"""
🔗 Твоя реферальная ссылка на бота:

{ref_link}

Используй эту ссылку в своих Reels, Stories, и постах.

Все, кто перейдёт по ней, будут получать ссылки на заказ с ТВОИМ ID партнёра NL.

📋 Для копирования — просто нажми на ссылку.
""")


async def get_partner_stats(partner_id: int) -> dict:
    """Собирает статистику партнёра"""
    async with AsyncSessionLocal() as session:
        now = datetime.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=7)

        # Лиды за сегодня
        today_leads = await session.execute(
            select(func.count(User.id)).where(
                and_(
                    User.parent_partner_id == partner_id,
                    User.created_at >= today_start
                )
            )
        )

        # ... аналогично для других метрик ...

        return {
            "today": {
                "leads": today_leads.scalar() or 0,
                "showed_product": 0,  # TODO: из funnel_events
                "clicked_order": 0,
                "left_contact": 0,
            },
            "week": {
                "leads": 0,
                "click_rate": 0,
                "left_contact": 0,
            },
            "total": {
                "leads": 0,
                "estimated_orders": 0,
                "estimated_pv": 0,
            },
            "hot_leads": 0,
        }
```

---

## Чеклист Фазы 3

- [ ] Реализовать `/become_leader` для регистрации партнёров
- [ ] Обновить `/start` для поддержки deep links с реферальным кодом
- [ ] Создать панель партнёра: `/my_stats`, `/my_leads`, `/my_link`
- [ ] Обновить логику генерации реф. ссылок (использовать ID партнёра)
- [ ] Добавить уведомления партнёру о его лидах
- [ ] Создать миграцию для новых полей
- [ ] Протестировать полный цикл: партнёр → его ссылка → лид → заказ
- [ ] Задеплоить на VPS

**Время на Фазу 3:** 15-18 часов
**Результат:** Партнёры могут использовать бота для своих команд

---

# ФАЗА 4: Обучение и запуск (Недели 7-8)

## Цель фазы
Создать обучающие материалы и запустить систему с первыми 5 партнёрами

## Задачи

### 4.1 Обучающие материалы в боте
**Файл:** `curator_bot/handlers/training.py` (новый)
**Время:** 4-5 часов

```python
"""
Обучение для партнёров-лидеров
"""
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command

router = Router(name="training")


@router.message(Command("training"))
async def cmd_training(message: Message):
    """Обучение для партнёров"""
    user = await get_user(message.from_user.id)

    if not user or not user.is_partner_leader:
        await message.answer("Обучение доступно только для партнёров-лидеров.")
        return

    await message.answer("""
🎓 ОБУЧЕНИЕ: Как использовать систему

Выбери тему:
""",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📱 Как снимать Reels", callback_data="train_reels")],
            [InlineKeyboardButton(text="🔗 Как использовать бота", callback_data="train_bot")],
            [InlineKeyboardButton(text="📊 Как читать статистику", callback_data="train_stats")],
            [InlineKeyboardButton(text="🔥 Как работать с лидами", callback_data="train_leads")],
        ])
    )


# Контент обучения
TRAINING_CONTENT = {
    "train_reels": """
📱 КАК СНИМАТЬ REELS ДЛЯ ВОРОНКИ

1️⃣ ФОРМУЛА УСПЕШНОГО REELS:
• Хук (первые 2 секунды) — цепляем внимание
• Боль/Проблема — то, что волнует аудиторию
• Решение — намёк на решение
• CTA — "Ссылка в описании" или "Напиши мне"

2️⃣ ТЕМЫ, КОТОРЫЕ РАБОТАЮТ:
• "3 причины, почему ты устаёшь к обеду"
• "Почему диеты не работают (и что работает)"
• "Один продукт, который изменил моё утро"
• "Как я зарабатываю из дома [сумма]/мес"

3️⃣ ВАЖНЫЕ ПРАВИЛА:
• Снимай при хорошем свете
• Говори в камеру, смотри в объектив
• Длина: 15-30 секунд оптимально
• Текст на экране дублирует речь
• Музыка — трендовая из библиотеки

4️⃣ CTA (призыв к действию):
• "Напиши 'хочу' в комментарии"
• "Переходи по ссылке в профиле"
• "Подписывайся, расскажу больше"

📎 Шаблоны текстов — /reels_templates
""",

    "train_bot": """
🔗 КАК ИСПОЛЬЗОВАТЬ БОТА

1️⃣ ТВОЯ ССЫЛКА:
Получи командой /my_link
Эту ссылку вставляй везде:
• В описание профиля Instagram
• В Linktree или Taplink
• В описание к Reels
• В Stories ("ссылка в профиле")

2️⃣ ЧТО ПРОИСХОДИТ:
1. Человек кликает по ссылке
2. Попадает в бота
3. Бот квалифицирует (клиент/бизнес)
4. Бот прогревает (цепочка сообщений)
5. Бот даёт ссылку на заказ С ТВОИМ ID
6. Ты получаешь комиссию!

3️⃣ ТВОЯ ЗАДАЧА:
• Создавать контент (Reels)
• Направлять трафик в бота
• Обрабатывать горячих лидов (кто оставил контакт)

4️⃣ КОМАНДЫ:
/my_stats — твоя статистика
/my_leads — список лидов
/my_link — твоя ссылка

Бот делает 80% работы. Тебе нужен только контент.
""",

    "train_stats": """
📊 КАК ЧИТАТЬ СТАТИСТИКУ

/my_stats показывает:

📈 ВОРОНКА:
• Лиды — сколько людей начали диалог
• Показан продукт — дошли до рекомендации
• Клик "Заказать" — кликнули по ссылке
• Оставил контакт — дали телефон

📊 КОНВЕРСИИ:
• Хорошая конверсия в клик: 15-25%
• Хорошая конверсия в контакт: 5-15%
• Примерная конверсия в заказ: 3-10%

🔥 ГОРЯЧИЕ ЛИДЫ:
Это люди, которые:
• Оставили телефон
• Много раз кликали
• Задавали вопросы

С ними нужно связаться лично!

💡 СОВЕТ:
Следи за конверсией "Лид → Клик".
Если меньше 10% — проблема в контенте или целевой аудитории.
""",

    "train_leads": """
🔥 КАК РАБОТАТЬ С ГОРЯЧИМИ ЛИДАМИ

1️⃣ КТО ТАКОЙ ГОРЯЧИЙ ЛИД:
• Оставил телефон
• Кликнул "Заказать" 2+ раза
• Задал конкретные вопросы
• Спросил про бизнес

2️⃣ КАК С НИМИ РАБОТАТЬ:
1. Получаешь уведомление от бота
2. Пишешь в личку (Telegram)
3. Представляешься, спрашиваешь как дела
4. Отвечаешь на вопросы
5. Помогаешь оформить заказ

3️⃣ СКРИПТ ПЕРВОГО СООБЩЕНИЯ:
"Привет, {имя}! Я видел, что ты интересовался [тема].
Есть вопросы? Могу помочь разобраться."

4️⃣ ВАЖНО:
• Отвечай быстро (в течение часа)
• Не дави, помогай
• Если не готов — оставь в покое
• Один горячий лид = потенциально 70-200 PV

📌 Горячие лиды — это 80% твоих заказов!
"""
}
```

---

### 4.2 Шаблоны Reels
**Файл:** `curator_bot/content/reels_templates.py` (новый)
**Время:** 2-3 часа

```python
"""
Шаблоны текстов для Reels
"""

REELS_TEMPLATES = {
    "weight": [
        {
            "hook": "Почему ты не худеешь, даже на диете?",
            "script": """
Потому что диеты убивают метаболизм.

Когда ты резко урезаешь калории,
организм думает, что наступил голод.

И начинает ЗАПАСАТЬ жир, а не сжигать.

Решение? Не голодать, а контролировать.
Я использую [продукт] — это 200 калорий,
но с белком и всеми витаминами.

Сытость на 4 часа, и метаболизм в порядке.

Хочешь попробовать? Ссылка в профиле.
""",
            "cta": "Напиши 'хочу' — расскажу подробнее"
        },
        {
            "hook": "Я сбросила 5 кг за месяц без спортзала",
            "script": """
И без голодания.

Секрет простой: контроль калорий + достаточно белка.

Я заменила завтрак на [продукт].
Это коктейль: 200 калорий, 25г белка.

Готовится за 2 минуты.
Сытость — до обеда.

За месяц минус 5 кг. Без срывов.

Если хочешь так же — ссылка в описании.
"""
        },
    ],

    "energy": [
        {
            "hook": "Устаёшь к обеду? Вот почему.",
            "script": """
Скорее всего, у тебя дефицит.

Нет, не сна. Дефицит нутриентов.

Железо, B-витамины, магний — это топливо для энергии.

Без них клетки буквально задыхаются.

Я начал пить [витамины] —
и забыл, что такое "не могу встать".

Проверь себя. Ссылка в профиле.
"""
        },
    ],

    "business": [
        {
            "hook": "Как я зарабатываю 50к/мес из дома",
            "script": """
Без вложений в рекламу.
Без холодных звонков.
Без впаривания друзьям.

Я создаю контент — вот такие ролики.
Люди сами приходят и спрашивают.

А дальше за меня работает AI-бот.
Он отвечает, прогревает, даёт ссылки.

Мне остаётся только получать комиссию.

Хочешь так же? Ссылка в профиле.
"""
        },
    ],
}


@router.message(Command("reels_templates"))
async def cmd_reels_templates(message: Message):
    """Шаблоны для Reels"""
    await message.answer("""
📝 ШАБЛОНЫ REELS

Выбери тему:
""",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔥 Похудение", callback_data="templates_weight")],
            [InlineKeyboardButton(text="⚡ Энергия", callback_data="templates_energy")],
            [InlineKeyboardButton(text="💼 Бизнес/Заработок", callback_data="templates_business")],
        ])
    )
```

---

### 4.3 Онбординг первых партнёров
**Время:** 5-10 часов (не код, а работа с людьми)

**Чеклист онбординга:**
1. [ ] Выбрать 5 партнёров из команды
2. [ ] Провести созвон/встречу — объяснить систему
3. [ ] Помочь каждому зарегистрироваться (`/become_leader`)
4. [ ] Убедиться, что получили ссылку (`/my_link`)
5. [ ] Помочь добавить ссылку в профиль Instagram
6. [ ] Дать задание: снять 3 Reels за неделю
7. [ ] Проверить статистику через неделю

---

## Чеклист Фазы 4

- [ ] Создать обучающие материалы в боте
- [ ] Создать шаблоны Reels для партнёров
- [ ] Записать видео-инструкцию (опционально)
- [ ] Выбрать 5 партнёров для пилота
- [ ] Провести онбординг каждого
- [ ] Мониторить первую неделю
- [ ] Собрать обратную связь
- [ ] Исправить проблемы

**Время на Фазу 4:** 15-20 часов
**Результат:** 5 партнёров активно используют систему

---

# ФАЗА 5-6: Масштабирование (Месяцы 3-12)

## Цель
Расширить до 50-200 партнёров, достичь квалификации TOP → AC1

## Ключевые метрики для отслеживания

| Метрика | Месяц 3 | Месяц 6 | Месяц 12 |
|---------|---------|---------|----------|
| Партнёров с ботами | 10-20 | 30-50 | 100-200 |
| Лидов/мес | 2,000 | 10,000 | 30,000 |
| Заказов/мес | 100-200 | 500-1,000 | 1,500-3,000 |
| Новых партнёров/мес | 30-50 | 100-200 | 300-500 |
| ГО | 15,000 PV | 50,000 PV | 200,000 PV |
| Квалификация | B2-B3 | TOP | AC1 |
| Доход | 80,000 ₽ | 200,000 ₽ | 600,000 ₽ |

## Задачи масштабирования

### Техническое масштабирование
- [ ] Upgrade VPS при нагрузке (2GB RAM)
- [ ] Мониторинг производительности
- [ ] Оптимизация запросов к AI
- [ ] Кеширование ответов бота

### Бизнес масштабирование
- [ ] Создать систему отбора партнёров
- [ ] Автоматизировать онбординг
- [ ] Создать чат поддержки партнёров
- [ ] Проводить еженедельные созвоны
- [ ] Геймификация (рейтинги, призы)

### Оптимизация конверсий
- [ ] A/B тестирование текстов
- [ ] Анализ точек отвала
- [ ] Улучшение цепочек прогрева
- [ ] Персонализация рекомендаций

---

# Сводная таблица: Весь план

| Фаза | Срок | Часы | Результат |
|------|------|------|-----------|
| **1. MVP Воронки** | Недели 1-2 | 12-15 | /start → ссылка на заказ |
| **2. Полная воронка** | Недели 3-4 | 15-20 | Прогрев + напоминания + контакты |
| **3. Мультипартнёрский** | Недели 5-6 | 15-18 | Партнёры используют систему |
| **4. Обучение и запуск** | Недели 7-8 | 15-20 | 5 партнёров активны |
| **5. Масштабирование** | Месяцы 3-6 | ongoing | 50 партнёров, TOP |
| **6. Полная сеть** | Месяцы 6-12 | ongoing | 200 партнёров, AC1 |

**Общее время разработки:** ~60-75 часов
**Время до первых результатов:** 2-4 недели
**Время до значительного дохода:** 3-6 месяцев

---

# Приложение: Структура новых файлов

```
curator_bot/
├── handlers/
│   ├── commands.py              # ОБНОВИТЬ: новый /start
│   ├── funnel_callbacks.py      # НОВЫЙ: обработчики воронки
│   ├── contact_collector.py     # НОВЫЙ: сбор контактов
│   ├── partner_registration.py  # НОВЫЙ: регистрация партнёров
│   ├── partner_panel.py         # НОВЫЙ: панель партнёра
│   └── training.py              # НОВЫЙ: обучение
│
├── funnels/
│   ├── __init__.py
│   ├── warmup_sequences.py      # НОВЫЙ: цепочки прогрева
│   └── income_calculator.py     # НОВЫЙ: расчёт дохода для бизнес-пути
│
├── config/
│   └── referral.py              # НОВЫЙ: конфигурация реф. ссылок
│
├── scheduler/
│   └── reminder_scheduler.py    # НОВЫЙ: автонапоминания
│
├── notifications/
│   └── lead_alerts.py           # НОВЫЙ: уведомления о лидах
│
├── content/
│   └── reels_templates.py       # НОВЫЙ: шаблоны для Reels
│
└── database/
    └── models.py                # ОБНОВИТЬ: новые поля

scripts/
├── migrate_funnel_phase1.py     # НОВЫЙ
├── migrate_funnel_phase2.py     # НОВЫЙ
└── migrate_funnel_phase3.py     # НОВЫЙ
```

---

# Что нужно от тебя для старта

1. **Твой ID партнёра NL** — для реферальных ссылок
2. **Ссылки на продукты** — базовый URL магазина NL
3. **Цены на продукты** — для рекомендаций
4. **5 партнёров для пилота** — кто готов тестировать

---

**Готов начать с Фазы 1?**
