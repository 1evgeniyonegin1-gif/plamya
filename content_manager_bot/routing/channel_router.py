"""
ChannelRouter — маршрутизация контента по каналам воронки.

Определяет куда публиковать пост на основе:
- Типа поста (invite_teaser, vip_content, обычный)
- Сегмента (zozh, mama, business)
- Расписания (когда публиковать инвайт-посты)
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, List
from zoneinfo import ZoneInfo

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from content_manager_bot.database.funnel_models import (
    ChannelTier, TierLevel, ChannelStatus, ChannelSegment
)
from shared.config.settings import settings

logger = logging.getLogger(__name__)

# Московское время
MSK = ZoneInfo("Europe/Moscow")


class ChannelRouter:
    """
    Маршрутизирует контент в правильный канал воронки.

    Логика:
    - invite_teaser → публикуется в публичный канал (public_warmup)
    - vip_content → публикуется в VIP канал (private_vip)
    - обычный пост → публикуется в публичные каналы по сегменту
    """

    def __init__(self, session: AsyncSession):
        self.session = session

        # Настройки из settings (можно переопределить через .env)
        self.invite_post_hours = getattr(settings, 'invite_post_schedule_hours', [18, 19, 20, 21])
        self.invite_post_min_days = getattr(settings, 'invite_post_min_days', 2)
        self.invite_post_weekdays = getattr(settings, 'invite_post_weekdays', [0, 1, 2, 3, 4, 5])  # Пн-Сб

    async def get_vip_channel(self) -> Optional[ChannelTier]:
        """
        Возвращает VIP канал.

        Returns:
            ChannelTier или None если не настроен
        """
        result = await self.session.execute(
            select(ChannelTier).where(
                and_(
                    ChannelTier.tier_level == TierLevel.PRIVATE_VIP.value,
                    ChannelTier.status == ChannelStatus.ACTIVE.value
                )
            ).limit(1)
        )
        return result.scalar_one_or_none()

    async def get_public_channels(
        self,
        segment: str = "universal",
        traffic_source_only: bool = False
    ) -> List[ChannelTier]:
        """
        Возвращает публичные каналы для прогрева.

        Args:
            segment: Сегмент контента (zozh, mama, business, universal)
            traffic_source_only: Только каналы с is_traffic_source=True

        Returns:
            Список каналов
        """
        conditions = [
            ChannelTier.tier_level == TierLevel.PUBLIC_WARMUP.value,
            ChannelTier.status == ChannelStatus.ACTIVE.value
        ]

        if segment != "universal":
            conditions.append(
                (ChannelTier.segment == segment) | (ChannelTier.segment == "universal")
            )

        if traffic_source_only:
            conditions.append(ChannelTier.is_traffic_source == True)

        result = await self.session.execute(
            select(ChannelTier).where(and_(*conditions))
        )
        return list(result.scalars().all())

    async def get_target_channel(
        self,
        post_type: str,
        segment: str = "universal",
        tier_preference: Optional[str] = None
    ) -> Optional[ChannelTier]:
        """
        Определяет целевой канал для публикации поста.

        Args:
            post_type: Тип поста (invite_teaser, vip_content, product, motivation, etc.)
            segment: Сегмент контента
            tier_preference: Предпочтительный уровень канала (опционально)

        Returns:
            ChannelTier для публикации или None

        Логика:
        - invite_teaser → любой публичный канал, который разрешает инвайт-посты
        - vip_content → только VIP канал
        - остальные → публичные каналы по сегменту
        """
        # VIP контент → только VIP канал
        if post_type == "vip_content":
            return await self.get_vip_channel()

        # Инвайт-пост → публичный канал с разрешением на инвайты
        if post_type == "invite_teaser":
            channels = await self.get_channels_for_invite()
            if channels:
                # Выбираем канал, который давно не получал инвайт-пост
                channels.sort(key=lambda c: c.last_invite_post_at or datetime.min)
                return channels[0]
            return None

        # Явное предпочтение уровня
        if tier_preference == TierLevel.PRIVATE_VIP.value:
            return await self.get_vip_channel()

        # Обычные посты → публичные каналы
        channels = await self.get_public_channels(segment=segment)
        if channels:
            # Можно добавить логику round-robin или по engagement_rate
            return channels[0]

        # Fallback: возвращаем None (будет использован hardcoded канал из settings)
        return None

    async def get_channels_for_invite(self) -> List[ChannelTier]:
        """
        Возвращает публичные каналы, которые могут публиковать инвайт-посты.

        Returns:
            Список каналов с allow_invite_posts=True и связанным VIP каналом
        """
        result = await self.session.execute(
            select(ChannelTier).where(
                and_(
                    ChannelTier.tier_level == TierLevel.PUBLIC_WARMUP.value,
                    ChannelTier.status == ChannelStatus.ACTIVE.value,
                    ChannelTier.allow_invite_posts == True,
                    ChannelTier.vip_channel_id.isnot(None)
                )
            )
        )
        channels = list(result.scalars().all())

        # Фильтруем по времени последнего инвайт-поста
        eligible = [c for c in channels if c.can_publish_invite(self.invite_post_min_days)]
        return eligible

    def should_publish_invite_now(self) -> bool:
        """
        Проверяет, подходящее ли сейчас время для публикации инвайт-поста.

        Условия:
        - Текущий час в диапазоне invite_post_hours (по умолчанию 18:00-21:00 MSK)
        - Сегодня не воскресенье (если настроено)

        Returns:
            True если можно публиковать
        """
        now_msk = datetime.now(MSK)

        # Проверяем день недели (0=Пн, 6=Вс)
        if now_msk.weekday() not in self.invite_post_weekdays:
            logger.debug(f"Сегодня {now_msk.strftime('%A')} — не день для инвайт-постов")
            return False

        # Проверяем час
        if now_msk.hour not in self.invite_post_hours:
            logger.debug(f"Сейчас {now_msk.hour}:00 MSK — не время для инвайт-постов")
            return False

        return True

    async def should_publish_invite_post(self) -> bool:
        """
        Комплексная проверка: нужно ли сейчас публиковать инвайт-пост.

        Проверяет:
        1. Подходящее время (час, день недели)
        2. Есть каналы, которые могут публиковать инвайт-посты
        3. Прошло достаточно времени с последнего инвайт-поста

        Returns:
            True если пора публиковать инвайт-пост
        """
        # Проверка времени
        if not self.should_publish_invite_now():
            return False

        # Проверяем есть ли каналы для инвайта
        channels = await self.get_channels_for_invite()
        if not channels:
            logger.debug("Нет каналов, готовых к публикации инвайт-постов")
            return False

        logger.info(f"Найдено {len(channels)} каналов для инвайт-поста")
        return True

    async def get_fallback_channel_id(self) -> int:
        """
        Возвращает fallback channel_id если нет каналов в БД.

        Использует settings.channel_username или VIP_CHANNEL_ID.

        Returns:
            channel_id из настроек
        """
        # Пробуем получить из settings
        vip_channel_id = getattr(settings, 'vip_channel_id', None)
        if vip_channel_id:
            return int(vip_channel_id)

        # Fallback на существующий channel_username (нужно будет резолвить)
        logger.warning("VIP канал не настроен в БД и settings, используем legacy channel")
        return None

    async def update_last_invite_post(self, channel_id: int) -> None:
        """
        Обновляет время последнего инвайт-поста для канала.

        Args:
            channel_id: ID записи в channel_tiers
        """
        result = await self.session.execute(
            select(ChannelTier).where(ChannelTier.id == channel_id)
        )
        channel = result.scalar_one_or_none()
        if channel:
            channel.last_invite_post_at = datetime.utcnow()
            channel.total_posts += 1
            await self.session.commit()
            logger.info(f"Обновлено last_invite_post_at для канала {channel.channel_title}")

    async def get_channel_by_telegram_id(self, telegram_channel_id: int) -> Optional[ChannelTier]:
        """
        Находит канал по Telegram channel_id.

        Args:
            telegram_channel_id: ID канала в Telegram (например -1001234567890)

        Returns:
            ChannelTier или None
        """
        result = await self.session.execute(
            select(ChannelTier).where(ChannelTier.channel_id == telegram_channel_id)
        )
        return result.scalar_one_or_none()

    async def ensure_channel_exists(
        self,
        telegram_channel_id: int,
        username: Optional[str] = None,
        title: str = "Unknown Channel",
        tier_level: str = TierLevel.PUBLIC_WARMUP.value,
        segment: str = "universal"
    ) -> ChannelTier:
        """
        Создаёт канал если не существует, или возвращает существующий.

        Args:
            telegram_channel_id: ID канала в Telegram
            username: @username канала
            title: Название канала
            tier_level: Уровень воронки
            segment: Сегмент контента

        Returns:
            ChannelTier (новый или существующий)
        """
        channel = await self.get_channel_by_telegram_id(telegram_channel_id)
        if channel:
            return channel

        # Создаём новый канал
        channel = ChannelTier(
            channel_id=telegram_channel_id,
            channel_username=username,
            channel_title=title,
            tier_level=tier_level,
            segment=segment,
            status=ChannelStatus.ACTIVE.value
        )
        self.session.add(channel)
        await self.session.commit()
        await self.session.refresh(channel)

        logger.info(f"Создан новый канал: {channel}")
        return channel
