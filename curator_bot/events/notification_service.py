"""
Сервис отправки уведомлений пользователям.

Отправляет персонализированные уведомления о новых постах.
"""
from loguru import logger

from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest

from shared.config.settings import settings


# Названия типов постов для уведомлений
POST_TYPE_NAMES = {
    "product": "📦 Новый продукт",
    "motivation": "💪 Мотивация",
    "tips": "💡 Полезный совет",
    "success_story": "🏆 История успеха",
    "news": "📰 Новости NL",
    "promo": "🎁 Акция"
}


async def send_post_notification(bot: Bot, user, post_type: str, content_preview: str):
    """
    Отправить персонализированное уведомление о новом посте.

    Args:
        bot: Экземпляр бота
        user: Объект пользователя из БД (User model)
        post_type: Тип поста (product, motivation, tips и т.д.)
        content_preview: Превью контента (первые 200 символов)
    """
    # Персонализация приветствия по user_intent
    first_name = user.first_name or "друг"

    if user.user_intent == "business":
        greeting = f"Йо, {first_name}! 🔥"
    elif user.user_intent == "client":
        greeting = f"Привет, {first_name}! 😊"
    else:
        greeting = f"Привет, {first_name}! 👋"

    type_name = POST_TYPE_NAMES.get(post_type, "📰 Новое")

    # Формируем текст сообщения
    message_text = f"""{greeting}

{type_name}:

{content_preview}...

Смотри в группе 👇"""

    # Кнопки для взаимодействия
    # Формируем ссылку на группу (только если group_id валидный)
    buttons = []

    if settings.group_id and settings.group_id.strip() and settings.group_id.startswith("-100"):
        group_id_for_link = settings.group_id.replace("-100", "")
        buttons.append([InlineKeyboardButton(
            text="📖 Читать полностью",
            url=f"https://t.me/c/{group_id_for_link}"
        )])

    buttons.append([InlineKeyboardButton(
        text="❓ Задать вопрос",
        callback_data="ask_curator"
    )])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    try:
        await bot.send_message(
            chat_id=user.telegram_id,
            text=message_text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        logger.debug(f"Notification sent to user {user.telegram_id} ({first_name})")

    except TelegramForbiddenError:
        # Пользователь заблокировал бота — помечаем в БД
        logger.warning(f"User {user.telegram_id} blocked the bot")
        await _mark_user_blocked(user.telegram_id)

    except TelegramBadRequest as e:
        # Другие ошибки Telegram
        logger.error(f"Bad request sending to {user.telegram_id}: {e}")

    except Exception as e:
        logger.error(f"Failed to send notification to {user.telegram_id}: {e}")


async def _mark_user_blocked(telegram_id: int):
    """
    Пометить пользователя как заблокировавшего бота.

    Args:
        telegram_id: Telegram ID пользователя
    """
    try:
        from shared.database.base import AsyncSessionLocal
        from curator_bot.database.models import User
        from sqlalchemy import select

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            user = result.scalar_one_or_none()

            if user:
                user.is_blocked = True
                await session.commit()
                logger.info(f"User {telegram_id} marked as blocked")

    except Exception as e:
        logger.error(f"Failed to mark user {telegram_id} as blocked: {e}")
