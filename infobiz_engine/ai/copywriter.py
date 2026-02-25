"""AI-генерация продающего текста для лендингов и промо через shared AI client."""

import json
import logging
import re

from shared.ai_client_cli import claude_call

from infobiz_engine.config import ANTI_AI_WORDS

logger = logging.getLogger("producer.ai.copy")

LANDING_PROMPT = """Ты — копирайтер, который пишет продающие тексты для лендингов онлайн-курсов.

Стиль: прямой, конкретный, без воды. Пиши как для друга, а не как для аудитории.
НЕ используй: безусловно, несомненно, революционный, синергия, уникальная возможность.
НЕ используй кликбейт и пустые обещания. Фокус на конкретных результатах.

Ответ СТРОГО в JSON:
{
  "hero_title": "Главный заголовок (макс 10 слов)",
  "hero_subtitle": "Подзаголовок — конкретный результат для студента",
  "problem_section": {
    "title": "Знакомая ситуация?",
    "problems": ["Проблема 1 ЦА", "Проблема 2", "Проблема 3"]
  },
  "solution_section": {
    "title": "Что ты получишь",
    "benefits": [
      {"title": "Бенефит 1", "description": "Описание"},
      {"title": "Бенефит 2", "description": "Описание"},
      {"title": "Бенефит 3", "description": "Описание"}
    ]
  },
  "program_intro": "Краткое описание программы (2-3 предложения)",
  "author_section": {
    "name": "Автор курса",
    "bio": "Короткая био (2-3 предложения)",
    "credentials": ["Достижение 1", "Достижение 2"]
  },
  "testimonials": [
    {"name": "Имя", "text": "Отзыв (2-3 предложения)", "result": "Конкретный результат"}
  ],
  "faq": [
    {"question": "Вопрос 1", "answer": "Ответ 1"},
    {"question": "Вопрос 2", "answer": "Ответ 2"},
    {"question": "Вопрос 3", "answer": "Ответ 3"}
  ],
  "cta_text": "Текст кнопки",
  "guarantee_text": "Гарантия возврата / пробный период"
}"""


PROMO_PROMPT = """Ты — SMM-копирайтер. Пиши короткие промо-посты для Telegram/соцсетей.

Стиль: живой, разговорный, с hook в первой строке. Макс 500 символов.
НЕ используй: безусловно, революционный, синергия. Пиши как реальный человек.

Ответ в JSON:
{
  "posts": [
    {
      "type": "hook",
      "text": "Текст поста",
      "cta": "Призыв к действию"
    }
  ]
}"""


async def generate_landing_copy(
    course_title: str,
    course_subtitle: str,
    target_audience: str,
    modules: list[dict],
    price_rub: int,
    learning_outcomes: list[str] | None = None,
) -> dict:
    """Сгенерировать продающий текст для лендинга.

    Returns:
        JSON с секциями лендинга
    """
    modules_text = "\n".join(
        f"  {m.get('module_num', '?')}. {m.get('title', '?')} ({len(m.get('lessons', []))} уроков)"
        for m in modules
    )

    prompt = (
        f"{LANDING_PROMPT}\n\n"
        f"Курс: {course_title}\n"
        f"Подзаголовок: {course_subtitle}\n"
        f"ЦА: {target_audience}\n"
        f"Цена: {price_rub}₽\n"
        f"Программа:\n{modules_text}\n"
    )
    if learning_outcomes:
        prompt += f"Результаты обучения: {', '.join(learning_outcomes)}\n"

    prompt += "\nСоздай продающий текст для всех секций лендинга."

    text = claude_call(prompt=prompt, agent="producer", timeout=120)

    if text is None:
        logger.warning("claude_call вернул None при генерации landing copy")
        return {}

    json_match = re.search(r'\{[\s\S]*\}', text)
    if json_match:
        try:
            result = json.loads(json_match.group())
            # Проверка AI-слов
            flat_text = json.dumps(result, ensure_ascii=False).lower()
            found = [w for w in ANTI_AI_WORDS if w in flat_text]
            if found:
                logger.warning(f"AI-слова в landing copy: {found}")
            return result
        except json.JSONDecodeError:
            pass

    logger.warning("Не удалось распарсить landing copy")
    return {}


async def generate_promo_posts(
    course_title: str,
    target_audience: str,
    price_rub: int,
    landing_url: str = "",
    count: int = 3,
) -> list[dict]:
    """Сгенерировать промо-посты для соцсетей.

    Returns:
        Список постов
    """
    prompt = (
        f"{PROMO_PROMPT}\n\n"
        f"Создай {count} промо-постов для Telegram о курсе:\n"
        f"Название: {course_title}\n"
        f"ЦА: {target_audience}\n"
        f"Цена: {price_rub}₽\n"
    )
    if landing_url:
        prompt += f"Ссылка: {landing_url}\n"

    prompt += "\nКаждый пост — разный hook (вопрос, факт, история, провокация)."

    text = claude_call(prompt=prompt, agent="producer", timeout=120)

    if text is None:
        logger.warning("claude_call вернул None при генерации promo posts")
        return []

    json_match = re.search(r'\{[\s\S]*\}', text)
    if json_match:
        try:
            data = json.loads(json_match.group())
            return data.get("posts", [])
        except json.JSONDecodeError:
            pass

    return []
