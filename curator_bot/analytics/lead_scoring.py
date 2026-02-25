"""
Скоринг лидов для воронки продаж
"""
from datetime import datetime
from typing import List
from sqlalchemy import select, update, and_

from shared.database.base import AsyncSessionLocal
from curator_bot.database.models import User
from curator_bot.analytics.funnel_stats import calculate_lead_score
from loguru import logger


async def update_lead_score(telegram_id: int) -> int:
    """
    Обновляет скоринг лида в БД

    Args:
        telegram_id: Telegram ID пользователя

    Returns:
        Новый скор
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()

        if user:
            new_score = calculate_lead_score(user)
            user.lead_score = new_score
            await session.commit()
            return new_score

    return 0


async def update_all_lead_scores():
    """
    Обновляет скоринг для всех активных лидов

    Вызывается периодически планировщиком
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(
                and_(
                    User.is_active == True,
                    User.user_intent.isnot(None)
                )
            )
        )
        users = list(result.scalars().all())

        updated = 0
        for user in users:
            new_score = calculate_lead_score(user)
            if user.lead_score != new_score:
                user.lead_score = new_score
                updated += 1

        await session.commit()
        logger.info(f"Updated lead scores for {updated} users")


async def get_hot_leads(min_score: int = 50) -> List[User]:
    """
    Получает список горячих лидов

    Args:
        min_score: Минимальный скор для "горячего" лида

    Returns:
        Список горячих лидов
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(
                and_(
                    User.is_active == True,
                    User.lead_score >= min_score
                )
            ).order_by(User.lead_score.desc())
        )
        return list(result.scalars().all())


async def get_leads_by_status(status: str) -> List[User]:
    """
    Получает лидов по статусу

    Args:
        status: Статус лида (new, cold, qualified, hot, etc.)

    Returns:
        Список лидов
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(
                and_(
                    User.is_active == True,
                    User.lead_status == status
                )
            ).order_by(User.lead_score.desc())
        )
        return list(result.scalars().all())


async def get_leads_needing_attention() -> List[User]:
    """
    Получает лидов, требующих внимания владельца

    Критерии:
    - Горячие (score >= 50)
    - Оставили контакт
    - Активны в последние 7 дней

    Returns:
        Список лидов
    """
    from datetime import timedelta

    cutoff = datetime.utcnow() - timedelta(days=7)

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(
                and_(
                    User.is_active == True,
                    User.lead_score >= 50,
                    (User.phone.isnot(None)) | (User.email.isnot(None)),
                    User.last_activity >= cutoff
                )
            ).order_by(User.lead_score.desc())
        )
        return list(result.scalars().all())
