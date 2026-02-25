"""
Система персон и настроений для AI-ботов NL International.

Этот модуль предоставляет:
- MoodSystem: управление настроением бота
- HookSelector: выбор цепляющих фраз
- PersonaManager: управление персонами Данила
- Конфигурация персон и настроений

Используется в:
- AI-Контент-Менеджер: генерация постов с разным настроением
- AI-Куратор: общение с партнёрами в разных персонах
"""

from .mood_config import (
    MOOD_CATEGORIES,
    MOOD_WEIGHTS,
    INTENSITY_DISTRIBUTION,
    PERSONA_CHARACTERISTICS,
    MOOD_TO_PERSONA_MAP,
    get_personas_for_mood,
    TOTAL_EMOTIONS
)

from .persona_manager import PersonaManager, PersonaContext, MoodState
from .hook_templates import HOOK_TEMPLATES, TOTAL_HOOKS
from .hook_selector import HookSelector

__all__ = [
    # Конфигурация
    "MOOD_CATEGORIES",
    "MOOD_WEIGHTS",
    "INTENSITY_DISTRIBUTION",
    "PERSONA_CHARACTERISTICS",
    "MOOD_TO_PERSONA_MAP",
    "HOOK_TEMPLATES",
    "TOTAL_HOOKS",
    "TOTAL_EMOTIONS",

    # Утилиты
    "get_personas_for_mood",

    # Классы
    "PersonaManager",
    "PersonaContext",
    "MoodState",
    "HookSelector",
]
