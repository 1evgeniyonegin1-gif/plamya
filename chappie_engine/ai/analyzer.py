"""Анализ контента конкурентов и классификация людей."""

import json
import logging

from chappie_engine.ai.text_generator import generate_text

logger = logging.getLogger("chappie.analyzer")


async def analyze_channel_posts(channel_name: str, posts: list[dict]) -> dict:
    """Проанализировать посты канала.

    Args:
        channel_name: Название канала
        posts: Список постов с полями text, views, reactions_count

    Returns:
        dict с анализом: themes, tone, posting_pattern, ideas
    """
    posts_text = ""
    for i, post in enumerate(posts[:5], 1):
        posts_text += (
            f"\nПост {i} (views: {post.get('views', 0)}, "
            f"reactions: {post.get('reactions_count', 0)}):\n"
            f"{post.get('text', '')[:300]}\n"
        )

    prompt = f"""Проанализируй посты из Telegram канала @{channel_name}.

{posts_text}

Ответь СТРОГО в JSON формате:
{{
  "main_themes": ["тема1", "тема2", "тема3"],
  "tone": "описание тона (1-2 слова)",
  "content_types": ["тип1", "тип2"],
  "best_post_index": 1,
  "best_post_why": "почему этот пост лучший",
  "ideas_to_steal": ["идея1", "идея2"],
  "weaknesses": ["слабость1", "слабость2"]
}}"""

    system = (
        "Ты — аналитик контента в сфере сетевого маркетинга. "
        "Анализируй конкурентов объективно. Отвечай ТОЛЬКО JSON."
    )

    try:
        result = await generate_text(prompt, system_prompt=system, temperature=0.3)
        # Попробуем распарсить JSON
        # Убрать markdown обёртку если есть
        result = result.strip()
        if result.startswith("```"):
            result = result.split("\n", 1)[1]
        if result.endswith("```"):
            result = result.rsplit("```", 1)[0]
        return json.loads(result)
    except (json.JSONDecodeError, Exception) as e:
        logger.warning(f"Не удалось распарсить анализ: {e}")
        return {
            "main_themes": [],
            "tone": "unknown",
            "content_types": [],
            "error": str(e),
            "raw": result if 'result' in dir() else "",
        }


async def classify_prospect(bio: str, messages: list[str] = None) -> dict:
    """Классифицировать потенциального клиента/партнёра.

    Args:
        bio: Биография пользователя
        messages: Последние сообщения (если есть)

    Returns:
        dict с segment, interest_level, suggested_approach
    """
    context = f"Био: {bio}"
    if messages:
        context += f"\nСообщения: {'; '.join(messages[:3])}"

    prompt = f"""Классифицируй этого человека для бизнеса NL International.

{context}

Ответь JSON:
{{
  "segment": "zozh|mama|business|student|unknown",
  "interest_level": "hot|warm|cold",
  "role": "client|partner|unknown",
  "suggested_product": "продукт или null",
  "approach": "как начать разговор (1 предложение)"
}}"""

    system = (
        "Ты — менеджер NL International. Классифицируй людей по сегментам. "
        "Отвечай ТОЛЬКО JSON."
    )

    try:
        result = await generate_text(prompt, system_prompt=system, temperature=0.3)
        result = result.strip()
        if result.startswith("```"):
            result = result.split("\n", 1)[1]
        if result.endswith("```"):
            result = result.rsplit("```", 1)[0]
        return json.loads(result)
    except Exception as e:
        logger.warning(f"Не удалось классифицировать: {e}")
        return {"segment": "unknown", "interest_level": "cold", "role": "unknown"}
