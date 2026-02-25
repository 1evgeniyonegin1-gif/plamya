#!/usr/bin/env python
"""
APEXFLOW Traffic Engine - Автокомментирование для NL International.

Использует 4 аккаунта с ротацией:
- Анна (@lemonlime192) - Нутрициолог
- Елена (@karinko_o) - Мама двоих
- Ольга (@lyuba_ok) - Фитнес + питание
- Михаил (@kirushka_94) - ЗОЖ энтузиаст

Запуск:
    python run_auto_comments.py

Остановка:
    Ctrl+C
"""

import asyncio
import sys
from loguru import logger

from traffic_engine.config import settings
from traffic_engine.database import init_db, get_session
from traffic_engine.database.models import Tenant
from traffic_engine.main import TrafficEngine


async def main():
    """Запустить автокомментирование для NL International."""

    # Настройка логирования
    logger.remove()  # Убираем дефолтный handler
    logger.add(
        sys.stderr,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )
    logger.add(
        "logs/apexflow_traffic_{time:YYYY-MM-DD}.log",
        rotation="00:00",
        retention="7 days",
        level="DEBUG"
    )

    logger.info("=" * 60)
    logger.info("APEXFLOW TRAFFIC ENGINE — NL INTERNATIONAL")
    logger.info("=" * 60)
    logger.info("")
    logger.info("Аккаунты для ротации:")
    logger.info("  1. Анна (@lemonlime192) — Нутрициолог")
    logger.info("  2. Елена (@karinko_o) — Мама двоих")
    logger.info("  3. Ольга (@lyuba_ok) — Фитнес + питание")
    logger.info("  4. Михаил (@kirushka_94) — ЗОЖ энтузиаст")
    logger.info("")
    logger.info("Для остановки нажмите Ctrl+C")
    logger.info("=" * 60)
    logger.info("")

    # Инициализируем БД
    await init_db()
    logger.info("База данных инициализирована")

    # Проверяем, есть ли тенант nl_international
    async with get_session() as session:
        from sqlalchemy import select
        result = await session.execute(
            select(Tenant).where(Tenant.name == "nl_international")
        )
        tenant = result.scalar_one_or_none()

        if not tenant:
            logger.error("Тенант 'nl_international' не найден в БД!")
            logger.info("Запустите: python scripts/traffic_engine/init_db.py")
            return

    logger.info(f"Запускаю APEXFLOW Traffic Engine для: {tenant.display_name}")
    logger.info("")

    # Создаём и запускаем движок
    engine = TrafficEngine()

    try:
        # Запускаем для NL International
        await engine.start(tenant_names=["nl_international"])
    except KeyboardInterrupt:
        logger.info("\n\nПолучен сигнал остановки...")
        await engine.stop()
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await engine.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Завершено пользователем")
