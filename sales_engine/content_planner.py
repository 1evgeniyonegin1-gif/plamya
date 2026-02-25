"""
Планировщик контента для NL International.
Генерирует посты от лица Данила для разных сегментов аудитории.
"""

import random
import httpx
from datetime import datetime
from .config import (
    DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL,
    SEGMENTS, SEGMENT_NAMES, TOP_PRODUCTS, CONTENT_TYPES, ANTI_AI_WORDS,
)
from .knowledge import get_compact_product_list, get_product_context


# ── Промпты ───────────────────────────────────────

SYSTEM_PROMPT = """Ты — Данил, 21 год. Пишешь посты для Telegram-канала.

КТО ТЫ:
- После армии, живёшь с отцом (у него цех ЧПУ)
- Строишь AI-систему для NL International (APEXFLOW)
- Не типичный сетевик — ты архитектор, AI — исполнитель
- Пьёшь чай (пуэр, улун), ненавидишь кофе
- Играешь Apex Legends, читаешь мангу
- Бегаешь у речки, думаешь о жизни
- Любимый продукт: ED Smart вишнёвый брауни с "Не молоко"

СТИЛЬ:
- 200-600 символов
- Короткие предложения + длинные (ритм)
- Мат органичный (кроме сегмента "мамы")
- Начинай без приветствия, с середины мысли
- Заканчивай резко или вопросом
- Не используй эмодзи-спам (максимум 1-2)

ЗАПРЕЩЕНО:
- AI-слова: "безусловно", "стоит отметить", "трансформация", "путешествие", "уникальный", "инновационный"
- Фейковые сцены: метро, кафе, пробки, офис
- Медицинские заявления ("лечит", "вылечит")
- Гарантии дохода ("ты точно заработаешь")
- Фейковые цифры и статистики

ПРИВАТНОЕ (НЕ УПОМИНАЙ):
- Девушка/невеста
- Мама, сёстры, семья
- Конкретные долги/доходы
- Травмы, болезни
"""

SEGMENT_OVERLAYS = {
    "zozh": """
АУДИТОРИЯ: люди интересующиеся ЗОЖ, питанием, тренировками.
ТОН: экспертный но простой. Цифры, факты, КБЖУ.
Мат можно, но умеренно.
Фокус: питание как инструмент для тела.""",

    "mama": """
АУДИТОРИЯ: мамы 25-40 лет, здоровье семьи, доход из дома.
ТОН: тёплый, понимающий. БЕЗ МАТА (максимум "блин").
Не снисходительный — на равных.
Фокус: забота о себе и детях, подработка без отрыва от семьи.""",

    "business": """
АУДИТОРИЯ: люди ищущие дополнительный доход, предприниматели.
ТОН: деловой-неформальный. Цифры, факты, план.
Мат минимально.
Фокус: пошаговый путь к доходу, автоматизация.""",

    "student": """
АУДИТОРИЯ: студенты 18-25, молодёжь.
ТОН: свой в доску. Мат ОК. Юмор, мемы, ирония.
Фокус: бюджетно, быстро, без корпоративного BS.
Порция 186₽ — дешевле доширака.""",
}


async def generate_post(
    segment: str,
    content_type: str | None = None,
    product_focus: str | None = None,
) -> dict:
    """
    Генерирует пост для конкретного сегмента.

    Returns:
        {"segment": str, "type": str, "text": str, "product": str|None}
    """
    if content_type is None:
        content_type = random.choice(CONTENT_TYPES)

    # Выбираем продукт если не указан
    if product_focus is None and content_type in ("product_review", "personal_result", "comparison"):
        segment_products = TOP_PRODUCTS.get(segment, TOP_PRODUCTS["zozh"])
        product = random.choice(segment_products)
        product_focus = product["name"]

    # Собираем контекст
    product_context = ""
    if product_focus:
        product_context = get_product_context(product_focus)
        if len(product_context) > 2000:
            product_context = product_context[:2000] + "..."

    # Формируем промпт
    segment_overlay = SEGMENT_OVERLAYS.get(segment, "")
    products_list = get_compact_product_list()

    user_prompt = f"""Напиши пост для Telegram-канала.

СЕГМЕНТ: {SEGMENT_NAMES.get(segment, segment)}
{segment_overlay}

ТИП ПОСТА: {content_type}
{'ПРОДУКТ: ' + product_focus if product_focus else ''}

{('ДАННЫЕ О ПРОДУКТЕ:\n' + product_context) if product_context else ''}

ПРОДУКТЫ NL:
{products_list}

ВАЖНО:
- Пиши от первого лица (я = Данил)
- 200-600 символов
- Без хештегов
- Без "подписывайтесь" и призывов подписаться
- Если продуктовый пост — вплети продукт в историю, НЕ делай описание-каталог
- Пост должен быть живым и настоящим
"""

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{DEEPSEEK_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "deepseek-chat",
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": 0.9,
                    "max_tokens": 1000,
                },
            )
            response.raise_for_status()
            data = response.json()
            text = data["choices"][0]["message"]["content"].strip()

            # Валидация: проверяем на AI-слова
            text_lower = text.lower()
            for word in ANTI_AI_WORDS:
                if word in text_lower:
                    text = text  # TODO: regenerate or edit

            return {
                "segment": segment,
                "type": content_type,
                "text": text,
                "product": product_focus,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
            }

    except Exception as e:
        return {
            "segment": segment,
            "type": content_type,
            "text": f"[ОШИБКА ГЕНЕРАЦИИ: {e}]",
            "product": product_focus,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }


async def generate_content_plan() -> list[dict]:
    """Генерирует план контента: 1 пост для каждого сегмента."""
    posts = []
    for segment in SEGMENTS:
        content_type = random.choice(CONTENT_TYPES)
        post = await generate_post(segment=segment, content_type=content_type)
        posts.append(post)
    return posts
