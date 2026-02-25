"""
OwnChannelMonitor — мониторинг комментов в тематических каналах и ответы.

Когда подписчик пишет коммент в канале бот-аккаунта:
1. Читаем контекст (пост + коммент)
2. Генерируем ответ в стиле сегмента
3. Отвечаем от имени аккаунта-админа
"""

import asyncio
import random
from datetime import datetime, timezone
from typing import Optional, Dict, Set

from loguru import logger
from sqlalchemy import select

from traffic_engine.config import settings
from traffic_engine.database import get_session
from traffic_engine.database.models import UserBotAccount, TrafficAction
from traffic_engine.core import AccountManager, HumanSimulator
from traffic_engine.notifications import TelegramNotifier

try:
    from telethon import TelegramClient, events
    from telethon.tl.functions.channels import GetFullChannelRequest
    from telethon.errors import FloodWaitError
    HAS_TELETHON = True
except ImportError:
    HAS_TELETHON = False


# Промпт для ответов на комменты в своём канале
REPLY_SYSTEM_PROMPT = """Ты — автор Telegram-канала. Подписчик написал комментарий под твоим постом.
Ответь дружелюбно, коротко (1-3 предложения).

Стиль: {segment_tone}

ПРАВИЛА:
1. Отвечай как живой человек, а не бот
2. Можешь задать уточняющий вопрос
3. Если хвалят — поблагодари просто, без пафоса
4. Если спрашивают — ответь по теме или скажи что напишешь об этом подробнее
5. Не используй: 'уникальный', 'превосходный', 'невероятный', 'удивительный'
6. Максимум 1 эмодзи
"""

SEGMENT_TONES = {
    "zozh": "экспертный, про питание/спорт, мат ок умеренный",
    "mama": "тёплый, БЕЗ мата, эмпатия",
    "business": "деловой, конкретный, цифры",
    "student": "как друг, юмор ок, мемы ок",
}


class OwnChannelMonitor:
    """
    Мониторинг комментариев в тематических каналах бот-аккаунтов.

    Для каждого аккаунта с linked_channel_id:
    - Слушает новые сообщения в discussion-группе канала
    - Генерирует ответ через AI
    - Отвечает от имени аккаунта
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
        self._handlers: Dict[int, callable] = {}  # account_id → handler
        self._daily_replies: Dict[int, int] = {}  # account_id → count today
        self._replied_messages: Set[str] = set()  # "account_id:msg_id" — дедупликация
        self._max_replied_messages = 10000  # Лимит для предотвращения утечки памяти
        self._max_replies_per_day = 10

    async def start(self) -> None:
        """Запустить мониторинг для всех аккаунтов с каналами."""
        if self._running:
            return

        self._running = True
        logger.info("Starting OwnChannelMonitor...")

        # Получаем аккаунты с привязанными каналами
        accounts = await self._get_accounts_with_channels()

        if not accounts:
            logger.info("No accounts with linked channels, OwnChannelMonitor sleeping")
            while self._running:
                await asyncio.sleep(300)
                accounts = await self._get_accounts_with_channels()
                if accounts:
                    break
            if not self._running:
                return

        # Для каждого аккаунта регистрируем event handler
        for account in accounts:
            try:
                client = await self.account_manager.get_client(account.id)
                if not client:
                    continue

                await self._register_handler(client, account)
            except Exception as e:
                logger.error(f"Failed to setup handler for account {account.id}: {e}")

        logger.info(f"OwnChannelMonitor started for {len(self._handlers)} accounts")

        # Держим процесс живым
        while self._running:
            await asyncio.sleep(60)

            # Сброс дневных счётчиков в полночь
            now = datetime.now(timezone.utc)
            if now.hour == 0 and now.minute == 0:
                self._daily_replies.clear()

    async def _get_accounts_with_channels(self) -> list:
        """Получить аккаунты с привязанными каналами."""
        try:
            async with get_session() as session:
                result = await session.execute(
                    select(UserBotAccount).where(
                        UserBotAccount.tenant_id == self.tenant_id,
                        UserBotAccount.status.in_(["active", "warming"]),
                        UserBotAccount.linked_channel_id.isnot(None),
                    )
                )
                return result.scalars().all()
        except Exception as e:
            logger.error(f"Failed to get accounts: {e}")
            return []

    async def _register_handler(self, client: TelegramClient, account: UserBotAccount) -> None:
        """Зарегистрировать event handler для комментов в канале."""
        channel_id = account.linked_channel_id

        # Получаем discussion group ID
        try:
            entity = await client.get_entity(channel_id)
            full = await client(GetFullChannelRequest(entity))
            linked_chat_id = getattr(full.full_chat, "linked_chat_id", None)

            if not linked_chat_id:
                logger.warning(
                    f"Channel {account.linked_channel_username or channel_id} "
                    f"has no discussion group"
                )
                return

        except Exception as e:
            logger.error(f"Failed to get discussion group for channel {channel_id}: {e}")
            return

        # Регистрируем handler на новые сообщения в discussion группе
        @client.on(events.NewMessage(chats=linked_chat_id))
        async def on_comment(event, acc=account, cid=channel_id):
            await self._handle_comment(event, client, acc)

        self._handlers[account.id] = on_comment
        logger.info(
            f"Registered comment handler for {account.linked_channel_username or channel_id} "
            f"(discussion: {linked_chat_id})"
        )

    async def _handle_comment(
        self, event, client: TelegramClient, account: UserBotAccount
    ) -> None:
        """Обработать новый комментарий."""
        msg = event.message
        if not msg or not msg.text:
            return

        # Не отвечаем на свои сообщения
        sender = await event.get_sender()
        if not sender:
            return

        me = await client.get_me()
        if sender.id == me.id:
            return

        # Не отвечаем ботам
        if getattr(sender, "bot", False):
            return

        # Дедупликация (с ограничением размера для предотвращения утечки памяти)
        dedup_key = f"{account.id}:{msg.id}"
        if dedup_key in self._replied_messages:
            return
        if len(self._replied_messages) >= self._max_replied_messages:
            self._replied_messages.clear()
        self._replied_messages.add(dedup_key)

        # Лимит на день
        daily = self._daily_replies.get(account.id, 0)
        if daily >= self._max_replies_per_day:
            return

        # Ночью не отвечаем
        if not self.human_sim.is_working_hours():
            return

        # Задержка перед ответом (30с - 5мин)
        delay = random.uniform(30, 300)
        logger.debug(f"Will reply in {delay:.0f}s to comment in {account.linked_channel_username}")
        await asyncio.sleep(delay)

        # Генерируем ответ
        reply_text = await self._generate_reply(msg.text, account.segment)
        if not reply_text:
            return

        # Отвечаем
        try:
            await msg.reply(reply_text)

            self._daily_replies[account.id] = daily + 1

            phone_masked = (
                account.phone[:4] + "***" + account.phone[-2:]
                if len(account.phone) > 6 else account.phone
            )
            logger.info(
                f"💬 Replied to comment in {account.linked_channel_username}: "
                f"\"{reply_text[:50]}...\" (via {phone_masked})"
            )

            # Логируем
            await self._log_reply(account, msg.text, reply_text)

            if self.notifier:
                await self.notifier.notify_action_success(
                    action_type="channel_reply",
                    account_phone=account.phone,
                    segment=account.segment or "",
                    channel=account.linked_channel_username or "",
                    content=reply_text[:100],
                )

        except FloodWaitError as e:
            logger.warning(f"FloodWait {e.seconds}s replying in own channel")
            await asyncio.sleep(e.seconds + 10)
        except Exception as e:
            logger.error(f"Failed to reply to comment: {e}")

    async def _generate_reply(self, comment_text: str, segment: Optional[str]) -> Optional[str]:
        """Сгенерировать ответ на комментарий."""
        tone = SEGMENT_TONES.get(segment or "zozh", SEGMENT_TONES["zozh"])

        system = REPLY_SYSTEM_PROMPT.format(segment_tone=tone)
        user_msg = f"Комментарий подписчика: {comment_text}\n\nОтветь коротко и дружелюбно."

        try:
            from shared.ai_clients.deepseek_client import DeepseekClient
            from shared.config.settings import settings as app_settings

            client = DeepseekClient(api_key=app_settings.DEEPSEEK_API_KEY)
            response = await client.generate_response(
                system_prompt=system,
                user_message=user_msg,
                temperature=0.8,
            )
            if response:
                return response.strip().strip('"')
        except ImportError:
            logger.warning("DeepseekClient not available")
        except Exception as e:
            logger.error(f"Failed to generate reply: {e}")

        return None

    async def _log_reply(
        self, account: UserBotAccount, comment: str, reply: str
    ) -> None:
        """Залогировать ответ в БД."""
        try:
            async with get_session() as session:
                action = TrafficAction(
                    tenant_id=self.tenant_id,
                    account_id=account.id,
                    action_type="channel_reply",
                    target_channel_id=account.linked_channel_id,
                    content=reply[:500],
                    status="success",
                    created_at=datetime.now(timezone.utc),
                )
                session.add(action)
                await session.commit()
        except Exception as e:
            logger.error(f"Failed to log reply: {e}")

    async def stop(self) -> None:
        """Остановить мониторинг."""
        logger.info("Stopping OwnChannelMonitor...")
        self._running = False
