"""
Менеджер персон Данила (УПРОЩЁННАЯ ВЕРСИЯ).

ИЗМЕНЕНИЯ 26.01.2026:
- Убрана генерация случайных эмоций
- Персона выбирается напрямую по типу поста
- Упрощён интерфейс

Используется в:
- AI-Контент-Менеджер: выбор тона для постов
- AI-Куратор: адаптация стиля общения
"""

import random
from typing import Optional, NamedTuple
from dataclasses import dataclass
from loguru import logger

from .mood_config import (
    PERSONA_CHARACTERISTICS,
    POST_TYPE_TO_PERSONAS,
    get_personas_for_post_type,
    get_persona_temperature
)
from .hook_selector import HookSelector


@dataclass
class MoodState:
    """Состояние (упрощённое — только персона)"""
    category: str = "neutral"
    emotion: str = "neutral"
    intensity: str = "medium"
    persona_version: str = "friend"
    trigger: Optional[str] = None


class PersonaContext(NamedTuple):
    """Контекст для генерации контента с персоной"""
    persona_version: str      # Версия персоны
    persona_name: str         # "Данил-Эксперт", etc.
    tone: str                 # Описание тона
    emoji: list[str]          # Подходящие эмодзи
    speech_patterns: list[str]  # Характерные фразы
    temperature: float        # Рекомендуемая температура AI
    hook: Optional[str]       # Цепляющая фраза (если запрошена)
    mood: Optional[MoodState]  # Совместимость со старым API


class PersonaManager:
    """
    Менеджер персон для AI-ботов (упрощённая версия).

    Предоставляет:
    - Выбор версии персоны по типу поста
    - Получение контекста для генерации
    - Выбор hook'ов
    """

    def __init__(self):
        """Инициализация менеджера"""
        self.hook_selector = HookSelector()
        self._current_persona: str = "friend"
        logger.info("[PersonaManager] Инициализирован (упрощённая версия)")

    def generate_mood(
        self,
        force_category: Optional[str] = None,
        force_intensity: Optional[str] = None,
        trigger: Optional[str] = None
    ) -> MoodState:
        """
        DEPRECATED: Возвращает MoodState для совместимости.
        Используй get_persona_context() напрямую.
        """
        return MoodState(
            category="neutral",
            emotion="neutral",
            intensity="medium",
            persona_version=self._current_persona,
            trigger=trigger
        )

    def trigger_mood_change(
        self,
        event: str,
        force_category: Optional[str] = None
    ) -> MoodState:
        """DEPRECATED: Возвращает MoodState для совместимости."""
        return self.generate_mood(trigger=event)

    def get_persona_context(
        self,
        mood: Optional[MoodState] = None,
        post_type: Optional[str] = None,
        include_hook: bool = False,
        hook_variables: Optional[dict[str, str]] = None
    ) -> PersonaContext:
        """
        Возвращает контекст персоны для генерации.

        Args:
            mood: Игнорируется (для совместимости)
            post_type: Тип поста — определяет выбор персоны
            include_hook: Включить цепляющую фразу
            hook_variables: Переменные для hook'а

        Returns:
            PersonaContext: Контекст для генерации
        """
        # Выбираем персону по типу поста
        if post_type:
            personas = get_personas_for_post_type(post_type)
            persona_version = random.choice(personas)
        else:
            persona_version = self._current_persona

        self._current_persona = persona_version

        # Получаем характеристики персоны
        persona_data = PERSONA_CHARACTERISTICS.get(
            persona_version,
            PERSONA_CHARACTERISTICS["friend"]
        )

        # Получаем hook если запрошен
        hook = None
        if include_hook:
            if hook_variables:
                hook = self.hook_selector.select_hook_with_variables(
                    persona_version=persona_version,
                    variables=hook_variables,
                    mood_category="neutral",
                    post_type=post_type
                )
            else:
                hook = self.hook_selector.select_hook(
                    persona_version=persona_version,
                    mood_category="neutral",
                    post_type=post_type
                )

        # Создаём MoodState для совместимости
        mood_state = MoodState(
            category="neutral",
            emotion="neutral",
            intensity="medium",
            persona_version=persona_version
        )

        return PersonaContext(
            persona_version=persona_version,
            persona_name=persona_data["name"],
            tone=persona_data["tone"],
            emoji=persona_data["emoji"],
            speech_patterns=persona_data["speech_patterns"],
            temperature=persona_data.get("temperature", 0.7),
            hook=hook,
            mood=mood_state
        )

    def get_prompt_enhancement(self, context: PersonaContext) -> str:
        """
        Возвращает дополнение к промпту на основе контекста персоны.

        Args:
            context: Контекст персоны

        Returns:
            str: Дополнительный текст для промпта
        """
        persona_data = PERSONA_CHARACTERISTICS.get(
            context.persona_version,
            PERSONA_CHARACTERISTICS["friend"]
        )

        enhancement = f"""
=== СТИЛЬ ОБЩЕНИЯ ===

ВЕРСИЯ ПЕРСОНЫ: {context.persona_name}
ТОН: {context.tone}

ХАРАКТЕРНЫЕ ФРАЗЫ:
{chr(10).join(f'- "{phrase}"' for phrase in context.speech_patterns)}

ОПИСАНИЕ: {persona_data['description']}

ЭМОДЗИ (используй умеренно): {' '.join(context.emoji[:5])}
"""

        if context.hook:
            enhancement += f"""

══════════════════════════════════════════
🎯 ОБЯЗАТЕЛЬНЫЙ HOOK (используй ДОСЛОВНО!)
══════════════════════════════════════════

НАЧНИ ПОСТ РОВНО С ЭТОЙ ФРАЗЫ:
"{context.hook}"

⚠️ СТРОГО! НЕ меняй эту фразу! НЕ переформулируй!
Используй её БУКВАЛЬНО как первое предложение.
После неё развивай мысль в стиле персоны.
══════════════════════════════════════════
"""

        return enhancement

    @property
    def current_mood(self) -> Optional[MoodState]:
        """DEPRECATED: Возвращает MoodState для совместимости"""
        return MoodState(persona_version=self._current_persona)

    def set_mood(self, mood: MoodState):
        """Устанавливает персону вручную"""
        self._current_persona = mood.persona_version
        logger.info(f"[PersonaManager] Персона установлена: {mood.persona_version}")

    @staticmethod
    def get_all_personas() -> list[str]:
        """Возвращает список всех доступных версий персоны"""
        return list(PERSONA_CHARACTERISTICS.keys())

    @staticmethod
    def get_persona_info(persona_version: str) -> dict:
        """
        Возвращает информацию о версии персоны.

        Args:
            persona_version: Версия персоны

        Returns:
            dict: Информация о персоне
        """
        return PERSONA_CHARACTERISTICS.get(
            persona_version,
            PERSONA_CHARACTERISTICS["friend"]
        )

    def explain_choice(
        self,
        mood: MoodState,
        post_type: Optional[str] = None
    ) -> str:
        """
        Объясняет почему была выбрана эта версия персоны.

        Args:
            mood: MoodState (используется persona_version)
            post_type: Тип поста

        Returns:
            str: Объяснение выбора
        """
        persona_data = self.get_persona_info(mood.persona_version)

        explanation = (
            f"Выбрана версия: {persona_data['name']}\n"
        )

        if post_type:
            explanation += f"Тип поста: {post_type}\n"
            personas = get_personas_for_post_type(post_type)
            explanation += f"Подходящие персоны: {', '.join(personas)}\n"

        explanation += (
            f"Тон: {persona_data['tone']}\n"
            f"Когда используется: {persona_data['when_to_use']}"
        )

        return explanation
