"""
Сбор статистики постов из Telegram
"""
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from content_manager_bot.database.models import Post, PostAnalytics
from shared.config.settings import settings

logger = logging.getLogger(__name__)


class StatsCollector:
    """Сервис сбора статистики постов из Telegram"""

    def __init__(self, bot: Bot, session: AsyncSession):
        self.bot = bot
        self.session = session

    async def collect_post_stats(self, post: Post) -> Optional[Dict[str, Any]]:
        """
        Собирает статистику для конкретного поста

        Args:
            post: Пост для сбора статистики

        Returns:
            Словарь с метриками или None при ошибке
        """
        if not post.channel_message_id:
            logger.warning(f"Пост {post.id} не имеет channel_message_id")
            return None

        # TODO: Реализовать сбор статистики через Telegram Bot API
        # Старый метод через forward_message не работает для каналов
        # Нужно использовать getChatStatistics (требует права администратора)
        # или парсить через Telethon/Pyrogram
        logger.debug(f"Сбор статистики временно отключён для поста {post.id}")
        return None

        # Старый код (не работает — group_id удалён):
        # try:
        #     message = await self.bot.forward_message(...)
        #     await message.delete()
        #     views = getattr(message, 'views', 0) or 0
        #     ... etc
        # except Exception as e:
        #     logger.error(f"Ошибка при сборе статистики для поста {post.id}: {e}")
        #     return None

    async def update_post_metrics(self, post: Post, create_snapshot: bool = True) -> bool:
        """
        Обновляет метрики поста и опционально создает снимок в PostAnalytics

        Args:
            post: Пост для обновления
            create_snapshot: Создавать ли исторический снимок

        Returns:
            True если обновление успешно
        """
        stats = await self.collect_post_stats(post)

        if not stats:
            return False

        try:
            # Сохраняем старые значения для расчета дельты
            old_views = post.views_count or 0
            old_reactions = post.reactions_count or 0

            # Обновляем метрики поста
            post.views_count = stats['views']
            post.reactions_count = stats['reactions']
            post.forwards_count = stats['forwards']
            post.reactions_breakdown = stats['reactions_breakdown']
            post.update_engagement_rate()

            # Создаем исторический снимок
            if create_snapshot and post.channel_message_id:
                snapshot = PostAnalytics(
                    post_id=post.id,
                    channel_message_id=post.channel_message_id,
                    views_count=stats['views'],
                    reactions_count=stats['reactions'],
                    forwards_count=stats['forwards'],
                    reactions_breakdown=stats['reactions_breakdown'],
                    snapshot_at=datetime.utcnow(),
                    views_delta=stats['views'] - old_views,
                    reactions_delta=stats['reactions'] - old_reactions
                )
                self.session.add(snapshot)

            await self.session.commit()
            logger.info(f"Метрики поста {post.id} обновлены успешно")
            return True

        except Exception as e:
            logger.error(f"Ошибка при обновлении метрик поста {post.id}: {e}")
            await self.session.rollback()
            return False

    async def update_all_published_posts(self) -> int:
        """
        Обновляет статистику для всех опубликованных постов

        Returns:
            Количество обновленных постов
        """
        result = await self.session.execute(
            select(Post).where(
                Post.status == "published",
                Post.channel_message_id.isnot(None)
            )
        )
        posts = result.scalars().all()

        updated_count = 0
        for post in posts:
            if await self.update_post_metrics(post, create_snapshot=True):
                updated_count += 1

        logger.info(f"Обновлено {updated_count} из {len(posts)} постов")
        return updated_count

    async def get_post_growth(self, post_id: int, hours: int = 24) -> Optional[Dict[str, int]]:
        """
        Получает прирост метрик за последние N часов

        Args:
            post_id: ID поста
            hours: Количество часов для анализа

        Returns:
            Словарь с приростом метрик
        """
        from datetime import timedelta

        cutoff_time = datetime.utcnow() - timedelta(hours=hours)

        result = await self.session.execute(
            select(PostAnalytics)
            .where(
                PostAnalytics.post_id == post_id,
                PostAnalytics.snapshot_at >= cutoff_time
            )
            .order_by(PostAnalytics.snapshot_at.asc())
        )
        snapshots = result.scalars().all()

        if len(snapshots) < 2:
            return None

        first = snapshots[0]
        last = snapshots[-1]

        return {
            'views_growth': last.views_count - first.views_count,
            'reactions_growth': last.reactions_count - first.reactions_count,
            'forwards_growth': last.forwards_count - first.forwards_count,
            'hours': hours
        }
