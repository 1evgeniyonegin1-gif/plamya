"""
Миграция квалификаций партнёров с устаревших названий на актуальные

Старая система: beginner, manager, master, star, diamond
Новая система: consultant, consultant_6, manager_9, senior_manager, manager_15, director_21,
               M1, M2, M3, B1, B2, B3, TOP, TOP1-5, AC1-6
"""
import asyncio
import sys
from pathlib import Path

# Добавляем корневую директорию в PYTHONPATH
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from sqlalchemy import select, update, func
from shared.database.base import AsyncSessionLocal
from curator_bot.database.models import User
from loguru import logger


# Маппинг старых квалификаций на новые
QUALIFICATION_MAPPING = {
    "beginner": "consultant",      # Новичок → Консультант
    "manager": "M1",                # Manager → Middle 1
    "master": "M2",                 # Master → Middle 2
    "star": "B1",                   # Star → Business Partner 1
    "diamond": "B2",                # Diamond → Business Partner 2
}


async def migrate_qualifications():
    """Мигрирует квалификации пользователей на новую систему"""

    logger.info("Начинаем миграцию квалификаций...")

    async with AsyncSessionLocal() as session:
        # Сначала получим статистику
        for old_qual, new_qual in QUALIFICATION_MAPPING.items():
            result = await session.execute(
                select(func.count(User.id))
                .where(User.qualification == old_qual)
            )
            count = result.scalar()
            if count > 0:
                logger.info(f"Найдено пользователей с квалификацией '{old_qual}': {count}")

        # Выполняем миграцию для каждой квалификации
        total_updated = 0
        for old_qual, new_qual in QUALIFICATION_MAPPING.items():
            result = await session.execute(
                update(User)
                .where(User.qualification == old_qual)
                .values(qualification=new_qual)
            )
            updated = result.rowcount
            if updated > 0:
                logger.success(f"Обновлено: {old_qual} → {new_qual} ({updated} пользователей)")
                total_updated += updated

        await session.commit()

        if total_updated == 0:
            logger.info("Нет пользователей с устаревшими квалификациями. Миграция не требуется.")
        else:
            logger.success(f"Миграция завершена! Обновлено пользователей: {total_updated}")

        # Проверим финальное состояние
        logger.info("\nТекущее распределение квалификаций:")
        result = await session.execute(
            select(User.qualification, func.count(User.id))
            .group_by(User.qualification)
        )
        for qual, count in result:
            logger.info(f"  {qual}: {count} пользователей")


async def rollback_qualifications():
    """Откатывает миграцию обратно (для тестирования)"""

    logger.warning("Откатываем миграцию квалификаций обратно...")

    # Обратный маппинг
    reverse_mapping = {v: k for k, v in QUALIFICATION_MAPPING.items()}

    async with AsyncSessionLocal() as session:
        total_rolled_back = 0
        for new_qual, old_qual in reverse_mapping.items():
            result = await session.execute(
                update(User)
                .where(User.qualification == new_qual)
                .values(qualification=old_qual)
            )
            rolled_back = result.rowcount
            if rolled_back > 0:
                logger.info(f"Откачено: {new_qual} → {old_qual} ({rolled_back} пользователей)")
                total_rolled_back += rolled_back

        await session.commit()
        logger.success(f"Откат завершён! Откачено пользователей: {total_rolled_back}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Миграция квалификаций партнёров NL")
    parser.add_argument(
        "--rollback",
        action="store_true",
        help="Откатить миграцию обратно (для тестирования)"
    )
    args = parser.parse_args()

    if args.rollback:
        logger.warning("ВНИМАНИЕ: Выполняется откат миграции!")
        asyncio.run(rollback_qualifications())
    else:
        asyncio.run(migrate_qualifications())
