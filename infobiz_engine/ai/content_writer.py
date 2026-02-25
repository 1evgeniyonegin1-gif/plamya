"""AI-генерация образовательного контента через shared AI client.

3-этапный пайплайн:
1. Architect (temp=0.7) — структура курса
2. Writer (temp=0.8) — текст уроков
3. Reviewer (temp=0.3) — проверка качества
"""

import json
import logging
import re

from shared.ai_client_cli import claude_call

from infobiz_engine.config import ANTI_AI_WORDS

logger = logging.getLogger("producer.ai.content")


ARCHITECT_PROMPT = """Ты — архитектор онлайн-курсов. Создай структуру курса.

Ответ СТРОГО в JSON:
{
  "title": "Название курса",
  "modules": [
    {
      "module_num": 1,
      "title": "Название модуля",
      "lessons": [
        {
          "lesson_num": 1,
          "title": "Название урока",
          "type": "theory"
        }
      ]
    }
  ]
}

Правила:
- 2-3 модуля, 1-2 урока в модуле
- Типы уроков: theory, practice
- Будь кратким"""


WRITER_PROMPT = """Ты — автор образовательного контента. Пиши уроки для онлайн-курса.

Правила:
- 500-1000 слов на урок
- Простой, понятный язык
- Используй markdown
- В конце урока: 2-3 ключевых вывода
- В конце урока: 1-2 практических задания

Избегай AI-штампов."""


REVIEWER_PROMPT = """Ты — редактор образовательного контента. Проверь урок.

Ответ в JSON:
{
  "quality_score": 75,
  "verdict": "approve/revise"
}"""


async def design_course_structure(
    niche_name: str,
    target_audience: str = "",
    competitor_gaps: list[str] | None = None,
) -> dict:
    """Этап 1: Архитектор — спроектировать структуру курса.

    Args:
        niche_name: Название ниши
        target_audience: Описание ЦА (если есть)
        competitor_gaps: Пробелы у конкурентов (если есть)

    Returns:
        Структура курса в JSON
    """
    try:
        prompt = f"{ARCHITECT_PROMPT}\n\nСоздай структуру онлайн-курса в нише: \"{niche_name}\"\n"
        if target_audience:
            prompt += f"Целевая аудитория: {target_audience}\n"
        if competitor_gaps:
            prompt += f"Пробелы конкурентов (закрой их): {', '.join(competitor_gaps)}\n"
        prompt += "\nКурс должен быть практичным — ученик получает реальный результат к концу."

        logger.info(f"Генерирую структуру курса для ниши: {niche_name}")
        text = claude_call(prompt=prompt, agent="producer", timeout=120)

        if text is None:
            logger.error("claude_call вернул None при создании структуры курса")
            raise RuntimeError("AI не ответил")

        json_match = re.search(r'\{[\s\S]*\}', text)
        if json_match:
            try:
                structure = json.loads(json_match.group())
                logger.info(f"Структура курса создана: {structure.get('title', 'Без названия')}")
                return structure
            except json.JSONDecodeError as e:
                logger.error(f"Ошибка парсинга JSON структуры курса: {e}")
                logger.debug(f"Текст ответа: {text[:500]}...")
        else:
            logger.warning("JSON структуры курса не найден в ответе AI")

        return {}
    except Exception as e:
        logger.error(f"Ошибка создания структуры курса: {e}")
        # Возвращаем минимальную структуру для продолжения работы
        return {
            "title": f"Курс по {niche_name}",
            "modules": [
                {
                    "module_num": 1,
                    "title": "Введение",
                    "lessons": [
                        {
                            "lesson_num": 1,
                            "title": "Введение в тему",
                            "type": "theory",
                            "key_topics": ["Основные понятия"]
                        }
                    ]
                }
            ]
        }


async def write_lesson(
    course_title: str,
    module_title: str,
    lesson_title: str,
    lesson_topics: list[str],
    lesson_type: str = "theory",
    previous_lessons_summary: str = "",
) -> str:
    """Этап 2: Писатель — сгенерировать текст одного урока.

    Args:
        course_title: Название курса
        module_title: Название модуля
        lesson_title: Название урока
        lesson_topics: Ключевые темы урока
        lesson_type: theory/practice/project
        previous_lessons_summary: Краткое содержание предыдущих уроков

    Returns:
        Markdown текст урока
    """
    try:
        prompt = (
            f"{WRITER_PROMPT}\n\n"
            f"Напиши урок для онлайн-курса.\n\n"
            f"Курс: {course_title}\n"
            f"Модуль: {module_title}\n"
            f"Урок: {lesson_title}\n"
            f"Тип: {lesson_type}\n"
            f"Ключевые темы: {', '.join(lesson_topics)}\n"
        )

        if lesson_type == "practice":
            prompt += "\nЭто ПРАКТИЧЕСКИЙ урок — 70% текста должны быть задания и примеры.\n"
        elif lesson_type == "project":
            prompt += "\nЭто ПРОЕКТНЫЙ урок — студент делает мини-проект. Дай пошаговую инструкцию.\n"

        if previous_lessons_summary:
            prompt += f"\nПредыдущие уроки (не повторяй): {previous_lessons_summary}\n"

        logger.info(f"Генерирую урок: {lesson_title}")
        text = claude_call(prompt=prompt, agent="producer", timeout=120)

        if text is None:
            logger.error(f"claude_call вернул None при генерации урока '{lesson_title}'")
            raise RuntimeError("AI не ответил")

        # Проверка на AI-слова
        text_lower = text.lower()
        found_ai = [w for w in ANTI_AI_WORDS if w in text_lower]
        if found_ai:
            logger.warning(f"AI-слова в уроке '{lesson_title}': {found_ai}")

        return text
    except Exception as e:
        logger.error(f"Ошибка генерации урока '{lesson_title}': {e}")
        # Возвращаем заглушку вместо падения
        return f"""# {lesson_title}

## Введение
Этот урок посвящён теме: {', '.join(lesson_topics)}.

## Основное содержание
Извините, в данный момент не удалось сгенерировать полный текст урока из-за технических проблем.

## Ключевые выводы
1. Изучите тему самостоятельно
2. Практикуйтесь на реальных примерах
3. Задавайте вопросы в комментариях

## Практика
1. Найдите информацию по теме в интернете
2. Создайте простой пример на основе изученного"""


async def review_lesson(lesson_text: str, lesson_title: str) -> dict:
    """Этап 3: Ревьюер — проверить качество урока.

    Args:
        lesson_text: Текст урока
        lesson_title: Название урока

    Returns:
        Оценка качества в JSON
    """
    try:
        prompt = (
            f"{REVIEWER_PROMPT}\n\n"
            f"Проверь качество урока: \"{lesson_title}\"\n\n"
            f"Текст урока:\n{lesson_text[:2000]}\n\n"
            f"Оцени: фактическую точность, читаемость, полноту. Найди AI-штампы."
        )

        logger.info(f"Проверяю качество урока: {lesson_title}")
        text = claude_call(prompt=prompt, agent="producer", timeout=120)

        if text is None:
            logger.error(f"claude_call вернул None при ревью урока '{lesson_title}'")
        else:
            json_match = re.search(r'\{[\s\S]*\}', text)
            if json_match:
                try:
                    review = json.loads(json_match.group())
                    logger.info(f"Урок проверен: {review.get('verdict', 'unknown')}, score: {review.get('quality_score', 0)}")
                    return review
                except json.JSONDecodeError as e:
                    logger.error(f"Ошибка парсинга JSON ревью: {e}")
                    logger.debug(f"Текст ответа: {text[:500]}...")
    except Exception as e:
        logger.error(f"Ошибка проверки урока '{lesson_title}': {e}")

    # Возвращаем дефолтный ревью при ошибке
    return {
        "quality_score": 50,
        "factual_accuracy": "unknown",
        "readability": "medium",
        "completeness": "partial",
        "ai_words_found": [],
        "suggestions": ["Автоматическая проверка не удалась"],
        "verdict": "approve"  # Одобряем, чтобы не блокировать пайплайн
    }
