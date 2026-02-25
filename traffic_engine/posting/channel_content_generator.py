"""
Channel Content Generator — генерация контента для тематических каналов.

Создаёт посты в стиле Данила, адаптированные под сегмент канала.
Использует Deepseek для генерации, CONTENT_SEGMENT_OVERLAYS для стиля.
"""

import random
from datetime import datetime, timedelta, timezone
from typing import Optional, List

from loguru import logger
from sqlalchemy import select, func, and_

from traffic_engine.database import get_session
from traffic_engine.database.models import ChannelPost, UserBotAccount


def _get_style_dna():
    """Lazy import стиля Данила из content_manager_bot (отдельный процесс)."""
    from content_manager_bot.ai.style_dna import (
        CONTENT_SEGMENT_OVERLAYS,
        get_content_segment_overlay,
        ANTI_AI_WORDS_RU,
    )
    return CONTENT_SEGMENT_OVERLAYS, get_content_segment_overlay, ANTI_AI_WORDS_RU


# Типы постов для каналов
CHANNEL_POST_TYPES = {
    "lifestyle": "Наблюдение из жизни, личный опыт, мысль дня",
    "tips": "Полезный совет по теме сегмента",
    "motivation": "Мотивационный пост, история, инсайт",
    "product_mention": "Естественное упоминание продукта NL в контексте",
    "channel_promo": "Анонс — 'написал пост об этом подробнее' с ссылкой или без",
}

# Расписание постов: часы публикации (MSK = UTC+3)
DEFAULT_POST_HOURS = [9, 13, 18]  # Утро, обед, вечер


SYSTEM_PROMPT = """Ты — {persona_name}. Пишешь пост для своего Telegram-канала.

{persona_desc}

{segment_tone}

ПРАВИЛА:
1. Пиши от первого лица, как будто делишься мыслями с подписчиками
2. Не используй: {anti_words}
3. Длина: 3-8 предложений (150-500 символов)
4. Не начинай с вопроса, начинай с утверждения или истории
5. Не пиши хештеги, не ставь больше 2 эмодзи
6. Текст должен быть живым, как сообщение другу
7. НИКАКИХ списков, пунктов, нумерации — только текст
8. Тип поста: {post_type_desc}
"""


async def generate_channel_post(
    account: UserBotAccount,
    post_type: Optional[str] = None,
) -> Optional[str]:
    """
    Сгенерировать пост для тематического канала аккаунта.

    Args:
        account: Аккаунт с привязанным каналом
        post_type: Тип поста (или случайный)

    Returns:
        Текст поста или None
    """
    segment = account.segment or "zozh"

    try:
        CONTENT_SEGMENT_OVERLAYS, get_content_segment_overlay, ANTI_AI_WORDS_RU = _get_style_dna()
    except ImportError:
        logger.warning("content_manager_bot.ai.style_dna not available")
        return None

    overlay = get_content_segment_overlay(segment)

    if not overlay:
        logger.warning(f"No overlay for segment {segment}")
        overlay = CONTENT_SEGMENT_OVERLAYS.get("zozh", {})

    # Выбираем тип поста
    if not post_type:
        post_type = random.choice(list(CHANNEL_POST_TYPES.keys()))

    post_type_desc = CHANNEL_POST_TYPES.get(post_type, "Свободная тема")

    # Выбираем тему из оверлея
    topics = overlay.get("topics_override", [])
    topic = random.choice(topics) if topics else "свободная тема"

    # Формируем промпт
    anti_words_sample = ", ".join(random.sample(ANTI_AI_WORDS_RU, min(15, len(ANTI_AI_WORDS_RU))))

    system = SYSTEM_PROMPT.format(
        persona_name="Данил",
        persona_desc="21 год, строю AI-систему для бизнеса, после армии, живу с батей",
        segment_tone=overlay.get("tone", ""),
        anti_words=anti_words_sample,
        post_type_desc=post_type_desc,
    )

    user_msg = f"Напиши пост на тему: {topic}"

    # Генерируем через Deepseek
    try:
        from shared.ai_clients.deepseek_client import DeepseekClient
        from shared.config.settings import settings as app_settings

        client = DeepseekClient(api_key=app_settings.DEEPSEEK_API_KEY)
        response = await client.generate_response(
            system_prompt=system,
            user_message=user_msg,
            temperature=0.9,
        )

        if response:
            # Чистим от кавычек и лишних символов
            text = response.strip().strip('"').strip("«»")
            logger.info(f"Generated channel post ({segment}/{post_type}): {text[:60]}...")
            return text

    except ImportError:
        logger.warning("DeepseekClient not available, using template fallback")
    except Exception as e:
        logger.error(f"Failed to generate channel post: {e}")

    return None


async def schedule_posts_for_account(
    account: UserBotAccount,
    tenant_id: int,
    days_ahead: int = 1,
    posts_per_day: int = 2,
) -> int:
    """
    Сгенерировать и запланировать посты для аккаунта.

    Args:
        account: Аккаунт с linked_channel_id
        tenant_id: ID тенанта
        days_ahead: На сколько дней вперёд планировать
        posts_per_day: Постов в день

    Returns:
        Количество запланированных постов
    """
    if not account.linked_channel_id:
        logger.debug(f"Account {account.id} has no linked channel, skipping")
        return 0

    scheduled = 0
    now = datetime.now(timezone.utc)

    for day_offset in range(days_ahead):
        day = now + timedelta(days=day_offset)

        # Выбираем часы публикации
        hours = random.sample(DEFAULT_POST_HOURS, min(posts_per_day, len(DEFAULT_POST_HOURS)))
        hours.sort()

        for hour in hours:
            # MSK (UTC+3) → UTC через timedelta (безопасно для любых часов)
            day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
            scheduled_at = (
                day_start
                + timedelta(hours=hour)
                - timedelta(hours=3)  # MSK → UTC
                + timedelta(minutes=random.randint(0, 30))
            )

            if scheduled_at <= now:
                continue

            # Проверяем нет ли уже запланированного поста в этот час
            existing = await _check_existing_post(
                account.id, account.linked_channel_id, scheduled_at
            )
            if existing:
                continue

            # Генерируем контент
            post_type = random.choice(list(CHANNEL_POST_TYPES.keys()))
            content = await generate_channel_post(account, post_type)

            if not content:
                continue

            # Сохраняем в БД
            try:
                async with get_session() as session:
                    post = ChannelPost(
                        tenant_id=tenant_id,
                        channel_id=account.linked_channel_id,
                        account_id=account.id,
                        post_type=post_type,
                        content=content,
                        status="pending",
                        scheduled_at=scheduled_at,
                    )
                    session.add(post)
                    await session.commit()
                    scheduled += 1

                    logger.info(
                        f"Scheduled {post_type} post for {scheduled_at.strftime('%d.%m %H:%M')} UTC "
                        f"to channel {account.linked_channel_username or account.linked_channel_id}"
                    )
            except Exception as e:
                logger.error(f"Failed to save scheduled post: {e}")

    return scheduled


async def _check_existing_post(
    account_id: int,
    channel_id: int,
    scheduled_at: datetime,
) -> bool:
    """Проверить есть ли уже пост в этот час."""
    try:
        hour_start = scheduled_at.replace(minute=0, second=0)
        hour_end = hour_start + timedelta(hours=1)

        async with get_session() as session:
            result = await session.execute(
                select(func.count(ChannelPost.id))
                .where(and_(
                    ChannelPost.account_id == account_id,
                    ChannelPost.channel_id == channel_id,
                    ChannelPost.scheduled_at >= hour_start,
                    ChannelPost.scheduled_at < hour_end,
                    ChannelPost.status != "cancelled",
                ))
            )
            count = result.scalar() or 0
            return count > 0
    except Exception as e:
        logger.error(f"Failed to check existing post: {e}")
        return False
