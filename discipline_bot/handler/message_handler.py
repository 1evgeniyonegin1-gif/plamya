"""
Обработчик входящих текстовых сообщений от Данила.

Маршрутизирует текстовые команды:
- "встал" → утренний чек-ин
- "1", "2", "3", "4" → отметка привычки по номеру
- "медитация", "душ" и т.д. → отметка по имени
- "план" → рабочий план
- "з1", "задача 1" → закрытие задачи
- "стат" → статистика
- "привычки" → список привычек
- "неделя" → недельная сводка
- "добавить <название>" → новая привычка
- "удалить <номер>" → удалить привычку
"""

import re
from datetime import datetime, date, timezone, timedelta
from typing import Optional, List

from loguru import logger
from sqlalchemy import select, func as sa_func
from telethon import TelegramClient

from traffic_engine.database import get_session
from discipline_bot.database.models import (
    Habit, HabitLog, DailyPlan, DailyPlanTask, DailyReview, CheckIn,
)
from discipline_bot.state import UserState
from discipline_bot.config import (
    ADMIN_TELEGRAM_ID,
    HABIT_ALIASES,
    HABIT_DONE,
    HABIT_DONE_RECORD,
    HABIT_ALL_DONE,
    PLAN_EMPTY,
    PLAN_SHOW,
    PLAN_ACCEPTED,
    PLAN_TASK_DONE,
    PLAN_ALL_DONE,
    MORNING_CONFIRMED,
    MORNING_VERDICTS,
    EVENING_TOMORROW_PLAN,
    EVENING_DONE,
    EVENING_SKIPPED,
    UNKNOWN_COMMAND,
)

MSK = timezone(timedelta(hours=3))


def _today_msk() -> date:
    return datetime.now(MSK).date()


def _now_msk() -> datetime:
    return datetime.now(MSK)


class MessageHandler:
    """Обработка входящих сообщений от Данила."""

    def __init__(self, client: TelegramClient, state: UserState):
        self.client = client
        self.state = state

    async def handle(self, event) -> None:
        """Главный маршрутизатор входящих сообщений."""
        if not event.message or not event.message.text:
            return

        text = event.message.text.strip()
        text_lower = text.lower()

        try:
            # 1. Приоритет: ожидающие состояния FSM
            if self.state.waiting_for == "morning_confirm":
                if text_lower in ("встал", "проснулся", "подъём", "подъем", "я встал"):
                    await self._handle_morning_confirm(event)
                    return

            if self.state.waiting_for == "plan_tasks":
                await self._handle_plan_input(event, text)
                return

            if self.state.waiting_for == "evening_reflection":
                await self._handle_evening_reflection(event, text)
                return

            if self.state.waiting_for == "tomorrow_plan":
                await self._handle_tomorrow_plan(event, text)
                return

            if self.state.waiting_for == "add_habit":
                await self._handle_add_habit(event, text)
                return

            # 2. Утренний подтверждение (даже без waiting_for — если пинг был отправлен)
            if self.state.morning_ping_sent and not self.state.morning_confirmed:
                if text_lower in ("встал", "проснулся", "подъём", "подъем", "я встал"):
                    await self._handle_morning_confirm(event)
                    return

            # 3. Отметка привычки по номеру
            if text_lower in ("1", "2", "3", "4", "5", "6", "7", "8", "9"):
                await self._handle_habit_by_number(event, int(text_lower))
                return

            # 4. Отметка привычки по алиасу
            if text_lower in HABIT_ALIASES:
                await self._handle_habit_by_name(event, HABIT_ALIASES[text_lower])
                return

            # 5. Закрытие задачи: "з1", "з 1", "задача 1", "задача1"
            task_match = re.match(r'^(?:з|задача)\s*(\d+)$', text_lower)
            if task_match:
                await self._handle_task_done(event, int(task_match.group(1)))
                return

            # 6. Команды
            if text_lower == "план":
                await self._handle_plan_request(event)
                return

            if text_lower in ("стат", "статистика"):
                await self._handle_stats(event)
                return

            if text_lower == "привычки":
                await self._handle_habits_list(event)
                return

            if text_lower == "неделя":
                await self._handle_weekly(event)
                return

            if text_lower == "пропустить" and self.state.waiting_for == "evening_reflection":
                await self._handle_evening_skip(event)
                return

            if text_lower.startswith("добавить "):
                name = text[len("добавить "):].strip()
                if name:
                    await self._create_habit(event, name)
                return

            if text_lower.startswith("удалить "):
                try:
                    num = int(text_lower.split()[-1])
                    await self._delete_habit(event, num)
                except (ValueError, IndexError):
                    await self._reply(event, "Формат: удалить <номер>")
                return

            # 7. Неизвестная команда — игнорируем если нет контекста
            # (не спамим пользователю на каждое сообщение)

        except Exception as e:
            logger.error(f"Error handling message: {e}", exc_info=True)

    # ═══════════ УТРЕННИЙ ПРОТОКОЛ ═══════════

    async def _handle_morning_confirm(self, event) -> None:
        """Пользователь подтвердил подъём."""
        now = _now_msk()
        response_seconds = 0

        if self.state.morning_ping_sent_at:
            delta = now - self.state.morning_ping_sent_at
            response_seconds = int(delta.total_seconds())

        self.state.morning_confirmed = True
        self.state.waiting_for = None

        # Определяем вердикт
        response_minutes = response_seconds // 60
        if response_minutes < 3:
            verdict = MORNING_VERDICTS["fast"]
        elif response_minutes < 10:
            verdict = MORNING_VERDICTS["ok"]
        elif response_minutes < 20:
            verdict = MORNING_VERDICTS["slow"]
        else:
            verdict = MORNING_VERDICTS["bad"]

        # Сохраняем чек-ин
        async with get_session() as session:
            checkin = CheckIn(
                telegram_id=ADMIN_TELEGRAM_ID,
                checkin_type="morning",
                checkin_date=_today_msk(),
                response_time_seconds=response_seconds,
            )
            session.add(checkin)

        # Формируем чеклист привычек
        checklist = await self._format_habit_checklist()

        msg = MORNING_CONFIRMED.format(
            response_time=response_minutes,
            verdict=verdict,
            checklist=checklist,
        )
        await self._reply(event, msg)

    # ═══════════ ПРИВЫЧКИ ═══════════

    async def _handle_habit_by_number(self, event, number: int) -> None:
        """Отметить привычку по порядковому номеру."""
        habits = await self._get_active_habits()
        if number < 1 or number > len(habits):
            await self._reply(event, f"Привычки с номером {number} нет.")
            return
        habit = habits[number - 1]
        await self._mark_habit_done(event, habit)

    async def _handle_habit_by_name(self, event, habit_name: str) -> None:
        """Отметить привычку по имени."""
        habits = await self._get_active_habits()
        habit = next((h for h in habits if h.name == habit_name), None)
        if not habit:
            await self._reply(event, f"Привычка '{habit_name}' не найдена.")
            return
        await self._mark_habit_done(event, habit)

    async def _mark_habit_done(self, event, habit: Habit) -> None:
        """Отметить привычку как выполненную."""
        today = _today_msk()
        now = datetime.now(timezone.utc)

        async with get_session() as session:
            # Проверяем, не отмечена ли уже
            existing = await session.execute(
                select(HabitLog).where(
                    HabitLog.habit_id == habit.id,
                    HabitLog.log_date == today,
                )
            )
            log = existing.scalar_one_or_none()

            if log and log.completed_at:
                await self._reply(event, f"{habit.emoji} {habit.name} уже отмечена сегодня.")
                return

            if log:
                log.completed_at = now
            else:
                log = HabitLog(
                    habit_id=habit.id,
                    log_date=today,
                    completed_at=now,
                )
                session.add(log)

            # Обновляем streak
            db_habit = await session.get(Habit, habit.id)
            db_habit.current_streak += 1
            is_record = db_habit.current_streak > db_habit.best_streak
            if is_record:
                db_habit.best_streak = db_habit.current_streak

        # Ответ
        template = HABIT_DONE_RECORD if is_record else HABIT_DONE
        await self._reply(event, template.format(
            emoji=habit.emoji,
            name=habit.name,
            streak=habit.current_streak + 1,  # +1 потому что уже обновили
        ))

        # Проверяем, все ли привычки закрыты
        if await self._all_habits_done_today():
            await self._reply(event, HABIT_ALL_DONE)

    async def _get_active_habits(self) -> List[Habit]:
        """Получить активные привычки, отсортированные по порядку."""
        async with get_session() as session:
            result = await session.execute(
                select(Habit)
                .where(
                    Habit.telegram_id == ADMIN_TELEGRAM_ID,
                    Habit.is_active == True,
                )
                .order_by(Habit.sort_order)
            )
            return list(result.scalars().all())

    async def _all_habits_done_today(self) -> bool:
        """Проверить, все ли привычки отмечены сегодня."""
        habits = await self._get_active_habits()
        today = _today_msk()

        async with get_session() as session:
            for habit in habits:
                result = await session.execute(
                    select(HabitLog).where(
                        HabitLog.habit_id == habit.id,
                        HabitLog.log_date == today,
                        HabitLog.completed_at.isnot(None),
                    )
                )
                if not result.scalar_one_or_none():
                    return False
        return True

    async def _format_habit_checklist(self) -> str:
        """Форматировать чеклист привычек на сегодня."""
        habits = await self._get_active_habits()
        today = _today_msk()
        lines = []

        async with get_session() as session:
            for i, habit in enumerate(habits, 1):
                result = await session.execute(
                    select(HabitLog).where(
                        HabitLog.habit_id == habit.id,
                        HabitLog.log_date == today,
                        HabitLog.completed_at.isnot(None),
                    )
                )
                done = result.scalar_one_or_none() is not None
                mark = "✅" if done else "⬜"
                window = ""
                if habit.window_end:
                    window = f" (до {habit.window_end.strftime('%H:%M')})"
                lines.append(f"{i}. {mark} {habit.emoji} {habit.name}{window}")

        return "\n".join(lines)

    async def _handle_habits_list(self, event) -> None:
        """Показать список привычек с управлением."""
        habits = await self._get_active_habits()
        today = _today_msk()

        if not habits:
            await self._reply(event, "Нет активных привычек. «добавить <название>» для новой.")
            return

        lines = ["Твои привычки:\n"]
        async with get_session() as session:
            for i, habit in enumerate(habits, 1):
                result = await session.execute(
                    select(HabitLog).where(
                        HabitLog.habit_id == habit.id,
                        HabitLog.log_date == today,
                        HabitLog.completed_at.isnot(None),
                    )
                )
                done = "✅" if result.scalar_one_or_none() else "⬜"
                window = ""
                if habit.window_start and habit.window_end:
                    window = f" ({habit.window_start.strftime('%H:%M')}-{habit.window_end.strftime('%H:%M')})"
                elif habit.window_end:
                    window = f" (до {habit.window_end.strftime('%H:%M')})"
                lines.append(
                    f"{i}. {done} {habit.emoji} {habit.name}{window} — streak {habit.current_streak}"
                )

        lines.append("\n«добавить <название>» или «удалить <номер>»")
        await self._reply(event, "\n".join(lines))

    async def _create_habit(self, event, name: str) -> None:
        """Создать новую привычку."""
        async with get_session() as session:
            max_order = await session.execute(
                select(sa_func.max(Habit.sort_order)).where(
                    Habit.telegram_id == ADMIN_TELEGRAM_ID
                )
            )
            order = (max_order.scalar() or 0) + 1

            habit = Habit(
                telegram_id=ADMIN_TELEGRAM_ID,
                name=name,
                sort_order=order,
            )
            session.add(habit)

        await self._reply(event, f"Привычка «{name}» добавлена (#{order}).")

    async def _delete_habit(self, event, number: int) -> None:
        """Удалить привычку по номеру."""
        habits = await self._get_active_habits()
        if number < 1 or number > len(habits):
            await self._reply(event, f"Привычки с номером {number} нет.")
            return

        habit = habits[number - 1]
        async with get_session() as session:
            db_habit = await session.get(Habit, habit.id)
            db_habit.is_active = False

        await self._reply(event, f"Привычка «{habit.name}» удалена.")

    # ═══════════ РАБОЧИЙ ПЛАН ═══════════

    async def _handle_plan_request(self, event) -> None:
        """Показать или создать план на сегодня."""
        today = _today_msk()

        async with get_session() as session:
            plan_result = await session.execute(
                select(DailyPlan).where(
                    DailyPlan.telegram_id == ADMIN_TELEGRAM_ID,
                    DailyPlan.plan_date == today,
                )
            )
            plan = plan_result.scalar_one_or_none()

            if plan:
                tasks_result = await session.execute(
                    select(DailyPlanTask)
                    .where(DailyPlanTask.plan_id == plan.id)
                    .order_by(DailyPlanTask.sort_order)
                )
                tasks = list(tasks_result.scalars().all())

                if tasks:
                    lines = []
                    for i, task in enumerate(tasks, 1):
                        mark = "✅" if task.completed_at else "⬜"
                        lines.append(f"{i}. {mark} {task.task_text}")
                    await self._reply(event, PLAN_SHOW.format(tasks="\n".join(lines)))
                    return

        # Плана нет — запрашиваем
        self.state.waiting_for = "plan_tasks"
        await self._reply(event, PLAN_EMPTY)

    async def _handle_plan_input(self, event, text: str) -> None:
        """Получить задачи для плана (каждая с новой строки)."""
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        # Убираем нумерацию если есть
        tasks = []
        for line in lines:
            cleaned = re.sub(r'^\d+[\.\)\-]\s*', '', line).strip()
            if cleaned:
                tasks.append(cleaned)

        if not tasks:
            await self._reply(event, "Пусто. Напиши задачи, каждая с новой строки.")
            return

        today = _today_msk()
        self.state.waiting_for = None

        async with get_session() as session:
            plan = DailyPlan(
                telegram_id=ADMIN_TELEGRAM_ID,
                plan_date=today,
            )
            session.add(plan)
            await session.flush()

            for i, task_text in enumerate(tasks):
                task = DailyPlanTask(
                    plan_id=plan.id,
                    task_text=task_text,
                    sort_order=i + 1,
                )
                session.add(task)

        # Показываем план
        lines = [f"{i}. ⬜ {t}" for i, t in enumerate(tasks, 1)]
        await self._reply(event, PLAN_ACCEPTED.format(tasks="\n".join(lines)))

    async def _handle_task_done(self, event, task_number: int) -> None:
        """Закрыть задачу по номеру."""
        today = _today_msk()

        async with get_session() as session:
            plan_result = await session.execute(
                select(DailyPlan).where(
                    DailyPlan.telegram_id == ADMIN_TELEGRAM_ID,
                    DailyPlan.plan_date == today,
                )
            )
            plan = plan_result.scalar_one_or_none()

            if not plan:
                await self._reply(event, "Нет плана на сегодня. Напиши «план».")
                return

            tasks_result = await session.execute(
                select(DailyPlanTask)
                .where(DailyPlanTask.plan_id == plan.id)
                .order_by(DailyPlanTask.sort_order)
            )
            tasks = list(tasks_result.scalars().all())

            if task_number < 1 or task_number > len(tasks):
                await self._reply(event, f"Задачи с номером {task_number} нет.")
                return

            task = tasks[task_number - 1]
            if task.completed_at:
                await self._reply(event, f"Задача {task_number} уже закрыта.")
                return

            task.completed_at = datetime.now(timezone.utc)

        done_count = sum(1 for t in tasks if t.completed_at) + 1  # +1 for just completed
        total = len(tasks)

        await self._reply(event, PLAN_TASK_DONE.format(
            number=task_number,
            done=done_count,
            total=total,
        ))

        if done_count >= total:
            await self._reply(event, PLAN_ALL_DONE)

    # ═══════════ ВЕЧЕРНИЙ РАЗБОР ═══════════

    async def _handle_evening_reflection(self, event, text: str) -> None:
        """Получить текст рефлексии от пользователя."""
        self.state.context["reflection"] = text
        self.state.waiting_for = None

        # Передаём управление обратно в шедулер — он вызовет AI и продолжит
        # Сохраняем флаг что рефлексия получена
        self.state.context["reflection_received"] = True

    async def _handle_evening_skip(self, event) -> None:
        """Пользователь пропустил рефлексию."""
        self.state.waiting_for = "tomorrow_plan"
        await self._reply(event, EVENING_SKIPPED)

    async def _handle_tomorrow_plan(self, event, text: str) -> None:
        """Получить задачи на завтра."""
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        tasks = []
        for line in lines:
            cleaned = re.sub(r'^\d+[\.\)\-]\s*', '', line).strip()
            if cleaned:
                tasks.append(cleaned)

        if not tasks:
            await self._reply(event, "Пусто. Напиши 3-5 задач на завтра.")
            return

        tomorrow = _today_msk() + timedelta(days=1)
        self.state.waiting_for = None
        self.state.evening_done = True

        async with get_session() as session:
            plan = DailyPlan(
                telegram_id=ADMIN_TELEGRAM_ID,
                plan_date=tomorrow,
            )
            session.add(plan)
            await session.flush()

            for i, task_text in enumerate(tasks):
                task = DailyPlanTask(
                    plan_id=plan.id,
                    task_text=task_text,
                    sort_order=i + 1,
                )
                session.add(task)

        # Определяем время подъёма
        from discipline_bot.scheduler.discipline_scheduler import get_morning_time_str
        morning_time = get_morning_time_str()

        await self._reply(event, EVENING_DONE.format(morning_time=morning_time))

    # ═══════════ СТАТИСТИКА ═══════════

    async def _handle_stats(self, event) -> None:
        """Показать статистику."""
        habits = await self._get_active_habits()
        today = _today_msk()

        # Привычки
        habit_lines = []
        async with get_session() as session:
            for habit in habits:
                result = await session.execute(
                    select(HabitLog).where(
                        HabitLog.habit_id == habit.id,
                        HabitLog.log_date == today,
                        HabitLog.completed_at.isnot(None),
                    )
                )
                done_today = "✅" if result.scalar_one_or_none() else "⬜"
                habit_lines.append(
                    f"{done_today} {habit.emoji} {habit.name}: streak {habit.current_streak} "
                    f"(лучший: {habit.best_streak})"
                )

        # Задачи
        tasks_done = 0
        tasks_total = 0
        plan_result_q = await self._get_today_plan_stats()
        tasks_done, tasks_total = plan_result_q

        # Средний score за неделю
        week_avg = await self._get_week_avg_score()

        msg = (
            f"Статистика:\n\n"
            f"{chr(10).join(habit_lines)}\n\n"
            f"Задачи сегодня: {tasks_done}/{tasks_total}\n"
            f"Средний score за неделю: {week_avg}%"
        )
        await self._reply(event, msg)

    async def _get_today_plan_stats(self) -> tuple:
        """Получить статистику задач на сегодня."""
        today = _today_msk()
        async with get_session() as session:
            plan_result = await session.execute(
                select(DailyPlan).where(
                    DailyPlan.telegram_id == ADMIN_TELEGRAM_ID,
                    DailyPlan.plan_date == today,
                )
            )
            plan = plan_result.scalar_one_or_none()
            if not plan:
                return (0, 0)

            tasks_result = await session.execute(
                select(DailyPlanTask).where(DailyPlanTask.plan_id == plan.id)
            )
            tasks = list(tasks_result.scalars().all())
            done = sum(1 for t in tasks if t.completed_at)
            return (done, len(tasks))

    async def _get_week_avg_score(self) -> int:
        """Средний score за последние 7 дней."""
        week_ago = _today_msk() - timedelta(days=7)
        async with get_session() as session:
            result = await session.execute(
                select(sa_func.avg(DailyReview.score)).where(
                    DailyReview.telegram_id == ADMIN_TELEGRAM_ID,
                    DailyReview.review_date >= week_ago,
                    DailyReview.score.isnot(None),
                )
            )
            avg = result.scalar()
            return int(avg) if avg else 0

    async def _handle_weekly(self, event) -> None:
        """Недельная сводка (по запросу)."""
        # Делегируем в шедулер/AI
        self.state.context["weekly_requested"] = True
        await self._reply(event, "Генерирую недельную сводку...")

    # ═══════════ ДОБАВЛЕНИЕ ПРИВЫЧКИ ═══════════

    async def _handle_add_habit(self, event, text: str) -> None:
        """Получить название новой привычки."""
        name = text.strip()
        if not name:
            await self._reply(event, "Напиши название привычки.")
            return
        self.state.waiting_for = None
        await self._create_habit(event, name)

    # ═══════════ УТИЛИТЫ ═══════════

    async def _reply(self, event, text: str) -> None:
        """Ответить пользователю (через reply на его сообщение)."""
        try:
            await event.reply(text)
        except Exception as e:
            logger.error(f"Failed to reply: {e}")
            # Фоллбэк — отправить напрямую
            try:
                await self.client.send_message(event.chat_id, text)
            except Exception as e2:
                logger.error(f"Failed to send message fallback: {e2}")

    async def get_today_summary(self) -> dict:
        """Получить сводку дня для вечернего разбора."""
        habits = await self._get_active_habits()
        today = _today_msk()

        habits_done = 0
        habits_total = len(habits)
        missed_habits = []

        async with get_session() as session:
            for habit in habits:
                result = await session.execute(
                    select(HabitLog).where(
                        HabitLog.habit_id == habit.id,
                        HabitLog.log_date == today,
                        HabitLog.completed_at.isnot(None),
                    )
                )
                if result.scalar_one_or_none():
                    habits_done += 1
                else:
                    missed_habits.append(habit.name)

        tasks_done, tasks_total = await self._get_today_plan_stats()

        total_possible = habits_total + tasks_total
        total_done = habits_done + tasks_done
        score = int((total_done / total_possible * 100)) if total_possible > 0 else 0

        return {
            "habits_done": habits_done,
            "habits_total": habits_total,
            "tasks_done": tasks_done,
            "tasks_total": tasks_total,
            "missed_habits": missed_habits,
            "score": score,
        }
