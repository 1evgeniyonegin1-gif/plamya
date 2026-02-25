"""
Auto Poster — публикация контента в тематические каналы бот-аккаунтов.

Фоновый процесс:
1. Читает ChannelPost из БД (status=pending, scheduled_at <= now)
2. Получает Telethon-клиент через AccountManager
3. Публикует в канал (linked_channel_id аккаунта)
4. Обновляет статус в БД
5. Отправляет уведомления
"""

import asyncio
from datetime import datetime, timezone
from typing import Optional

from loguru import logger
from sqlalchemy import select, and_

from traffic_engine.config import settings
from traffic_engine.database import get_session
from traffic_engine.database.models import ChannelPost, UserBotAccount
from traffic_engine.core import AccountManager, HumanSimulator
from traffic_engine.notifications import TelegramNotifier

try:
    from telethon.errors import (
        FloodWaitError,
        ChatWriteForbiddenError,
        ChannelPrivateError,
    )
    HAS_TELETHON = True
except ImportError:
    HAS_TELETHON = False


class AutoPoster:
    """
    Автопостинг в тематические каналы.

    Работает с ChannelPost моделью из БД.
    Публикует через Telethon-клиент аккаунта.
    """

    def __init__(
        self,
        tenant_id: int,
        account_manager: AccountManager,
        notifier: Optional[TelegramNotifier] = None,
        check_interval: int = 120,
    ):
        self.tenant_id = tenant_id
        self.account_manager = account_manager
        self.notifier = notifier
        self.check_interval = check_interval

        self.human_sim = HumanSimulator()
        self._running = False
        self._session_actions = 0

    async def start(self) -> None:
        """Запустить фоновый цикл автопостинга."""
        if self._running:
            logger.warning("AutoPoster already running")
            return

        self._running = True
        logger.info("Starting AutoPoster...")

        while self._running:
            try:
                await self._posting_loop()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"AutoPoster error: {e}")
                await asyncio.sleep(60)

        logger.info("AutoPoster stopped")

    async def _posting_loop(self) -> None:
        """Основной цикл: проверяем очередь и публикуем."""
        while self._running:
            try:
                # Ночью не постим
                if not self.human_sim.is_working_hours():
                    sleep_sec = self.human_sim.get_sleep_until_morning_seconds()
                    await asyncio.sleep(sleep_sec)
                    continue

                # Получаем следующий пост из очереди
                post = await self._get_next_post()
                if not post:
                    await asyncio.sleep(self.check_interval)
                    continue

                # Получаем аккаунт
                account = await self._get_account(post.account_id)
                if not account:
                    await self._mark_failed(post.id, "Account not found")
                    continue

                # Получаем клиент
                client = await self.account_manager.get_client(account.id)
                if not client:
                    await self._mark_failed(post.id, "Failed to get Telethon client")
                    continue

                # Публикуем
                await self._publish(client, account, post)

                # Перерыв между постами
                if self.human_sim.should_take_break(self._session_actions):
                    break_min = self.human_sim.get_break_duration()
                    logger.info(f"☕ Posting break: {break_min:.0f} min")
                    await asyncio.sleep(break_min * 60)
                    self._session_actions = 0

                # Пауза 3-10 мин между постами
                delay = self.human_sim.get_random_pause(180, 600)
                await asyncio.sleep(delay)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Posting loop error: {e}")
                await asyncio.sleep(60)

    async def _get_next_post(self) -> Optional[ChannelPost]:
        """Получить следующий пост для публикации."""
        try:
            now = datetime.now(timezone.utc)
            async with get_session() as session:
                result = await session.execute(
                    select(ChannelPost)
                    .where(and_(
                        ChannelPost.tenant_id == self.tenant_id,
                        ChannelPost.status == "pending",
                        ChannelPost.is_story.is_(False),
                        ChannelPost.scheduled_at <= now,
                    ))
                    .order_by(ChannelPost.scheduled_at)
                    .limit(1)
                )
                return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Failed to get next post: {e}")
            return None

    async def _get_account(self, account_id: int) -> Optional[UserBotAccount]:
        """Получить аккаунт из БД."""
        try:
            async with get_session() as session:
                return await session.get(UserBotAccount, account_id)
        except Exception as e:
            logger.error(f"Failed to get account {account_id}: {e}")
            return None

    async def _publish(self, client, account: UserBotAccount, post: ChannelPost) -> None:
        """Опубликовать пост в канал."""
        channel_id = post.channel_id
        phone_masked = account.phone[:4] + "***" + account.phone[-2:] if len(account.phone) > 6 else account.phone

        try:
            # Получаем entity канала
            try:
                entity = await client.get_entity(channel_id)
            except Exception as e:
                await self._mark_failed(post.id, f"Cannot get channel entity: {e}")
                return

            # Публикуем
            if post.media_file_id and post.media_type == "photo":
                message = await client.send_file(
                    entity,
                    post.media_file_id,
                    caption=post.content,
                    parse_mode="html",
                )
            else:
                message = await client.send_message(
                    entity,
                    post.content,
                    parse_mode="html",
                )

            # Успех
            await self._mark_published(post.id, message.id)
            self._session_actions += 1

            segment = getattr(account, "segment", "") or ""
            logger.info(
                f"✅ Published post {post.id} ({post.post_type}) to channel {channel_id} "
                f"via {phone_masked} [{segment}]"
            )

            if self.notifier:
                await self.notifier.notify_action_success(
                    action_type="channel_post",
                    account_phone=account.phone,
                    segment=segment,
                    channel=account.linked_channel_username or str(channel_id),
                    content=post.content[:100],
                )

        except FloodWaitError as e:
            logger.warning(f"⚠️ FloodWait {e.seconds}s for posting")
            await self.account_manager.set_cooldown(account.id, e.seconds)
            # Не помечаем как failed — попробуем позже
            await asyncio.sleep(e.seconds + 10)

            if self.notifier:
                await self.notifier.notify_action_failed(
                    action_type="channel_post",
                    account_phone=account.phone,
                    segment=getattr(account, "segment", "") or "",
                    channel=account.linked_channel_username or str(channel_id),
                    error_type="FloodWait",
                    error_message=f"FloodWait {e.seconds}s",
                )

        except (ChatWriteForbiddenError, ChannelPrivateError) as e:
            error_msg = f"{type(e).__name__}: {e}"
            logger.error(f"❌ {error_msg}")
            await self._mark_failed(post.id, error_msg)

            if self.notifier:
                await self.notifier.notify_action_failed(
                    action_type="channel_post",
                    account_phone=account.phone,
                    segment=getattr(account, "segment", "") or "",
                    channel=account.linked_channel_username or str(channel_id),
                    error_type=type(e).__name__,
                    error_message=error_msg,
                )

        except Exception as e:
            error_msg = str(e)[:300]
            logger.error(f"❌ Failed to publish post {post.id}: {error_msg}")
            await self._mark_failed(post.id, error_msg)

            if self.notifier:
                await self.notifier.notify_action_failed(
                    action_type="channel_post",
                    account_phone=account.phone,
                    segment=getattr(account, "segment", "") or "",
                    channel=account.linked_channel_username or str(channel_id),
                    error_type=type(e).__name__,
                    error_message=error_msg,
                )

    async def _mark_published(self, post_id: int, message_id: int) -> None:
        """Пометить пост как опубликованный."""
        try:
            async with get_session() as session:
                post = await session.get(ChannelPost, post_id)
                if post:
                    post.status = "published"
                    post.message_id = message_id
                    post.published_at = datetime.now(timezone.utc)
                    await session.commit()
        except Exception as e:
            logger.error(f"Failed to mark post {post_id} as published: {e}")

    async def _mark_failed(self, post_id: int, error: str) -> None:
        """Пометить пост как failed."""
        try:
            async with get_session() as session:
                post = await session.get(ChannelPost, post_id)
                if post:
                    post.status = "failed"
                    post.error_message = error[:500]
                    await session.commit()
        except Exception as e:
            logger.error(f"Failed to mark post {post_id} as failed: {e}")

    async def stop(self) -> None:
        """Остановить автопостер."""
        logger.info("Stopping AutoPoster...")
        self._running = False
