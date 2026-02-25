"""
Telegram Publisher — sends posts to Telegram channels via Bot API.

Uses the same bot token as content_manager_bot to send messages.
"""
import base64
from typing import Optional
from loguru import logger
from aiogram import Bot
from aiogram.types import BufferedInputFile

from shared.config.settings import settings as shared_settings
from ..config import settings


def _get_bot() -> Bot:
    """Create an aiogram Bot instance from the content manager bot token."""
    return Bot(token=settings.bot_token)


def _split_post(text: str, max_length: int = 900) -> list[str]:
    """Split long post into multiple messages by paragraphs."""
    if len(text) <= max_length:
        return [text]

    messages = []
    current = ""

    for paragraph in text.split('\n\n'):
        if len(paragraph) > max_length:
            if current:
                messages.append(current.strip())
                current = ""
            for line in paragraph.split('\n'):
                if len(current) + len(line) + 1 <= max_length:
                    current += ('\n' if current else '') + line
                else:
                    if current:
                        messages.append(current.strip())
                    current = line
        elif len(current) + len(paragraph) + 2 <= max_length:
            current += ('\n\n' if current else '') + paragraph
        else:
            if current:
                messages.append(current.strip())
            current = paragraph

    if current:
        messages.append(current.strip())

    return messages


async def publish_to_telegram(
    post_content: str,
    post_id: int,
    segment: Optional[str] = None,
    image_base64: Optional[str] = None,
) -> Optional[int]:
    """
    Publish a post to the appropriate Telegram channel.

    Returns the channel_message_id if successful, None if failed.
    """
    bot = _get_bot()

    try:
        # Determine target channel
        target_chat = None

        if segment and segment in shared_settings.thematic_channels:
            target_chat = shared_settings.thematic_channels[segment]
            logger.info(f"[PUBLISHER] Routing post #{post_id} to thematic channel: {target_chat} (segment={segment})")
        else:
            target_chat = shared_settings.channel_username
            logger.info(f"[PUBLISHER] Routing post #{post_id} to main channel: {target_chat}")

        if not target_chat:
            logger.error(f"[PUBLISHER] No target channel for post #{post_id}")
            return None

        # Add curator footer (only for main channel)
        curator_footer = ""
        if not segment:
            curator_footer = (
                f"\n\n━━━━━━━━━━━━━━━\n"
                f"❓ Есть вопросы? Спроси AI-Куратора → {shared_settings.curator_bot_username}"
            )

        # Split post into parts
        post_parts = _split_post(post_content)
        if post_parts:
            post_parts[-1] = post_parts[-1] + curator_footer

        channel_message = None

        # Publish with or without image
        if image_base64:
            try:
                image_bytes = base64.b64decode(image_base64)
                image_file = BufferedInputFile(image_bytes, filename=f"post_{post_id}.jpg")

                first_part = post_parts[0] if post_parts else ""
                if len(first_part) > 1024:
                    first_part = first_part[:1020] + "..."

                channel_message = await bot.send_photo(
                    chat_id=target_chat,
                    photo=image_file,
                    caption=first_part,
                    parse_mode="HTML",
                )

                for part in post_parts[1:]:
                    await bot.send_message(
                        chat_id=target_chat,
                        text=part,
                        parse_mode="HTML",
                    )
            except Exception as img_err:
                logger.error(f"[PUBLISHER] Image send failed for post #{post_id}: {img_err}, fallback to text")
                for i, part in enumerate(post_parts):
                    msg = await bot.send_message(
                        chat_id=target_chat,
                        text=part,
                        parse_mode="HTML",
                    )
                    if i == 0:
                        channel_message = msg
        else:
            for i, part in enumerate(post_parts):
                msg = await bot.send_message(
                    chat_id=target_chat,
                    text=part,
                    parse_mode="HTML",
                )
                if i == 0:
                    channel_message = msg

        message_id = channel_message.message_id if channel_message else None
        logger.info(f"[PUBLISHER] Post #{post_id} published, message_id={message_id}")
        return message_id

    except Exception as e:
        logger.error(f"[PUBLISHER] Failed to publish post #{post_id}: {e}")
        raise
    finally:
        await bot.session.close()
