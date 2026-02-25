"""
AI-Судья для оценки качества ответов и постов.

Использует Deepseek для оценки:
- Куратор: recurring characters, фирменные фразы, эмоциональные горки
- Контент: cliffhangers, типы постов, стиль

Дата: 03.02.2026
"""
import json
import re
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from loguru import logger


@dataclass
class EvaluationResult:
    """Результат оценки одного теста"""
    scenario_id: str
    scenario_name: str
    category: str

    # Ввод/вывод
    input_text: str  # вопрос или тема
    output_text: str  # ответ или пост

    # Оценки (1-10)
    scores: Dict[str, int] = field(default_factory=dict)

    # Проверки (True/False)
    checks: Dict[str, bool] = field(default_factory=dict)

    # Комментарии
    comments: Dict[str, str] = field(default_factory=dict)

    # Общий результат
    total_score: float = 0.0
    verdict: str = "UNKNOWN"  # PASS, WARN, FAIL
    summary: str = ""

    def to_dict(self) -> dict:
        return {
            "scenario_id": self.scenario_id,
            "scenario_name": self.scenario_name,
            "category": self.category,
            "input_text": self.input_text,
            "output_text": self.output_text,
            "scores": self.scores,
            "checks": self.checks,
            "comments": self.comments,
            "total_score": self.total_score,
            "verdict": self.verdict,
            "summary": self.summary
        }


class AIJudge:
    """
    AI-судья для оценки качества.

    Использует Deepseek для семантической оценки и
    правила для структурной проверки.
    """

    # Recurring characters для проверки
    RECURRING_CHARACTERS = ["Артём", "Артема", "Петровна", "Маша", "Олег"]

    # Фирменные фразы
    SIGNATURE_PHRASES = [
        "Честно?", "Стоп. Это важно", "Ну что, погнали?",
        "Смотри", "Знаешь что?", "Короче"
    ]

    # Cliffhanger маркеры
    CLIFFHANGER_MARKERS = [
        "продолжение", "завтра", "расскажу", "узнаешь",
        "следующ", "что было дальше", "...", "👇"
    ]

    # Запрещённые паттерны
    FORBIDDEN_PATTERNS = [
        r"^#\s",  # markdown заголовки
        r"✔️",  # галочки
        r"\d{2,3}% людей",  # фейковые проценты
        r"В современном мире",
        r"Уникальный продукт",
        r"лучший на рынке"
    ]

    def __init__(self, ai_client=None):
        """
        Args:
            ai_client: Клиент AI (Deepseek или любой совместимый)
        """
        self.ai_client = ai_client

    async def evaluate_curator_response(
        self,
        scenario: dict,
        response: str
    ) -> EvaluationResult:
        """
        Оценивает ответ AI-Куратора.

        Args:
            scenario: Сценарий из YAML
            response: Ответ куратора

        Returns:
            EvaluationResult
        """
        result = EvaluationResult(
            scenario_id=scenario.get("id", "unknown"),
            scenario_name=scenario.get("name", ""),
            category=scenario.get("category", ""),
            input_text=scenario.get("user_message", ""),
            output_text=response
        )

        expected = scenario.get("expected", {})

        # 1. Проверка recurring characters
        if expected.get("recurring_character"):
            chars_to_check = expected["recurring_character"]
            if isinstance(chars_to_check, str):
                chars_to_check = [chars_to_check]

            found_char = self._check_recurring_characters(response, chars_to_check)
            result.checks["recurring_character"] = found_char is not None
            result.comments["recurring_character"] = f"Найден: {found_char}" if found_char else "Персонаж не упомянут"
            result.scores["recurring_character"] = 10 if found_char else 3

        # 2. Проверка фирменных фраз
        if expected.get("signature_phrases"):
            found_phrase = self._check_signature_phrases(response, expected["signature_phrases"])
            result.checks["signature_phrases"] = found_phrase is not None
            result.comments["signature_phrases"] = f"Найдена: '{found_phrase}'" if found_phrase else "Фраза не найдена"
            result.scores["signature_phrases"] = 10 if found_phrase else 5

        # 3. Проверка эмоциональных горок
        if expected.get("emotional_arc"):
            has_arc = self._check_emotional_arc(response)
            result.checks["emotional_arc"] = has_arc
            result.scores["emotional_arc"] = 9 if has_arc else 5

        # 4. Проверка запрещённого контента
        forbidden = scenario.get("forbidden", [])
        forbidden_found = self._check_forbidden(response, forbidden)
        result.checks["no_forbidden"] = len(forbidden_found) == 0
        if forbidden_found:
            result.comments["forbidden"] = f"Найдено запрещённое: {forbidden_found}"
            result.scores["no_forbidden"] = 2
        else:
            result.scores["no_forbidden"] = 10

        # 5. Проверка длины (короткие сообщения)
        sentences = len(re.split(r'[.!?]', response))
        result.checks["short_message"] = sentences <= 8
        result.scores["short_message"] = 10 if sentences <= 5 else (7 if sentences <= 8 else 4)

        # Вычисление итога
        if result.scores:
            result.total_score = sum(result.scores.values()) / len(result.scores)

        # Verdict
        if result.total_score >= 8:
            result.verdict = "PASS"
        elif result.total_score >= 6:
            result.verdict = "WARN"
        else:
            result.verdict = "FAIL"

        # Summary
        result.summary = self._generate_summary(result)

        return result

    async def evaluate_content_post(
        self,
        scenario: dict,
        post_text: str
    ) -> EvaluationResult:
        """
        Оценивает сгенерированный пост.

        Args:
            scenario: Сценарий из YAML
            post_text: Текст поста

        Returns:
            EvaluationResult
        """
        result = EvaluationResult(
            scenario_id=scenario.get("id", "unknown"),
            scenario_name=scenario.get("name", ""),
            category=scenario.get("category", ""),
            input_text=scenario.get("topic", ""),
            output_text=post_text
        )

        expected = scenario.get("expected", {})
        post_type = scenario.get("post_type", "")

        # 1. Проверка recurring characters
        if expected.get("recurring_character"):
            chars = expected["recurring_character"]
            if isinstance(chars, str):
                chars = [chars]
            found_char = self._check_recurring_characters(post_text, chars)
            result.checks["recurring_character"] = found_char is not None
            result.comments["recurring_character"] = f"Найден: {found_char}" if found_char else "Персонаж не упомянут"
            result.scores["recurring_character"] = 10 if found_char else 3

        # 2. Проверка cliffhanger (для series)
        if expected.get("cliffhanger"):
            has_cliffhanger = self._check_cliffhanger(post_text)
            result.checks["cliffhanger"] = has_cliffhanger
            result.comments["cliffhanger"] = "Cliffhanger найден" if has_cliffhanger else "Нет cliffhanger"
            result.scores["cliffhanger"] = 10 if has_cliffhanger else 2

        # 3. Проверка HTML тегов
        has_html = self._check_html_tags(post_text)
        result.checks["html_tags"] = has_html
        result.scores["html_tags"] = 9 if has_html else 5

        # 4. Проверка эмодзи (1-4)
        emoji_count = self._count_emojis(post_text)
        good_emoji = 1 <= emoji_count <= 4
        result.checks["emoji_count"] = good_emoji
        result.comments["emoji_count"] = f"Эмодзи: {emoji_count}"
        result.scores["emoji_count"] = 10 if good_emoji else (6 if emoji_count < 6 else 3)

        # 5. Проверка запрещённого
        forbidden = scenario.get("forbidden", [])
        forbidden_found = self._check_forbidden(post_text, forbidden)
        result.checks["no_forbidden"] = len(forbidden_found) == 0
        if forbidden_found:
            result.comments["forbidden"] = f"Найдено: {forbidden_found}"
        result.scores["no_forbidden"] = 10 if not forbidden_found else 2

        # 6. Специфичные проверки по типу поста
        if post_type == "dark_moment":
            # Проверка уязвимости
            has_vulnerability = self._check_vulnerability(post_text)
            result.checks["vulnerability"] = has_vulnerability
            result.scores["vulnerability"] = 10 if has_vulnerability else 4

        elif post_type in ["series_intro", "series_continue"]:
            # Не раскрывает всё
            if expected.get("not_reveal_all"):
                not_reveals = not self._check_full_resolution(post_text)
                result.checks["not_reveal_all"] = not_reveals
                result.scores["not_reveal_all"] = 10 if not_reveals else 3

        elif post_type == "series_finale":
            # Раскрывает урок
            has_lesson = self._check_lesson(post_text)
            result.checks["lesson_learned"] = has_lesson
            result.scores["lesson_learned"] = 10 if has_lesson else 5

        elif post_type == "enemy_post":
            # Чёткий враг
            has_enemy = self._check_clear_enemy(post_text)
            result.checks["clear_enemy"] = has_enemy
            result.scores["clear_enemy"] = 10 if has_enemy else 4

        elif post_type == "urgency_post":
            # FOMO
            has_fomo = self._check_fomo(post_text)
            result.checks["fomo"] = has_fomo
            result.scores["fomo"] = 10 if has_fomo else 4

        # Вычисление итога
        if result.scores:
            result.total_score = sum(result.scores.values()) / len(result.scores)

        # Verdict
        if result.total_score >= 8:
            result.verdict = "PASS"
        elif result.total_score >= 6:
            result.verdict = "WARN"
        else:
            result.verdict = "FAIL"

        result.summary = self._generate_summary(result)

        return result

    # ═══════════════════════════════════════════════════════════════
    # Вспомогательные методы проверки
    # ═══════════════════════════════════════════════════════════════

    def _check_recurring_characters(self, text: str, expected_chars: List[str]) -> Optional[str]:
        """Проверяет упоминание recurring characters"""
        text_lower = text.lower()
        for char in expected_chars:
            if char.lower() in text_lower:
                return char
        # Также проверяем общий список
        for char in self.RECURRING_CHARACTERS:
            if char.lower() in text_lower:
                return char
        return None

    def _check_signature_phrases(self, text: str, expected_phrases: List[str]) -> Optional[str]:
        """Проверяет наличие фирменных фраз"""
        text_lower = text.lower()
        # Сначала проверяем ожидаемые
        for phrase in expected_phrases:
            if phrase.lower() in text_lower:
                return phrase
        # Потом общий список
        for phrase in self.SIGNATURE_PHRASES:
            if phrase.lower() in text_lower:
                return phrase
        return None

    def _check_emotional_arc(self, text: str) -> bool:
        """
        Проверяет наличие эмоциональных горок.
        НИЗ (проблема) → ПОВОРОТ (надежда) → ПОДЪЁМ (вывод)
        """
        # Маркеры низа (проблема)
        low_markers = ["устал", "не получ", "трудно", "сложно", "страшно", "боялс", "провал", "ошиб"]
        # Маркеры поворота
        turn_markers = ["но потом", "а потом", "и тогда", "однажды", "в один момент", "но однажд"]
        # Маркеры подъёма
        rise_markers = ["сейчас", "теперь", "понял", "научил", "получил", "смог", "вышло"]

        text_lower = text.lower()

        has_low = any(m in text_lower for m in low_markers)
        has_turn = any(m in text_lower for m in turn_markers)
        has_rise = any(m in text_lower for m in rise_markers)

        # Достаточно 2 из 3 элементов
        return sum([has_low, has_turn, has_rise]) >= 2

    def _check_forbidden(self, text: str, forbidden_list: List[str]) -> List[str]:
        """Проверяет наличие запрещённого контента"""
        found = []
        for pattern in forbidden_list:
            if re.search(pattern, text, re.IGNORECASE):
                found.append(pattern)
        # Также проверяем стандартные
        for pattern in self.FORBIDDEN_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                found.append(pattern)
        return found

    def _check_cliffhanger(self, text: str) -> bool:
        """Проверяет наличие cliffhanger"""
        text_lower = text.lower()
        return any(m in text_lower for m in self.CLIFFHANGER_MARKERS)

    def _check_html_tags(self, text: str) -> bool:
        """Проверяет наличие HTML тегов"""
        html_tags = ["<b>", "<i>", "<blockquote>", "</b>", "</i>", "</blockquote>"]
        return any(tag in text for tag in html_tags)

    def _count_emojis(self, text: str) -> int:
        """Считает количество эмодзи"""
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # symbols & pictographs
            "\U0001F680-\U0001F6FF"  # transport & map
            "\U0001F1E0-\U0001F1FF"  # flags
            "\U00002702-\U000027B0"
            "\U000024C2-\U0001F251"
            "]+",
            flags=re.UNICODE
        )
        return len(emoji_pattern.findall(text))

    def _check_vulnerability(self, text: str) -> bool:
        """Проверяет наличие уязвимости/честности"""
        markers = [
            "боялс", "страшно", "плакал", "не знал", "сомневал",
            "хотел брос", "устал", "не получ", "ошиб", "провал",
            "признаюсь", "честно", "правда в том"
        ]
        text_lower = text.lower()
        return any(m in text_lower for m in markers)

    def _check_full_resolution(self, text: str) -> bool:
        """Проверяет, раскрыта ли история полностью"""
        resolution_markers = [
            "итог", "вывод", "урок", "понял что", "научил меня",
            "в результате", "в конце концов", "мораль"
        ]
        text_lower = text.lower()
        return any(m in text_lower for m in resolution_markers)

    def _check_lesson(self, text: str) -> bool:
        """Проверяет наличие урока/вывода"""
        return self._check_full_resolution(text)

    def _check_clear_enemy(self, text: str) -> bool:
        """Проверяет наличие чёткого 'врага'"""
        enemy_markers = [
            "враг", "против", "борьба", "система", "они говорят",
            "все говорят", "рутина", "страх", "сомнения", "критики"
        ]
        text_lower = text.lower()
        return any(m in text_lower for m in enemy_markers)

    def _check_fomo(self, text: str) -> bool:
        """Проверяет наличие FOMO/срочности"""
        fomo_markers = [
            "осталось", "только", "сегодня", "последн", "успей",
            "заканчивается", "ограничен", "не упусти", "срочно"
        ]
        text_lower = text.lower()
        return any(m in text_lower for m in fomo_markers)

    def _generate_summary(self, result: EvaluationResult) -> str:
        """Генерирует краткое резюме"""
        passed = sum(1 for v in result.checks.values() if v)
        total = len(result.checks)

        if result.verdict == "PASS":
            return f"Отлично! {passed}/{total} проверок пройдено. Оценка: {result.total_score:.1f}/10"
        elif result.verdict == "WARN":
            failed = [k for k, v in result.checks.items() if not v]
            return f"Неплохо, но есть замечания: {', '.join(failed[:2])}. Оценка: {result.total_score:.1f}/10"
        else:
            failed = [k for k, v in result.checks.items() if not v]
            return f"Требует доработки: {', '.join(failed[:3])}. Оценка: {result.total_score:.1f}/10"
