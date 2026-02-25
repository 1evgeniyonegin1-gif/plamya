"""Генерация текста через общий AI-клиент (Claude CLI)."""

import asyncio
import logging

from shared.ai_client_cli import claude_call

logger = logging.getLogger("chappie.ai")

# Персона Данила (из style_dna.py)
PERSONA = """Ты пишешь от лица Данила — 21 год, вернулся из армии (октябрь 2025).
Живёт с отцом в Армавире. Построил AI-систему APEXFLOW для NL International.
Пьёт пуэр/улун (ненавидит кофе). Играет в Apex Legends. Читает мангу. Бегает у реки.
Философия: "Страшно падать, страшнее не полететь".

ЗАПРЕЩЕНО выдумывать: метро, кафе, офис, машину, семью, детей. Данил сидит дома за компом.
Утро: DrainEffect → чай → работа. Вечер: Apex или манга.
"""

# Анти-AI слова (не использовать)
ANTI_AI_WORDS = [
    "безусловно", "несомненно", "примечательно", "поразительно",
    "стоит отметить", "в заключение", "давайте разберёмся",
    "уникальная возможность", "революционный", "синергия",
    "трансформация", "парадигма", "инновационный", "кардинально",
    "фундаментально", "беспрецедентный", "не могу не отметить",
    "позвольте", "хотелось бы подчеркнуть", "важно понимать",
]


async def generate_text(
    prompt: str,
    system_prompt: str = "",
    temperature: float = 0.9,
    max_tokens: int = 1000,
) -> str:
    """Сгенерировать текст через AI-клиент (Claude CLI).

    Args:
        prompt: Что сгенерировать
        system_prompt: Системный промпт (по умолчанию — персона Данила)
        temperature: Креативность (0.0-1.0) — игнорируется Claude CLI
        max_tokens: Макс длина ответа — игнорируется Claude CLI
    """
    if not system_prompt:
        system_prompt = PERSONA

    anti_ai_note = (
        "\n\nНИКОГДА не используй слова: " +
        ", ".join(ANTI_AI_WORDS[:10]) +
        ". Пиши как реальный человек, не как AI."
    )

    full_system = system_prompt + anti_ai_note

    # claude_call — синхронный (subprocess), запускаем в thread pool
    result = await asyncio.to_thread(
        claude_call,
        prompt,
        "chappie",
        full_system,
    )

    if result is None:
        raise RuntimeError("AI-клиент недоступен (Claude CLI и fallback не сработали)")

    # Проверка на AI-слова
    text_lower = result.lower()
    found_ai_words = [w for w in ANTI_AI_WORDS if w in text_lower]
    if found_ai_words:
        logger.warning(f"AI-слова в тексте: {found_ai_words}")

    return result.strip()
