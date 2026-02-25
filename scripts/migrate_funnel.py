"""
Миграция БД для воронки продаж

Добавляет новые поля в таблицу users:
- user_intent (client/business/curious)
- pain_point (weight/energy/immunity/beauty/kids/sport)
- income_goal (10_30k/50_100k/200k_plus/unsure)
- funnel_step (текущий шаг воронки)
- funnel_started_at (когда начал воронку)
- email (для рассылки)
- lead_status (статус лида)
- lead_score (скоринг 0-100)

Создаёт таблицу funnel_events для аналитики

Запуск:
    python -m scripts.migrate_funnel
"""
import asyncio
import sys
import os

# Добавляем корневую директорию проекта в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from shared.database.base import engine
from loguru import logger


async def migrate():
    """Выполняет миграцию БД для воронки продаж"""
    logger.info("🚀 Starting funnel migration...")

    async with engine.begin() as conn:
        # Добавляем поля для воронки в таблицу users
        logger.info("Adding funnel fields to users table...")

        try:
            await conn.execute(text("""
                ALTER TABLE users
                ADD COLUMN IF NOT EXISTS user_intent VARCHAR(50),
                ADD COLUMN IF NOT EXISTS pain_point VARCHAR(100),
                ADD COLUMN IF NOT EXISTS income_goal VARCHAR(50),
                ADD COLUMN IF NOT EXISTS funnel_step INTEGER DEFAULT 0,
                ADD COLUMN IF NOT EXISTS funnel_started_at TIMESTAMP,
                ADD COLUMN IF NOT EXISTS email VARCHAR(100),
                ADD COLUMN IF NOT EXISTS lead_status VARCHAR(50) DEFAULT 'new',
                ADD COLUMN IF NOT EXISTS lead_score INTEGER DEFAULT 0
            """))
            logger.info("✅ Funnel fields added to users table")
        except Exception as e:
            logger.warning(f"Some fields may already exist: {e}")

        # Создаём таблицу событий воронки (для детальной аналитики)
        logger.info("Creating funnel_events table...")

        try:
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS funnel_events (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                    event_type VARCHAR(50) NOT NULL,
                    event_data JSONB,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """))

            # Создаём индексы для быстрого поиска
            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_funnel_events_user_id
                ON funnel_events(user_id)
            """))

            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_funnel_events_type
                ON funnel_events(event_type)
            """))

            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_funnel_events_created_at
                ON funnel_events(created_at)
            """))

            logger.info("✅ funnel_events table created with indexes")
        except Exception as e:
            logger.warning(f"funnel_events table may already exist: {e}")

        # Создаём индексы для воронки в users
        logger.info("Creating funnel indexes on users table...")

        try:
            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_users_lead_status
                ON users(lead_status)
            """))

            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_users_user_intent
                ON users(user_intent)
            """))

            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_users_lead_score
                ON users(lead_score)
            """))

            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_users_funnel_started_at
                ON users(funnel_started_at)
            """))

            logger.info("✅ Funnel indexes created on users table")
        except Exception as e:
            logger.warning(f"Some indexes may already exist: {e}")

        # Обновляем существующих пользователей
        logger.info("Updating existing users with default funnel values...")

        try:
            await conn.execute(text("""
                UPDATE users
                SET lead_status = 'new',
                    funnel_step = 0,
                    lead_score = 0
                WHERE lead_status IS NULL
            """))
            logger.info("✅ Existing users updated")
        except Exception as e:
            logger.warning(f"Could not update existing users: {e}")

    logger.info("✅ Funnel migration completed successfully!")


async def rollback():
    """Откатывает миграцию (удаляет добавленные поля)"""
    logger.warning("⚠️ Rolling back funnel migration...")

    async with engine.begin() as conn:
        # Удаляем таблицу событий
        await conn.execute(text("DROP TABLE IF EXISTS funnel_events CASCADE"))

        # Удаляем поля из users (осторожно!)
        # Раскомментируйте если нужен полный откат:
        # await conn.execute(text("""
        #     ALTER TABLE users
        #     DROP COLUMN IF EXISTS user_intent,
        #     DROP COLUMN IF EXISTS pain_point,
        #     DROP COLUMN IF EXISTS income_goal,
        #     DROP COLUMN IF EXISTS funnel_step,
        #     DROP COLUMN IF EXISTS funnel_started_at,
        #     DROP COLUMN IF EXISTS email,
        #     DROP COLUMN IF EXISTS lead_status,
        #     DROP COLUMN IF EXISTS lead_score
        # """))

    logger.info("✅ Rollback completed")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Funnel migration script")
    parser.add_argument(
        "--rollback",
        action="store_true",
        help="Rollback migration (remove funnel_events table)"
    )
    args = parser.parse_args()

    if args.rollback:
        asyncio.run(rollback())
    else:
        asyncio.run(migrate())
