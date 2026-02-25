"""
Анализатор потенциальных клиентов/партнёров NL International.
Определяет сегмент, интерес и рекомендует подход.
"""

import httpx
from .config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, SEGMENT_NAMES, TOP_PRODUCTS


def classify_prospect_simple(bio: str, messages: list[str] = None) -> dict:
    """
    Простая классификация без API.

    Returns:
        {"segment": str, "interest": str, "approach": str}
    """
    text = (bio + " " + " ".join(messages or [])).lower()

    # Определяем сегмент
    segment_scores = {"zozh": 0, "mama": 0, "business": 0, "student": 0}

    zozh_kw = ["спорт", "тренировк", "фитнес", "питани", "бжу", "кбжу", "белок", "протеин",
                "похуде", "вес", "здоровь", "зож", "пп", "калори"]
    mama_kw = ["мама", "ребёнок", "ребенок", "дети", "декрет", "малыш", "семья",
               "беременн", "материнств", "грудн"]
    business_kw = ["бизнес", "доход", "заработ", "деньги", "подработ", "инвест",
                   "партнёр", "партнер", "сетев", "mlm", "предпринимат"]
    student_kw = ["студент", "учёба", "учеба", "универ", "вуз", "стипендия", "общага",
                  "пара", "сессия", "диплом"]

    for kw in zozh_kw:
        if kw in text:
            segment_scores["zozh"] += 1
    for kw in mama_kw:
        if kw in text:
            segment_scores["mama"] += 1
    for kw in business_kw:
        if kw in text:
            segment_scores["business"] += 1
    for kw in student_kw:
        if kw in text:
            segment_scores["student"] += 1

    # Лучший сегмент
    segment = max(segment_scores, key=segment_scores.get)
    if segment_scores[segment] == 0:
        segment = "business"  # дефолт

    # Определяем интерес
    interest = "client"  # по умолчанию — клиент
    partner_signals = ["заработ", "доход", "бизнес", "подработ", "партнёр", "партнер",
                       "свободн", "пассивн", "сетев"]
    for signal in partner_signals:
        if signal in text:
            interest = "partner"
            break

    # Рекомендуем подход
    products = TOP_PRODUCTS.get(segment, TOP_PRODUCTS["business"])
    first_product = products[0]["name"] if products else "ED Smart"

    approaches = {
        ("zozh", "client"): f"Предложи попробовать {first_product}. Упомяни КБЖУ и цену за порцию.",
        ("zozh", "partner"): "Расскажи про AI-автоматизацию и как строишь систему. ЗОЖ-ниша растёт.",
        ("mama", "client"): "Расскажи про детские витамины NLKA. Без давления, мягко.",
        ("mama", "partner"): "Доход из дома без отрыва от семьи. Клиентский клуб как первый шаг.",
        ("business", "client"): "Клиентский клуб — скидка без обязательств. Попробуй ED Smart.",
        ("business", "partner"): "Покажи бизнес-план: M1→B1, маркетинг-план, AI-автоматизация.",
        ("student", "client"): f"186₽ за порцию — дешевле столовой. Попробуй {first_product}.",
        ("student", "partner"): "Подработка 30 мин/день. AI делает 80%. Без корпоративного BS.",
    }

    approach = approaches.get((segment, interest), "Начни с Клиентского клуба — без обязательств.")

    return {
        "segment": segment,
        "segment_name": SEGMENT_NAMES.get(segment, segment),
        "interest": interest,
        "approach": approach,
        "recommended_product": first_product,
    }


async def analyze_prospect_ai(bio: str, messages: list[str] = None) -> dict:
    """Глубокий анализ через Deepseek."""
    context = f"Биография: {bio}\n"
    if messages:
        context += "Сообщения:\n" + "\n".join(f"- {m}" for m in messages[:5])

    prompt = f"""Проанализируй потенциального клиента/партнёра NL International.

{context}

Определи:
1. СЕГМЕНТ: zozh (ЗОЖ), mama (мамы), business (бизнес), student (студенты)
2. ИНТЕРЕС: client (покупатель) или partner (хочет зарабатывать)
3. РЕКОМЕНДАЦИЯ: какой продукт предложить первым и как подойти
4. БОЛЬ: что человека волнует/беспокоит
5. ВОЗРАЖЕНИЯ: какие возражения вероятны

Ответь в формате:
СЕГМЕНТ: ...
ИНТЕРЕС: ...
ПРОДУКТ: ...
ПОДХОД: ... (2-3 предложения)
БОЛЬ: ...
ВОЗРАЖЕНИЯ: ...
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
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.7,
                    "max_tokens": 500,
                },
            )
            response.raise_for_status()
            data = response.json()
            analysis = data["choices"][0]["message"]["content"].strip()
            return {"raw_analysis": analysis, "source": "deepseek"}
    except Exception as e:
        # Fallback на простой анализ
        result = classify_prospect_simple(bio, messages)
        result["error"] = str(e)
        return result
