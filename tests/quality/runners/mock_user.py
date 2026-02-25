"""
Mock User для тестирования без реальной БД.

Создаёт тестового пользователя для генерации ответов.
"""
from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime


@dataclass
class MockUser:
    """Тестовый пользователь"""
    id: int = 1
    telegram_id: int = 123456789
    username: str = "test_user"
    first_name: str = "Тест"
    last_name: str = "Тестов"
    segment: str = "D"  # Потребитель
    qualification: str = "consultant"
    is_active: bool = True
    created_at: datetime = None
    referral_link: str = "https://nlstore.com/ref/test/"

    # Поля для onboarding
    lessons_completed: int = 0
    current_day: int = 1
    completed_tasks: List[str] = field(default_factory=list)
    is_onboarding_completed: bool = False

    # Поля для целей
    current_goal: Optional[str] = None
    goal_deadline: Optional[datetime] = None

    # Дополнительные поля
    phone: Optional[str] = None
    email: Optional[str] = None
    city: Optional[str] = None
    bio: Optional[str] = None
    sponsor_id: Optional[int] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()


def create_mock_user(
    segment: str = "D",
    qualification: str = "consultant",
    first_name: str = "Тест"
) -> MockUser:
    """
    Создаёт тестового пользователя.

    Args:
        segment: D (потребитель), A (партнёр начальный), B (партнёр активный)
        qualification: consultant, M1, M2, M3, B1, B2, B3
        first_name: Имя

    Returns:
        MockUser
    """
    return MockUser(
        segment=segment,
        qualification=qualification,
        first_name=first_name
    )
