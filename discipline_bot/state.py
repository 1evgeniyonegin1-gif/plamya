"""
In-memory FSM для отслеживания текущего состояния диалога.

Поскольку бот работает через Telethon (не aiogram),
используем простой класс вместо StatesGroup.
"""

from datetime import datetime
from typing import Optional, Dict, Any


class UserState:
    """Состояние текущего диалога с пользователем."""

    def __init__(self):
        # Что ожидаем от пользователя
        self.waiting_for: Optional[str] = None
        # morning_confirm — ожидаем "встал"
        # plan_tasks — ожидаем задачи (каждая с новой строки)
        # evening_reflection — ожидаем текст рефлексии
        # tomorrow_plan — ожидаем задачи на завтра
        # add_habit — ожидаем название новой привычки

        # Дополнительный контекст
        self.context: Dict[str, Any] = {}

        # Флаги дневных действий (сбрасываются в полночь)
        self.morning_ping_sent: bool = False
        self.morning_ping_sent_at: Optional[datetime] = None
        self.morning_confirmed: bool = False
        self.evening_sent: bool = False
        self.evening_done: bool = False
        self.work_reminder_sent: bool = False
        self.weekly_sent: bool = False

        # Эскалация
        self.morning_escalation_level: int = -1  # -1 = пинг не отправлен, 0-2 = уровни
        self.morning_failed: bool = False  # Не ответил за 30 мин

        # Напоминания по привычкам (habit_id -> уже отправлено)
        self.habit_reminders_sent: Dict[int, bool] = {}

    def reset_daily(self):
        """Сброс дневных флагов (вызывать в полночь МСК)."""
        self.waiting_for = None
        self.context = {}
        self.morning_ping_sent = False
        self.morning_ping_sent_at = None
        self.morning_confirmed = False
        self.evening_sent = False
        self.evening_done = False
        self.work_reminder_sent = False
        self.morning_escalation_level = -1
        self.morning_failed = False
        self.habit_reminders_sent = {}
        # weekly_sent сбрасывается только в понедельник

    def reset_weekly(self):
        """Сброс недельных флагов (вызывать в понедельник)."""
        self.weekly_sent = False
