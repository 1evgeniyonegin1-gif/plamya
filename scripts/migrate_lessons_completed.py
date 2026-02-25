"""
Миграция БД: добавление поля lessons_completed в таблицу users
"""
import asyncio
import sys
from pathlib import Path

# Добавляем корневую директорию в PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from shared.database.base import AsyncSessionLocal, engine
from loguru import logger


async def run_migration():
    """Выполнение миграции БД"""

    logger.info("Starting lessons_completed migration...")

    async with engine.begin() as conn:
        # Добавляем новое поле в таблицу users
        logger.info("Adding lessons_completed field to users table...")

        await conn.execute(text("""
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS lessons_completed INTEGER DEFAULT 0
        """))

        logger.info("✅ Updated users table")

        # Инициализируем значения по умолчанию для существующих пользователей
        logger.info("Initializing default values for existing users...")

        await conn.execute(text("""
            UPDATE users
            SET lessons_completed = 0
            WHERE lessons_completed IS NULL
        """))

        logger.info("✅ Migration completed successfully!")


async def main():
    """Главная функция"""
    try:
        await run_migration()
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        raise
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
