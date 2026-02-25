"""
AI-Контент-Менеджер - Главный файл бота
Автоматическая генерация и публикация контента в Telegram канал
"""
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from shared.config.settings import settings
from shared.utils.logger import setup_logger
from shared.database.base import init_db
from content_manager_bot.handlers import admin_router, callbacks_router, channel_admin_router, vip_welcome_router
from content_manager_bot.scheduler.content_scheduler import ContentScheduler


# Настраиваем логгер
logger = setup_logger("content_manager", settings.log_level)


async def main():
    """Главная функция запуска бота"""

    logger.info("🚀 Starting AI-Content-Manager Bot...")

    # Инициализируем базу данных
    logger.info("Initializing database...")
    await init_db()
    logger.info("✅ Database initialized")

    # Создаем бота
    bot = Bot(
        token=settings.content_manager_bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    # Создаем диспетчер с хранилищем состояний
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Регистрируем роутеры (callbacks первым для FSM)
    dp.include_router(callbacks_router)
    dp.include_router(channel_admin_router)
    dp.include_router(vip_welcome_router)
    dp.include_router(admin_router)

    logger.info("✅ Handlers registered")

    # Создаем планировщик
    scheduler = ContentScheduler(bot)

    # Запускаем планировщик
    await scheduler.start()
    logger.info("✅ Content scheduler started")

    # Запускаем polling
    try:
        logger.info("🤖 AI-Content-Manager Bot is running!")
        logger.info(f"AI Model: {settings.content_manager_ai_model or 'GigaChat'}")
        logger.info(f"Channel: {settings.channel_username}")
        logger.info(f"Admins: {settings.admin_ids_list}")

        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await scheduler.stop()
        await bot.session.close()
        logger.info("👋 AI-Content-Manager Bot stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped by user")
