"""AI-анализ конкурентных курсов через shared AI client."""

import json
import logging
import re

from shared.ai_client_cli import claude_call

logger = logging.getLogger("producer.ai.competitor")

SYSTEM_PROMPT = """Ты — аналитик рынка онлайн-образования. Проанализируй конкурентов в нише.

Ответ СТРОГО в JSON формате:
{
  "niche": "название ниши",
  "competitors": [
    {
      "name": "Название курса",
      "platform": "платформа",
      "price_rub": 1000
    }
  ],
  "market_gaps": ["пробел 1"],
  "recommended_price_rub": 1000
}

Будь кратким. 2-3 конкурента максимум."""


async def analyze_competitors(niche_name: str, niche_slug: str, scraped_content: str = "") -> dict:
    """Проанализировать конкурентов в нише через AI.

    Args:
        niche_name: Название ниши на русском
        niche_slug: Slug ниши
        scraped_content: Скрапленные данные о конкурентах (если есть, изолируются как untrusted)

    Returns:
        Анализ конкурентов с рекомендациями
    """
    prompt = (
        f"{SYSTEM_PROMPT}\n\n"
        f"Проанализируй рынок онлайн-курсов в нише: \"{niche_name}\"\n"
        f"Найди 2-3 основных конкурента. Укажи название, платформу и цену.\n"
        f"Определи 1-2 пробела на рынке.\n"
        f"Предложи оптимальную цену для нашего курса."
    )

    try:
        logger.info(f"Начинаю анализ конкурентов для ниши: {niche_name}")

        if scraped_content:
            text = claude_call(
                prompt=prompt,
                agent="producer",
                untrusted_data=scraped_content,
                untrusted_source="competitor_website",
                timeout=120,
            )
        else:
            text = claude_call(prompt=prompt, agent="producer", timeout=120)

        if text is None:
            logger.error(f"claude_call вернул None при анализе конкурентов для ниши: {niche_name}")
            return {"niche": niche_name, "competitors": [], "market_gaps": [], "error": "AI не ответил"}

        logger.info(f"Ответ получен, длина: {len(text)} символов")
        result = _parse_json(text)
        logger.info(f"Анализ конкурентов: {len(result.get('competitors', []))} найдено")
        return result

    except Exception as e:
        logger.error(f"Ошибка анализа конкурентов: {type(e).__name__}: {e}")
        return {"niche": niche_name, "competitors": [], "market_gaps": [], "error": str(e)}


def _parse_json(text: str) -> dict:
    """Извлечь JSON из ответа AI."""
    logger.debug(f"Парсинг JSON из текста длиной {len(text)} символов")

    json_match = re.search(r'\{[\s\S]*\}', text)
    if json_match:
        json_str = json_match.group()
        logger.debug(f"Найден JSON, длина: {len(json_str)} символов")
        try:
            result = json.loads(json_str)
            logger.debug(f"JSON успешно распарсен, ключи: {list(result.keys())}")
            return result
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка парсинга JSON: {e}")
            logger.debug(f"Проблемный JSON: {json_str[:500]}...")
    else:
        logger.warning(f"JSON не найден в ответе. Текст: {text[:300]}...")

    return {}
