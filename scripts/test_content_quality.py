"""
Скрипт для тестирования качества генерации контента.
Вызывает AI напрямую и проверяет результаты на галлюцинации.

Запуск:
    python scripts/test_content_quality.py
"""
import asyncio
import sys
import os
import re
from pathlib import Path
from datetime import datetime

# Добавляем корень проекта в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

# Пытаемся загрузить dotenv
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
    pass


# Типы постов для тестирования
TEST_POST_TYPES = [
    "product",
    "motivation",
    "tips",
    "myth_busting",
    "success_story",
]

# Паттерны галлюцинаций
HALLUCINATION_PATTERNS = {
    "fake_family": [
        r"мо[йяе]\s+муж",
        r"мо[йяе]\s+жен[аы]",
        r"мо[ийе]\s+дет[иейям]",
        r"мо[йяе]\s+реб[её]нок",
        r"мо[йяе]\s+сын",
        r"мо[йяе]\s+дочь",
        r"женат",
        r"замужем",
    ],
    "wrong_age": [
        r"мне\s+2[2-9]\s+",
        r"мне\s+3\d\s+",
        r"мне\s+4\d\s+",
        r"24\s+года",
        r"25\s+лет",
    ],
    "fake_products": [
        r"omega-?3\s+premium",
        r"collagen\s+ultra",
        r"draineffect\s+plus",
        r"metaboost\s+turbo",
        r"vitamin\s+d\s+forte",
        r"ed\s+smart\s+pro",
    ],
    "marketing_spam": [
        r"✔️",
        r"87%\s+людей",
        r"в\s+3\s+раза",
        r"уникальн\w+\s+продукт",
        r"невероятн\w+\s+результат",
    ],
}

# Упрощённые промпты для тестирования
SYSTEM_PROMPT = """Ты - Данил, 21 год, партнёр NL International.

ЛИЧНЫЕ ФАКТЫ (НИКОГДА НЕ МЕНЯЙ!):
• Тебе 21 год
• НЕ женат, детей нет
• Живёшь один

⚠️ НИКОГДА НЕ ВЫДУМЫВАЙ факты о своей личной жизни!
Если спросят про семью — скажи что не женат, детей нет.

Пишешь посты для Telegram канала о продуктах NL International и бизнес-возможностях.

ПРАВИЛА:
• Короткие абзацы (1-2 предложения)
• Живой разговорный язык
• ОДИН продукт = ОДНА история
• В конце — CTA со ссылкой на @nl_mentor1_bot

ЗАПРЕЩЕНО:
❌ Выдумывать что ты женат или есть дети
❌ Использовать галочки ✔️
❌ Писать фейковые цифры ("87% людей")
"""

POST_PROMPTS = {
    "product": "Напиши пост про коллаген через личную историю. БЕЗ списков с галочками.",
    "motivation": "Напиши мотивационный пост через свою уязвимость и сложный момент.",
    "tips": "Напиши пост-совет через свою ошибку которую ты исправил.",
    "myth_busting": "Напиши пост разрушающий миф 'БАДы — это развод' через свой личный опыт.",
    "success_story": "Напиши историю успеха используя recurring character Машу (новичок) или Валентину Петровну (58 лет).",
}


def check_hallucinations(text: str) -> dict:
    """Проверяет текст на наличие галлюцинаций."""
    results = {
        "has_issues": False,
        "issues": [],
    }

    text_lower = text.lower()

    for category, patterns in HALLUCINATION_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                results["has_issues"] = True
                results["issues"].append({
                    "category": category,
                    "pattern": pattern,
                    "found": re.findall(pattern, text_lower, re.IGNORECASE)
                })

    return results


async def call_deepseek(prompt: str, system: str) -> str:
    """Вызывает Deepseek API напрямую."""
    import httpx

    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise ValueError("DEEPSEEK_API_KEY not found in environment")

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.7,
                "max_tokens": 1000,
            },
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]


async def call_anthropic(prompt: str, system: str) -> str:
    """Вызывает Claude API напрямую."""
    import httpx

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not found in environment")

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            json={
                "model": "claude-3-5-sonnet-20241022",
                "max_tokens": 1000,
                "system": system,
                "messages": [
                    {"role": "user", "content": prompt},
                ],
            },
        )
        response.raise_for_status()
        data = response.json()
        return data["content"][0]["text"]


async def test_content_generator():
    """Тестирует генератор контента."""

    # Фиксим кодировку для Windows
    import sys
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')

    # Определяем какой API использовать
    deepseek_key = os.getenv("DEEPSEEK_API_KEY")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")

    if deepseek_key:
        call_ai = call_deepseek
        model_name = "Deepseek"
    elif anthropic_key:
        call_ai = call_anthropic
        model_name = "Claude"
    else:
        print("[ERROR] Net nastroennykh AI klyuchey!")
        return

    print(f"\n{'='*60}")
    print(f"[TEST] TESTIROVANIE KACHESTVA KONTENTA")
    print(f"AI model: {model_name}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    results = []

    for post_type in TEST_POST_TYPES:
        print(f"\n{'-'*60}")
        print(f"[POST] Generiruyu post tipa: {post_type}")
        print(f"{'-'*60}")

        prompt = POST_PROMPTS.get(post_type, "Напиши пост.")

        try:
            response = await call_ai(prompt, SYSTEM_PROMPT)

            print(f"\n[RESULT]:\n")
            print(response)
            print(f"\n")

            # Проверяем на галлюцинации
            check = check_hallucinations(response)

            if check["has_issues"]:
                print(f"[WARNING] OBNARUZHENY PROBLEMY:")
                for issue in check["issues"]:
                    print(f"   - {issue['category']}: {issue['found']}")
            else:
                print(f"[OK] Proverka proydena")

            results.append({
                "type": post_type,
                "text": response,
                "check": check,
            })

        except Exception as e:
            print(f"[ERROR] Oshibka: {e}")
            results.append({
                "type": post_type,
                "text": None,
                "error": str(e),
            })

    # Итоговый отчёт
    print(f"\n{'='*60}")
    print(f"[REPORT] ITOGOVYY OTCHET")
    print(f"{'='*60}\n")

    total = len(results)
    passed = sum(1 for r in results if r.get("check") and not r["check"]["has_issues"])
    failed = total - passed

    print(f"Vsego testov: {total}")
    print(f"[OK] Proydeno: {passed}")
    print(f"[FAIL] Problemy: {failed}")
    print(f"Procent uspekha: {passed/total*100:.1f}%")

    if failed > 0:
        print(f"\n[WARNING] Posty s problemami:")
        for r in results:
            if r.get("check") and r["check"]["has_issues"]:
                print(f"   - {r['type']}: {[i['category'] for i in r['check']['issues']]}")

    return results


if __name__ == "__main__":
    asyncio.run(test_content_generator())
