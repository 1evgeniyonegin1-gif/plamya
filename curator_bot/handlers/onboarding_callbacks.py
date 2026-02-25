"""
Обработчики callback-кнопок для интерактивного онбординга.

Кнопки:
- onb_complete:{task_id} — отметить задачу выполненной
- onb_skip:{task_id} — пропустить задачу
- onb_next_day:{day} — перейти к следующему дню
- onb_show_all:{day} — показать весь чеклист дня
"""
from datetime import datetime
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import select
from loguru import logger

from shared.database.base import AsyncSessionLocal
from curator_bot.database.models import User, UserOnboardingProgress
from curator_bot.onboarding.proactive_tasks import OnboardingTasks


router = Router(name="onboarding_callbacks")


@router.callback_query(F.data.startswith("onb_complete:"))
async def handle_task_complete(callback: CallbackQuery):
    """Пользователь отметил задачу как выполненную"""
    await callback.answer("✅ Отлично!")

    task_id = callback.data.split(":")[1]
    telegram_id = callback.from_user.id

    async with AsyncSessionLocal() as session:
        # Получаем пользователя
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            await callback.message.answer("Сначала нажми /start")
            return

        # Получаем прогресс онбординга
        progress_result = await session.execute(
            select(UserOnboardingProgress).where(UserOnboardingProgress.user_id == user.id)
        )
        progress = progress_result.scalar_one_or_none()

        if not progress:
            await callback.message.answer("Онбординг не найден. Нажми /start")
            return

        # Добавляем задачу в выполненные
        completed = list(progress.completed_tasks or [])
        if task_id not in completed:
            completed.append(task_id)
            progress.completed_tasks = completed
            progress.last_activity = datetime.now()
            await session.commit()
            logger.info(f"User {telegram_id} completed task {task_id}")

        # Формируем обновлённое сообщение
        message, keyboard = OnboardingTasks.format_tasks_message(
            day=progress.current_day,
            completed_tasks=completed
        )

        # Проверяем, все ли задачи дня выполнены
        day_info = OnboardingTasks.get_day_tasks(progress.current_day)
        if day_info:
            all_done = all(t["id"] in completed for t in day_info["tasks"])
            if all_done:
                message += "\n\n🎉 Молодец! Все задачи дня выполнены!"

        # Обновляем сообщение
        try:
            await callback.message.edit_text(
                text=message,
                reply_markup=keyboard
            )
        except Exception as e:
            # Если сообщение не изменилось, игнорируем
            logger.debug(f"Message not modified: {e}")


@router.callback_query(F.data.startswith("onb_skip:"))
async def handle_task_skip(callback: CallbackQuery):
    """Пользователь пропустил задачу"""
    await callback.answer("⏭️ Пропущено")

    task_id = callback.data.split(":")[1]
    telegram_id = callback.from_user.id

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            return

        progress_result = await session.execute(
            select(UserOnboardingProgress).where(UserOnboardingProgress.user_id == user.id)
        )
        progress = progress_result.scalar_one_or_none()

        if not progress:
            return

        # Добавляем задачу как пропущенную (всё равно считаем "выполненной" для прогресса)
        completed = list(progress.completed_tasks or [])
        skipped_id = f"{task_id}_skipped"
        if task_id not in completed and skipped_id not in completed:
            completed.append(skipped_id)  # Помечаем как пропущенную
            progress.completed_tasks = completed
            progress.last_activity = datetime.now()
            await session.commit()
            logger.info(f"User {telegram_id} skipped task {task_id}")

        # Формируем обновлённое сообщение
        # При форматировании учитываем и выполненные, и пропущенные
        display_completed = [t.replace("_skipped", "") for t in completed]
        message, keyboard = OnboardingTasks.format_tasks_message(
            day=progress.current_day,
            completed_tasks=display_completed
        )

        try:
            await callback.message.edit_text(
                text=message,
                reply_markup=keyboard
            )
        except Exception:
            pass


@router.callback_query(F.data.startswith("onb_next_day:"))
async def handle_next_day(callback: CallbackQuery):
    """Переход на следующий день"""
    next_day = int(callback.data.split(":")[1])
    telegram_id = callback.from_user.id

    await callback.answer(f"➡️ Переходим к дню {next_day}")

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            return

        progress_result = await session.execute(
            select(UserOnboardingProgress).where(UserOnboardingProgress.user_id == user.id)
        )
        progress = progress_result.scalar_one_or_none()

        if not progress:
            return

        # Обновляем текущий день
        progress.current_day = next_day
        progress.last_activity = datetime.now()

        # Если день > 7, завершаем онбординг
        if next_day > 7:
            progress.is_completed = True
            await session.commit()

            await callback.message.edit_text(
                "🏆 <b>Поздравляю!</b>\n\n"
                "Ты прошёл весь онбординг за 7 дней!\n\n"
                "Теперь ты знаешь основы и можешь работать самостоятельно.\n"
                "Я всегда рядом — задавай любые вопросы.\n\n"
                "Удачи в бизнесе! 💪"
            )
            return

        await session.commit()
        logger.info(f"User {telegram_id} moved to day {next_day}")

        # Показываем задачи нового дня
        message, keyboard = OnboardingTasks.format_tasks_message(
            day=next_day,
            completed_tasks=[]  # Новый день — задачи пустые
        )

        try:
            await callback.message.edit_text(
                text=message,
                reply_markup=keyboard
            )
        except Exception:
            # Если не можем отредактировать, отправляем новое сообщение
            await callback.message.answer(
                text=message,
                reply_markup=keyboard
            )


@router.callback_query(F.data.startswith("onb_show_all:"))
async def handle_show_all(callback: CallbackQuery):
    """Показать весь чеклист дня"""
    day = int(callback.data.split(":")[1])
    telegram_id = callback.from_user.id

    await callback.answer("📋 Чеклист")

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            return

        progress_result = await session.execute(
            select(UserOnboardingProgress).where(UserOnboardingProgress.user_id == user.id)
        )
        progress = progress_result.scalar_one_or_none()

        completed = list(progress.completed_tasks or []) if progress else []
        # Учитываем пропущенные
        display_completed = [t.replace("_skipped", "") for t in completed]

        # Формируем полное сообщение
        day_info = OnboardingTasks.get_day_tasks(day)
        if not day_info:
            return

        message = f"{day_info['emoji']} <b>{day_info['title']}</b>\n\n"

        for i, task in enumerate(day_info["tasks"], 1):
            is_done = task["id"] in display_completed
            checkbox = "✅" if is_done else "⬜"
            message += f"{checkbox} {task['text']}\n"
            if not is_done and task.get("hint"):
                message += f"   <i>💡 {task['hint']}</i>\n"
            message += "\n"

        # Кнопки для невыполненных задач
        buttons = []
        for task in day_info["tasks"]:
            if task["id"] not in display_completed:
                buttons.append([
                    InlineKeyboardButton(
                        text=f"✅ {task['text'][:30]}",
                        callback_data=f"onb_complete:{task['id']}"
                    )
                ])

        buttons.append([
            InlineKeyboardButton(text="⬅️ Назад", callback_data=f"onb_back:{day}")
        ])

        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

        try:
            await callback.message.edit_text(
                text=message,
                reply_markup=keyboard
            )
        except Exception:
            pass


@router.callback_query(F.data.startswith("onb_back:"))
async def handle_back(callback: CallbackQuery):
    """Вернуться к основному виду дня"""
    day = int(callback.data.split(":")[1])
    telegram_id = callback.from_user.id

    await callback.answer()

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            return

        progress_result = await session.execute(
            select(UserOnboardingProgress).where(UserOnboardingProgress.user_id == user.id)
        )
        progress = progress_result.scalar_one_or_none()

        completed = list(progress.completed_tasks or []) if progress else []
        display_completed = [t.replace("_skipped", "") for t in completed]

        message, keyboard = OnboardingTasks.format_tasks_message(
            day=day,
            completed_tasks=display_completed
        )

        try:
            await callback.message.edit_text(
                text=message,
                reply_markup=keyboard
            )
        except Exception:
            pass


@router.callback_query(F.data.startswith("onb_done:"))
async def handle_already_done(callback: CallbackQuery):
    """Задача уже выполнена — просто показываем уведомление"""
    await callback.answer("✅ Эта задача уже выполнена!")
