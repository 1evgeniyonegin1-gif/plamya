"""
Обработчики команд для AI-Куратора
"""
from datetime import datetime
from aiogram import Router, F
from aiogram.filters import Command, CommandStart, CommandObject
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.base import AsyncSessionLocal
from shared.config.settings import settings
from curator_bot.database.models import User, TrafficSource
from content_manager_bot.database.models import DiaryEntry
from curator_bot.ai.prompts import get_welcome_message
from curator_bot.ai.segment_styles import extract_segment_from_source, get_segment_welcome
# Кнопки убраны - диалоговый режим
# from curator_bot.funnels.keyboards import get_start_keyboard, get_main_menu_reply_keyboard
from curator_bot.analytics.funnel_stats import get_funnel_stats, format_funnel_stats
from curator_bot.analytics.lead_scoring import get_leads_needing_attention
from curator_bot.utils.webapp_keyboards import get_miniapp_keyboard, get_products_button, get_business_button, get_miniapp_reply_keyboard
from loguru import logger


router = Router(name="commands")


# ═══════════════════════════════════════════════════════════════
# FSM — Состояния дневника
# ═══════════════════════════════════════════════════════════════

class DiaryStates(StatesGroup):
    waiting_for_entry = State()


async def track_traffic_source(session: AsyncSession, source_id: str, is_new_user: bool):
    """
    Обновляет статистику источника трафика.

    Args:
        session: Сессия БД
        source_id: ID источника (channel_zozh_1, etc.)
        is_new_user: True если это новая регистрация
    """
    try:
        # Проверяем существует ли источник
        result = await session.execute(
            select(TrafficSource).where(TrafficSource.source_id == source_id)
        )
        source = result.scalar_one_or_none()

        if source:
            # Обновляем статистику
            source.total_clicks += 1
            if is_new_user:
                source.total_registrations += 1
            await session.commit()
            logger.info(f"Traffic tracked: {source_id} (new_user={is_new_user})")
        else:
            # Создаём новый источник автоматически
            new_source = TrafficSource(
                source_id=source_id,
                name=f"Auto: {source_id}",
                source_type="channel",
                total_clicks=1,
                total_registrations=1 if is_new_user else 0
            )
            session.add(new_source)
            await session.commit()
            logger.info(f"New traffic source created: {source_id}")

    except Exception as e:
        logger.error(f"Error tracking traffic source: {e}")


@router.message(CommandStart(deep_link=True))
async def cmd_start_with_source(message: Message, command: CommandObject):
    """
    Обработчик команды /start с deep link параметром.
    Пример: /start channel_zozh_1

    Используется для трекинга источников трафика из Traffic Engine.
    """
    source_id = command.args  # Получаем параметр после /start
    await _handle_start(message, source_id=source_id)


@router.message(CommandStart())
async def cmd_start(message: Message):
    """
    Обработчик команды /start без параметров.
    Регистрирует нового пользователя и начинает ДИАЛОГОВЫЙ режим (без кнопок)
    """
    await _handle_start(message, source_id=None)


async def _handle_start(message: Message, source_id: str | None = None):
    """
    Общая логика обработки /start.

    Args:
        message: Сообщение от пользователя
        source_id: ID источника трафика (channel_zozh_1, etc.) или None
    """
    try:
        async with AsyncSessionLocal() as session:
            # Проверяем, есть ли пользователь в БД
            result = await session.execute(
                select(User).where(User.telegram_id == message.from_user.id)
            )
            user = result.scalar_one_or_none()

            first_name = message.from_user.first_name or "Друг"
            is_new_user = user is None

            if not user:
                # Создаем нового пользователя
                user = User(
                    telegram_id=message.from_user.id,
                    username=message.from_user.username,
                    first_name=message.from_user.first_name,
                    last_name=message.from_user.last_name,
                    user_type="lead",
                    qualification="consultant",
                    funnel_started_at=datetime.utcnow(),
                    lead_status="new",
                    traffic_source=source_id  # Сохраняем источник трафика
                )
                session.add(user)
                await session.commit()
                logger.info(f"New user registered: {message.from_user.id} from source: {source_id}")

                # Трекинг источника трафика
                if source_id:
                    await track_traffic_source(session, source_id, is_new_user=True)

                # Создаём запись онбординга
                from curator_bot.database.models import UserOnboardingProgress

                onboarding_progress = UserOnboardingProgress(
                    user_id=user.id,
                    current_day=1,
                    completed_tasks=[],
                    started_at=datetime.utcnow(),
                    last_activity=datetime.utcnow()
                )
                session.add(onboarding_progress)
                await session.commit()
                logger.info(f"Onboarding progress created for user {message.from_user.id}")

                # Получаем чеклист для дня 1 (с inline-кнопками)
                from curator_bot.onboarding.proactive_tasks import OnboardingTasks
                tasks_text, tasks_keyboard = OnboardingTasks.format_tasks_message(day=1, completed_tasks=[])

                # ДИАЛОГОВЫЙ РЕЖИМ — приветствие (с учётом сегмента)
                segment = extract_segment_from_source(source_id)
                segment_welcome = get_segment_welcome(segment) if segment else None

                if segment_welcome:
                    welcome_text = f"""Йо, {first_name}!

Я бот-куратор по NL. {segment_welcome}
Задавай вопросы — отвечу."""
                else:
                    welcome_text = f"""Йо, {first_name}!

Я бот-куратор по NL. Задавай вопросы — отвечу."""

                _is_admin = message.from_user.id in settings.admin_ids_list
                await message.answer(welcome_text, reply_markup=get_miniapp_reply_keyboard(is_admin=_is_admin))

                # Отправляем чеклист отдельным сообщением с inline-кнопками
                await message.answer(tasks_text, reply_markup=tasks_keyboard)

            else:
                # Существующий пользователь — диалоговый режим
                user.last_activity = datetime.utcnow()

                # Если пришёл по новой ссылке — обновляем источник и трекаем
                if source_id and user.traffic_source != source_id:
                    user.traffic_source = source_id
                    await track_traffic_source(session, source_id, is_new_user=False)

                await session.commit()

                welcome_text = f"""Йо, {first_name}! Рад что вернулся.

Чё надо? Продукты, бизнес, или просто поболтать?"""

                _is_admin = message.from_user.id in settings.admin_ids_list
                await message.answer(welcome_text, reply_markup=get_miniapp_reply_keyboard(is_admin=_is_admin))
                logger.info(f"Existing user returned: {message.from_user.id}")

    except Exception as e:
        logger.error(f"Error in /start command: {e}")
        await message.answer(
            "Извини, произошла ошибка при регистрации. "
            "Попробуй еще раз через несколько секунд."
        )


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Обработчик команды /help"""
    help_text = """<b>📚 Справка по AI-Куратору</b>

<b>Что я умею:</b>
✅ Отвечать на вопросы о продуктах NL
✅ Объяснять маркетинг-план и квалификации
✅ Помогать с продажами и привлечением
✅ Мотивировать и поддерживать
✅ Давать практические советы

<b>Доступные команды:</b>
/start - Начать работу с куратором
/help - Эта справка
/menu - 🚀 Меню с каталогом и бизнесом
/catalog - 🛒 Каталог продуктов NL
/business - 💼 Узнать про бизнес
/progress - Мой прогресс и статистика
/goal - Установить цель
/support - Связаться с руководителем

<b>Просто напиши мне любой вопрос!</b>
Я работаю 24/7 и всегда рад помочь 🚀"""

    await message.answer(help_text)


@router.message(Command("progress"))
async def cmd_progress(message: Message):
    """Показывает прогресс пользователя"""
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == message.from_user.id)
            )
            user = result.scalar_one_or_none()

            if not user:
                await message.answer("Сначала нажми /start для регистрации")
                return

            # Словарь квалификаций по системе NL International
            qual_names = {
                "consultant": "🌱 Консультант (3%)",
                "consultant_6": "📈 Консультант 6%",
                "manager_9": "⭐ Менеджер 9%",
                "senior_manager": "💼 Старший менеджер (12%)",
                "manager_15": "📊 Менеджер 15%",
                "director_21": "🎯 Директор 21%",
                "M1": "🔥 Middle 1",
                "M2": "🔥 Middle 2",
                "M3": "🔥 Middle 3",
                "B1": "💼 Business Partner 1",
                "B2": "💼 Business Partner 2",
                "B3": "💼 Business Partner 3",
                "TOP": "⭐ TOP",
                "TOP1": "⭐ TOP 1",
                "TOP2": "⭐ TOP 2",
                "TOP3": "⭐ TOP 3",
                "TOP4": "⭐ TOP 4",
                "TOP5": "⭐ TOP 5",
                "AC1": "👑 Ambassador Club 1",
                "AC2": "👑 Ambassador Club 2",
                "AC3": "👑 Ambassador Club 3",
                "AC4": "👑 Ambassador Club 4",
                "AC5": "👑 Ambassador Club 5",
                "AC6": "👑 Ambassador Club 6",
            }

            progress_text = f"""<b>📊 Твой прогресс</b>

<b>Текущая квалификация:</b> {qual_names.get(user.qualification, "🌱 Консультант")}
<b>Пройдено уроков:</b> 0 из 25
<b>Дней в бизнесе:</b> {(message.date - user.created_at).days}

<b>Твои достижения:</b>
🏆 Зарегистрирован в системе
"""

            if user.current_goal:
                progress_text += f"\n<b>Твоя цель:</b> {user.current_goal}"

            progress_text += "\n\n💪 Продолжай в том же духе!"

            await message.answer(progress_text)

    except Exception as e:
        logger.error(f"Error in /progress command: {e}")
        await message.answer("Произошла ошибка при получении статистики")


@router.message(Command("goal"))
async def cmd_goal(message: Message):
    """Помогает установить цель"""
    from curator_bot.ai.prompts import get_goal_setting_prompt

    await message.answer(get_goal_setting_prompt())


@router.message(Command("support"))
async def cmd_support(message: Message):
    """Связь с руководителем"""
    support_text = """<b>🆘 Техподдержка</b>

По техническим вопросам:
📧 support@example.com

По вопросам бизнеса - напиши своему руководителю.

Также ты всегда можешь задать вопрос мне!"""

    await message.answer(support_text)


@router.message(Command("funnel_stats"))
async def cmd_funnel_stats(message: Message):
    """
    Статистика воронки продаж (только для админов)
    Использование: /funnel_stats [дней]
    """
    # Проверяем права админа
    if message.from_user.id not in settings.admin_ids_list:
        await message.answer("❌ Эта команда доступна только администраторам")
        return

    try:
        # Парсим количество дней из аргументов
        args = message.text.split()
        period_days = 7  # по умолчанию
        if len(args) > 1:
            try:
                period_days = int(args[1])
                period_days = max(1, min(period_days, 365))  # Ограничиваем 1-365
            except ValueError:
                pass

        await message.answer("⏳ Собираю статистику...")

        # Получаем статистику
        stats = await get_funnel_stats(period_days)
        stats_text = format_funnel_stats(stats)

        await message.answer(stats_text)

    except Exception as e:
        logger.error(f"Error in /funnel_stats command: {e}", exc_info=True)
        await message.answer("❌ Ошибка при получении статистики")


@router.message(Command("hot_leads"))
async def cmd_hot_leads(message: Message):
    """
    Список горячих лидов (только для админов)
    """
    # Проверяем права админа
    if message.from_user.id not in settings.admin_ids_list:
        await message.answer("❌ Эта команда доступна только администраторам")
        return

    try:
        leads = await get_leads_needing_attention()

        if not leads:
            await message.answer("🔍 Горячих лидов, требующих внимания, нет")
            return

        intent_names = {
            "client": "Клиент",
            "business": "Бизнес",
        }

        response = f"🔥 <b>ГОРЯЧИЕ ЛИДЫ ({len(leads)})</b>\n\n"

        for i, lead in enumerate(leads[:10], 1):  # Максимум 10
            contact = lead.phone or lead.email or "нет контакта"
            intent = intent_names.get(lead.user_intent, lead.user_intent or "-")

            response += f"""{i}. <b>{lead.first_name or 'Без имени'}</b>
   📞 {contact}
   🎯 {intent} | Скор: {lead.lead_score}
   👉 @{lead.username or f'id{lead.telegram_id}'}

"""

        if len(leads) > 10:
            response += f"\n<i>...и ещё {len(leads) - 10} лидов</i>"

        await message.answer(response)

    except Exception as e:
        logger.error(f"Error in /hot_leads command: {e}", exc_info=True)
        await message.answer("❌ Ошибка при получении списка лидов")


@router.message(Command("stats_traffic"))
async def cmd_stats_traffic(message: Message):
    """
    Статистика источников трафика (Traffic Engine).
    Только для админов.

    Показывает:
    - Все источники трафика
    - Клики, регистрации, конверсии
    - Сортировка по регистрациям
    """
    if message.from_user.id not in settings.admin_ids_list:
        await message.answer("❌ Эта команда доступна только администраторам")
        return

    try:
        async with AsyncSessionLocal() as session:
            # Получаем все источники, сортируем по регистрациям
            result = await session.execute(
                select(TrafficSource)
                .where(TrafficSource.is_active == True)
                .order_by(TrafficSource.total_registrations.desc())
            )
            sources = result.scalars().all()

            if not sources:
                await message.answer(
                    "📊 <b>Traffic Engine — Статистика</b>\n\n"
                    "Пока нет данных.\n\n"
                    "Создай источник командой:\n"
                    "<code>/add_traffic_source channel_zozh_1 \"ЗОЖ канал Марины\"</code>"
                )
                return

            # Считаем общие показатели
            total_clicks = sum(s.total_clicks for s in sources)
            total_regs = sum(s.total_registrations for s in sources)
            total_partners = sum(s.total_partners for s in sources)

            response = f"""📊 <b>Traffic Engine — Статистика</b>

<b>Общие показатели:</b>
👆 Кликов: {total_clicks}
👤 Регистраций: {total_regs}
🤝 Партнёров: {total_partners}
📈 Конверсия клик→рег: {round(total_regs / total_clicks * 100, 1) if total_clicks > 0 else 0}%

<b>По источникам:</b>
"""

            for source in sources[:15]:  # Максимум 15
                conv = source.conversion_rate
                partner_rate = source.partner_rate
                segment_emoji = {
                    "zozh": "🥗",
                    "mama": "👶",
                    "business": "💼",
                }.get(source.segment, "📢")

                response += f"""
{segment_emoji} <b>{source.name}</b>
   ID: <code>{source.source_id}</code>
   👆 {source.total_clicks} → 👤 {source.total_registrations} ({conv}%)
"""

            if len(sources) > 15:
                response += f"\n<i>...и ещё {len(sources) - 15} источников</i>"

            response += "\n\n💡 Ссылка: <code>t.me/nl_curator_bot?start=SOURCE_ID</code>"

            await message.answer(response)

    except Exception as e:
        logger.error(f"Error in /stats_traffic command: {e}", exc_info=True)
        await message.answer("❌ Ошибка при получении статистики трафика")


@router.message(Command("add_traffic_source"))
async def cmd_add_traffic_source(message: Message):
    """
    Добавить новый источник трафика.
    Только для админов.

    Использование: /add_traffic_source source_id "Название" [segment]
    Пример: /add_traffic_source channel_zozh_1 "ЗОЖ канал Марины" zozh
    """
    if message.from_user.id not in settings.admin_ids_list:
        await message.answer("❌ Эта команда доступна только администраторам")
        return

    try:
        # Парсим аргументы
        text = message.text.replace("/add_traffic_source", "").strip()
        if not text:
            await message.answer(
                "❌ Укажи параметры:\n\n"
                "<code>/add_traffic_source source_id \"Название\" [segment]</code>\n\n"
                "Примеры:\n"
                "<code>/add_traffic_source channel_zozh_1 \"ЗОЖ канал Марины\" zozh</code>\n"
                "<code>/add_traffic_source channel_mama_1 \"Канал для мам\" mama</code>\n"
                "<code>/add_traffic_source channel_biz_1 \"Бизнес канал\" business</code>\n\n"
                "Сегменты: zozh, mama, business"
            )
            return

        # Простой парсинг: source_id "name" segment
        parts = text.split('"')
        if len(parts) < 2:
            # Попробуем без кавычек
            args = text.split()
            source_id = args[0]
            name = args[1] if len(args) > 1 else source_id
            segment = args[2] if len(args) > 2 else None
        else:
            source_id = parts[0].strip()
            name = parts[1].strip()
            segment = parts[2].strip() if len(parts) > 2 else None

        async with AsyncSessionLocal() as session:
            # Проверяем существует ли уже
            result = await session.execute(
                select(TrafficSource).where(TrafficSource.source_id == source_id)
            )
            existing = result.scalar_one_or_none()

            if existing:
                await message.answer(f"❌ Источник <code>{source_id}</code> уже существует")
                return

            # Создаём новый источник
            new_source = TrafficSource(
                source_id=source_id,
                name=name,
                source_type="channel",
                segment=segment,
                is_active=True
            )
            session.add(new_source)
            await session.commit()

            await message.answer(
                f"✅ Источник создан!\n\n"
                f"<b>ID:</b> <code>{source_id}</code>\n"
                f"<b>Название:</b> {name}\n"
                f"<b>Сегмент:</b> {segment or 'не указан'}\n\n"
                f"🔗 Ссылка для канала:\n"
                f"<code>https://t.me/nl_curator_bot?start={source_id}</code>"
            )

    except Exception as e:
        logger.error(f"Error in /add_traffic_source command: {e}", exc_info=True)
        await message.answer("❌ Ошибка при создании источника")


@router.message(Command("menu"))
async def cmd_menu(message: Message):
    """
    Показывает меню с Mini App кнопками.
    Открывает доступ к каталогу продуктов и бизнес-разделу.
    """
    menu_text = """🚀 <b>Меню APEXFLOW</b>

Выбери раздел:

🛒 <b>Продукция</b> — каталог 190 продуктов NL с ценами и фото

💼 <b>Бизнес</b> — узнай как зарабатывать с системой автоматизации"""

    _is_admin = message.from_user.id in settings.admin_ids_list
    await message.answer(menu_text, reply_markup=get_miniapp_reply_keyboard(is_admin=_is_admin))


@router.message(Command("catalog"))
async def cmd_catalog(message: Message):
    """
    Открывает каталог продуктов NL.
    """
    catalog_text = """🛒 <b>Каталог продуктов NL International</b>

190 продуктов в 28 категориях:
• Функциональное питание
• БАДы и витамины
• Косметика и уход
• Детская линейка

Нажми кнопку чтобы открыть каталог 👇"""

    await message.answer(catalog_text, reply_markup=get_products_button())


@router.message(Command("business"))
async def cmd_business(message: Message):
    """
    Открывает бизнес-раздел с моделью APEXFLOW.
    """
    business_text = """💼 <b>Бизнес с APEXFLOW</b>

Узнай как автоматизировать сетевой бизнес:

🤖 <b>Traffic Engine</b> — боты комментируют за тебя
✨ <b>AI-Контент</b> — посты генерируются автоматически
🎯 <b>AI-Куратор</b> — прогрев лидов 24/7

Нажми кнопку чтобы узнать больше 👇"""

    await message.answer(business_text, reply_markup=get_business_button())


# ═══════════════════════════════════════════════════════════════
# ДНЕВНИК АДМИНА — /diary
# ═══════════════════════════════════════════════════════════════

def _diary_menu_keyboard() -> InlineKeyboardMarkup:
    """Inline-клавиатура меню дневника"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✍️ Новая запись", callback_data="diary:new"),
        InlineKeyboardButton(text="📖 Последние", callback_data="diary:recent"),
    )
    return builder.as_markup()


def _diary_after_save_keyboard() -> InlineKeyboardMarkup:
    """Inline-клавиатура после сохранения записи"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✍️ Ещё запись", callback_data="diary:new"),
        InlineKeyboardButton(text="📖 Все записи", callback_data="diary:recent"),
    )
    return builder.as_markup()


@router.message(F.text == "📓 Дневник")
async def btn_diary(message: Message):
    """Обработчик кнопки '📓 Дневник' из reply-клавиатуры"""
    await cmd_diary(message)


@router.message(Command("diary"))
async def cmd_diary(message: Message):
    """Команда /diary — меню дневника (только для админов)"""
    if message.from_user.id not in settings.admin_ids_list:
        await message.answer("❌ Команда доступна только администраторам")
        return

    # Считаем количество записей
    async with AsyncSessionLocal() as session:
        count_result = await session.execute(
            select(func.count(DiaryEntry.id))
            .where(DiaryEntry.admin_id == message.from_user.id)
        )
        total = count_result.scalar() or 0

    await message.answer(
        f"📓 <b>Дневник</b>\n\n"
        f"Записей: {total}\n\n"
        f"Записи дневника используются AI для генерации постов и ответов куратора.",
        reply_markup=_diary_menu_keyboard()
    )


@router.callback_query(F.data == "diary:new")
async def callback_diary_new(callback: CallbackQuery, state: FSMContext):
    """Начало создания новой записи дневника"""
    if callback.from_user.id not in settings.admin_ids_list:
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    await callback.answer()
    await callback.message.edit_text(
        "📓 <b>Новая запись</b>\n\n"
        "Напиши что произошло, о чём думаешь, идеи — что угодно.\n"
        "Отправь текст следующим сообщением.",
    )
    await state.set_state(DiaryStates.waiting_for_entry)


@router.message(DiaryStates.waiting_for_entry)
async def process_diary_entry(message: Message, state: FSMContext):
    """Сохранение записи дневника (FSM)"""
    if message.from_user.id not in settings.admin_ids_list:
        await state.clear()
        return

    text = message.text
    if not text or len(text.strip()) < 10:
        await message.answer("Слишком коротко — напиши хотя бы пару предложений.")
        return

    async with AsyncSessionLocal() as session:
        entry = DiaryEntry(
            admin_id=message.from_user.id,
            entry_text=text.strip()
        )
        session.add(entry)
        await session.commit()
        await session.refresh(entry)
        entry_id = entry.id

    await state.clear()
    logger.info(f"[DIARY] New entry #{entry_id} by admin {message.from_user.id} ({len(text)} chars)")

    await message.answer(
        f"✅ Записано! Запись #{entry_id}\n\n"
        f"<i>{text[:200]}{'...' if len(text) > 200 else ''}</i>",
        reply_markup=_diary_after_save_keyboard()
    )


@router.callback_query(F.data == "diary:recent")
async def callback_diary_recent(callback: CallbackQuery):
    """Показ последних записей дневника"""
    if callback.from_user.id not in settings.admin_ids_list:
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    await callback.answer()

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(DiaryEntry)
            .where(DiaryEntry.admin_id == callback.from_user.id)
            .order_by(DiaryEntry.created_at.desc())
            .limit(5)
        )
        entries = result.scalars().all()

    if not entries:
        await callback.message.edit_text(
            "📓 Дневник пуст. Напиши первую запись!",
            reply_markup=_diary_menu_keyboard()
        )
        return

    text = "📓 <b>Последние записи:</b>\n\n"
    for entry in entries:
        date_str = entry.created_at.strftime("%d.%m %H:%M")
        preview = entry.entry_text[:150]
        if len(entry.entry_text) > 150:
            preview += "..."
        text += f"<b>#{entry.id}</b> [{date_str}]\n<i>{preview}</i>\n\n"

    # Кнопки: новая запись + удалить
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✍️ Новая запись", callback_data="diary:new"),
    )
    # Кнопка удаления последней записи
    if entries:
        builder.row(
            InlineKeyboardButton(
                text=f"🗑 Удалить #{entries[0].id}",
                callback_data=f"diary:delete:{entries[0].id}"
            ),
        )

    await callback.message.edit_text(text, reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith("diary:delete:"))
async def callback_diary_delete(callback: CallbackQuery):
    """Удаление записи дневника"""
    if callback.from_user.id not in settings.admin_ids_list:
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    entry_id = int(callback.data.split(":")[2])

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(DiaryEntry)
            .where(DiaryEntry.id == entry_id)
            .where(DiaryEntry.admin_id == callback.from_user.id)
        )
        entry = result.scalar_one_or_none()

        if not entry:
            await callback.answer("Запись не найдена", show_alert=True)
            return

        await session.delete(entry)
        await session.commit()

    logger.info(f"[DIARY] Entry #{entry_id} deleted by admin {callback.from_user.id}")
    await callback.answer(f"Запись #{entry_id} удалена")

    # Обновляем список
    await callback_diary_recent(callback)
