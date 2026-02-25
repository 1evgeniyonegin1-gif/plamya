"""
PartnerVerifier — проверка, является ли пользователь зарегистрированным партнёром NL.

Используется для:
- Допуска в VIP канал (только верифицированные партнёры)
- Трекинга конверсий (FunnelConversion)
"""
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from content_manager_bot.database.funnel_models import FunnelConversion

logger = logging.getLogger(__name__)


class PartnerVerifier:
    """
    Проверяет статус партнёра NL International через curator_bot БД.

    Используется общая база данных — curator_bot.database.models.User
    доступна через тот же AsyncSessionLocal.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def is_nl_partner(self, telegram_id: int) -> bool:
        """
        Проверяет, зарегистрирован ли пользователь как партнёр NL.

        Args:
            telegram_id: Telegram user ID

        Returns:
            True если user_type == 'partner'
        """
        try:
            from curator_bot.database.models import User

            result = await self.session.execute(
                select(User).where(
                    User.telegram_id == telegram_id,
                    User.is_active == True,
                )
            )
            user = result.scalar_one_or_none()

            if not user:
                logger.debug(f"User {telegram_id} not found in curator_bot DB")
                return False

            is_partner = user.user_type == "partner"
            logger.info(
                f"User {telegram_id}: type={user.user_type}, "
                f"qualification={user.qualification}, is_partner={is_partner}"
            )
            return is_partner

        except Exception as e:
            logger.error(f"Error checking partner status for {telegram_id}: {e}")
            return False

    async def get_partner_info(self, telegram_id: int) -> Optional[dict]:
        """
        Получает информацию о партнёре.

        Returns:
            Dict с данными или None
        """
        try:
            from curator_bot.database.models import User

            result = await self.session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            user = result.scalar_one_or_none()

            if not user:
                return None

            return {
                "telegram_id": user.telegram_id,
                "first_name": user.first_name,
                "username": user.username,
                "user_type": user.user_type,
                "qualification": user.qualification,
                "lead_score": user.lead_score,
                "is_active": user.is_active,
            }

        except Exception as e:
            logger.error(f"Error getting partner info for {telegram_id}: {e}")
            return None

    async def verify_and_track(
        self,
        telegram_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        invite_link_id: Optional[int] = None,
        source_channel_id: Optional[int] = None,
    ) -> FunnelConversion:
        """
        Верифицирует пользователя и создаёт запись конверсии.

        Args:
            telegram_id: Telegram user ID
            username: @username
            first_name: Имя
            invite_link_id: ID инвайт-ссылки (если пришёл по ссылке)
            source_channel_id: ID канала-источника

        Returns:
            FunnelConversion запись
        """
        # Проверяем, есть ли уже конверсия
        existing = await self.session.execute(
            select(FunnelConversion).where(
                FunnelConversion.user_id == telegram_id
            )
        )
        conversion = existing.scalar_one_or_none()

        if conversion:
            logger.info(f"Conversion already exists for user {telegram_id}: {conversion.status}")
            return conversion

        # Проверяем статус партнёра
        is_partner = await self.is_nl_partner(telegram_id)
        partner_info = await self.get_partner_info(telegram_id) if is_partner else None

        # Создаём запись конверсии
        conversion = FunnelConversion(
            user_id=telegram_id,
            username=username,
            first_name=first_name,
            invite_link_id=invite_link_id,
            source_channel_id=source_channel_id,
            is_verified_partner=is_partner,
            verified_at=datetime.utcnow() if is_partner else None,
            partner_level=partner_info.get("qualification") if partner_info else None,
            status="verified" if is_partner else "joined",
        )

        self.session.add(conversion)
        await self.session.commit()
        await self.session.refresh(conversion)

        logger.info(
            f"Funnel conversion tracked: user={telegram_id}, "
            f"verified={is_partner}, status={conversion.status}"
        )
        return conversion
