"""
Обработчик событий из system_events таблицы.

Читает необработанные события и выполняет соответствующие действия.
"""
from datetime import datetime
from typing import List
from loguru import logger

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram import Bot

from shared.database.base import AsyncSessionLocal
from shared.database.models import SystemEvent


async def process_pending_events(bot: Bot):
    """
    Обработать все необработанные события для curator_bot.

    Вызывается из OnboardingScheduler каждые 30 секунд.

    Args:
        bot: Экземпляр бота для отправки сообщений
    """
    async with AsyncSessionLocal() as session:
        try:
            result = await session.execute(
                select(SystemEvent).where(
                    and_(
                        SystemEvent.processed == False,
                        or_(
                            SystemEvent.target_module == "curator",
                            SystemEvent.target_module == "all",
                            SystemEvent.target_module.is_(None)
                        ),
                        or_(
                            SystemEvent.expires_at > datetime.utcnow(),
                            SystemEvent.expires_at.is_(None)
                        )
                    )
                ).order_by(SystemEvent.created_at.asc())
            )
            events = result.scalars().all()

            if events:
                logger.info(f"Processing {len(events)} pending events for curator")

            for event in events:
                await process_event(bot, event, session)
                await mark_event_processed(session, event.id)

        except Exception as e:
            logger.error(f"Error processing pending events: {e}")


async def process_event(bot: Bot, event: SystemEvent, session: AsyncSession):
    """
    Обработать одно событие.

    Args:
        bot: Экземпляр бота
        event: Событие для обработки
        session: Сессия БД
    """
    logger.info(f"Processing event #{event.id}: {event.event_type}")

    if event.event_type == "post_published":
        await handle_post_published(bot, event, session)
    else:
        logger.warning(f"Unknown event type: {event.event_type}")


async def handle_post_published(bot: Bot, event: SystemEvent, session: AsyncSession):
    """
    Обработать событие публикации поста.

    Получает целевых пользователей на основе типа поста и отправляет уведомления.

    Args:
        bot: Экземпляр бота
        event: Событие публикации
        session: Сессия БД
    """
    from curator_bot.events.notification_service import send_post_notification

    payload = event.payload
    post_type = payload.get("post_type", "news")
    content_preview = payload.get("content_preview", "")

    # Получаем целевых пользователей (с сегментацией!)
    target_users = await get_target_users_for_post(session, post_type)

    logger.info(f"Found {len(target_users)} target users for post type '{post_type}'")

    # Отправляем уведомления
    sent_count = 0
    for user in target_users:
        try:
            await send_post_notification(bot, user, post_type, content_preview)
            sent_count += 1
        except Exception as e:
            logger.error(f"Failed to send notification to user {user.telegram_id}: {e}")

    logger.info(f"Sent {sent_count}/{len(target_users)} notifications for event #{event.id}")


async def get_target_users_for_post(session: AsyncSession, post_type: str) -> list:
    """
    Получить целевых пользователей для поста на основе его типа.

    Таргетинг:
    - product: client, curious (потенциальные покупатели)
    - tips: business (партнёры, строят бизнес)
    - motivation: cold, qualified (нужна мотивация)
    - promo: cold, qualified, hot (заинтересованные в скидках)
    - success_story, news: все активные пользователи

    Args:
        session: Сессия БД
        post_type: Тип поста

    Returns:
        Список пользователей
    """
    from curator_bot.database.models import User

    # Базовый запрос: только активные пользователи, которые не заблокировали бота
    base_query = select(User).where(
        and_(
            User.is_active == True,
            User.is_blocked == False
        )
    )

    # Сегментация по типу поста
    if post_type == "product":
        # Продукты — для клиентов и любопытных
        query = base_query.where(
            or_(
                User.user_intent == "client",
                User.user_intent == "curious",
                User.user_intent.is_(None)  # Новые пользователи тоже
            )
        )
    elif post_type == "tips":
        # Советы — для партнёров (бизнес)
        query = base_query.where(
            User.user_intent == "business"
        )
    elif post_type == "motivation":
        # Мотивация — для cold и qualified (нужна поддержка)
        query = base_query.where(
            or_(
                User.lead_status == "cold",
                User.lead_status == "qualified",
                User.lead_status.is_(None)
            )
        )
    elif post_type == "promo":
        # Акции — для всех кроме тех, кто уже клиент (hot)
        query = base_query.where(
            or_(
                User.lead_status == "cold",
                User.lead_status == "qualified",
                User.lead_status == "hot",
                User.lead_status.is_(None)
            )
        )
    else:
        # success_story, news — всем активным
        query = base_query

    result = await session.execute(query)
    return list(result.scalars().all())


async def mark_event_processed(session: AsyncSession, event_id: int):
    """
    Пометить событие как обработанное.

    Args:
        session: Сессия БД
        event_id: ID события
    """
    event = await session.get(SystemEvent, event_id)
    if event:
        event.processed = True
        event.processed_at = datetime.utcnow()
        await session.commit()
        logger.debug(f"Event #{event_id} marked as processed")
