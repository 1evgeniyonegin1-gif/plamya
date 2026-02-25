"""
AI-Куратор - Главный файл бота
"""
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from shared.config.settings import settings
from shared.utils.logger import setup_logger
from shared.database.base import init_db
from curator_bot.handlers import messages, commands, onboarding_callbacks
from curator_bot.scheduler.reminder_scheduler import setup_reminder_scheduler, shutdown_scheduler


# Настраиваем логгер
logger = setup_logger("curator", settings.log_level)


async def main():
    """Главная функция запуска бота"""

    logger.info("🚀 Starting AI-Curator Bot...")

    # Инициализируем базу данных
    logger.info("Initializing database...")
    await init_db()
    logger.info("✅ Database initialized")

    # Создаем бота
    bot = Bot(
        token=settings.curator_bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    # Создаем диспетчер
    dp = Dispatcher()

    # Регистрируем роутеры
    dp.include_router(commands.router)
    dp.include_router(onboarding_callbacks.router)  # Callback-кнопки онбординга
    dp.include_router(messages.router)   # Должен быть последним (обрабатывает все текстовые сообщения)

    logger.info("✅ Handlers registered")

    # Запускаем планировщик напоминаний
    setup_reminder_scheduler(bot)
    logger.info("✅ Reminder scheduler started")

    # Запускаем онбординг-планировщик
    from curator_bot.onboarding.onboarding_scheduler import OnboardingScheduler
    onboarding_scheduler = OnboardingScheduler(bot)
    await onboarding_scheduler.start()
    logger.info("✅ Onboarding scheduler started")

    # Сохраняем ссылку для graceful shutdown
    dp.onboarding_scheduler = onboarding_scheduler

    # Запускаем polling
    try:
        logger.info("🤖 AI-Curator Bot is running!")
        logger.info(f"Model: {settings.curator_ai_model}")
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        shutdown_scheduler()

        # Останавливаем онбординг-планировщик
        if hasattr(dp, 'onboarding_scheduler'):
            await dp.onboarding_scheduler.stop()
            logger.info("✅ Onboarding scheduler stopped")

        await bot.session.close()
        logger.info("👋 AI-Curator Bot stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped by user")
