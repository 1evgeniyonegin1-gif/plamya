"""
InviteManager — управление временными инвайт-ссылками через Telethon API.

Создаёт инвайт-ссылки с ограниченным сроком действия (TTL) для VIP канала.
Автоматически отзывает истёкшие ссылки и удаляет связанные посты.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Tuple

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from telethon import TelegramClient
from telethon.tl.functions.messages import (
    ExportChatInviteRequest,
    EditExportedChatInviteRequest,
    DeleteRevokedExportedChatInvitesRequest,
    GetExportedChatInvitesRequest
)
from telethon.tl.types import ChatInviteExported
from telethon.errors import ChatAdminRequiredError, FloodWaitError

from content_manager_bot.database.funnel_models import (
    InviteLink, InviteLinkStatus, ChannelTier
)
from shared.config.settings import settings

logger = logging.getLogger(__name__)


class InviteManager:
    """
    Управляет временными инвайт-ссылками для VIP канала.

    Использует Telethon API для создания/отзыва ссылок.
    Требует userbot аккаунт с правами администратора в VIP канале.
    """

    def __init__(
        self,
        session: AsyncSession,
        telethon_client: Optional[TelegramClient] = None
    ):
        self.session = session
        self.client = telethon_client

        # Настройки по умолчанию
        self.default_hours_valid = getattr(settings, 'invite_post_hours_valid', 6)
        self.default_usage_limit = getattr(settings, 'invite_post_usage_limit', 100)
        self.auto_delete_buffer_minutes = 30  # Удалять пост через 30 мин после истечения ссылки

    async def create_temporary_invite(
        self,
        target_channel: ChannelTier,
        hours_valid: Optional[int] = None,
        usage_limit: Optional[int] = None,
        title: str = "VIP доступ"
    ) -> Optional[InviteLink]:
        """
        Создаёт временную инвайт-ссылку через Telethon API.

        Args:
            target_channel: VIP канал для которого создаётся ссылка
            hours_valid: Часов действия (по умолчанию 6)
            usage_limit: Лимит использований (по умолчанию 100, None = безлимит)
            title: Название инвайт-ссылки для аналитики

        Returns:
            InviteLink или None при ошибке
        """
        if not self.client:
            logger.error("Telethon client не инициализирован")
            return None

        hours = hours_valid or self.default_hours_valid
        limit = usage_limit if usage_limit is not None else self.default_usage_limit
        expire_date = datetime.utcnow() + timedelta(hours=hours)

        try:
            # Telethon API: создаём инвайт-ссылку
            result = await self.client(ExportChatInviteRequest(
                peer=target_channel.channel_id,
                expire_date=int(expire_date.timestamp()),
                usage_limit=limit if limit > 0 else None,
                title=title,
                request_needed=False  # Без одобрения админа
            ))

            if not isinstance(result, ChatInviteExported):
                logger.error(f"Неожиданный ответ от Telegram: {type(result)}")
                return None

            # Сохраняем в БД
            invite_link = InviteLink(
                target_channel_id=target_channel.id,
                invite_link=result.link,
                telegram_invite_hash=result.link.split('+')[-1] if '+' in result.link else result.link.split('/')[-1],
                invite_title=title,
                expire_date=expire_date,
                usage_limit=limit if limit > 0 else None,
                status=InviteLinkStatus.ACTIVE.value
            )
            self.session.add(invite_link)
            await self.session.commit()
            await self.session.refresh(invite_link)

            logger.info(f"Создана инвайт-ссылка: {result.link} (TTL: {hours}ч, лимит: {limit})")
            return invite_link

        except ChatAdminRequiredError:
            logger.error(f"Нет прав администратора в канале {target_channel.channel_title}")
            return None
        except FloodWaitError as e:
            logger.warning(f"Flood wait: нужно подождать {e.seconds} секунд")
            return None
        except Exception as e:
            logger.exception(f"Ошибка создания инвайт-ссылки: {e}")
            return None

    async def revoke_invite(self, invite_link_id: int) -> bool:
        """
        Отзывает инвайт-ссылку досрочно.

        Args:
            invite_link_id: ID записи в invite_links

        Returns:
            True если успешно отозвана
        """
        result = await self.session.execute(
            select(InviteLink).where(InviteLink.id == invite_link_id)
        )
        invite = result.scalar_one_or_none()

        if not invite:
            logger.warning(f"Инвайт-ссылка #{invite_link_id} не найдена")
            return False

        if invite.status != InviteLinkStatus.ACTIVE.value:
            logger.info(f"Инвайт-ссылка #{invite_link_id} уже не активна: {invite.status}")
            return True

        if self.client:
            try:
                # Получаем channel_id через relationship
                target_result = await self.session.execute(
                    select(ChannelTier).where(ChannelTier.id == invite.target_channel_id)
                )
                target_channel = target_result.scalar_one_or_none()

                if target_channel:
                    await self.client(EditExportedChatInviteRequest(
                        peer=target_channel.channel_id,
                        link=invite.invite_link,
                        revoked=True
                    ))
                    logger.info(f"Инвайт-ссылка отозвана в Telegram: {invite.invite_link[:30]}...")
            except Exception as e:
                logger.warning(f"Не удалось отозвать ссылку в Telegram: {e}")
                # Продолжаем обновление статуса в БД

        # Обновляем статус в БД
        invite.mark_revoked()
        await self.session.commit()
        return True

    async def get_expired_invites(self) -> List[InviteLink]:
        """
        Возвращает все истёкшие но не обработанные инвайт-ссылки.

        Returns:
            Список InviteLink с expire_date < NOW() и status='active'
        """
        now = datetime.utcnow()
        result = await self.session.execute(
            select(InviteLink).where(
                and_(
                    InviteLink.status == InviteLinkStatus.ACTIVE.value,
                    InviteLink.expire_date.isnot(None),
                    InviteLink.expire_date <= now
                )
            )
        )
        return list(result.scalars().all())

    async def cleanup_expired_invites(self) -> int:
        """
        Фоновая задача: обрабатывает истёкшие инвайт-ссылки.

        Действия:
        1. Находит все истёкшие ссылки со статусом 'active'
        2. Помечает их как 'expired'
        3. (Опционально) Отзывает в Telegram API

        Returns:
            Количество обработанных ссылок
        """
        expired = await self.get_expired_invites()

        if not expired:
            return 0

        count = 0
        for invite in expired:
            try:
                # Помечаем как истёкшую
                invite.mark_expired()

                # Пробуем отозвать в Telegram (чтобы ссылка точно не работала)
                if self.client:
                    try:
                        target_result = await self.session.execute(
                            select(ChannelTier).where(ChannelTier.id == invite.target_channel_id)
                        )
                        target_channel = target_result.scalar_one_or_none()

                        if target_channel:
                            await self.client(EditExportedChatInviteRequest(
                                peer=target_channel.channel_id,
                                link=invite.invite_link,
                                revoked=True
                            ))
                    except Exception as e:
                        # Ссылка могла уже быть отозвана или истечь
                        logger.debug(f"Не удалось отозвать {invite.invite_link[:30]}: {e}")

                count += 1
                logger.info(f"Инвайт-ссылка #{invite.id} помечена как истёкшая")

            except Exception as e:
                logger.error(f"Ошибка обработки инвайт-ссылки #{invite.id}: {e}")

        await self.session.commit()
        logger.info(f"Обработано {count} истёкших инвайт-ссылок")
        return count

    async def get_posts_to_delete(self) -> List[Tuple[InviteLink, int, int]]:
        """
        Возвращает список постов для автоудаления.

        Returns:
            Список кортежей (InviteLink, channel_id, message_id)
        """
        # Импортируем Post здесь чтобы избежать circular import
        from content_manager_bot.database.models import Post

        now = datetime.utcnow()
        result = await self.session.execute(
            select(Post).where(
                and_(
                    Post.is_invite_post == True,
                    Post.auto_delete_at.isnot(None),
                    Post.auto_delete_at <= now,
                    Post.status == "published",
                    Post.channel_message_id.isnot(None)
                )
            )
        )
        posts = list(result.scalars().all())

        posts_to_delete = []
        for post in posts:
            if post.target_channel_id and post.channel_message_id:
                # Получаем Telegram channel_id
                channel_result = await self.session.execute(
                    select(ChannelTier).where(ChannelTier.id == post.target_channel_id)
                )
                channel = channel_result.scalar_one_or_none()

                if channel:
                    # Находим связанную инвайт-ссылку
                    invite_result = await self.session.execute(
                        select(InviteLink).where(InviteLink.invite_post_id == post.id)
                    )
                    invite = invite_result.scalar_one_or_none()

                    posts_to_delete.append((
                        invite,
                        channel.channel_id,
                        post.channel_message_id
                    ))

        return posts_to_delete

    async def get_active_invite_for_channel(self, target_channel_id: int) -> Optional[InviteLink]:
        """
        Возвращает активную инвайт-ссылку для канала (если есть).

        Args:
            target_channel_id: ID записи в channel_tiers

        Returns:
            InviteLink или None
        """
        now = datetime.utcnow()
        result = await self.session.execute(
            select(InviteLink).where(
                and_(
                    InviteLink.target_channel_id == target_channel_id,
                    InviteLink.status == InviteLinkStatus.ACTIVE.value,
                    or_(
                        InviteLink.expire_date.is_(None),
                        InviteLink.expire_date > now
                    )
                )
            ).order_by(InviteLink.created_at.desc()).limit(1)
        )
        return result.scalar_one_or_none()

    async def get_invite_stats(self, invite_link_id: int) -> dict:
        """
        Возвращает статистику инвайт-ссылки.

        Args:
            invite_link_id: ID записи в invite_links

        Returns:
            Dict со статистикой
        """
        result = await self.session.execute(
            select(InviteLink).where(InviteLink.id == invite_link_id)
        )
        invite = result.scalar_one_or_none()

        if not invite:
            return {}

        # Если есть Telethon клиент, пробуем получить актуальную статистику
        if self.client and invite.status == InviteLinkStatus.ACTIVE.value:
            try:
                target_result = await self.session.execute(
                    select(ChannelTier).where(ChannelTier.id == invite.target_channel_id)
                )
                target_channel = target_result.scalar_one_or_none()

                if target_channel:
                    invites_result = await self.client(GetExportedChatInvitesRequest(
                        peer=target_channel.channel_id,
                        admin_id=await self.client.get_me(),
                        limit=100
                    ))

                    for tg_invite in invites_result.invites:
                        if isinstance(tg_invite, ChatInviteExported) and tg_invite.link == invite.invite_link:
                            # Обновляем статистику из Telegram
                            invite.total_uses = tg_invite.usage or 0
                            await self.session.commit()
                            break
            except Exception as e:
                logger.debug(f"Не удалось получить статистику из Telegram: {e}")

        return {
            "id": invite.id,
            "link": invite.invite_link,
            "status": invite.status,
            "total_uses": invite.total_uses,
            "total_joins": invite.total_joins,
            "usage_limit": invite.usage_limit,
            "expire_date": invite.expire_date.isoformat() if invite.expire_date else None,
            "created_at": invite.created_at.isoformat() if invite.created_at else None,
            "is_expired": invite.is_expired,
            "is_exhausted": invite.is_exhausted
        }

    def calculate_auto_delete_time(self, expire_date: datetime) -> datetime:
        """
        Рассчитывает время автоудаления поста.

        Пост удаляется через N минут после истечения ссылки.

        Args:
            expire_date: Время истечения инвайт-ссылки

        Returns:
            Время автоудаления поста
        """
        return expire_date + timedelta(minutes=self.auto_delete_buffer_minutes)
