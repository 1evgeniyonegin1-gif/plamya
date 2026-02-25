"""
Проактивный онбординг для AI-Куратора

Модуль включает:
- proactive_tasks.py - Чеклисты по дням для новичков
- onboarding_scheduler.py - Автоматические напоминания
- onboarding_service.py - Сервис для работы с БД
"""

from .proactive_tasks import (
    OnboardingTasks,
    get_task_for_day,
    get_user_progress,
    mark_task_completed
)
from .onboarding_scheduler import OnboardingScheduler
from .onboarding_service import OnboardingService

__all__ = [
    'OnboardingTasks',
    'get_task_for_day',
    'get_user_progress',
    'mark_task_completed',
    'OnboardingScheduler',
    'OnboardingService'
]
