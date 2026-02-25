"""
Database models for Discipline Bot.

Таблицы:
- DisciplineConfig — настройки (расписание, тихие часы)
- Habit — привычки с окнами и стриками
- HabitLog — ежедневные логи привычек
- DailyPlan — рабочие планы на день
- DailyPlanTask — задачи плана
- DailyReview — вечерние AI-разборы
- CheckIn — чек-ины с таймингом отклика
"""

from datetime import datetime, date, time
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Time,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from traffic_engine.database.models import Base, TimestampMixin


class DisciplineConfig(Base, TimestampMixin):
    """Настройки дисциплины (1 строка на юзера)."""

    __tablename__ = "discipline_config"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)

    # Сезонный подъём
    winter_morning: Mapped[time] = mapped_column(Time, default=time(6, 0))
    summer_morning: Mapped[time] = mapped_column(Time, default=time(5, 0))
    morning_grace_minutes: Mapped[int] = mapped_column(Integer, default=30)

    # Вечерний разбор
    evening_time: Mapped[time] = mapped_column(Time, default=time(22, 0))

    # Напоминание по рабочему плану
    work_reminder_time: Mapped[time] = mapped_column(Time, default=time(18, 0))

    # Тихие часы
    quiet_start: Mapped[time] = mapped_column(Time, default=time(23, 0))
    quiet_end: Mapped[time] = mapped_column(Time, default=time(4, 30))

    # Фиксированный аккаунт для дисциплины (опционально)
    discipline_account_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)


class Habit(Base, TimestampMixin):
    """Привычка для отслеживания."""

    __tablename__ = "discipline_habits"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, index=True)

    name: Mapped[str] = mapped_column(String(100))
    emoji: Mapped[str] = mapped_column(String(10), default="✅")

    # Временное окно (MSK). NULL = в любое время
    window_start: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    window_end: Mapped[Optional[time]] = mapped_column(Time, nullable=True)

    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Стрики
    current_streak: Mapped[int] = mapped_column(Integer, default=0)
    best_streak: Mapped[int] = mapped_column(Integer, default=0)

    __table_args__ = (
        Index("idx_dh_telegram_active", "telegram_id", "is_active"),
    )


class HabitLog(Base):
    """Ежедневный лог привычки."""

    __tablename__ = "discipline_habit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    habit_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("discipline_habits.id", ondelete="CASCADE"), index=True
    )
    log_date: Mapped[date] = mapped_column(Date)
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    skipped: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("idx_dhl_habit_date", "habit_id", "log_date"),
        Index("idx_dhl_unique", "habit_id", "log_date", unique=True),
    )


class DailyPlan(Base, TimestampMixin):
    """Рабочий план на день."""

    __tablename__ = "discipline_daily_plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger)
    plan_date: Mapped[date] = mapped_column(Date)

    __table_args__ = (
        Index("idx_ddp_unique", "telegram_id", "plan_date", unique=True),
    )


class DailyPlanTask(Base):
    """Задача в рабочем плане."""

    __tablename__ = "discipline_plan_tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    plan_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("discipline_daily_plans.id", ondelete="CASCADE")
    )
    task_text: Mapped[str] = mapped_column(Text)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("idx_dpt_plan", "plan_id"),
    )


class DailyReview(Base):
    """Вечерний разбор дня."""

    __tablename__ = "discipline_daily_reviews"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger)
    review_date: Mapped[date] = mapped_column(Date)

    reflection_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ai_analysis: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    habits_completed: Mapped[int] = mapped_column(Integer, default=0)
    habits_total: Mapped[int] = mapped_column(Integer, default=0)
    tasks_completed: Mapped[int] = mapped_column(Integer, default=0)
    tasks_total: Mapped[int] = mapped_column(Integer, default=0)
    score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("idx_ddr_unique", "telegram_id", "review_date", unique=True),
    )


class CheckIn(Base):
    """Чек-ин с замером скорости отклика."""

    __tablename__ = "discipline_checkins"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger)
    checkin_type: Mapped[str] = mapped_column(String(30))  # morning, evening, habit, work
    checkin_date: Mapped[date] = mapped_column(Date)
    response_time_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("idx_dc_type_date", "telegram_id", "checkin_type", "checkin_date"),
    )
