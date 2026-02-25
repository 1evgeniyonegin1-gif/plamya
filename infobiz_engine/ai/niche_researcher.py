"""AI-анализ и скоринг ниш для инфопродуктов через shared AI client."""

import json
import logging
import re

from shared.ai_client_cli import claude_call

logger = logging.getLogger("producer.ai.niche")

SYSTEM_PROMPT = """Ты — аналитик рынка инфопродуктов. Твоя задача — оценивать ниши для создания онлайн-курсов.

Для каждой ниши оцени по шкале 0-100:
- demand (0-25): спрос — ищут ли люди обучение по этой теме?
- monetizability (0-25): готовы ли платить? существуют ли платные курсы?
- ai_generability (0-25): можно ли AI сгенерировать качественный контент? (программирование — да, хирургия — нет)
- low_competition (0-15): мало ли качественных бесплатных альтернатив?
- evergreen (0-10): будет ли контент актуален через год?

Общий score = сумма всех метрик (0-100).

Ответ СТРОГО в JSON формате:
{
  "niches": [
    {
      "name": "Название ниши на русском",
      "slug": "niche-slug-english",
      "demand": 20,
      "monetizability": 18,
      "ai_generability": 22,
      "low_competition": 10,
      "evergreen": 8,
      "score": 78,
      "target_audience": "Кто будет покупать",
      "price_range_rub": "2990-9990",
      "demand_signals": ["сигнал 1", "сигнал 2"],
      "risks": ["риск 1"]
    }
  ]
}"""


async def research_niches(query: str = "", count: int = 5) -> list[dict]:
    """Исследовать ниши через AI.

    Args:
        query: Конкретная тема для исследования (или пустая строка для общего поиска)
        count: Сколько ниш предложить

    Returns:
        Список ниш с метриками и скорами
    """
    if query:
        user_prompt = (
            f"Проанализируй нишу для инфопродукта: \"{query}\"\n"
            f"Предложи {count} вариаций/поднищ в этой области.\n"
            f"Для каждой дай скоринг по 5 критериям."
        )
    else:
        user_prompt = (
            f"Предложи {count} самых перспективных ниш для создания онлайн-курсов в 2026 году.\n"
            f"Фокус на нишах, где AI может генерировать качественный образовательный контент.\n"
            f"Для каждой дай скоринг по 5 критериям."
        )

    prompt = f"{SYSTEM_PROMPT}\n\n{user_prompt}"

    try:
        text = claude_call(prompt=prompt, agent="producer", timeout=120)

        if text is None:
            logger.error("claude_call вернул None при исследовании ниш")
            raise RuntimeError("AI не ответил")

        # Извлечь JSON из ответа
        niches = _parse_niches_json(text)
        logger.info(f"Найдено {len(niches)} ниш")
        return niches

    except Exception as e:
        logger.error(f"Ошибка исследования ниш: {e}")
        raise


async def score_niche_detailed(niche_name: str, competitor_data: str = "") -> dict:
    """Детальный скоринг конкретной ниши.

    Args:
        niche_name: Название ниши
        competitor_data: Данные о конкурентах (если есть, передаются как untrusted_data)

    Returns:
        Детальный скоринг с рекомендациями
    """
    user_prompt = (
        f"Детально проанализируй нишу для инфопродукта: \"{niche_name}\"\n\n"
        f"Дай скоринг по 5 критериям + рекомендации:\n"
        f"1. Конкретная целевая аудитория и их боли\n"
        f"2. Оптимальная цена и формат (текст, видео, практикум)\n"
        f"3. Что должно быть в курсе (5-8 ключевых модулей)\n"
        f"4. Как привлечь первых клиентов\n"
        f"\nОтвет в JSON формате (как в системном промпте, плюс поля 'recommended_modules' и 'marketing_channels')."
    )

    prompt = f"{SYSTEM_PROMPT}\n\n{user_prompt}"

    try:
        if competitor_data:
            text = claude_call(
                prompt=prompt,
                agent="producer",
                untrusted_data=competitor_data,
                untrusted_source="competitor_website",
                timeout=120,
            )
        else:
            text = claude_call(prompt=prompt, agent="producer", timeout=120)

        if text is None:
            logger.error("claude_call вернул None при детальном скоринге ниши")
            raise RuntimeError("AI не ответил")

        result = _parse_niches_json(text)
        return result[0] if result else {}

    except Exception as e:
        logger.error(f"Ошибка детального скоринга: {e}")
        raise


def _parse_niches_json(text: str) -> list[dict]:
    """Извлечь JSON со списком ниш из текста ответа AI."""
    # Попробовать найти JSON блок
    json_match = re.search(r'\{[\s\S]*"niches"[\s\S]*\}', text)
    if json_match:
        try:
            data = json.loads(json_match.group())
            return data.get("niches", [])
        except json.JSONDecodeError:
            pass

    # Попробовать найти JSON array
    array_match = re.search(r'\[[\s\S]*\]', text)
    if array_match:
        try:
            return json.loads(array_match.group())
        except json.JSONDecodeError:
            pass

    logger.warning(f"Не удалось распарсить JSON из ответа AI: {text[:200]}...")
    return []
