"""
Scheduler для автоматического мониторинга Telegram каналов.

Цикл работы (каждые 30 минут):
1. Fetch Phase - загрузка новых постов
2. Quality Assessment - оценка качества
3. RAG Sync - добавление в базу знаний
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.models import StylePost, StyleChannel
from shared.database.base import AsyncSessionLocal
from shared.config.settings import settings
from shared.style_monitor.channel_fetcher import get_style_service
from shared.style_monitor.quality_assessment import QualityAssessmentEngine
from shared.style_monitor.rag_integration import RAGIntegrationService

logger = logging.getLogger(__name__)


class ChannelMonitorScheduler:
    """Автономный scheduler для мониторинга каналов"""

    def __init__(self):
        """Инициализация scheduler"""
        self.style_service = get_style_service()
        self.quality_engine = QualityAssessmentEngine()
        self.rag_service = RAGIntegrationService()
        self.running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self):
        """Запустить scheduler в фоне"""
        if self.running:
            logger.warning("Channel Monitor Scheduler already running")
            return

        self.running = True

        # Проверяем настроен ли Telethon
        if not self.style_service.fetcher.is_configured:
            logger.warning(
                "Telethon not configured (TELETHON_API_ID/HASH missing). "
                "Running in fallback mode (quality assessment and RAG sync only)"
            )

        # Запускаем в фоне
        self._task = asyncio.create_task(self._scheduler_loop())
        logger.info(
            f"Channel Monitor Scheduler started "
            f"(interval: {settings.channel_monitor_interval} min)"
        )

    async def stop(self):
        """Остановить scheduler"""
        if not self.running:
            return

        self.running = False

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        logger.info("Channel Monitor Scheduler stopped")

    async def _scheduler_loop(self):
        """Главный цикл scheduler"""
        while self.running:
            try:
                loop_start = datetime.now()

                # 1. Fetch Phase (если Telethon настроен)
                if self.style_service.fetcher.is_configured:
                    await self._fetch_all_channels()
                else:
                    logger.debug("Skipping fetch phase (Telethon not configured)")

                # 2. Quality Assessment Phase
                await self._process_quality_posts()

                # 3. RAG Sync Phase (если включено)
                if settings.channel_auto_rag_sync:
                    await self._update_rag_if_needed()

                # 4. Update Channel Stats
                await self._update_channel_stats()

                # Логируем время выполнения
                loop_duration = (datetime.now() - loop_start).seconds
                logger.info(f"Monitor loop completed in {loop_duration}s")

                # Ждём до следующего цикла
                await asyncio.sleep(settings.channel_monitor_interval * 60)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitor loop: {e}", exc_info=True)
                # При ошибке ждём 5 минут перед повтором
                await asyncio.sleep(300)

    async def _fetch_all_channels(self):
        """
        Fetch Phase: загрузить посты из всех активных каналов.

        Приоритизация:
        - Priority 9-10: каждые 15 минут
        - Priority 7-8: каждые 30 минут
        - Priority 5-6: каждый час
        - Priority 1-4: каждые 2 часа
        """
        async with AsyncSessionLocal() as session:
            # Получаем активные каналы
            result = await session.execute(
                select(StyleChannel)
                .where(StyleChannel.is_active == True)
                .order_by(StyleChannel.priority.desc())
            )
            channels = result.scalars().all()

            if not channels:
                logger.info("No active channels to fetch")
                return

            logger.info(f"Checking {len(channels)} active channels for updates")

            stats = {"fetched": 0, "new_posts": 0, "errors": 0}

            for channel in channels:
                # Проверяем нужно ли обновлять этот канал
                if not self._should_fetch_channel(channel):
                    logger.debug(
                        f"Skipping {channel.title} (priority {channel.priority}, "
                        f"last fetch: {channel.last_fetched_at})"
                    )
                    continue

                # Fetch posts
                try:
                    new_posts_count = await self.style_service.fetch_and_save_posts(
                        channel,
                        limit=settings.channel_fetch_limit,
                        days_back=settings.channel_fetch_days_back
                    )

                    stats["fetched"] += 1
                    stats["new_posts"] += new_posts_count

                    logger.info(
                        f"Fetched {new_posts_count} new posts from "
                        f"{channel.title} (priority {channel.priority})"
                    )

                except Exception as e:
                    logger.error(f"Error fetching {channel.title}: {e}", exc_info=True)
                    stats["errors"] += 1

            logger.info(
                f"Fetch phase completed: {stats['fetched']} channels, "
                f"{stats['new_posts']} new posts, {stats['errors']} errors"
            )

    def _should_fetch_channel(self, channel: StyleChannel) -> bool:
        """
        Определить нужно ли fetch этот канал сейчас.

        Зависит от приоритета и времени последнего fetch.
        """
        if not channel.last_fetched_at:
            return True  # Ещё ни разу не загружали

        time_since_fetch = datetime.now() - channel.last_fetched_at
        seconds_since = time_since_fetch.total_seconds()

        # Приоритет 9-10: каждые 15 минут
        if channel.priority >= 9:
            return seconds_since >= 900  # 15 min

        # Приоритет 7-8: каждые 30 минут
        elif channel.priority >= 7:
            return seconds_since >= 1800  # 30 min

        # Приоритет 5-6: каждый час
        elif channel.priority >= 5:
            return seconds_since >= 3600  # 1 hour

        # Приоритет 1-4: каждые 2 часа
        else:
            return seconds_since >= 7200  # 2 hours

    async def _process_quality_posts(self):
        """
        Quality Assessment Phase: оценить качество новых постов.

        Обрабатывает посты с is_analyzed=False.
        """
        async with AsyncSessionLocal() as session:
            # Находим неанализированные посты
            result = await session.execute(
                select(StylePost, StyleChannel)
                .join(StyleChannel, StylePost.channel_id == StyleChannel.id)
                .where(StylePost.is_analyzed == False)
                .limit(100)  # Batch processing
            )
            posts_with_channels = result.all()

            if not posts_with_channels:
                logger.debug("No posts to analyze")
                return

            logger.info(f"Analyzing quality of {len(posts_with_channels)} posts")

            analyzed_count = 0
            high_quality_count = 0

            for post, channel in posts_with_channels:
                try:
                    # Оценка качества
                    assessment = await self.quality_engine.assess_post(post, channel, session)

                    # Обновляем пост
                    post.is_analyzed = True
                    post.quality_score = assessment["quality_score"]
                    post.style_tags = assessment["style_tags"]

                    analyzed_count += 1

                    if assessment["quality_score"] >= settings.channel_min_quality_score:
                        high_quality_count += 1

                        logger.debug(
                            f"High quality post found: {channel.title} - "
                            f"score {assessment['quality_score']}"
                        )

                except Exception as e:
                    logger.error(f"Error analyzing post {post.id}: {e}", exc_info=True)

            # Коммитим изменения
            await session.commit()

            logger.info(
                f"Quality assessment completed: {analyzed_count} analyzed, "
                f"{high_quality_count} high quality (>={settings.channel_min_quality_score})"
            )

    async def _update_rag_if_needed(self):
        """
        RAG Sync Phase: добавить качественные посты в RAG.

        Добавляет посты с quality_score >= threshold и added_to_rag=False.
        """
        stats = await self.rag_service.sync_posts_to_rag(
            channel_id=None,  # Все каналы
            min_quality_score=settings.channel_min_quality_score,
            limit=20  # Не больше 20 за раз, чтобы не нагружать
        )

        if stats["added"] > 0 or stats["errors"] > 0:
            logger.info(
                f"RAG sync: {stats['added']} added, "
                f"{stats['skipped']} skipped, {stats['errors']} errors"
            )

    async def _update_channel_stats(self):
        """Обновить статистику каналов (avg_quality_score, high_quality_count)"""
        async with AsyncSessionLocal() as session:
            # Получаем все активные каналы
            result = await session.execute(
                select(StyleChannel).where(StyleChannel.is_active == True)
            )
            channels = result.scalars().all()

            for channel in channels:
                # Статистика по постам канала
                stats_result = await session.execute(
                    select(
                        func.avg(StylePost.quality_score).label("avg_quality"),
                        func.count(StylePost.id)
                        .filter(StylePost.quality_score >= 7)
                        .label("high_quality_count")
                    ).where(
                        StylePost.channel_id == channel.id,
                        StylePost.is_analyzed == True
                    )
                )
                stats = stats_result.one()

                # Обновляем канал
                channel.avg_quality_score = stats.avg_quality
                channel.high_quality_count = stats.high_quality_count or 0

            await session.commit()

            logger.debug("Channel stats updated")

    async def force_fetch_now(self, channel_id: Optional[int] = None) -> Dict:
        """
        Принудительно загрузить посты сейчас (минуя проверку времени).

        Args:
            channel_id: ID канала (None = все каналы)

        Returns:
            {"channels_processed": int, "total_new_posts": int, "errors": list}
        """
        stats = {
            "channels_processed": 0,
            "total_new_posts": 0,
            "errors": []
        }

        async with AsyncSessionLocal() as session:
            # Получаем каналы
            query = select(StyleChannel).where(StyleChannel.is_active == True)

            if channel_id:
                query = query.where(StyleChannel.id == channel_id)

            result = await session.execute(query)
            channels = result.scalars().all()

            for channel in channels:
                try:
                    new_posts = await self.style_service.fetch_and_save_posts(
                        channel,
                        limit=settings.channel_fetch_limit,
                        days_back=settings.channel_fetch_days_back
                    )

                    stats["channels_processed"] += 1
                    stats["total_new_posts"] += new_posts

                    logger.info(f"Force fetched {new_posts} posts from {channel.title}")

                except Exception as e:
                    error_msg = f"Error fetching {channel.title}: {str(e)}"
                    logger.error(error_msg, exc_info=True)
                    stats["errors"].append(error_msg)

        return stats


# Global singleton instance
_scheduler_instance: Optional[ChannelMonitorScheduler] = None


def get_channel_monitor_scheduler() -> ChannelMonitorScheduler:
    """Получить singleton instance scheduler"""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = ChannelMonitorScheduler()
    return _scheduler_instance
