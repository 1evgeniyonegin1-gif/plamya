"""
Скрипт для создания базы данных
Создаёт все таблицы для обоих ботов: AI-Куратор и AI-Контент-Менеджер
"""
import asyncio
import sys
from pathlib import Path

# Добавляем корень проекта в PYTHONPATH
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from shared.database.base import init_db
from shared.utils.logger import setup_logger

# Импортируем модели чтобы они зарегистрировались в metadata
# AI-Куратор
from curator_bot.database.models import (
    User, ConversationMessage, ConversationContext,
    KnowledgeBaseChunk, UserReminder, UserFeedback
)
# AI-Контент-Менеджер
from content_manager_bot.database.models import Post, ContentSchedule, AdminAction

logger = setup_logger("db_init", "INFO")


async def main():
    """Создает все таблицы в базе данных"""
    try:
        logger.info("Creating database tables...")
        logger.info("Tables to create:")
        logger.info("  AI-Куратор:")
        logger.info("    - users")
        logger.info("    - conversation_messages")
        logger.info("    - conversation_contexts")
        logger.info("    - knowledge_base_chunks")
        logger.info("    - user_reminders")
        logger.info("    - user_feedback")
        logger.info("  AI-Контент-Менеджер:")
        logger.info("    - content_posts")
        logger.info("    - content_schedules")
        logger.info("    - content_admin_actions")

        await init_db()
        logger.info("✅ Database tables created successfully!")

    except Exception as e:
        logger.error(f"❌ Error creating database: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
