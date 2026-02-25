"""
Сервис для работы с онбордингом пользователей

Работает с БД для хранения прогресса.
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from curator_bot.database.models import UserOnboardingProgress, User
from shared.database.base import AsyncSessionLocal


class OnboardingService:
    """Сервис для управления прогрессом онбординга"""

    @staticmethod
    async def get_or_create_progress(user_id: int) -> UserOnboardingProgress:
        """
        Получить или создать прогресс онбординга для пользователя

        Args:
            user_id: ID пользователя в таблице users

        Returns:
            UserOnboardingProgress
        """
        async with AsyncSessionLocal() as session:
            # Ищем существующий прогресс
            result = await session.execute(
                select(UserOnboardingProgress).where(
                    UserOnboardingProgress.user_id == user_id
                )
            )
            progress = result.scalar_one_or_none()

            if not progress:
                # Создаём новый
                progress = UserOnboardingProgress(
                    user_id=user_id,
                    current_day=1,
                    completed_tasks=[],
                    started_at=datetime.utcnow(),
                    last_activity=datetime.utcnow()
                )
                session.add(progress)
                await session.commit()
                await session.refresh(progress)
                logger.info(f"Created onboarding progress for user_id={user_id}")

            return progress

    @staticmethod
    async def get_progress_by_telegram_id(telegram_id: int) -> Optional[UserOnboardingProgress]:
        """
        Получить прогресс по telegram_id

        Args:
            telegram_id: Telegram ID пользователя

        Returns:
            UserOnboardingProgress или None
        """
        async with AsyncSessionLocal() as session:
            # Сначала находим user_id
            user_result = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            user = user_result.scalar_one_or_none()

            if not user:
                return None

            # Получаем прогресс
            progress_result = await session.execute(
                select(UserOnboardingProgress).where(
                    UserOnboardingProgress.user_id == user.id
                )
            )
            return progress_result.scalar_one_or_none()

    @staticmethod
    async def mark_task_completed(telegram_id: int, task_id: str) -> bool:
        """
        Отметить задачу как выполненную

        Args:
            telegram_id: Telegram ID пользователя
            task_id: ID задачи (например: d1_catalog)

        Returns:
            True если успешно
        """
        async with AsyncSessionLocal() as session:
            # Находим user
            user_result = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            user = user_result.scalar_one_or_none()

            if not user:
                logger.warning(f"User not found for telegram_id={telegram_id}")
                return False

            # Получаем или создаём прогресс
            progress_result = await session.execute(
                select(UserOnboardingProgress).where(
                    UserOnboardingProgress.user_id == user.id
                )
            )
            progress = progress_result.scalar_one_or_none()

            if not progress:
                progress = UserOnboardingProgress(
                    user_id=user.id,
                    current_day=1,
                    completed_tasks=[],
                    started_at=datetime.utcnow(),
                    last_activity=datetime.utcnow()
                )
                session.add(progress)

            # Добавляем задачу если ещё не выполнена
            if progress.completed_tasks is None:
                progress.completed_tasks = []

            if task_id not in progress.completed_tasks:
                progress.completed_tasks = progress.completed_tasks + [task_id]
                progress.last_activity = datetime.utcnow()
                await session.commit()
                logger.info(f"Task {task_id} completed for user telegram_id={telegram_id}")
                return True

            return False

    @staticmethod
    async def advance_to_next_day(telegram_id: int) -> int:
        """
        Переход на следующий день онбординга

        Args:
            telegram_id: Telegram ID пользователя

        Returns:
            Новый номер дня
        """
        async with AsyncSessionLocal() as session:
            user_result = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            user = user_result.scalar_one_or_none()

            if not user:
                return 1

            progress_result = await session.execute(
                select(UserOnboardingProgress).where(
                    UserOnboardingProgress.user_id == user.id
                )
            )
            progress = progress_result.scalar_one_or_none()

            if not progress:
                return 1

            if progress.current_day < 7:
                progress.current_day += 1
                progress.last_activity = datetime.utcnow()
                await session.commit()
                logger.info(f"User {telegram_id} advanced to day {progress.current_day}")

            if progress.current_day >= 7:
                progress.is_completed = True
                await session.commit()

            return progress.current_day

    @staticmethod
    async def update_last_activity(telegram_id: int) -> None:
        """
        Обновить время последней активности

        Args:
            telegram_id: Telegram ID пользователя
        """
        async with AsyncSessionLocal() as session:
            user_result = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            user = user_result.scalar_one_or_none()

            if not user:
                return

            progress_result = await session.execute(
                select(UserOnboardingProgress).where(
                    UserOnboardingProgress.user_id == user.id
                )
            )
            progress = progress_result.scalar_one_or_none()

            if progress:
                progress.last_activity = datetime.utcnow()
                await session.commit()

    @staticmethod
    async def get_inactive_users(hours: int) -> List[Dict]:
        """
        Получить пользователей без активности N часов

        Args:
            hours: Количество часов неактивности

        Returns:
            Список словарей с telegram_id и hours_inactive
        """
        async with AsyncSessionLocal() as session:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)

            result = await session.execute(
                select(UserOnboardingProgress, User)
                .join(User, UserOnboardingProgress.user_id == User.id)
                .where(
                    UserOnboardingProgress.last_activity < cutoff_time,
                    UserOnboardingProgress.is_completed == False,
                    User.is_blocked == False
                )
            )

            inactive_users = []
            for progress, user in result.all():
                hours_inactive = int(
                    (datetime.utcnow() - progress.last_activity).total_seconds() / 3600
                )
                inactive_users.append({
                    "telegram_id": user.telegram_id,
                    "user_id": user.id,
                    "hours_inactive": hours_inactive,
                    "current_day": progress.current_day,
                    "last_reminder_hours": progress.last_reminder_hours
                })

            return inactive_users

    @staticmethod
    async def update_last_reminder(telegram_id: int, hours: int) -> None:
        """
        Обновить время последнего напоминания

        Args:
            telegram_id: Telegram ID пользователя
            hours: На каком пороге часов отправлено напоминание
        """
        async with AsyncSessionLocal() as session:
            user_result = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            user = user_result.scalar_one_or_none()

            if not user:
                return

            progress_result = await session.execute(
                select(UserOnboardingProgress).where(
                    UserOnboardingProgress.user_id == user.id
                )
            )
            progress = progress_result.scalar_one_or_none()

            if progress:
                progress.last_reminder_hours = hours
                await session.commit()

    @staticmethod
    async def get_user_progress_dict(telegram_id: int) -> Dict:
        """
        Получить прогресс пользователя в виде словаря

        Args:
            telegram_id: Telegram ID пользователя

        Returns:
            Dict с прогрессом
        """
        progress = await OnboardingService.get_progress_by_telegram_id(telegram_id)

        if not progress:
            return {
                "current_day": 1,
                "completed_tasks": [],
                "started_at": datetime.utcnow(),
                "last_activity": datetime.utcnow(),
                "is_completed": False
            }

        return {
            "current_day": progress.current_day,
            "completed_tasks": progress.completed_tasks or [],
            "started_at": progress.started_at,
            "last_activity": progress.last_activity,
            "is_completed": progress.is_completed
        }
