"""
DisciplineScheduler — главный шедулер дисциплины.

Запускается как asyncio-задача внутри Traffic Engine.
Каждые 30 секунд проверяет:
- Утренний пинг (сезонное время)
- Эскалация если нет ответа
- Напоминания по окнам привычек
- Напоминание по рабочему плану (18:00)
- Вечерний разбор (22:00)
- Недельная сводка (вс 23:00)
"""

import asyncio
from datetime import datetime, date, time, timezone, timedelta
from typing import Optional, Dict

from loguru import logger
from sqlalchemy import select, func as sa_func
from telethon import TelegramClient, events

from traffic_engine.core import AccountManager
from traffic_engine.database import get_session
from traffic_engine.database.models import UserBotAccount

from discipline_bot.config import (
    ADMIN_TELEGRAM_ID,
    ESCALATION_DELAYS,
    MAX_ESCALATION_LEVEL,
    MORNING_PING,
    MORNING_ESCALATION,
    EVENING_START,
    EVENING_TOMORROW_PLAN,
    HABIT_WINDOW_REMINDER,
    HABIT_WINDOW_EXPIRED,
    PLAN_REMINDER,
)
from discipline_bot.database.models import (
    DisciplineConfig,
    Habit,
    HabitLog,
    DailyPlan,
    DailyPlanTask,
    DailyReview,
)
from discipline_bot.state import UserState
from discipline_bot.handler import MessageHandler
from discipline_bot.ai import Sergeant


MSK = timezone(timedelta(hours=3))


def _now_msk() -> datetime:
    return datetime.now(MSK)


def _today_msk() -> date:
    return datetime.now(MSK).date()


def get_morning_time_str() -> str:
    """Получить время подъёма как строку (для сообщений)."""
    month = _now_msk().month
    if month in (12, 1, 2):
        return "06:00"
    return "05:00"


class DisciplineScheduler:
    """Шедулер дисциплины — работает внутри TE."""

    def __init__(
        self,
        account_manager: AccountManager,
        notifier=None,
    ):
        self.account_manager = account_manager
        self.notifier = notifier
        self.running = False
        self._task: Optional[asyncio.Task] = None
        self._account_id: Optional[int] = None
        self._client: Optional[TelegramClient] = None
        self._state = UserState()
        self._handler: Optional[MessageHandler] = None
        self._sergeant = Sergeant()
        self._event_handler_registered = False
        self._admin_entity = None  # Кэш entity админа

    async def start(self) -> None:
        """Запустить шедулер."""
        if self.running:
            logger.warning("DisciplineScheduler already running")
            return

        # Выбрать аккаунт
        if not await self._select_account():
            logger.warning("No accounts available for discipline bot — will retry")

        self.running = True
        self._task = asyncio.create_task(self._scheduler_loop())
        logger.info("DisciplineScheduler started")

    async def stop(self) -> None:
        """Остановить шедулер."""
        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("DisciplineScheduler stopped")

    async def _select_account(self) -> bool:
        """Выбрать наименее загруженный аккаунт."""
        # Сначала проверяем фиксированный аккаунт из конфига
        async with get_session() as session:
            config_result = await session.execute(
                select(DisciplineConfig).where(
                    DisciplineConfig.telegram_id == ADMIN_TELEGRAM_ID
                )
            )
            config = config_result.scalar_one_or_none()

            if config and config.discipline_account_id:
                client = await self.account_manager.get_client(config.discipline_account_id)
                if client:
                    self._account_id = config.discipline_account_id
                    self._client = client
                    await self._setup_client()
                    logger.info(f"Using fixed discipline account #{self._account_id}")
                    return True

        # Автовыбор: наименее загруженный
        async with get_session() as session:
            result = await session.execute(
                select(UserBotAccount)
                .where(
                    UserBotAccount.tenant_id == self.account_manager.tenant_id,
                    UserBotAccount.status.in_(["active", "warming"]),
                )
                .order_by(UserBotAccount.daily_comments.asc())
            )
            accounts = list(result.scalars().all())

            for account in accounts:
                client = await self.account_manager.get_client(account.id)
                if client:
                    self._account_id = account.id
                    self._client = client
                    await self._setup_client()
                    logger.info(
                        f"Selected discipline account: {account.phone} "
                        f"(#{account.id}, {account.daily_comments} comments today)"
                    )
                    return True

        logger.warning("No Telethon clients available for discipline")
        return False

    async def _setup_client(self) -> None:
        """Настроить клиент: подключить, зарегистрировать обработчик."""
        if not self._client:
            return

        if not self._client.is_connected():
            await self._client.connect()

        self._handler = MessageHandler(self._client, self._state)

        # Регистрируем обработчик входящих сообщений от админа
        if not self._event_handler_registered:

            @self._client.on(events.NewMessage(
                from_users=[ADMIN_TELEGRAM_ID],
                incoming=True,
            ))
            async def _on_admin_message(event):
                if self._handler:
                    await self._handler.handle(event)
                    # Проверяем если нужно обработать рефлексию через AI
                    if self._state.context.get("reflection_received"):
                        await self._process_evening_reflection()
                    # Проверяем если запрошена недельная сводка
                    if self._state.context.get("weekly_requested"):
                        self._state.context.pop("weekly_requested", None)
                        await self._send_weekly_summary()

            self._event_handler_registered = True
            logger.info("Registered message handler for discipline bot")

    async def _scheduler_loop(self) -> None:
        """Главный цикл — проверки каждые 30 секунд."""
        while self.running:
            try:
                # Убедимся что аккаунт выбран
                if not self._client:
                    if not await self._select_account():
                        await asyncio.sleep(60)
                        continue

                now = _now_msk()

                # Сброс дневных флагов в полночь
                if now.hour == 0 and now.minute < 1:
                    self._state.reset_daily()
                    await self._reset_streaks_for_missed()

                # Сброс недельных в понедельник
                if now.weekday() == 0 and now.hour == 0 and now.minute < 1:
                    self._state.reset_weekly()

                # Проверка тихих часов
                config = await self._get_config()
                if self._is_quiet_hours(now, config):
                    await asyncio.sleep(30)
                    continue

                # 1. Утренний пинг
                await self._check_morning_ping(now, config)

                # 2. Эскалация утреннего пинга
                await self._check_morning_escalation(now)

                # 3. Напоминания по окнам привычек
                await self._check_habit_windows(now)

                # 4. Напоминание по рабочему плану
                await self._check_work_reminder(now, config)

                # 5. Вечерний разбор
                await self._check_evening_review(now, config)

                # 6. Недельная сводка (воскресенье)
                await self._check_weekly_summary(now, config)

                await asyncio.sleep(30)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in discipline scheduler: {e}", exc_info=True)
                await asyncio.sleep(30)

    # ═══════════ УТРЕННИЙ ПРОТОКОЛ ═══════════

    async def _check_morning_ping(self, now: datetime, config: DisciplineConfig) -> None:
        """Отправить утренний пинг если пора."""
        if self._state.morning_ping_sent or self._state.morning_confirmed:
            return

        morning_time = self._get_morning_time(now, config)
        if now.hour == morning_time.hour and now.minute >= morning_time.minute:
            await self._send(MORNING_PING)
            self._state.morning_ping_sent = True
            self._state.morning_ping_sent_at = now
            self._state.morning_escalation_level = -1
            self._state.waiting_for = "morning_confirm"
            logger.info(f"Morning ping sent at {now.strftime('%H:%M')}")

    async def _check_morning_escalation(self, now: datetime) -> None:
        """Эскалация если нет ответа на утренний пинг."""
        if not self._state.morning_ping_sent:
            return
        if self._state.morning_confirmed or self._state.morning_failed:
            return
        if not self._state.morning_ping_sent_at:
            return

        elapsed = now - self._state.morning_ping_sent_at
        next_level = self._state.morning_escalation_level + 1

        if next_level > MAX_ESCALATION_LEVEL:
            # Все уровни исчерпаны — проверяем grace period
            grace_minutes = 30  # default
            config = await self._get_config()
            if config:
                grace_minutes = config.morning_grace_minutes

            if elapsed.total_seconds() >= grace_minutes * 60:
                if not self._state.morning_failed:
                    self._state.morning_failed = True
                    self._state.waiting_for = None
                    logger.info("Morning check-in failed — no response")
            return

        # Проверяем, пора ли отправить следующий уровень
        delay = ESCALATION_DELAYS[next_level]
        if elapsed >= delay:
            if next_level < len(MORNING_ESCALATION):
                await self._send(MORNING_ESCALATION[next_level])
                self._state.morning_escalation_level = next_level
                logger.info(f"Morning escalation level {next_level} sent")

    # ═══════════ ПРИВЫЧКИ ═══════════

    async def _check_habit_windows(self, now: datetime) -> None:
        """Напоминания когда окно привычки закрывается."""
        if not self._state.morning_confirmed:
            return

        habits = await self._get_active_habits()
        today = _today_msk()

        async with get_session() as session:
            for habit in habits:
                if not habit.window_end:
                    continue
                if self._state.habit_reminders_sent.get(habit.id):
                    continue

                # Проверяем, не выполнена ли уже
                result = await session.execute(
                    select(HabitLog).where(
                        HabitLog.habit_id == habit.id,
                        HabitLog.log_date == today,
                        HabitLog.completed_at.isnot(None),
                    )
                )
                if result.scalar_one_or_none():
                    continue

                # Время до конца окна
                window_end_dt = now.replace(
                    hour=habit.window_end.hour,
                    minute=habit.window_end.minute,
                    second=0,
                )
                minutes_left = (window_end_dt - now).total_seconds() / 60

                if minutes_left <= 0:
                    # Окно закрылось — обнуляем streak
                    self._state.habit_reminders_sent[habit.id] = True
                    old_streak = habit.current_streak
                    if old_streak > 0:
                        db_habit = await session.get(Habit, habit.id)
                        db_habit.current_streak = 0
                        await session.commit()
                        await self._send(HABIT_WINDOW_EXPIRED.format(
                            emoji=habit.emoji,
                            name=habit.name,
                            old_streak=old_streak,
                        ))
                elif minutes_left <= 20:
                    # 20 минут до конца — напоминание
                    self._state.habit_reminders_sent[habit.id] = True
                    await self._send(HABIT_WINDOW_REMINDER.format(
                        emoji=habit.emoji,
                        name=habit.name,
                        minutes_left=int(minutes_left),
                        streak=habit.current_streak,
                    ))

    # ═══════════ РАБОЧИЙ ПЛАН ═══════════

    async def _check_work_reminder(self, now: datetime, config: DisciplineConfig) -> None:
        """Напоминание по рабочему плану."""
        if self._state.work_reminder_sent:
            return

        reminder_time = config.work_reminder_time if config else time(18, 0)
        if now.hour != reminder_time.hour or now.minute > 2:
            return

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
                return

            tasks_result = await session.execute(
                select(DailyPlanTask).where(DailyPlanTask.plan_id == plan.id)
            )
            tasks = list(tasks_result.scalars().all())
            done = sum(1 for t in tasks if t.completed_at)
            total = len(tasks)

            if done >= total:
                return  # Всё закрыто

        self._state.work_reminder_sent = True
        await self._send(PLAN_REMINDER.format(
            time=f"{reminder_time.hour}:00",
            done=done,
            total=total,
        ))

    # ═══════════ ВЕЧЕРНИЙ РАЗБОР ═══════════

    async def _check_evening_review(self, now: datetime, config: DisciplineConfig) -> None:
        """Вечерний разбор."""
        if self._state.evening_sent:
            return

        evening_time = config.evening_time if config else time(22, 0)
        if now.hour != evening_time.hour or now.minute > 2:
            return

        self._state.evening_sent = True

        # Собираем сводку дня
        summary = await self._handler.get_today_summary() if self._handler else {}

        habits_done = summary.get("habits_done", 0)
        habits_total = summary.get("habits_total", 0)
        tasks_done = summary.get("tasks_done", 0)
        tasks_total = summary.get("tasks_total", 0)
        missed = summary.get("missed_habits", [])
        score = summary.get("score", 0)

        missed_line = f"Пропущено: {', '.join(missed)}\n" if missed else ""

        await self._send(EVENING_START.format(
            habits_done=habits_done,
            habits_total=habits_total,
            tasks_done=tasks_done,
            tasks_total=tasks_total,
            missed_line=missed_line,
            score=score,
        ))

        self._state.waiting_for = "evening_reflection"
        self._state.context["evening_summary"] = summary

    async def _process_evening_reflection(self) -> None:
        """Обработать полученную рефлексию через AI."""
        self._state.context.pop("reflection_received", None)
        reflection = self._state.context.get("reflection", "")
        summary = self._state.context.get("evening_summary", {})

        # Получаем стрики
        streak_info = await self._format_streak_info()

        # AI разбор
        analysis = await self._sergeant.generate_evening_review(
            habits_done=summary.get("habits_done", 0),
            habits_total=summary.get("habits_total", 0),
            tasks_done=summary.get("tasks_done", 0),
            tasks_total=summary.get("tasks_total", 0),
            missed_habits=summary.get("missed_habits", []),
            score=summary.get("score", 0),
            reflection=reflection,
            streak_info=streak_info,
        )

        await self._send(analysis)

        # Сохраняем ревью
        today = _today_msk()
        async with get_session() as session:
            review = DailyReview(
                telegram_id=ADMIN_TELEGRAM_ID,
                review_date=today,
                reflection_text=reflection,
                ai_analysis=analysis,
                habits_completed=summary.get("habits_done", 0),
                habits_total=summary.get("habits_total", 0),
                tasks_completed=summary.get("tasks_done", 0),
                tasks_total=summary.get("tasks_total", 0),
                score=summary.get("score", 0),
            )
            session.add(review)

        # Запрашиваем план на завтра
        self._state.waiting_for = "tomorrow_plan"
        await self._send(EVENING_TOMORROW_PLAN)

    # ═══════════ НЕДЕЛЬНАЯ СВОДКА ═══════════

    async def _check_weekly_summary(self, now: datetime, config: DisciplineConfig) -> None:
        """Недельная сводка по воскресеньям."""
        if self._state.weekly_sent:
            return
        if now.weekday() != 6:  # 6 = воскресенье
            return

        evening_time = config.evening_time if config else time(22, 0)
        # Через час после вечернего разбора
        if now.hour != evening_time.hour + 1 or now.minute > 2:
            return

        self._state.weekly_sent = True
        await self._send_weekly_summary()

    async def _send_weekly_summary(self) -> None:
        """Генерировать и отправить недельную сводку."""
        today = _today_msk()
        week_start = today - timedelta(days=6)

        async with get_session() as session:
            # Ревью за неделю
            reviews_result = await session.execute(
                select(DailyReview)
                .where(
                    DailyReview.telegram_id == ADMIN_TELEGRAM_ID,
                    DailyReview.review_date >= week_start,
                    DailyReview.review_date <= today,
                )
                .order_by(DailyReview.review_date)
            )
            reviews = list(reviews_result.scalars().all())

            if not reviews:
                await self._send("Нет данных за неделю.")
                return

            # Статистика
            scores = [r.score for r in reviews if r.score is not None]
            avg_score = int(sum(scores) / len(scores)) if scores else 0

            total_habits = sum(r.habits_total for r in reviews)
            done_habits = sum(r.habits_completed for r in reviews)
            habits_pct = int(done_habits / total_habits * 100) if total_habits > 0 else 0

            total_tasks = sum(r.tasks_total for r in reviews)
            done_tasks = sum(r.tasks_completed for r in reviews)
            tasks_pct = int(done_tasks / total_tasks * 100) if total_tasks > 0 else 0

            # Лучший/худший день
            best = max(reviews, key=lambda r: r.score or 0)
            worst = min(reviews, key=lambda r: r.score or 100)
            days_ru = ["пн", "вт", "ср", "чт", "пт", "сб", "вс"]
            best_day = f"{days_ru[best.review_date.weekday()]} ({int(best.score or 0)}%)"
            worst_day = f"{days_ru[worst.review_date.weekday()]} ({int(worst.score or 0)}%)"

            # Прошлая неделя для тренда
            prev_week_start = week_start - timedelta(days=7)
            prev_result = await session.execute(
                select(sa_func.avg(DailyReview.score)).where(
                    DailyReview.telegram_id == ADMIN_TELEGRAM_ID,
                    DailyReview.review_date >= prev_week_start,
                    DailyReview.review_date < week_start,
                    DailyReview.score.isnot(None),
                )
            )
            prev_avg = prev_result.scalar()
            prev_week_avg = int(prev_avg) if prev_avg else None

        streak_info = await self._format_streak_info()

        # AI сводка
        analysis = await self._sergeant.generate_weekly_summary(
            habits_pct=habits_pct,
            tasks_pct=tasks_pct,
            avg_score=avg_score,
            best_day=best_day,
            worst_day=worst_day,
            streak_info=streak_info,
            prev_week_avg=prev_week_avg,
        )

        header = (
            f"НЕДЕЛЬНЫЙ РАЗБОР\n"
            f"Неделя: {week_start.strftime('%d.%m')} — {today.strftime('%d.%m')}\n\n"
            f"Привычки: {habits_pct}% ({done_habits}/{total_habits})\n"
            f"Задачи: {tasks_pct}% ({done_tasks}/{total_tasks})\n"
            f"Средний score: {avg_score}%\n"
            f"Лучший день: {best_day}\n"
            f"Худший день: {worst_day}\n\n"
            f"Стрики:\n{streak_info}\n\n"
            f"---\n{analysis}"
        )

        await self._send(header)

    # ═══════════ ВСПОМОГАТЕЛЬНЫЕ ═══════════

    async def _get_config(self) -> Optional[DisciplineConfig]:
        """Получить конфиг из БД."""
        async with get_session() as session:
            result = await session.execute(
                select(DisciplineConfig).where(
                    DisciplineConfig.telegram_id == ADMIN_TELEGRAM_ID
                )
            )
            return result.scalar_one_or_none()

    async def _get_active_habits(self) -> list:
        """Получить активные привычки."""
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

    def _get_morning_time(self, now: datetime, config: Optional[DisciplineConfig]) -> time:
        """Получить время подъёма с учётом сезона."""
        month = now.month
        if config:
            if month in (12, 1, 2):
                return config.winter_morning
            return config.summer_morning
        # Дефолт
        if month in (12, 1, 2):
            return time(6, 0)
        return time(5, 0)

    def _is_quiet_hours(self, now: datetime, config: Optional[DisciplineConfig]) -> bool:
        """Проверить тихие часы."""
        if not config:
            quiet_start = time(23, 0)
            quiet_end = time(4, 30)
        else:
            quiet_start = config.quiet_start
            quiet_end = config.quiet_end

        current = now.time()

        # Тихие часы через полночь (23:00 - 04:30)
        if quiet_start > quiet_end:
            return current >= quiet_start or current <= quiet_end
        else:
            return quiet_start <= current <= quiet_end

    async def _format_streak_info(self) -> str:
        """Форматировать информацию о стриках."""
        habits = await self._get_active_habits()
        lines = []
        for h in habits:
            record = f" (рекорд!)" if h.current_streak >= h.best_streak and h.current_streak > 0 else ""
            lines.append(f"{h.emoji} {h.name}: {h.current_streak} дней{record}")
        return "\n".join(lines)

    async def _reset_streaks_for_missed(self) -> None:
        """Обнулить стрики для пропущенных вчера привычек."""
        yesterday = _today_msk() - timedelta(days=1)
        habits = await self._get_active_habits()

        async with get_session() as session:
            for habit in habits:
                result = await session.execute(
                    select(HabitLog).where(
                        HabitLog.habit_id == habit.id,
                        HabitLog.log_date == yesterday,
                        HabitLog.completed_at.isnot(None),
                    )
                )
                if not result.scalar_one_or_none():
                    # Пропущено вчера — обнуляем streak
                    db_habit = await session.get(Habit, habit.id)
                    if db_habit and db_habit.current_streak > 0:
                        logger.info(
                            f"Resetting streak for {habit.name}: "
                            f"{db_habit.current_streak} → 0"
                        )
                        db_habit.current_streak = 0

    async def _resolve_admin_entity(self):
        """Резолвить entity админа (нужно для первого сообщения)."""
        if self._admin_entity is not None:
            return self._admin_entity

        try:
            # Пробуем по ID
            self._admin_entity = await self._client.get_input_entity(ADMIN_TELEGRAM_ID)
            return self._admin_entity
        except (ValueError, Exception):
            logger.warning(
                f"Cannot resolve admin by ID {ADMIN_TELEGRAM_ID}. "
                f"Admin should send any message to this account first."
            )
            return None

    async def _send(self, text: str) -> None:
        """Отправить сообщение Данилу."""
        if not self._client:
            logger.warning("No client available for discipline message")
            return

        try:
            entity = await self._resolve_admin_entity()
            if entity is None:
                logger.error(
                    "Cannot send discipline message: admin entity not resolved. "
                    "Admin needs to send any message to this account first."
                )
                return
            await self._client.send_message(entity, text)
        except Exception as e:
            logger.error(f"Failed to send discipline message: {e}")
