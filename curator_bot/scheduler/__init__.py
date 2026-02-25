"""
Планировщик для автоматических напоминаний воронки продаж
"""

from curator_bot.scheduler.reminder_scheduler import (
    setup_reminder_scheduler,
    shutdown_scheduler,
)

__all__ = [
    "setup_reminder_scheduler",
    "shutdown_scheduler",
]
