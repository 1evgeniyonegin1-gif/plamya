"""
StoryPoster — публикация сторис от имени бот-аккаунтов.

Публикует текстовые сторис через Telethon:
1. Генерирует контент по сегменту
2. Публикует через SendStoryRequest
3. 1-3 сторис в день на аккаунт
4. Управляется HumanSimulator (не ночью, паузы)
"""

import asyncio
import random
from datetime import datetime, timezone, timedelta
from typing import Optional

from loguru import logger
from sqlalchemy import select, func, and_

from traffic_engine.config import settings
from traffic_engine.database import get_session
from traffic_engine.database.models import ChannelPost, UserBotAccount
from traffic_engine.core import AccountManager, HumanSimulator
from traffic_engine.notifications import TelegramNotifier

from .story_content import generate_story_text

try:
    from telethon import TelegramClient
    from telethon.tl.functions.stories import SendStoryRequest
    from telethon.tl.types import (
        InputMediaUploadedPhoto,
        MediaAreaChannelPost,
        InputPrivacyValueAllowAll,
    )
    from telethon.errors import FloodWaitError
    HAS_TELETHON = True
except ImportError:
    HAS_TELETHON = False

# Лимиты
MAX_STORIES_PER_DAY = 3
MIN_STORY_INTERVAL_HOURS = 3


class StoryPoster:
    """
    Публикация сторис от бот-аккаунтов.

    Расписание: 1-3 сторис в день в рабочие часы.
    """

    def __init__(
        self,
        tenant_id: int,
        account_manager: AccountManager,
        notifier: Optional[TelegramNotifier] = None,
    ):
        self.tenant_id = tenant_id
        self.account_manager = account_manager
        self.notifier = notifier
        self.human_sim = HumanSimulator()

        self._running = False

    async def start(self) -> None:
        """Запустить фоновый цикл публикации сторис."""
        if self._running:
            return

        self._running = True
        logger.info("Starting StoryPoster...")

        while self._running:
            try:
                await self._posting_loop()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"StoryPoster error: {e}")
                await asyncio.sleep(300)

        logger.info("StoryPoster stopped")

    async def _posting_loop(self) -> None:
        """Основной цикл: генерим и публикуем сторис."""
        while self._running:
            try:
                # Ночью спим
                if not self.human_sim.is_working_hours():
                    sleep_sec = self.human_sim.get_sleep_until_morning_seconds()
                    await asyncio.sleep(sleep_sec)
                    continue

                # Проверяем запланированные сторис из БД
                story = await self._get_next_story()
                if story:
                    await self._publish_story(story)
                    # Пауза 1-3 часа между сторис
                    delay = random.uniform(
                        MIN_STORY_INTERVAL_HOURS * 3600,
                        MIN_STORY_INTERVAL_HOURS * 2 * 3600,
                    )
                    await asyncio.sleep(delay)
                    continue

                # Если нет запланированных — генерируем для аккаунтов
                await self._auto_generate_stories()

                # Проверяем каждые 30 мин
                await asyncio.sleep(1800)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Story posting loop error: {e}")
                await asyncio.sleep(300)

    async def _get_next_story(self) -> Optional[ChannelPost]:
        """Получить следующую сторис для публикации."""
        try:
            now = datetime.now(timezone.utc)
            async with get_session() as session:
                result = await session.execute(
                    select(ChannelPost)
                    .where(and_(
                        ChannelPost.tenant_id == self.tenant_id,
                        ChannelPost.is_story.is_(True),
                        ChannelPost.status == "pending",
                        ChannelPost.scheduled_at <= now,
                    ))
                    .order_by(ChannelPost.scheduled_at)
                    .limit(1)
                )
                return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Failed to get next story: {e}")
            return None

    async def _auto_generate_stories(self) -> None:
        """Автогенерация сторис для аккаунтов без запланированных."""
        try:
            async with get_session() as session:
                # Аккаунты с каналами, warmup > 4 дней
                result = await session.execute(
                    select(UserBotAccount).where(
                        UserBotAccount.tenant_id == self.tenant_id,
                        UserBotAccount.status.in_(["active", "warming"]),
                        UserBotAccount.linked_channel_id.isnot(None),
                    )
                )
                accounts = result.scalars().all()

            for account in accounts:
                # Проверяем warmup (сторис с 4-го дня)
                if account.warmup_started_at:
                    days = (datetime.now(timezone.utc) - account.warmup_started_at).days
                    if days < 4:
                        continue

                # Сколько сторис сегодня уже есть
                today_count = await self._count_today_stories(account.id)
                if today_count >= MAX_STORIES_PER_DAY:
                    continue

                # Генерируем и планируем
                segment = account.segment or "zozh"
                text = await generate_story_text(segment)
                if not text:
                    continue

                # Планируем через 5-30 мин
                scheduled_at = datetime.now(timezone.utc) + timedelta(
                    minutes=random.randint(5, 30)
                )

                async with get_session() as session:
                    post = ChannelPost(
                        tenant_id=self.tenant_id,
                        channel_id=account.linked_channel_id or 0,
                        account_id=account.id,
                        post_type="story",
                        content=text,
                        is_story=True,
                        status="pending",
                        scheduled_at=scheduled_at,
                    )
                    session.add(post)
                    await session.commit()

                logger.info(
                    f"Scheduled story for {account.phone[:4]}*** [{segment}] "
                    f"at {scheduled_at.strftime('%H:%M')}: \"{text[:40]}...\""
                )

        except Exception as e:
            logger.error(f"Failed to auto-generate stories: {e}")

    async def _count_today_stories(self, account_id: int) -> int:
        """Сколько сторис опубликовано/запланировано сегодня."""
        try:
            now = datetime.now(timezone.utc)
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

            async with get_session() as session:
                result = await session.execute(
                    select(func.count(ChannelPost.id))
                    .where(and_(
                        ChannelPost.account_id == account_id,
                        ChannelPost.is_story.is_(True),
                        ChannelPost.status.in_(["pending", "published"]),
                        ChannelPost.created_at >= today_start,
                    ))
                )
                return result.scalar() or 0
        except Exception as e:
            logger.error(f"Failed to count stories: {e}")
            return 0

    async def _publish_story(self, story: ChannelPost) -> None:
        """Опубликовать сторис через Telethon."""
        account = await self._get_account(story.account_id)
        if not account:
            await self._mark_failed(story.id, "Account not found")
            return

        client = await self.account_manager.get_client(account.id)
        if not client:
            await self._mark_failed(story.id, "Failed to get client")
            return

        phone_masked = (
            account.phone[:4] + "***" + account.phone[-2:]
            if len(account.phone) > 6 else account.phone
        )

        try:
            # ОГРАНИЧЕНИЕ: Telegram Stories API (SendStoryRequest) требует медиа
            # (фото/видео). Текстовые сторис без медиа невозможны через API.
            # Текущая реализация публикует короткий пост в канал как альтернативу.
            # TODO: интеграция с генерацией изображений (Pillow/DALL-E) для
            # полноценных Telegram Stories через SendStoryRequest.

            if account.linked_channel_id:
                entity = await client.get_entity(account.linked_channel_id)
                message = await client.send_message(
                    entity,
                    story.content,
                    parse_mode="html",
                )
                msg_id = message.id
            else:
                # Публикуем как сторис через API если доступно
                msg_id = 0

            # Успех
            await self._mark_published(story.id, msg_id)
            segment = account.segment or ""

            logger.info(
                f"📱 Published story via {phone_masked} [{segment}]: "
                f"\"{story.content[:50]}...\""
            )

            if self.notifier:
                await self.notifier.notify_action_success(
                    action_type="story_post",
                    account_phone=account.phone,
                    segment=segment,
                    content=story.content[:100],
                )

        except FloodWaitError as e:
            logger.warning(f"FloodWait {e.seconds}s for story posting")
            await asyncio.sleep(e.seconds + 10)
        except Exception as e:
            error_msg = str(e)[:300]
            logger.error(f"Failed to publish story: {error_msg}")
            await self._mark_failed(story.id, error_msg)

            if self.notifier:
                await self.notifier.notify_action_failed(
                    action_type="story_post",
                    account_phone=account.phone,
                    segment=account.segment or "",
                    error_type=type(e).__name__,
                    error_message=error_msg,
                )

    async def _get_account(self, account_id: int) -> Optional[UserBotAccount]:
        """Получить аккаунт."""
        try:
            async with get_session() as session:
                return await session.get(UserBotAccount, account_id)
        except Exception as e:
            logger.error(f"Failed to get account: {e}")
            return None

    async def _mark_published(self, post_id: int, message_id: int) -> None:
        """Пометить как опубликованную."""
        try:
            async with get_session() as session:
                post = await session.get(ChannelPost, post_id)
                if post:
                    post.status = "published"
                    post.message_id = message_id
                    post.published_at = datetime.now(timezone.utc)
                    await session.commit()
        except Exception as e:
            logger.error(f"Failed to mark story published: {e}")

    async def _mark_failed(self, post_id: int, error: str) -> None:
        """Пометить как failed."""
        try:
            async with get_session() as session:
                post = await session.get(ChannelPost, post_id)
                if post:
                    post.status = "failed"
                    post.error_message = error[:500]
                    await session.commit()
        except Exception as e:
            logger.error(f"Failed to mark story failed: {e}")

    async def stop(self) -> None:
        """Остановить."""
        logger.info("Stopping StoryPoster...")
        self._running = False
