"""
VIP Welcome Handler — приветствие новых участников VIP канала.

При вступлении пользователя в VIP канал:
1. Верифицирует как партнёра NL (через curator_bot БД)
2. Трекает конверсию (FunnelConversion)
3. Отправляет приветственное DM через бота
"""
import logging
from typing import Optional

from aiogram import Router, F
from aiogram.types import ChatMemberUpdated
from aiogram.filters import ChatMemberUpdatedFilter, IS_NOT_MEMBER, IS_MEMBER

from shared.config.settings import settings
from shared.database.base import AsyncSessionLocal
from content_manager_bot.verification import PartnerVerifier

logger = logging.getLogger(__name__)

router = Router()

# ID VIP канала из settings
VIP_CHANNEL_ID = getattr(settings, "vip_channel_id", None)


@router.chat_member(ChatMemberUpdatedFilter(IS_NOT_MEMBER >> IS_MEMBER))
async def on_user_joined_channel(event: ChatMemberUpdated):
    """
    Обработчик: пользователь вступил в канал/группу.

    Проверяет, что это VIP канал, и запускает верификацию.
    """
    # Проверяем что это наш VIP канал
    if VIP_CHANNEL_ID and event.chat.id != int(VIP_CHANNEL_ID):
        return

    user = event.new_chat_member.user
    if user.is_bot:
        return

    logger.info(
        f"New VIP member: {user.first_name} (@{user.username}, id={user.id})"
    )

    async with AsyncSessionLocal() as session:
        verifier = PartnerVerifier(session)
        conversion = await verifier.verify_and_track(
            telegram_id=user.id,
            username=user.username,
            first_name=user.first_name,
        )

    # Отправляем приветственное DM
    try:
        if conversion.is_verified_partner:
            welcome_text = (
                f"Привет, {user.first_name}! 👋\n\n"
                f"Добро пожаловать в VIP-канал APEXFLOW!\n\n"
                f"Здесь ты найдёшь:\n"
                f"• Лайв-контент и закулисье\n"
                f"• Инструкции по системе\n"
                f"• Доступ к Partner Panel\n\n"
                f"Если есть вопросы — пиши @nl_curator_bot"
            )
        else:
            welcome_text = (
                f"Привет, {user.first_name}! 👋\n\n"
                f"Ты попал в VIP-канал.\n"
                f"Чтобы получить полный доступ, зарегистрируйся как партнёр NL "
                f"через @nl_curator_bot"
            )

        await event.bot.send_message(chat_id=user.id, text=welcome_text)
        logger.info(f"Welcome DM sent to {user.id}")

    except Exception as e:
        # Пользователь мог не начать диалог с ботом
        logger.debug(f"Could not send welcome DM to {user.id}: {e}")
