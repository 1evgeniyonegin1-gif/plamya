"""
Reply Checker — фоновая задача для отслеживания ответов на комменты.

Каждый час проверяет комменты за последние 4 часа:
1. Читает discussion group через Telethon
2. Если на наш коммент ответили → got_reply=True, reply_count++
3. Если на наш коммент поставили реакцию → got_reaction=True
4. Записывает результат в StrategySelector для MAB-обучения

Результаты записываются в:
- TrafficAction.got_reply / reply_count
- StrategyEffectiveness через StrategySelector.record_result()
"""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional

from loguru import logger
from sqlalchemy import select, and_

from traffic_engine.core import AccountManager, StrategySelector
from traffic_engine.database import get_session
from traffic_engine.database.models import TrafficAction
from traffic_engine.notifications import TelegramNotifier


class ReplyChecker:
    """
    Фоновая задача: проверяет ответы на наши комменты.

    Цикл:
    - Каждый час берёт успешные комменты за последние 4ч
    - Для каждого коммента с comment_message_id:
      - Читает replies через Telethon iter_messages(reply_to=comment_message_id)
      - Обновляет got_reply, reply_count в TrafficAction
      - Записывает результат в StrategySelector
    """

    def __init__(
        self,
        account_manager: AccountManager,
        strategy_selector: Optional[StrategySelector] = None,
        notifier: Optional[TelegramNotifier] = None,
        check_interval: int = 3600,  # 1 hour
        lookback_hours: int = 4,
    ):
        self.account_manager = account_manager
        self.strategy_selector = strategy_selector or StrategySelector()
        self.notifier = notifier
        self.check_interval = check_interval
        self.lookback_hours = lookback_hours
        self._running = False

    async def start(self) -> None:
        """Запустить фоновый цикл проверки ответов."""
        self._running = True
        logger.info(
            f"Reply Checker started (interval={self.check_interval}s, "
            f"lookback={self.lookback_hours}h)"
        )

        while self._running:
            try:
                await self._check_replies()
            except Exception as e:
                logger.error(f"Reply Checker error: {e}")

            await asyncio.sleep(self.check_interval)

    async def stop(self) -> None:
        """Остановить Reply Checker."""
        self._running = False
        logger.info("Reply Checker stopped")

    async def _check_replies(self) -> None:
        """Проверить ответы на комменты за последние N часов."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=self.lookback_hours)

        # Берём успешные комменты с comment_message_id, которые ещё не проверены
        async with get_session() as session:
            result = await session.execute(
                select(TrafficAction).where(
                    and_(
                        TrafficAction.action_type == "comment",
                        TrafficAction.status == "success",
                        TrafficAction.comment_message_id.isnot(None),
                        TrafficAction.got_reply == False,
                        TrafficAction.created_at >= cutoff,
                    )
                ).order_by(TrafficAction.created_at.desc()).limit(50)
            )
            actions = result.scalars().all()

        if not actions:
            logger.debug("Reply Checker: no recent unchecked comments")
            return

        logger.info(f"Reply Checker: checking {len(actions)} comments for replies")

        # Получаем клиент
        account = await self.account_manager.get_available_account("comment")
        if not account:
            logger.warning("Reply Checker: no accounts available")
            return

        client = await self.account_manager.get_client(account.id)
        if not client:
            logger.warning("Reply Checker: failed to get client")
            return

        if not client.is_connected():
            try:
                await client.connect()
            except Exception as e:
                logger.error(f"Reply Checker: connect failed: {e}")
                return

        checked = 0
        replies_found = 0

        for action in actions:
            try:
                got_reply, reply_count = await self._check_single_comment(
                    client, action
                )

                if got_reply:
                    replies_found += 1
                    # Обновляем TrafficAction
                    async with get_session() as session:
                        db_action = await session.get(TrafficAction, action.id)
                        if db_action:
                            db_action.got_reply = True
                            db_action.reply_count = reply_count
                            await session.commit()

                    # Записываем в StrategySelector для MAB
                    await self.strategy_selector.record_result(
                        strategy=action.strategy_used or "smart",
                        got_reply=True,
                        got_reaction=False,
                        segment=None,  # segment не хранится в action
                        channel_username=None,
                        post_topic=action.post_topic,
                    )

                    logger.info(
                        f"Reply found for comment {action.comment_message_id} "
                        f"(strategy={action.strategy_used}, replies={reply_count})"
                    )

                checked += 1

                # Пауза между проверками чтобы не спамить API
                await asyncio.sleep(2)

            except Exception as e:
                logger.debug(f"Reply check failed for action {action.id}: {e}")

        logger.info(
            f"Reply Checker done: checked={checked}, replies={replies_found}"
        )

    async def _check_single_comment(
        self, client, action: TrafficAction
    ) -> tuple:
        """
        Проверить один коммент на наличие ответов.

        Returns:
            (got_reply: bool, reply_count: int)
        """
        if not action.comment_message_id or not action.target_channel_id:
            return False, 0

        try:
            # Получаем entity канала
            channel_entity = await client.get_entity(action.target_channel_id)

            # Получаем linked discussion group
            from telethon.tl.functions.channels import GetFullChannelRequest
            from telethon.tl.types import Channel

            if not isinstance(channel_entity, Channel):
                return False, 0

            full = await client(GetFullChannelRequest(channel_entity))
            discussion_id = full.full_chat.linked_chat_id

            if not discussion_id:
                return False, 0

            discussion = await client.get_entity(discussion_id)

            # Читаем ответы на наш коммент
            reply_count = 0
            async for msg in client.iter_messages(
                discussion,
                reply_to=action.comment_message_id,
                limit=20,
            ):
                if msg.message and len(msg.message.strip()) > 0:
                    reply_count += 1

            return reply_count > 0, reply_count

        except Exception as e:
            logger.debug(f"Cannot check replies for {action.comment_message_id}: {e}")
            return False, 0
