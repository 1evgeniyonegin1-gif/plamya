"""
Запуск обоих ботов в одном процессе для Railway
"""
import asyncio
import sys
from loguru import logger

# Настройка логирования
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> - <level>{message}</level>",
    level="INFO"
)


async def run_curator_bot():
    """Запуск AI-Куратора"""
    from curator_bot.main import main as curator_main
    logger.info("Starting AI-Curator Bot...")
    await curator_main()


async def run_content_manager_bot():
    """Запуск AI-Контент-Менеджера"""
    from content_manager_bot.main import main as content_main
    logger.info("Starting AI-Content-Manager Bot...")
    await content_main()


async def main():
    """Запуск обоих ботов параллельно"""
    logger.info("=" * 50)
    logger.info("NL International AI Bots - Starting...")
    logger.info("=" * 50)

    # Запускаем оба бота параллельно
    await asyncio.gather(
        run_curator_bot(),
        run_content_manager_bot(),
        return_exceptions=True
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bots stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
