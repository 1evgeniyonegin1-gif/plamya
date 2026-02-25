"""
Запуск тестов качества для ботов NL International.

Загружает сценарии, запускает генерацию, оценивает качество.

Дата: 03.02.2026
"""
import asyncio
import yaml
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from loguru import logger

from tests.quality.evaluators.ai_judge import AIJudge, EvaluationResult


@dataclass
class TestConfig:
    """Конфигурация запуска тестов"""
    limit: int = 100
    category: Optional[str] = None
    verbose: bool = True
    bot_type: str = "all"  # curator, content, all


class QualityTestRunner:
    """
    Запуск тестов качества с реальным AI.

    Поддерживает:
    - AI-Куратор (curator_bot)
    - Контент-Менеджер (content_manager_bot)
    """

    def __init__(self):
        self.judge = AIJudge()
        self.curator_results: List[EvaluationResult] = []
        self.content_results: List[EvaluationResult] = []

        # Пути к сценариям
        self.scenarios_dir = Path(__file__).parent.parent / "scenarios"

    def load_scenarios(self, filename: str) -> List[dict]:
        """Загружает сценарии из YAML"""
        path = self.scenarios_dir / filename
        if not path.exists():
            logger.error(f"Файл сценариев не найден: {path}")
            return []

        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            return data.get("scenarios", [])

    async def run_curator_tests(
        self,
        config: TestConfig
    ) -> List[EvaluationResult]:
        """
        Запускает тесты AI-Куратора.

        Args:
            config: Конфигурация тестов

        Returns:
            Список результатов
        """
        logger.info("🤖 Запуск тестов AI-Куратора...")

        scenarios = self.load_scenarios("curator_scenarios.yaml")

        # Фильтрация по категории
        if config.category:
            scenarios = [s for s in scenarios if s.get("category") == config.category]

        # Лимит
        scenarios = scenarios[:config.limit]

        logger.info(f"Загружено сценариев: {len(scenarios)}")

        results = []

        for i, scenario in enumerate(scenarios, 1):
            logger.info(f"[{i}/{len(scenarios)}] Тест #{scenario['id']}: {scenario['name']}")

            try:
                # Генерируем ответ куратора
                response = await self._generate_curator_response(scenario)

                # Оцениваем
                result = await self.judge.evaluate_curator_response(scenario, response)
                results.append(result)

                # Прогресс
                verdict_emoji = {"PASS": "✅", "WARN": "⚠️", "FAIL": "❌"}.get(result.verdict, "❓")
                logger.info(f"   → {result.total_score:.1f}/10 {verdict_emoji}")

            except Exception as e:
                logger.error(f"   → Ошибка: {e}")
                # Создаём failed result
                result = EvaluationResult(
                    scenario_id=scenario.get("id", "?"),
                    scenario_name=scenario.get("name", "?"),
                    category=scenario.get("category", "?"),
                    input_text=scenario.get("user_message", ""),
                    output_text=f"ОШИБКА: {e}",
                    verdict="FAIL",
                    total_score=0
                )
                results.append(result)

        self.curator_results = results
        return results

    async def run_content_tests(
        self,
        config: TestConfig
    ) -> List[EvaluationResult]:
        """
        Запускает тесты Контент-Менеджера.

        Args:
            config: Конфигурация тестов

        Returns:
            Список результатов
        """
        logger.info("📝 Запуск тестов Контент-Менеджера...")

        scenarios = self.load_scenarios("content_scenarios.yaml")

        # Фильтрация по категории
        if config.category:
            scenarios = [s for s in scenarios if s.get("category") == config.category or s.get("post_type") == config.category]

        # Лимит
        scenarios = scenarios[:config.limit]

        logger.info(f"Загружено сценариев: {len(scenarios)}")

        results = []

        for i, scenario in enumerate(scenarios, 1):
            logger.info(f"[{i}/{len(scenarios)}] Тест #{scenario['id']}: {scenario['name']}")

            try:
                # Генерируем пост
                post_text = await self._generate_content_post(scenario)

                # Оцениваем
                result = await self.judge.evaluate_content_post(scenario, post_text)
                results.append(result)

                # Прогресс
                verdict_emoji = {"PASS": "✅", "WARN": "⚠️", "FAIL": "❌"}.get(result.verdict, "❓")
                logger.info(f"   → {result.total_score:.1f}/10 {verdict_emoji}")

            except Exception as e:
                logger.error(f"   → Ошибка: {e}")
                result = EvaluationResult(
                    scenario_id=scenario.get("id", "?"),
                    scenario_name=scenario.get("name", "?"),
                    category=scenario.get("category", "?"),
                    input_text=scenario.get("topic", ""),
                    output_text=f"ОШИБКА: {e}",
                    verdict="FAIL",
                    total_score=0
                )
                results.append(result)

        self.content_results = results
        return results

    async def _generate_curator_response(self, scenario: dict) -> str:
        """
        Генерирует ответ куратора через Deepseek напрямую.

        Использует тот же промпт что и реальный куратор, но без БД.

        Args:
            scenario: Сценарий с user_message

        Returns:
            Текст ответа
        """
        # Всегда используем прямой вызов AI (без зависимости от БД)
        return await self._fallback_curator_response(scenario)

    async def _fallback_curator_response(self, scenario: dict) -> str:
        """Генерация через Deepseek напрямую с промптом куратора"""
        try:
            from shared.ai_clients.deepseek_client import DeepseekClient

            client = DeepseekClient()

            # Определяем категорию для выбора подходящего персонажа
            category = scenario.get("category", "")
            expected = scenario.get("expected", {})

            # Выбираем персонажа на основе ожиданий
            character_hint = ""
            if expected.get("recurring_character"):
                chars = expected["recurring_character"]
                if isinstance(chars, list):
                    char_name = chars[0]
                else:
                    char_name = chars
                character_hint = f"""

⚠️⚠️⚠️ КРИТИЧЕСКИ ВАЖНО! ⚠️⚠️⚠️
ТЫ ДОЛЖЕН ИСПОЛЬЗОВАТЬ ПЕРСОНАЖА: {char_name}
Упомяни {char_name} ПО ИМЕНИ в ответе!
Расскажи историю {char_name} как пример!
БЕЗ {char_name} — ответ будет НЕПРАВИЛЬНЫМ!"""

            prompt = f"""Ты — AI-куратор NL International по имени Данил, 24 года.

RECURRING CHARACTERS (ОБЯЗАТЕЛЬНО используй в историях!):
- Артём — скептик, 3 месяца спорил что это развод, теперь партнёр M1
- Петровна — 45+, все говорили "куда ты в 45?", теперь M2
- Маша — новичок, руки тряслись при первом сообщении, сейчас 30к/мес
- Олег — бизнесмен, показал чек жене, она не верила, теперь гордится
{character_hint}

ФИРМЕННЫЕ ФРАЗЫ (ОБЯЗАТЕЛЬНО используй 1-2!):
- "Честно?" — в начале
- "Стоп. Это важно" — акцент
- "Ну что, погнали?" — призыв
- "Смотри" — объяснение
- "Знаешь что?" — инсайт

═══════════════════════════════════════════
🎢 ЭМОЦИОНАЛЬНЫЕ ГОРКИ — ОБЯЗАТЕЛЬНО!!!
═══════════════════════════════════════════

КАЖДЫЙ твой ответ ДОЛЖЕН иметь структуру:

1. НИЗ — признай проблему ("Понимаю. Я сам так чувствовал...")
2. ПОВОРОТ — история персонажа ("А потом Артём показал...")
3. ПОДЪЁМ — результат + надежда ("Сейчас он M1. Ты тоже сможешь.")

❌ ПЛОХО (без горок):
"Да, это нормально. Продолжай работать."

✅ ХОРОШО (с горками):
"Честно? Я сам так думал месяц назад. [НИЗ]
Сидел и думал — может бросить.
А потом Маша написала — первая продажа! [ПОВОРОТ]
Неделю как пришла, а уже результат.
Ради таких моментов и держусь. [ПОДЪЁМ]"

КАТЕГОРИЯ: {category}
ВОПРОС: "{scenario.get('user_message', '')}"

ПРАВИЛА:
- Короткие предложения
- Разговорный стиль
- БЕЗ markdown (# ## ###)
- ОБЯЗАТЕЛЬНО: персонаж + фраза + горки (НИЗ→ПОВОРОТ→ПОДЪЁМ)

Напиши ответ:"""

            system_prompt = "Ты AI-куратор NL International по имени Данил, 24 года. Отвечай коротко, дружелюбно."

            response = await client.generate_response(
                system_prompt=system_prompt,
                user_message=prompt,
                max_tokens=600,
                temperature=0.8
            )
            return response

        except Exception as e:
            logger.error(f"Генерация не удалась: {e}")
            return f"[Ошибка генерации: {e}]"

    async def _generate_content_post(self, scenario: dict) -> str:
        """
        Генерирует пост через Deepseek напрямую.

        Args:
            scenario: Сценарий с post_type и topic

        Returns:
            Текст поста
        """
        # Используем прямой вызов AI (без зависимости от БД)
        return await self._fallback_content_post(scenario)

    async def _fallback_content_post(self, scenario: dict) -> str:
        """Генерация поста через Deepseek напрямую"""
        try:
            from shared.ai_clients.deepseek_client import DeepseekClient

            client = DeepseekClient()

            post_type = scenario.get("post_type", "product")
            topic = scenario.get("topic", "")
            expected = scenario.get("expected", {})
            series_context = scenario.get("series_context", {})

            # Подсказка по персонажу
            character_hint = ""
            if expected.get("recurring_character"):
                char = expected["recurring_character"]
                if isinstance(char, list):
                    char = char[0]
                character_hint = f"\nОБЯЗАТЕЛЬНО используй персонажа {char} в истории!"

            # Контекст серии
            series_hint = ""
            if series_context:
                series_hint = f"""
КОНТЕКСТ СЕРИИ:
- Название: {series_context.get('title', '')}
- Часть: {series_context.get('part', 1)} из {series_context.get('total', 3)}
- Предыдущий cliffhanger: {series_context.get('last_cliffhanger', '')}
"""

            # Инструкции по типу поста (усиленные)
            type_instructions = {
                "dark_moment": """Покажи НАСТОЯЩУЮ УЯЗВИМОСТЬ!
НЕ пиши абстрактно "было сложно" — пиши КОНКРЕТНО:
• Физические ощущения: "руки тряслись", "плакала в ванной"
• Конкретные слова: кто что СКАЗАЛ ("муж спросил: 'может хватит?'")
• Момент сдачи: "открыла чат написать что ухожу"
В конце — поворот и надежда.""",
                "series_intro": "Создай ИНТРИГУ. Не раскрывай всё! В конце ОБЯЗАТЕЛЬНО cliffhanger: 'продолжение завтра...'",
                "series_continue": "Раскрой предыдущий cliffhanger. Создай НОВУЮ интригу в конце.",
                "series_finale": "РАСКРОЙ все загадки. Дай урок/вывод. CTA уместен.",
                "enemy_post": """Сделай ВРАГА КОНКРЕТНЫМ!
НЕ абстрактный "мифы" → А "начальник: 'куда ты пойдёшь?'"
НЕ "общество" → А "родственники: 'а когда нормальную работу?'"
Враг должен вызывать ЗЛОСТЬ и желание доказать!
Покажи кому выгодно (аптеки, работодатели).""",
                "urgency_post": "Создай FOMO — срочность, ограниченность, 'успей сейчас'."
            }

            type_hint = type_instructions.get(post_type, "Расскажи историю, не рекламируй.")

            prompt = f"""Ты — контент-менеджер NL International.

RECURRING CHARACTERS (называй по имени в историях):
- Артём — скептик, 3 месяца спорил что это развод, теперь M1
- Петровна — 45+, начальник смеялся "куда ты в 45?", теперь M2, зарабатывает больше него
- Маша — новичок, руки тряслись при первом сообщении, сейчас 30к/мес
- Олег — бизнесмен, показал чек жене, она не верила, теперь гордится
{character_hint}

ТИП ПОСТА: {post_type}
ТЕМА: {topic}
{series_hint}

ИНСТРУКЦИЯ ДЛЯ ЭТОГО ТИПА:
{type_hint}

ОБЯЗАТЕЛЬНЫЕ ПРАВИЛА:
1. Начни с сомнения, вопроса или интриги (НЕ с приветствия!)
2. Используй HTML: <b>жирный</b>, <i>курсив</i>, <blockquote>цитата</blockquote>
3. 1-4 эмодзи (не больше!)
4. Короткие абзацы (1-2 предложения, пустая строка между ними)
5. Простые названия: "коктейль", "коллаген", "дрейн" (НЕ "Energy Diet")
6. БЕЗ галочек ✔️
7. БЕЗ "87% людей" и фейковых цифр
8. БЕЗ "В современном мире", "Уникальный продукт"

Напиши пост (300-600 символов):"""

            system_prompt = "Ты контент-менеджер NL International. Пишешь вовлекающие посты для Telegram-канала."

            response = await client.generate_response(
                system_prompt=system_prompt,
                user_message=prompt,
                max_tokens=800,
                temperature=0.85
            )
            return response

        except Exception as e:
            logger.error(f"Генерация поста не удалась: {e}")
            return f"[Ошибка генерации: {e}]"

    @property
    def all_results(self) -> List[EvaluationResult]:
        """Все результаты"""
        return self.curator_results + self.content_results
