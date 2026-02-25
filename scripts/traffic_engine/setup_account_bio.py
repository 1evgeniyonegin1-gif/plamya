"""
Setup Account Bio — Автоматическая установка био для всех аккаунтов.

Формирует био на основе сегмента + ссылки на привязанный канал.

Использование:
    python scripts/traffic_engine/setup_account_bio.py
    python scripts/traffic_engine/setup_account_bio.py --account-id 3
    python scripts/traffic_engine/setup_account_bio.py --dry-run
"""

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from loguru import logger
from telethon import TelegramClient
from telethon.tl.functions.account import UpdateProfileRequest
from telethon.errors import FloodWaitError
from telethon.sessions import StringSession
from sqlalchemy import select

from traffic_engine.config import settings
from traffic_engine.database import get_session, init_db
from traffic_engine.database.models import UserBotAccount


# Шаблоны био по сегментам
BIO_TEMPLATES = {
    "zozh": "ЗОЖ без фанатизма 💪 Про питание, спорт и энергию\nКанал: t.me/{channel}",
    "mama": "Мама, энергия, здоровье 🌸 Как всё успевать\nКанал: t.me/{channel}",
    "business": "Бизнес и доход 📈 Из найма в свободу\nКанал: t.me/{channel}",
    "student": "Учёба, AI, развитие 🚀 Про деньги и технологии\nКанал: t.me/{channel}",
}

# Био без канала (если канал не привязан)
BIO_NO_CHANNEL = {
    "zozh": "ЗОЖ без фанатизма 💪 Про питание, спорт и энергию",
    "mama": "Мама, энергия, здоровье 🌸 Как всё успевать",
    "business": "Бизнес и доход 📈 Из найма в свободу",
    "student": "Учёба, AI, развитие 🚀 Про деньги и технологии",
}


async def setup_bio(account: UserBotAccount, dry_run: bool = False) -> bool:
    """
    Установить био для одного аккаунта.

    Args:
        account: Запись аккаунта из БД
        dry_run: Только показать что будет сделано

    Returns:
        True если успешно (или dry_run)
    """
    segment = account.segment or "zozh"
    channel = account.linked_channel_username

    # Формируем био
    if channel:
        channel_clean = channel.lstrip("@")
        bio = BIO_TEMPLATES.get(segment, BIO_TEMPLATES["zozh"]).format(channel=channel_clean)
    else:
        bio = BIO_NO_CHANNEL.get(segment, BIO_NO_CHANNEL["zozh"])

    phone_masked = account.phone[:4] + "***" + account.phone[-2:] if len(account.phone) > 6 else account.phone

    if dry_run:
        logger.info(f"[DRY RUN] {phone_masked} [{segment}] → bio: {bio}")
        return True

    # Подключаемся через Telethon
    try:
        client = TelegramClient(
            StringSession(account.session_string),
            settings.telegram_api_id,
            settings.telegram_api_hash,
        )
        await client.connect()

        if not await client.is_user_authorized():
            logger.error(f"❌ {phone_masked} — не авторизован")
            await client.disconnect()
            return False

        # Обновляем био
        await client(UpdateProfileRequest(about=bio))

        # Сохраняем в БД
        async with get_session() as session:
            db_account = await session.get(UserBotAccount, account.id)
            if db_account:
                db_account.bio = bio
                await session.commit()

        logger.info(f"✅ {phone_masked} [{segment}] — bio обновлён: {bio}")

        await client.disconnect()
        return True

    except FloodWaitError as e:
        logger.error(f"⚠️ {phone_masked} — FloodWait {e.seconds}s, пропускаю")
        return False
    except Exception as e:
        logger.error(f"❌ {phone_masked} — ошибка: {e}")
        return False


async def main():
    parser = argparse.ArgumentParser(description="Установка био для аккаунтов Traffic Engine")
    parser.add_argument("--account-id", type=int, help="ID конкретного аккаунта")
    parser.add_argument("--dry-run", action="store_true", help="Только показать без изменений")
    args = parser.parse_args()

    await init_db()

    async with get_session() as session:
        query = select(UserBotAccount).where(
            UserBotAccount.status.in_(["active", "warming"])
        )
        if args.account_id:
            query = query.where(UserBotAccount.id == args.account_id)

        result = await session.execute(query)
        accounts = result.scalars().all()

    if not accounts:
        logger.warning("Нет активных аккаунтов")
        return

    logger.info(f"Найдено {len(accounts)} аккаунтов")

    success = 0
    for account in accounts:
        if await setup_bio(account, dry_run=args.dry_run):
            success += 1
        await asyncio.sleep(2)  # Пауза между аккаунтами

    logger.info(f"Готово: {success}/{len(accounts)} обновлено")


if __name__ == "__main__":
    asyncio.run(main())
