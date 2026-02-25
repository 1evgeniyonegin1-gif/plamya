"""
Миграция БД: добавление полей аналитики
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

    logger.info("Starting analytics migration...")

    async with engine.begin() as conn:
        # Добавляем новые поля в таблицу content_posts
        logger.info("Adding new fields to content_posts table...")

        await conn.execute(text("""
            ALTER TABLE content_posts
            ADD COLUMN IF NOT EXISTS forwards_count INTEGER DEFAULT 0,
            ADD COLUMN IF NOT EXISTS reactions_breakdown JSONB,
            ADD COLUMN IF NOT EXISTS engagement_rate FLOAT,
            ADD COLUMN IF NOT EXISTS last_metrics_update TIMESTAMP
        """))

        logger.info("✅ Updated content_posts table")

        # Создаем новую таблицу content_post_analytics
        logger.info("Creating content_post_analytics table...")

        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS content_post_analytics (
                id SERIAL PRIMARY KEY,
                post_id INTEGER NOT NULL,
                channel_message_id BIGINT NOT NULL,
                views_count INTEGER DEFAULT 0,
                reactions_count INTEGER DEFAULT 0,
                forwards_count INTEGER DEFAULT 0,
                reactions_breakdown JSONB,
                snapshot_at TIMESTAMP NOT NULL DEFAULT NOW(),
                views_delta INTEGER,
                reactions_delta INTEGER,
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """))

        logger.info("✅ Created content_post_analytics table")

        # Создаем индексы для быстрого поиска
        logger.info("Creating indexes...")

        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_post_analytics_post_id
            ON content_post_analytics(post_id)
        """))

        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_post_analytics_snapshot_at
            ON content_post_analytics(snapshot_at)
        """))

        logger.info("✅ Created indexes")

        # Инициализируем значения по умолчанию для существующих постов
        logger.info("Initializing default values for existing posts...")

        await conn.execute(text("""
            UPDATE content_posts
            SET forwards_count = 0
            WHERE forwards_count IS NULL
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
