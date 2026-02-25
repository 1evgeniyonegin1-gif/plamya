#!/usr/bin/env python
"""
Добавление целевых каналов для мониторинга.

Каналы разделены по сегментам:
- zozh: ЗОЖ, питание, фитнес, здоровье
- business: бизнес, доход, предпринимательство, карьера
- universal: мотивация, саморазвитие (подходят всем сегментам)
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from sqlalchemy import select
from telethon import TelegramClient
from telethon.sessions import StringSession

from traffic_engine.config import settings
from traffic_engine.database import get_session
from traffic_engine.database.models import TargetChannel, Tenant, UserBotAccount


# Формат: (username, title, comment_strategy, segment)
# segment: "zozh", "business", "universal" (для всех)
TARGET_CHANNELS = [
    # === ЗОЖ / Питание / Фитнес (segment=zozh) ===
    ("zdorovie_ru", "Здоровье", "supportive", "zozh"),
    ("pp_recepty", "ПП рецепты", "supportive", "zozh"),
    ("pravilnoe_pitanie", "Правильное питание", "supportive", "zozh"),
    ("fitness_motivation", "Фитнес мотивация", "smart", "zozh"),
    ("workout_ru", "Тренировки", "smart", "zozh"),
    ("zhenskoe_zdorovie", "Женское здоровье", "supportive", "zozh"),
    ("pohudet_ru", "Похудение", "supportive", "zozh"),
    ("dieta_tips", "Советы по диете", "supportive", "zozh"),

    # === Бизнес / Доход / Карьера (segment=business) ===
    ("ikniga", "Книги на миллион", "supportive", "business"),             # 923K
    ("grebenukm", "Михаил Гребенюк", "smart", "business"),                # 282K
    ("prostoecon", "Простая экономика", "expert", "business"),             # 202K
    ("portnyaginlive", "Дима Портнягин", "supportive", "business"),        # 103K
    ("careerspace", "careerspace", "supportive", "business"),              # 139K
    ("normrabota", "Норм работа", "supportive", "business"),               # 111K
    ("oskar_hartmann", "Оскар Хартманн", "smart", "business"),             # 88K
    ("addmeto", "addmeto", "supportive", "business"),                      # 74K
    ("morejobs", "Больше джобсов", "supportive", "business"),              # 65K
    ("mspiridonov", "Максим Спиридонов", "supportive", "business"),        # 63K
    ("sberstartup", "СберСтартап", "smart", "business"),                   # 62K
    ("startupoftheday", "Стартап дня", "smart", "business"),               # 60K

    # === Универсальные — мотивация, саморазвитие (segment=universal) ===
    ("silaslovv", "Сила Слов", "supportive", "universal"),                 # 120K
    ("anettaorlova", "Анетта Орлова", "supportive", "universal"),          # 42K
    ("guzenuk", "Филипп Гузенюк", "smart", "universal"),                   # 22K
    ("stoicstrategy", "StoicStrategy", "smart", "universal"),              # 19K
]

TENANT_NAME = "nl_international"


async def get_channel_info(client: TelegramClient, username: str) -> dict | None:
    """Получить информацию о канале через Telethon."""
    try:
        entity = await client.get_entity(username)
        return {
            "channel_id": entity.id,
            "title": entity.title if hasattr(entity, 'title') else username,
            "username": entity.username,
        }
    except Exception as e:
        logger.warning(f"Could not get info for @{username}: {e}")
        return None


async def main():
    """Добавить каналы в базу данных."""
    logger.info("=== Добавление целевых каналов ===")
    logger.info(f"Всего каналов: {len(TARGET_CHANNELS)}")

    # Получаем tenant
    async with get_session() as session:
        result = await session.execute(
            select(Tenant).where(Tenant.name == TENANT_NAME)
        )
        tenant = result.scalar_one_or_none()
        if not tenant:
            logger.error(f"Tenant '{TENANT_NAME}' не найден!")
            return

        tenant_id = tenant.id
        logger.info(f"Tenant ID: {tenant_id}")

        # Получаем первый аккаунт для проверки каналов
        result = await session.execute(
            select(UserBotAccount).where(
                UserBotAccount.tenant_id == tenant_id,
                UserBotAccount.status.in_(["active", "warming"])
            ).limit(1)
        )
        account = result.scalar_one_or_none()

        if not account:
            logger.error("Нет активных аккаунтов для проверки каналов!")
            return

    # Подключаемся через Telethon
    client = TelegramClient(
        StringSession(account.session_string),
        settings.telegram_api_id,
        settings.telegram_api_hash
    )

    await client.connect()

    if not await client.is_user_authorized():
        logger.error("Аккаунт не авторизован!")
        await client.disconnect()
        return

    logger.info(f"Подключились как: {account.first_name}")

    added = 0
    skipped = 0
    failed = 0

    async with get_session() as session:
        for username, title, strategy, segment in TARGET_CHANNELS:
            # Проверяем, не добавлен ли уже
            result = await session.execute(
                select(TargetChannel).where(TargetChannel.username == username)
            )
            existing = result.scalar_one_or_none()

            if existing:
                # Обновляем сегмент если изменился
                if existing.segment != segment:
                    existing.segment = segment
                    logger.info(f"🔄 @{username} — обновлён сегмент → {segment}")
                else:
                    logger.info(f"⏭️ @{username} уже добавлен (segment={segment})")
                skipped += 1
                continue

            # Получаем информацию о канале
            info = await get_channel_info(client, username)

            if not info:
                logger.warning(f"❌ @{username} - не найден или недоступен")
                failed += 1
                await asyncio.sleep(2)
                continue

            # Добавляем канал с сегментом
            channel = TargetChannel(
                tenant_id=tenant_id,
                channel_id=info["channel_id"],
                username=info["username"] or username,
                title=info["title"] or title,
                is_active=True,
                priority=5,
                segment=segment,
                comment_strategy=strategy,
                max_delay_minutes=10,
                skip_ads=True,
                skip_reposts=True,
                min_post_length=100,
            )
            session.add(channel)
            logger.info(f"✅ @{username} ({info['title']}) — segment={segment}")
            added += 1

            # Небольшая задержка между запросами
            await asyncio.sleep(3)

        await session.commit()

    await client.disconnect()

    logger.info("=" * 50)
    logger.info(f"Добавлено: {added}")
    logger.info(f"Пропущено (уже есть): {skipped}")
    logger.info(f"Не найдено: {failed}")
    logger.info("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
