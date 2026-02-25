"""
Channel Monitor - Мониторинг каналов для автокомментирования.

Использует Telethon для подписки на обновления каналов
и обработки новых постов.

КОНТЕНТ-ЗАВОД: Каждый аккаунт привязан к сегменту.
Перед комментированием AI анализирует пост + существующие комменты.
"""

import asyncio
import random
from datetime import datetime, timedelta, timezone
from typing import Callable, Dict, List, Optional, Set

from loguru import logger
from telethon import TelegramClient
from telethon.tl.types import Message, Channel
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.errors import (
    FloodWaitError,
    ChannelPrivateError,
    UserBannedInChannelError,
    ChatWriteForbiddenError,
)
from sqlalchemy import select

from traffic_engine.config import settings
from traffic_engine.database import get_session
from traffic_engine.database.models import TargetChannel, TrafficAction, Tenant
from traffic_engine.core import AccountManager, HumanSimulator, StrategySelector
from traffic_engine.notifications import TelegramNotifier

from .comment_generator import CommentGenerator
from .comment_poster import CommentPoster


class ChannelMonitor:
    """
    Мониторинг каналов для автокомментирования.

    Функции:
    - Подписка на обновления целевых каналов
    - Фильтрация постов (реклама, репосты, короткие)
    - Вызов генератора и постера комментариев

    Использует Telethon для работы с Telegram API.
    """

    def __init__(
        self,
        tenant_id: int,
        account_manager: AccountManager,
        notifier: Optional[TelegramNotifier] = None,
        on_new_post: Optional[Callable] = None,
    ):
        """
        Initialize channel monitor.

        Args:
            tenant_id: ID тенанта
            account_manager: Менеджер аккаунтов
            notifier: Telegram notifier для алертов
            on_new_post: Callback для новых постов (опционально)
        """
        self.tenant_id = tenant_id
        self.account_manager = account_manager
        self.notifier = notifier
        self.on_new_post = on_new_post

        self.human_sim = HumanSimulator()
        self.strategy_selector = StrategySelector()
        self.comment_generator: Optional[CommentGenerator] = None
        self.comment_poster: Optional[CommentPoster] = None

        self._running = False
        self._client: Optional[TelegramClient] = None
        self._channels: Dict[int, TargetChannel] = {}  # channel_id -> TargetChannel
        self._subscribed_channels: Set[int] = set()  # Каналы, на которые уже подписаны
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 10
        self._reconnect_delay = 30  # Начальная задержка в секундах
        self._session_actions = 0  # Счётчик действий в текущей сессии

    async def initialize(self, tenant_name: str = "nl_international") -> None:
        """
        Initialize monitor with generators and poster.

        Args:
            tenant_name: Название тенанта для контекста
        """
        self.comment_generator = CommentGenerator(tenant_name=tenant_name)
        self.comment_poster = CommentPoster(self.account_manager, self.notifier)

        # Загружаем каналы из БД
        await self._load_channels()

        logger.info(f"Channel monitor initialized with {len(self._channels)} channels")

    async def _load_channels(self) -> None:
        """Загрузить активные каналы из БД."""
        async with get_session() as session:
            result = await session.execute(
                select(TargetChannel).where(
                    TargetChannel.tenant_id == self.tenant_id,
                    TargetChannel.is_active == True,
                )
            )
            channels = result.scalars().all()

            self._channels = {ch.channel_id: ch for ch in channels}

    async def start(self) -> None:
        """Запустить мониторинг каналов с автоперезапуском."""
        if self._running:
            logger.warning("Monitor already running")
            return

        self._running = True
        logger.info("Starting channel monitor...")

        while self._running:
            try:
                # Получаем клиент от первого доступного аккаунта
                account = await self.account_manager.get_available_account("comment")
                if not account:
                    logger.error("No accounts available for monitoring")
                    await asyncio.sleep(60)
                    continue

                self._client = await self.account_manager.get_client(account.id)
                if not self._client:
                    logger.error("Failed to get client")
                    await asyncio.sleep(60)
                    continue

                await self._client.connect()
                if not await self._client.is_user_authorized():
                    logger.error("Client not authorized!")
                    await asyncio.sleep(60)
                    continue

                logger.info("✅ Telethon client connected")
                self._reconnect_attempts = 0  # Сбрасываем счётчик при успешном подключении

                # Медленная подписка на каналы (1-2 за запуск)
                await self._slow_join_channels()

                # Запускаем polling
                await self._polling_loop()

            except (ConnectionError, OSError, asyncio.TimeoutError) as e:
                # Ошибки сети — пробуем переподключиться
                self._reconnect_attempts += 1
                delay = min(self._reconnect_delay * (2 ** self._reconnect_attempts), 600)  # Max 10 min

                if self._reconnect_attempts > self._max_reconnect_attempts:
                    logger.error(f"❌ Max reconnect attempts ({self._max_reconnect_attempts}) reached. Stopping.")
                    self._running = False
                    break

                logger.warning(
                    f"🔌 Connection lost: {e}. "
                    f"Attempt {self._reconnect_attempts}/{self._max_reconnect_attempts}. "
                    f"Reconnecting in {delay}s..."
                )
                await self._safe_disconnect()
                await asyncio.sleep(delay)

            except Exception as e:
                import traceback
                logger.error(f"❌ Monitor error: {e}\n{traceback.format_exc()}")
                self._reconnect_attempts += 1
                delay = 60

                if self._reconnect_attempts > self._max_reconnect_attempts:
                    logger.error(f"❌ Max reconnect attempts reached. Stopping.")
                    self._running = False
                    break

                logger.info(f"Restarting in {delay}s...")
                await self._safe_disconnect()
                await asyncio.sleep(delay)

        await self._safe_disconnect()
        logger.info("Channel monitor stopped")

    async def _safe_disconnect(self) -> None:
        """Безопасно отключить клиент."""
        try:
            if self._client and self._client.is_connected():
                await self._client.disconnect()
        except Exception as e:
            logger.debug(f"Disconnect error (ignored): {e}")

    async def _slow_join_channels(self) -> None:
        """
        Медленная подписка на каналы (1-2 за запуск).

        Безопасная стратегия:
        - Подписываемся только на 1-2 канала за цикл запуска
        - Пауза 5-10 минут между подписками
        - Пропускаем каналы, на которые уже подписаны
        """
        # Находим каналы, на которые нужно подписаться
        channels_to_join = [
            ch for ch_id, ch in self._channels.items()
            if ch_id not in self._subscribed_channels and ch.username
        ]

        if not channels_to_join:
            logger.debug("All channels already subscribed or no username")
            return

        # Выбираем 1-2 случайных канала
        num_to_join = min(random.randint(1, 2), len(channels_to_join))
        selected = random.sample(channels_to_join, num_to_join)

        logger.info(f"📢 Slow join: {num_to_join} channel(s) this session")

        for channel in selected:
            try:
                # Проверяем, можем ли читать без подписки
                try:
                    entity = await self._client.get_entity(channel.username)
                    self._subscribed_channels.add(channel.channel_id)
                    logger.debug(f"Can read @{channel.username} without subscription")
                    continue
                except ChannelPrivateError:
                    pass  # Нужна подписка

                # Подписываемся
                await self._client(JoinChannelRequest(channel.username))
                self._subscribed_channels.add(channel.channel_id)
                logger.info(f"✅ Joined @{channel.username}")

                # Большая пауза между подписками (5-10 минут)
                if channel != selected[-1]:
                    delay = random.randint(300, 600)
                    logger.info(f"⏳ Waiting {delay // 60} min before next join...")
                    await asyncio.sleep(delay)

            except FloodWaitError as e:
                logger.warning(f"⚠️ FloodWait for {e.seconds}s on @{channel.username}")
                await asyncio.sleep(e.seconds + 10)
            except (ChannelPrivateError, UserBannedInChannelError) as e:
                logger.warning(f"⚠️ Cannot join @{channel.username}: {e}")
            except Exception as e:
                logger.error(f"❌ Failed to join @{channel.username}: {e}")

    async def _join_channels(self) -> None:
        """Вступить в целевые каналы (если ещё не вступили). DEPRECATED - use _slow_join_channels."""
        for channel_id, channel in self._channels.items():
            try:
                # Проверяем, вступили ли уже
                entity = await self._client.get_entity(channel_id)
                logger.debug(f"Already in channel: {getattr(entity, 'title', channel_id)}")
            except Exception:
                # Пробуем вступить
                try:
                    if channel.username:
                        await self._client(JoinChannelRequest(channel.username))
                        logger.info(f"Joined channel: @{channel.username}")
                except Exception as e:
                    logger.error(f"Failed to join {channel.username}: {e}")

    async def _polling_loop(self) -> None:
        """
        Основной цикл polling новых постов.

        Каждые 30-60 секунд проверяем каналы на новые посты.
        При сетевых ошибках пробрасываем их наверх для автоперезапуска.
        """
        consecutive_errors = 0

        while self._running:
            try:
                # Проверяем рабочие часы — ночью спим до утра
                if not self.human_sim.is_working_hours():
                    sleep_sec = self.human_sim.get_sleep_until_morning_seconds()
                    await asyncio.sleep(sleep_sec)
                    continue

                # Проверяем каналы
                await self._check_channels()
                consecutive_errors = 0  # Сбрасываем при успехе
                self._session_actions += 1

                # Session/Break: после 20-40 действий — перерыв
                if self.human_sim.should_take_break(self._session_actions):
                    break_min = self.human_sim.get_break_duration()
                    logger.info(f"☕ Taking a break: {break_min:.0f} min ({self._session_actions} actions in session)")
                    await asyncio.sleep(break_min * 60)
                    self._session_actions = 0

                # Случайная пауза между проверками
                delay = self.human_sim.get_random_pause(30, 90)
                await asyncio.sleep(delay)

            except asyncio.CancelledError:
                logger.info("Polling cancelled")
                break
            except (ConnectionError, OSError, asyncio.TimeoutError) as e:
                # Сетевые ошибки — пробрасываем наверх для переподключения
                logger.warning(f"🔌 Network error in polling: {e}")
                raise
            except Exception as e:
                consecutive_errors += 1
                logger.error(f"Polling error ({consecutive_errors}): {e}")

                if consecutive_errors >= 5:
                    logger.error("Too many consecutive errors, triggering reconnect")
                    raise ConnectionError(f"Too many errors: {e}")

                await asyncio.sleep(60)

    def _channel_lurk_ok(self, channel: TargetChannel) -> bool:
        """
        Проверяет lurk-паузу: нельзя комментить первые 24ч после вступления.

        Returns:
            True если lurk пауза прошла (можно комментить)
        """
        joined_at = getattr(channel, "joined_at", None)
        if not joined_at:
            return True  # Нет данных — разрешаем (совместимость)

        now = datetime.now(timezone.utc)
        if joined_at.tzinfo is None:
            joined_at = joined_at.replace(tzinfo=timezone.utc)

        hours_since_join = (now - joined_at).total_seconds() / 3600
        if hours_since_join < 24:
            logger.debug(
                f"⏳ Lurk pause: @{channel.username} joined {hours_since_join:.1f}h ago (need 24h)"
            )
            return False
        return True

    async def _check_channels(self) -> None:
        """Проверить все каналы на новые посты."""
        for channel_id, channel in self._channels.items():
            try:
                # Lurk пауза — не комментим первые 24ч после вступления
                if not self._channel_lurk_ok(channel):
                    continue
                await self._check_channel(channel)
            except Exception as e:
                logger.error(f"Error checking channel {channel.username}: {e}")

    async def _check_channel(self, channel: TargetChannel) -> None:
        """
        Проверить один канал на новые посты.

        Args:
            channel: Канал для проверки
        """
        # Получаем последние сообщения через Telethon
        # Используем username для публичных каналов (не требует подписки)
        messages: List[Message] = []
        channel_ref = channel.username if channel.username else channel.channel_id
        async for message in self._client.iter_messages(
            channel_ref,
            limit=5  # Последние 5 постов
        ):
            messages.append(message)

        if not messages:
            return

        # Фильтруем новые посты (которые ещё не обрабатывали)
        new_posts = [
            msg for msg in messages
            if msg.id > (channel.last_post_id or 0)
        ]

        if not new_posts:
            logger.debug(f"No new posts in @{channel.username} (last_post_id={channel.last_post_id})")
            return

        logger.info(f"✨ Found {len(new_posts)} NEW posts in @{channel.username}!")

        # Обрабатываем каждый новый пост
        for post in sorted(new_posts, key=lambda m: m.id):
            await self._process_post(channel, post)

        # Обновляем last_post_id
        await self._update_last_post_id(channel.id, messages[0].id)

    async def _read_post_comments(
        self, channel: TargetChannel, post: Message, limit: int = 15
    ) -> List[str]:
        """
        Прочитать существующие комменты под постом через Telethon.

        Args:
            channel: Канал
            post: Пост
            limit: Макс. количество комментов

        Returns:
            Список текстов комментариев
        """
        comments = []
        try:
            channel_ref = channel.username if channel.username else channel.channel_id
            async for msg in self._client.iter_messages(
                channel_ref,
                reply_to=post.id,
                limit=limit,
            ):
                if msg.message and len(msg.message.strip()) > 5:
                    comments.append(msg.message.strip())
        except Exception as e:
            logger.debug(f"Could not read comments for post {post.id}: {e}")

        return comments

    async def _check_cross_account(
        self, channel_id: int, message_id: int
    ) -> bool:
        """
        Проверить, не комментировал ли уже другой аккаунт этот пост.

        Returns:
            True если можно комментить, False если уже есть коммент
        """
        try:
            async with get_session() as session:
                result = await session.execute(
                    select(TrafficAction).where(
                        TrafficAction.target_channel_id == channel_id,
                        TrafficAction.target_message_id == message_id,
                        TrafficAction.action_type == "comment",
                        TrafficAction.status == "success",
                    ).limit(1)
                )
                existing = result.scalar_one_or_none()
                if existing:
                    logger.info(
                        f"⏭️ Cross-account: post {message_id} already commented "
                        f"by account {existing.account_id}"
                    )
                    return False
                return True
        except Exception as e:
            logger.error(f"Cross-account check failed: {e}")
            return True  # В случае ошибки — разрешаем (лучше дубль чем пропуск)

    async def _process_post(self, channel: TargetChannel, post: Message) -> None:
        """
        Обработать новый пост с анализом и сегментной маршрутизацией.

        Новый pipeline:
        1. Базовые фильтры (реклама, репост, короткий)
        2. Cross-account check (не комментили ли другие аккаунты)
        3. Читаем существующие комменты под постом
        4. AI анализирует пост + комменты → решение + стратегия
        5. Генерируем коммент в стиле Данила (адаптированный под сегмент)
        6. Публикуем с сохранением метаданных
        """
        post_text = post.message or ""

        # --- БАЗОВЫЕ ФИЛЬТРЫ ---
        is_ad = self._is_ad(post)
        is_repost = post.fwd_from is not None

        # Быстрая проверка без AI
        if is_ad or is_repost or len(post_text.strip()) < 50:
            logger.info(
                f"⏭️ Skipping post {post.id} in @{channel.username} "
                f"(ad={is_ad}, repost={is_repost}, short={len(post_text) < 50})"
            )
            return

        # --- HUMAN-LIKE SKIP ---
        if not self.human_sim.should_act_now():
            logger.info(f"⏭️ Random skip post {post.id} in @{channel.username} (human-like)")
            return

        # --- CROSS-ACCOUNT CHECK ---
        can_comment = await self._check_cross_account(channel.channel_id, post.id)
        if not can_comment:
            return

        # --- СЕГМЕНТ ---
        segment = getattr(channel, "segment", None)

        # --- ИМИТАЦИЯ ЧТЕНИЯ ПОСТА ---
        reading_delay = self.human_sim.get_reading_delay(post_text)
        logger.debug(f"📖 Reading post {post.id} for {reading_delay:.1f}s...")
        await asyncio.sleep(reading_delay)

        # --- ЧИТАЕМ КОММЕНТЫ ПОД ПОСТОМ ---
        logger.debug(f"📖 Reading comments for post {post.id} in @{channel.username}...")
        comments = await self._read_post_comments(channel, post)
        if comments:
            logger.debug(f"Found {len(comments)} comments under post {post.id}")

        # --- AI АНАЛИЗ ---
        logger.info(f"🔍 Analyzing post {post.id} in @{channel.username}...")
        analysis = await self.comment_generator.analyze_post(
            post_text=post_text,
            comments=comments if comments else None,
            channel_title=channel.title,
            segment=segment,
        )

        # Проверяем should_comment с учётом анализа
        should_comment = await self.comment_generator.should_comment(
            post_text=post_text,
            is_ad=is_ad,
            is_repost=is_repost,
            analysis=analysis,
        )

        if not should_comment:
            logger.info(
                f"⏭️ Skipping post {post.id} in @{channel.username} "
                f"(analysis: relevance={analysis.get('relevance', '?')}, "
                f"mood={analysis.get('discussion_mood', '?')}, "
                f"should_comment={analysis.get('should_comment', '?')})"
            )
            return

        # Стратегия: Thompson Sampling (если есть данные) → AI analysis → fallback
        strategy = await self.strategy_selector.select_strategy(
            segment=segment,
            channel_username=channel.username,
        )
        ai_strategy = analysis.get("strategy", "smart")
        if strategy != ai_strategy:
            logger.debug(
                f"Strategy: MAB={strategy}, AI={ai_strategy} — using MAB"
            )

        logger.info(
            f"📝 Generating comment for post {post.id} in @{channel.username} "
            f"(segment={segment}, strategy={strategy}, "
            f"relevance={analysis.get('relevance', '?')}, "
            f"topic={analysis.get('topic', '?')})"
        )

        # --- ГЕНЕРАЦИЯ КОММЕНТАРИЯ ---
        comment = await self.comment_generator.generate(
            post_text=post_text,
            strategy=strategy,
            channel_title=channel.title,
            segment=segment,
            analysis=analysis,
            comments=comments if comments else None,
        )

        if not comment:
            logger.warning(f"❌ Failed to generate comment for post {post.id}")
            if self.notifier:
                await self.notifier.notify_action_failed(
                    action_type="comment",
                    account_phone="system",
                    channel=channel.username or str(channel.channel_id),
                    error_type="AI_GenerationFailed",
                    error_message=f"Failed to generate comment for post {post.id} in @{channel.username}",
                )
            return

        logger.info(f"✅ Generated ({strategy}, {segment}): {comment[:60]}...")

        # --- ЗАДЕРЖКА ПЕРЕД ПУБЛИКАЦИЕЙ ---
        now = datetime.now(timezone.utc)
        post_date = post.date
        if post_date.tzinfo is None:
            post_date = post_date.replace(tzinfo=timezone.utc)
        post_age = (now - post_date).total_seconds()

        delay = self.human_sim.get_random_pause(300, 600)  # 5-10 минут
        logger.info(f"Post is {post_age/60:.1f} min old. Waiting {delay/60:.1f} min before commenting...")
        await asyncio.sleep(delay)

        # --- ПУБЛИКАЦИЯ ---
        success = await self.comment_poster.post_comment(
            channel_id=channel.channel_id,
            message_id=post.id,
            comment_text=comment,
            strategy=strategy,
            channel_username=channel.username,
            relevance_score=analysis.get("relevance"),
            post_topic=analysis.get("topic"),
            segment=segment,
        )

        if success:
            await self._update_channel_stats(channel.id)

    def _is_ad(self, post: Message) -> bool:
        """Определить, является ли пост рекламой."""
        # Telethon использует post.message вместо post.text
        text = (post.message or "").lower()

        ad_markers = [
            "реклама", "#реклама", "erid:", "promo", "#ad",
            "рекламный пост", "на правах рекламы",
        ]

        for marker in ad_markers:
            if marker in text:
                return True

        return False

    async def _update_last_post_id(self, channel_db_id: int, post_id: int) -> None:
        """Обновить ID последнего обработанного поста."""
        async with get_session() as session:
            channel = await session.get(TargetChannel, channel_db_id)
            if channel:
                channel.last_post_id = post_id
                channel.last_processed_at = datetime.now(timezone.utc)
                await session.commit()

    async def _update_channel_stats(self, channel_db_id: int) -> None:
        """Обновить статистику канала."""
        async with get_session() as session:
            channel = await session.get(TargetChannel, channel_db_id)
            if channel:
                channel.posts_processed += 1
                channel.comments_posted += 1
                await session.commit()

    async def stop(self) -> None:
        """Остановить мониторинг."""
        logger.info("Stopping channel monitor...")
        self._running = False
        await self._safe_disconnect()
        logger.info("Channel monitor stopped")

    async def add_channel(
        self,
        channel_id: int,
        username: Optional[str] = None,
        title: Optional[str] = None,
    ) -> None:
        """
        Добавить канал для мониторинга.

        Args:
            channel_id: ID канала
            username: Username канала (без @)
            title: Название канала
        """
        async with get_session() as session:
            # Проверяем, есть ли уже
            result = await session.execute(
                select(TargetChannel).where(
                    TargetChannel.channel_id == channel_id
                )
            )
            existing = result.scalar_one_or_none()

            if existing:
                logger.warning(f"Channel {channel_id} already exists")
                return

            # Создаём новый
            channel = TargetChannel(
                tenant_id=self.tenant_id,
                channel_id=channel_id,
                username=username,
                title=title or f"Channel {channel_id}",
                is_active=True,
            )
            session.add(channel)
            await session.commit()

            # Добавляем в память
            self._channels[channel_id] = channel

            logger.info(f"Added channel @{username or channel_id}")

    async def remove_channel(self, channel_id: int) -> None:
        """Удалить канал из мониторинга."""
        async with get_session() as session:
            result = await session.execute(
                select(TargetChannel).where(
                    TargetChannel.channel_id == channel_id
                )
            )
            channel = result.scalar_one_or_none()

            if channel:
                channel.is_active = False
                await session.commit()

                # Удаляем из памяти
                self._channels.pop(channel_id, None)

                logger.info(f"Removed channel {channel_id}")
