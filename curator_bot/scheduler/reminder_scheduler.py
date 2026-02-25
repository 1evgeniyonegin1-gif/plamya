"""
Планировщик напоминаний для воронки продаж

Отправляет напоминания неактивным пользователям:
- Через 24 часа неактивности
- Через 48 часов (со скидкой)
- Через 7 дней (финальное)
"""
from datetime import datetime, timedelta
from typing import List
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select, and_
from aiogram import Bot

from shared.database.base import AsyncSessionLocal
from shared.config.settings import settings
from curator_bot.database.models import User
from curator_bot.funnels.messages import (
    get_reminder_24h,
    get_reminder_48h,
    get_reminder_7d,
)
from curator_bot.funnels.keyboards import get_reminder_response_keyboard
from curator_bot.funnels.referral_links import get_shop_link
from loguru import logger


# Глобальный scheduler
scheduler: AsyncIOScheduler = None
bot_instance: Bot = None


async def get_inactive_users(hours: int, exclude_statuses: List[str] = None) -> List[User]:
    """
    Получает пользователей, неактивных указанное количество часов

    Args:
        hours: Количество часов неактивности
        exclude_statuses: Статусы лидов для исключения

    Returns:
        Список неактивных пользователей
    """
    if exclude_statuses is None:
        exclude_statuses = ["ordered", "partner", "inactive"]

    cutoff_time = datetime.utcnow() - timedelta(hours=hours)
    min_time = datetime.utcnow() - timedelta(hours=hours + 24)  # Не старше чем hours+24

    async with AsyncSessionLocal() as session:
        query = select(User).where(
            and_(
                User.last_activity.isnot(None),
                User.last_activity <= cutoff_time,
                User.last_activity >= min_time,  # Только в окне напоминания
                User.is_active == True,
                User.is_blocked == False,
                User.user_intent.isnot(None),  # Только прошедшие квалификацию
                ~User.lead_status.in_(exclude_statuses)
            )
        )
        result = await session.execute(query)
        return list(result.scalars().all())


async def send_reminder_24h(user: User):
    """Отправляет напоминание через 24 часа"""
    if not bot_instance:
        return

    try:
        message = get_reminder_24h(
            first_name=user.first_name or "Друг",
            pain_point=user.pain_point or "weight"
        )

        await bot_instance.send_message(
            chat_id=user.telegram_id,
            text=message,
            reply_markup=get_reminder_response_keyboard()
        )

        logger.info(f"Sent 24h reminder to user {user.telegram_id}")

    except Exception as e:
        logger.error(f"Failed to send 24h reminder to {user.telegram_id}: {e}")


async def send_reminder_48h(user: User):
    """Отправляет напоминание через 48 часов со скидкой"""
    if not bot_instance:
        return

    try:
        message = get_reminder_48h(
            first_name=user.first_name or "Друг",
            product_link=get_shop_link()
        )

        await bot_instance.send_message(
            chat_id=user.telegram_id,
            text=message,
            reply_markup=get_reminder_response_keyboard(),
            disable_web_page_preview=True
        )

        logger.info(f"Sent 48h reminder to user {user.telegram_id}")

    except Exception as e:
        logger.error(f"Failed to send 48h reminder to {user.telegram_id}: {e}")


async def send_reminder_7d(user: User):
    """Отправляет финальное напоминание через 7 дней"""
    if not bot_instance:
        return

    try:
        message = get_reminder_7d(
            first_name=user.first_name or "Друг",
            pain_point=user.pain_point or "weight"
        )

        await bot_instance.send_message(
            chat_id=user.telegram_id,
            text=message,
            reply_markup=get_reminder_response_keyboard()
        )

        # Помечаем как неактивного после финального напоминания
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == user.telegram_id)
            )
            db_user = result.scalar_one_or_none()
            if db_user:
                db_user.lead_status = "inactive"
                await session.commit()

        logger.info(f"Sent 7d reminder to user {user.telegram_id}")

    except Exception as e:
        logger.error(f"Failed to send 7d reminder to {user.telegram_id}: {e}")


async def check_inactive_users():
    """
    Проверяет неактивных пользователей и отправляет напоминания

    Запускается каждые 6 часов
    """
    from curator_bot.utils.quiet_hours import is_sending_allowed

    if not is_sending_allowed():
        logger.debug("Quiet hours — skipping inactive user reminders")
        return

    logger.info("Checking inactive users for reminders...")

    try:
        # 24 часа неактивности
        users_24h = await get_inactive_users(hours=24)
        for user in users_24h:
            await send_reminder_24h(user)

        # 48 часов неактивности
        users_48h = await get_inactive_users(hours=48)
        for user in users_48h:
            await send_reminder_48h(user)

        # 7 дней неактивности
        users_7d = await get_inactive_users(hours=168)
        for user in users_7d:
            await send_reminder_7d(user)

        logger.info(
            f"Reminders sent: 24h={len(users_24h)}, 48h={len(users_48h)}, 7d={len(users_7d)}"
        )

    except Exception as e:
        logger.error(f"Error checking inactive users: {e}", exc_info=True)


async def notify_hot_lead(user: User):
    """
    Отправляет уведомление владельцу о горячем лиде

    Args:
        user: Горячий лид
    """
    if not bot_instance:
        return

    try:
        admin_ids = settings.admin_ids_list

        intent_names = {
            "client": "Клиент (здоровье)",
            "business": "Бизнес",
            "curious": "Любопытный",
        }

        pain_names = {
            "weight": "Похудение",
            "energy": "Энергия",
            "immunity": "Иммунитет",
            "beauty": "Красота",
            "kids": "Дети",
            "sport": "Спорт",
        }

        income_names = {
            "10_30k": "10-30к/мес",
            "50_100k": "50-100к/мес",
            "200k_plus": "200к+/мес",
            "unsure": "Не определился",
        }

        message = f"""🔥 <b>ГОРЯЧИЙ ЛИД!</b>

👤 <b>Имя:</b> {user.first_name or 'Не указано'}
📱 <b>Телефон:</b> {user.phone or 'Не оставил'}
📧 <b>Email:</b> {user.email or 'Не оставил'}

🎯 <b>Интерес:</b> {intent_names.get(user.user_intent, user.user_intent)}
💊 <b>Боль:</b> {pain_names.get(user.pain_point, user.pain_point or '-')}
💰 <b>Цель дохода:</b> {income_names.get(user.income_goal, user.income_goal or '-')}

📊 <b>Прошёл шагов:</b> {user.funnel_step}
⏰ <b>В воронке с:</b> {user.funnel_started_at.strftime('%d.%m.%Y %H:%M') if user.funnel_started_at else '-'}

👉 <b>Telegram:</b> @{user.username or f'id{user.telegram_id}'}"""

        for admin_id in admin_ids:
            try:
                await bot_instance.send_message(
                    chat_id=admin_id,
                    text=message
                )
            except Exception as e:
                logger.error(f"Failed to notify admin {admin_id}: {e}")

        logger.info(f"Hot lead notification sent for user {user.telegram_id}")

    except Exception as e:
        logger.error(f"Error notifying hot lead: {e}")


async def check_hot_leads():
    """
    Проверяет новых горячих лидов и уведомляет владельца

    Запускается каждый час
    """
    logger.info("Checking for hot leads...")

    try:
        # Ищем горячих лидов, о которых ещё не уведомляли
        cutoff_time = datetime.utcnow() - timedelta(hours=1)

        async with AsyncSessionLocal() as session:
            query = select(User).where(
                and_(
                    User.lead_status == "hot",
                    User.lead_score >= 50,  # Достаточно горячий
                    User.last_activity >= cutoff_time,  # Активность за последний час
                )
            )
            result = await session.execute(query)
            hot_leads = list(result.scalars().all())

        for lead in hot_leads:
            await notify_hot_lead(lead)

        if hot_leads:
            logger.info(f"Notified about {len(hot_leads)} hot leads")

    except Exception as e:
        logger.error(f"Error checking hot leads: {e}", exc_info=True)


def setup_reminder_scheduler(bot: Bot) -> AsyncIOScheduler:
    """
    Настраивает и запускает планировщик напоминаний

    Args:
        bot: Экземпляр бота для отправки сообщений

    Returns:
        Настроенный планировщик
    """
    global scheduler, bot_instance

    bot_instance = bot
    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")

    # Проверка неактивных пользователей каждые 6 часов
    scheduler.add_job(
        check_inactive_users,
        trigger=IntervalTrigger(hours=6),
        id="check_inactive_users",
        name="Check inactive users and send reminders",
        replace_existing=True
    )

    # Проверка горячих лидов каждый час
    scheduler.add_job(
        check_hot_leads,
        trigger=IntervalTrigger(hours=1),
        id="check_hot_leads",
        name="Check hot leads and notify admin",
        replace_existing=True
    )

    scheduler.start()
    logger.info("✅ Reminder scheduler started")

    return scheduler


def shutdown_scheduler():
    """Останавливает планировщик"""
    global scheduler

    if scheduler:
        scheduler.shutdown(wait=False)
        logger.info("Reminder scheduler stopped")
