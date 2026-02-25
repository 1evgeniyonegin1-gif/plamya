#!/usr/bin/env python
"""
APEXFLOW — Обновление профилей аккаунтов на NL International персоны.

Переключает 4 аккаунта с инфобизнес-персон на NL:
- Лёша Лаймов → Анна (Нутрициолог)
- Карина → Елена (Мама двоих)
- Люба → Ольга (Фитнес)
- Кира → Михаил (ЗОЖ)

Запуск:
    python scripts/traffic_engine/update_profiles_to_nl.py

Требуется:
    - Активные сессии Telethon для всех аккаунтов
    - Подключение к БД
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from loguru import logger
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.account import UpdateProfileRequest
from telethon.tl.functions.photos import DeletePhotosRequest, UploadProfilePhotoRequest

from traffic_engine.config import settings
from traffic_engine.database import get_session
from traffic_engine.database.models import UserBotAccount

# Маппинг старых аккаунтов на новые NL персоны
PROFILE_MAPPING = {
    # username -> new profile
    "lemonlime192": {
        "first_name": "Анна",
        "last_name": "",
        "bio": "Нутрициолог 🥗 | -12 кг за 3 мес | Помогаю с питанием",
    },
    "karinko_o": {
        "first_name": "Елена",
        "last_name": "",
        "bio": "Мама двоих 👶 | ЗОЖ и энергия | Energy Diet",
    },
    "lyuba_ok": {
        "first_name": "Ольга",
        "last_name": "",
        "bio": "Фитнес + правильное питание 💪 | Консультирую",
    },
    "kirushka_94": {
        "first_name": "Михаил",
        "last_name": "",
        "bio": "Похудел на 15 кг 🏃 | ЗОЖ 2 года | Делюсь опытом",
    },
}


async def update_profile(client: TelegramClient, profile: dict) -> bool:
    """Update Telegram profile."""
    try:
        # Update name and bio
        await client(UpdateProfileRequest(
            first_name=profile["first_name"],
            last_name=profile.get("last_name", ""),
            about=profile["bio"],
        ))
        logger.info(f"Profile updated: {profile['first_name']} - {profile['bio']}")
        return True
    except Exception as e:
        logger.error(f"Failed to update profile: {e}")
        return False


async def get_current_profile(client: TelegramClient) -> dict:
    """Get current profile info."""
    me = await client.get_me()
    return {
        "id": me.id,
        "username": me.username,
        "first_name": me.first_name,
        "last_name": me.last_name or "",
        "phone": me.phone,
    }


async def main():
    """Main function."""
    logger.info("=" * 60)
    logger.info("APEXFLOW — Обновление профилей на NL International")
    logger.info("=" * 60)

    # Get accounts from database
    async with get_session() as session:
        from sqlalchemy import select
        result = await session.execute(
            select(UserBotAccount).where(UserBotAccount.is_active == True)
        )
        accounts = result.scalars().all()

        if not accounts:
            logger.error("Нет активных аккаунтов в БД!")
            return

        logger.info(f"Найдено {len(accounts)} активных аккаунтов")

        updated = 0
        for account in accounts:
            username = account.username.lstrip("@") if account.username else None

            if not username or username not in PROFILE_MAPPING:
                logger.warning(f"Аккаунт {account.phone} ({username}) не в списке для обновления")
                continue

            new_profile = PROFILE_MAPPING[username]
            logger.info(f"\nОбновляю: @{username} → {new_profile['first_name']}")

            # Create Telethon client
            if not account.session_string:
                logger.error(f"Нет session_string для @{username}")
                continue

            try:
                client = TelegramClient(
                    StringSession(account.session_string),
                    settings.telegram_api_id,
                    settings.telegram_api_hash,
                )
                await client.connect()

                if not await client.is_user_authorized():
                    logger.error(f"Аккаунт @{username} не авторизован!")
                    continue

                # Get current profile
                current = await get_current_profile(client)
                logger.info(f"  Текущий: {current['first_name']} {current['last_name']}")

                # Update profile
                if await update_profile(client, new_profile):
                    updated += 1

                    # Update in database
                    account.display_name = new_profile["first_name"]
                    session.add(account)

                await client.disconnect()

            except Exception as e:
                logger.error(f"Ошибка с аккаунтом @{username}: {e}")
                continue

            # Delay between updates
            await asyncio.sleep(2)

        await session.commit()

    logger.info("")
    logger.info("=" * 60)
    logger.info(f"Готово! Обновлено {updated}/{len(accounts)} профилей")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
