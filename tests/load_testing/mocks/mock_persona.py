"""
Mock Persona Manager для нагрузочного тестирования

Детерминированный выбор персоны без AI.
Эмулирует логику выбора tone/style/hooks.
"""

from typing import Optional, Dict, List
from dataclasses import dataclass


@dataclass
class PersonaContext:
    """Контекст персоны для генерации контента"""
    persona_name: str
    persona_version: str
    temperature: float
    tone: str
    emoji: List[str]
    speech_patterns: List[str]
    hook: Optional[str] = None


class MockPersonaManager:
    """
    Детерминированный выбор персоны

    Используется для тестирования без реальной логики персон
    """

    def __init__(self):
        self.persona_calls = 0
        self.persona_distribution = {}

        # Определяем персоны
        self.personas = {
            "expert": {
                "tone": "дружелюбный, экспертный",
                "emoji": ["💪", "✅", "🔥", "⚡"],
                "speech_patterns": ["Давай разберёмся", "Честно?", "Окей,", "Слушай"],
                "temperature": 0.7,
            },
            "friend": {
                "tone": "дружеский, неформальный",
                "emoji": ["😊", "👍", "🎉", "💬"],
                "speech_patterns": ["Слушай,", "Вчера мне", "Знаешь что?", "Прикинь"],
                "temperature": 0.8,
            },
            "motivator": {
                "tone": "мотивирующий, энергичный",
                "emoji": ["🔥", "💪", "🚀", "⭐"],
                "speech_patterns": ["Давай!", "Ты можешь!", "Вперёд!", "Не сдавайся!"],
                "temperature": 0.9,
            },
        }

        # Hooks для разных персон
        self.hooks = {
            "expert": [
                "Давай разберёмся что внутри:",
                "Честно? Я сам сначала не знал.",
                "Окей, вот как это работает:",
                "Слушай, тут важный момент:",
            ],
            "friend": [
                "Вчера получил сообщение от подписчика...",
                "Слушай, у меня история для тебя.",
                "Знаешь что самое крутое?",
                "Прикинь, вчера узнал...",
            ],
            "motivator": [
                "Хватит откладывать!",
                "Твой успех начинается сегодня.",
                "Время действовать!",
                "Вперёд к цели!",
            ],
        }

    def get_persona_context(
        self,
        post_type: Optional[str] = None,
        include_hook: bool = False,
        hook_variables: Optional[Dict] = None
    ) -> PersonaContext:
        """
        Возвращает контекст персоны

        Args:
            post_type: Тип поста (product, motivation, tips, etc.)
            include_hook: Включить hook в контекст
            hook_variables: Переменные для подстановки в hook

        Returns:
            PersonaContext с настройками персоны
        """
        self.persona_calls += 1

        # Детерминированный выбор персоны на основе post_type
        persona_map = {
            "product": "expert",
            "motivation": "motivator",
            "tips": "expert",
            "success_story": "friend",
            "news": "expert",
            "promo": "motivator",
            None: "expert",
        }

        persona_name = persona_map.get(post_type, "expert")

        # Обновляем распределение
        self.persona_distribution[persona_name] = self.persona_distribution.get(persona_name, 0) + 1

        persona_data = self.personas[persona_name]

        # Выбираем hook (если нужно)
        hook = None
        if include_hook:
            import random
            hooks = self.hooks.get(persona_name, [])
            hook = random.choice(hooks) if hooks else None

            # Подставляем переменные в hook
            if hook and hook_variables:
                for key, value in hook_variables.items():
                    hook = hook.replace(f"{{{key}}}", str(value))

        return PersonaContext(
            persona_name=persona_name,
            persona_version="v1",
            temperature=persona_data["temperature"],
            tone=persona_data["tone"],
            emoji=persona_data["emoji"],
            speech_patterns=persona_data["speech_patterns"],
            hook=hook,
        )

    def get_random_persona(self) -> PersonaContext:
        """Возвращает случайную персону"""
        import random
        persona_name = random.choice(list(self.personas.keys()))
        return self.get_persona_context(post_type=None)

    def get_metrics(self) -> Dict:
        """Возвращает метрики использования персон"""
        return {
            "persona_calls": self.persona_calls,
            "persona_distribution": self.persona_distribution,
        }

    def reset_metrics(self):
        """Сбрасывает метрики"""
        self.persona_calls = 0
        self.persona_distribution = {}
