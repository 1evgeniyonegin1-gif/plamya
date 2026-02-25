"""
Планировщик проактивных напоминаний для онбординга

Проверяет неактивных пользователей и отправляет напоминания.
"""
import asyncio
from datetime import datetime, timedelta
from typing import Optional, List
from loguru import logger

from aiogram import Bot


class OnboardingScheduler:
    """Планировщик напоминаний для онбординга"""

    # Интервал проверки (в часах)
    CHECK_INTERVAL_HOURS = 2

    def __init__(self, bot: Bot):
        """
        Args:
            bot: Экземпляр бота для отправки сообщений
        """
        self.bot = bot
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self):
        """Запустить планировщик"""
        if self._running:
            logger.warning("Onboarding scheduler already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._scheduler_loop())
        logger.info("Onboarding scheduler started")

    async def stop(self):
        """Остановить планировщик"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Onboarding scheduler stopped")

    async def _scheduler_loop(self):
        """Основной цикл планировщика"""
        while self._running:
            try:
                from curator_bot.utils.quiet_hours import is_sending_allowed

                if not is_sending_allowed():
                    await asyncio.sleep(30)
                    continue

                await self._check_inactive_users()
                await self._send_daily_tasks()

                # Обработка событий из system_events (уведомления о новых постах)
                from curator_bot.events.event_consumer import process_pending_events
                await process_pending_events(self.bot)

            except Exception as e:
                logger.error(f"Error in onboarding scheduler: {e}")

            # Проверяем каждые 30 секунд (для быстрой обработки событий)
            await asyncio.sleep(30)

    async def _check_inactive_users(self):
        """Проверить неактивных пользователей и отправить напоминания"""
        from .proactive_tasks import OnboardingTasks

        # TODO: Получить список неактивных пользователей из БД
        inactive_users = await self._get_inactive_users()

        for user in inactive_users:
            hours_inactive = user.get("hours_inactive", 0)
            reminder = OnboardingTasks.get_inactivity_reminder(hours_inactive)

            if reminder and not user.get("reminder_sent_for_hours"):
                try:
                    await self.send_reminder(
                        user_id=user["telegram_id"],
                        message=reminder,
                        hours_inactive=hours_inactive
                    )
                    logger.info(
                        f"Sent inactivity reminder to user {user['telegram_id']} "
                        f"(inactive {hours_inactive}h)"
                    )
                except Exception as e:
                    logger.error(f"Failed to send reminder to {user['telegram_id']}: {e}")

    async def _send_daily_tasks(self):
        """Отправить задачи на день пользователям, которые ещё не получили"""
        from .proactive_tasks import OnboardingTasks

        # TODO: Получить пользователей, которым пора отправить задачи
        users_for_daily_tasks = await self._get_users_for_daily_tasks()

        for user in users_for_daily_tasks:
            day = user.get("current_day", 1)
            completed_tasks = user.get("completed_tasks", [])

            message, keyboard = OnboardingTasks.format_tasks_message(day, completed_tasks)

            try:
                await self.bot.send_message(
                    chat_id=user["telegram_id"],
                    text=message,
                    reply_markup=keyboard,
                    parse_mode="HTML"
                )
                logger.info(f"Sent day {day} tasks to user {user['telegram_id']}")
            except Exception as e:
                logger.error(f"Failed to send daily tasks to {user['telegram_id']}: {e}")

    async def send_reminder(self, user_id: int, message: str, hours_inactive: int = 0):
        """
        Отправить напоминание пользователю

        Args:
            user_id: Telegram ID пользователя
            message: Текст напоминания
            hours_inactive: Часов без активности (для логирования)
        """
        from .proactive_tasks import OnboardingTasks, get_user_progress
        from .onboarding_service import OnboardingService

        progress = await get_user_progress(user_id)
        current_day = progress.get("current_day", 1)

        # Формируем полное сообщение
        full_message = f"{message}\n\n"

        # Добавляем задачи, если есть
        if current_day <= 7:
            tasks_message, _ = OnboardingTasks.format_tasks_message(
                current_day,
                progress.get("completed_tasks", []),
                include_keyboard=False
            )
            full_message += tasks_message

        await self.bot.send_message(
            chat_id=user_id,
            text=full_message,
            parse_mode="HTML"
        )

        # Обновляем время последнего напоминания
        await OnboardingService.update_last_reminder(user_id, hours_inactive)

    async def _get_inactive_users(self) -> List[dict]:
        """
        Получить список неактивных пользователей из БД

        Returns:
            Список пользователей с их данными
        """
        from .onboarding_service import OnboardingService

        # Проверяем по минимальному порогу (4 часа)
        inactive_users = await OnboardingService.get_inactive_users(hours=4)

        # Фильтруем только тех, кому ещё не отправляли напоминание на этом пороге
        result = []
        for user in inactive_users:
            hours_inactive = user["hours_inactive"]
            last_reminder = user["last_reminder_hours"]

            # Определяем нужный порог
            reminder_thresholds = [4, 12, 24, 48, 168]
            current_threshold = None
            for threshold in reminder_thresholds:
                if hours_inactive >= threshold:
                    current_threshold = threshold

            # Если ещё не отправляли на этом пороге
            if current_threshold and current_threshold > last_reminder:
                result.append(user)

        return result

    async def _get_users_for_daily_tasks(self) -> List[dict]:
        """
        Получить пользователей, которым пора отправить дневные задачи

        Returns:
            Список пользователей
        """
        # Пока не реализовано автоматическое продвижение по дням
        # Пользователи сами проходят чеклисты
        return []


# Вспомогательные функции для интеграции в handlers

async def send_onboarding_welcome(bot: Bot, user_id: int):
    """
    Отправить приветственное сообщение онбординга

    Args:
        bot: Экземпляр бота
        user_id: Telegram ID пользователя
    """
    from .proactive_tasks import OnboardingTasks

    message, keyboard = OnboardingTasks.format_tasks_message(day=1, completed_tasks=[])

    welcome_text = (
        "🎉 <b>Добро пожаловать в NL International!</b>\n\n"
        "Я — твой AI-куратор. Помогу разобраться во всём:\n"
        "• Продукты и их особенности\n"
        "• Бизнес-модель и заработок\n"
        "• Работа с клиентами\n"
        "• Ответы на любые вопросы\n\n"
        "━━━━━━━━━━━━━━━\n\n"
        f"{message}\n\n"
        "💬 <i>Напиши мне что угодно — я отвечу!</i>"
    )

    await bot.send_message(
        chat_id=user_id,
        text=welcome_text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    logger.info(f"Sent onboarding welcome to user {user_id}")


async def check_and_send_progress(bot: Bot, user_id: int):
    """
    Проверить прогресс пользователя и отправить следующие задачи если нужно

    Args:
        bot: Экземпляр бота
        user_id: Telegram ID пользователя
    """
    from .proactive_tasks import OnboardingTasks, get_user_progress
    from .onboarding_service import OnboardingService

    progress = await get_user_progress(user_id)
    current_day = progress.get("current_day", 1)
    completed_tasks = progress.get("completed_tasks", [])

    # Проверяем, все ли задачи текущего дня выполнены
    day_info = OnboardingTasks.get_day_tasks(current_day)
    if day_info:
        day_task_ids = [t["id"] for t in day_info["tasks"]]
        all_completed = all(tid in completed_tasks for tid in day_task_ids)

        if all_completed and current_day < 7:
            # Переходим на следующий день
            next_day = await OnboardingService.advance_to_next_day(user_id)
            message, keyboard = OnboardingTasks.format_tasks_message(next_day, completed_tasks)

            congrats_text = (
                f"🎉 <b>Отлично! День {current_day} завершён!</b>\n\n"
                f"Переходим к следующему этапу:\n\n"
                f"{message}"
            )

            await bot.send_message(
                chat_id=user_id,
                text=congrats_text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
            logger.info(f"User {user_id} advanced to day {next_day}")
