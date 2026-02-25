#!/usr/bin/env python3
"""
Скрипт для тестирования куратора на галлюцинации.
Загружает тестовые вопросы и проверяет ответы AI.

Запуск:
    python scripts/run_hallucination_tests.py [--limit N] [--category CATEGORY]

Примеры:
    python scripts/run_hallucination_tests.py --limit 10
    python scripts/run_hallucination_tests.py --category fake_product_lines
    python scripts/run_hallucination_tests.py --dry-run
"""

import json
import asyncio
import argparse
import sys
import os
from pathlib import Path
from datetime import datetime

# Добавляем корневую директорию проекта в путь
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Загружаем переменные окружения из .env
from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")


# Список реальных продуктов NL для валидации
REAL_PRODUCTS = {
    # The LAB (мужская косметика) - ЕДИНСТВЕННАЯ мужская линейка!
    "thelab": ["бальзам", "гель для бритья", "гель для умывания", "дезодорант", "гель для душа 2в1"],

    # Energy Diet
    "ed_smart": ["шоколад", "капучино", "ваниль", "клубника", "банан", "фисташка"],
    "ed_balance": True,
    "ed_start": True,

    # Greenflash БАДы
    "collagen_peptides": True,
    "omega_3": True,
    "vitamin_d3": True,
    "vitamin_c_liposomal": True,
    "metabrain": True,
    "detox_step_123": True,
    "marine_magnesium": True,
    "soft_sorb": True,
    "vision_plus": True,
    "food_control": True,
    "gelm_cleanse": True,
    "gut_vigyan": True,
    "lactoferra": True,
    "lymph_gyan": True,
    "no_yoyo_effect": True,

    # 3D Slim
    "metaboost": True,
    "draineffect_green": True,
    "draineffect_red": True,
    "white_tea_slimdose": True,
    "hot_gel": True,
    "cold_gel": True,
    "shaping_scrub": True,
    "lifting_serum": True,

    # NLka (дети)
    "happy_smile": True,
    "omega_3_dha": True,
    "mg_b6_kids": True,
    "liquid_ca": True,
    "vision_lecithin": True,

    # Biotuning
    "metabiotic": True,
    "biodrone": True,
    "biotuning": True,

    # Occuba косметика
    "occuba": True,

    # Be Loved парфюмерия
    "gentleman_perfume": True,  # Это ПАРФЮМ, не косметика!
    "donna_bella": True,
    "every_black": True,
    "every_deep_black": True,
    "every_green": True,
    "every_mix": True,
    "every_red": True,
    "liverpool": True,
    "prana": True,
    "valery": True,
    "vodoley": True,
    "white_tea_beloved": True,

    # Enerwood чаи
    "green_tea": True,
    "herbal_tea": True,
    "imperial_herb": True,

    # Fineffect
    "fineffect_active_plus": True,
    "fineffect_protect": True,
    "fineffect_sensitive": True,
    "fineffect_textile": True,

    # Sport
    "energy_pro": True,

    # Другое
    "calcium_marine": True,
    "prohelper": True,
    "antiage": True,
    "starter_kit": True,
}

# Фейковые продукты и линейки которых НЕТ
FAKE_PRODUCTS = [
    # Несуществующие мужские линейки
    "gentlemen series", "gentlemen shaving", "gentlemen face care", "gentlemen body care",
    "men's line", "for men", "мужская серия", "homme", "man care",

    # Фейковые продукты Gentleman (это ПАРФЮМ!)
    "gentleman крем", "gentleman гель", "gentleman шампунь", "gentleman дезодорант",
    "джентльмен крем", "джентльмен бритье", "джентльмен уход",

    # Фейковые версии продуктов
    "ed smart pro", "ed smart plus", "ed smart ultra", "ed smart max",
    "collagen ultra", "collagen premium", "collagen marine", "collagen beauty",
    "draineffect plus", "draineffect blue", "draineffect yellow",
    "metaboost turbo", "metaboost extreme",
    "omega-3 premium", "vitamin d forte",
    "happy smile plus", "happy smile teen",

    # Фейковые линейки
    "pro line", "expert", "premium", "professional", "clinic",
    "beauty line", "skin care series", "hair pro",
    "wellness", "immunity boost",
]

# Реальные цены (для проверки)
REAL_PRICES = {
    "ed_smart": 2790,
    "collagen_peptides": 1890,
    "omega_3": 1590,
    "vitamin_d3": 990,
    "vitamin_c_liposomal": 650,
    "metabrain": 1290,
    "detox_kit": 2800,
    "marine_magnesium": 990,
    "soft_sorb": 1390,
    "metaboost": 1690,
    "draineffect": 1490,
    "white_tea_slimdose": 1890,
    "hot_gel": 990,
    "cold_gel": 990,
    "shaping_scrub": 1090,
    "lifting_serum": 750,
    "happy_smile": 790,
    "omega_3_dha_kids": 2290,
    "mg_b6_kids": 990,
    "thelab_balsam": 750,
    "thelab_shave_gel": 650,
    "thelab_face_gel": 650,
    "collagentrinity": 2190,
    "starter_kit": 6700,
}


def load_tests():
    """Загружает все тестовые файлы"""
    tests_dir = Path(__file__).parent.parent / "tests"
    all_tests = []

    for json_file in tests_dir.glob("hallucination_tests*.json"):
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            if "tests" in data:
                all_tests.extend(data["tests"])

    return all_tests


def check_for_hallucination(response: str, test_data: dict = None) -> dict:
    """
    Проверяет ответ AI на наличие галлюцинаций.

    Returns:
        dict: {
            "has_hallucination": bool,
            "issues": list[str],
            "fake_products_found": list[str],
            "fake_lines_found": list[str],
            "correct_refusal": bool  # AI правильно отказался отвечать о фейковом продукте
        }
    """
    response_lower = response.lower()
    issues = []
    fake_products_found = []
    fake_lines_found = []
    correct_refusal = False

    # Паттерны правильного отказа/коррекции
    refusal_patterns = [
        "не существует", "нет такой линейки", "нет такого продукта",
        "такой линейки нет", "такого продукта нет", "не выпускает",
        "не производит", "в ассортименте нет", "не знаком",
        "не слышал", "не могу найти информацию", "нет информации",
        "путаница", "возможно вы имели в виду", "может быть вы путаете",
        "единственная мужская линейка", "the lab", "thelab",
        # Новые паттерны для правильных ответов
        "нет линейки", "нет серии", "не существует серии",
        "**нет**", "**нет линейки", "**нет серии", "нет такой серии",
        "в nl нет", "в nl international нет", "у нас нет"
    ]

    # Проверяем что AI правильно отвечает (отрицает существование фейковых линеек)
    if any(pattern in response_lower for pattern in refusal_patterns):
        correct_refusal = True

    # Проверка для тестов где ожидается отказ/уточнение
    expected = test_data.get("expected_response", "") if test_data else ""
    if expected in ["reject", "clarify", "redirect_thelab", "correct"]:
        if correct_refusal:
            # Если AI правильно сказал "нет такой линейки" или уточнил — это успех!
            return {
                "has_hallucination": False,
                "issues": [],
                "fake_products_found": [],
                "fake_lines_found": [],
                "correct_refusal": True,
            }

    # Проверка на фейковые продукты/линейки
    for fake in FAKE_PRODUCTS:
        if fake.lower() in response_lower:
            # Проверяем что это не в контексте отказа
            if not correct_refusal:
                if "серия" in fake or "line" in fake or "series" in fake:
                    fake_lines_found.append(fake)
                else:
                    fake_products_found.append(fake)

    # Специальная проверка на GENTLEMEN (частая галлюцинация)
    gentlemen_patterns = [
        "gentlemen shaving", "gentlemen face", "gentlemen body",
        "gentlemen series", "gentlemen line", "gentlemen care",
        "пенка для бритья gentleman", "бальзам gentleman",
        "стик gentleman", "скраб gentleman", "крем gentleman",
    ]
    for pattern in gentlemen_patterns:
        if pattern.lower() in response_lower and not correct_refusal:
            fake_lines_found.append(f"GENTLEMEN галлюцинация: {pattern}")

    # Проверка что Gentleman не путают с косметикой
    if "gentleman" in response_lower and not correct_refusal:
        cosmetics_words = ["крем", "гель", "шампунь", "бальзам", "скраб", "маска", "пенка", "лосьон"]
        for word in cosmetics_words:
            # Исключаем случаи когда AI говорит что это парфюм
            if word in response_lower and "парфюм" not in response_lower and "духи" not in response_lower:
                # Дополнительная проверка - не в контексте отрицания
                if "не" not in response_lower[:response_lower.index(word)] if word in response_lower else True:
                    issues.append(f"Gentleman описан как косметика ({word}), но это ПАРФЮМ!")

    # Формируем результат
    has_hallucination = bool(fake_products_found or fake_lines_found or issues)

    if fake_products_found:
        issues.append(f"Найдены фейковые продукты: {fake_products_found}")
    if fake_lines_found:
        issues.append(f"Найдены фейковые линейки: {fake_lines_found}")

    return {
        "has_hallucination": has_hallucination,
        "issues": issues,
        "fake_products_found": fake_products_found,
        "fake_lines_found": fake_lines_found,
        "correct_refusal": correct_refusal,
    }


def generate_report(results: list) -> str:
    """Генерирует отчет о тестировании"""
    total = len(results)

    # Подсчет статистики
    passed = 0
    failed = 0
    correct_refusals = 0

    for r in results:
        hall = r["hallucination"]
        if hall["correct_refusal"]:
            correct_refusals += 1
            passed += 1
        elif not hall["has_hallucination"]:
            passed += 1
        else:
            failed += 1

    report = []
    report.append("=" * 60)
    report.append("ОТЧЕТ О ТЕСТИРОВАНИИ НА ГАЛЛЮЦИНАЦИИ")
    report.append(f"Дата: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    report.append("=" * 60)
    report.append(f"\nВсего тестов: {total}")
    report.append(f"Пройдено: {passed} ({passed/total*100:.1f}%)")
    report.append(f"  - Правильных отказов: {correct_refusals}")
    report.append(f"Провалено: {failed} ({failed/total*100:.1f}%)")

    if failed > 0:
        report.append("\n" + "-" * 60)
        report.append("ПРОВАЛИВШИЕСЯ ТЕСТЫ:")
        report.append("-" * 60)

        for r in results:
            if r["hallucination"]["has_hallucination"] and not r["hallucination"]["correct_refusal"]:
                report.append(f"\n[ID {r['test_id']}] {r['question']}")
                report.append(f"  Ответ AI: {r['response'][:200]}...")
                for issue in r["hallucination"]["issues"]:
                    report.append(f"  [X] {issue}")

    report.append("\n" + "=" * 60)
    return "\n".join(report)


async def run_single_test(ai_client, system_prompt: str, test: dict, test_num: int, total: int) -> dict:
    """Запускает один тест"""
    question = test["question"]
    test_id = test.get("id", test_num)

    print(f"[{test_num}/{total}] Тестируем: {question[:50]}...")

    try:
        response = await ai_client.generate_response(
            system_prompt=system_prompt,
            user_message=question,
            temperature=0.3,  # Низкая температура для более точных ответов
            max_tokens=800
        )

        hallucination_check = check_for_hallucination(response, test)

        status = "[OK]" if not hallucination_check["has_hallucination"] or hallucination_check["correct_refusal"] else "[FAIL]"
        print(f"  {status} Результат: {'Галлюцинация!' if hallucination_check['has_hallucination'] and not hallucination_check['correct_refusal'] else 'OK'}")

        return {
            "test_id": test_id,
            "question": question,
            "category": test.get("category", "unknown"),
            "response": response,
            "hallucination": hallucination_check
        }

    except Exception as e:
        print(f"  [ERR] Ошибка: {e}")
        return {
            "test_id": test_id,
            "question": question,
            "category": test.get("category", "unknown"),
            "response": f"ERROR: {e}",
            "hallucination": {
                "has_hallucination": False,
                "issues": [f"Ошибка API: {e}"],
                "fake_products_found": [],
                "fake_lines_found": [],
                "correct_refusal": False
            }
        }


async def main():
    parser = argparse.ArgumentParser(description="Тест куратора на галлюцинации")
    parser.add_argument("--limit", type=int, default=20, help="Ограничить количество тестов (default: 20)")
    parser.add_argument("--category", type=str, help="Фильтр по категории")
    parser.add_argument("--dry-run", action="store_true", help="Только загрузить тесты без запуска AI")
    parser.add_argument("--save", action="store_true", help="Сохранить результаты в файл")
    parser.add_argument("--yandex", action="store_true", help="Использовать YandexGPT вместо Claude")
    parser.add_argument("--deepseek", action="store_true", help="Использовать Deepseek вместо Claude")
    args = parser.parse_args()

    # Загружаем тесты
    tests = load_tests()
    print(f"Загружено {len(tests)} тестов")

    # Фильтруем
    if args.category:
        tests = [t for t in tests if t.get("category") == args.category]
        print(f"После фильтра по категории '{args.category}': {len(tests)} тестов")

    if args.limit:
        tests = tests[:args.limit]
        print(f"Ограничено до {len(tests)} тестов")

    if args.dry_run:
        print("\n=== DRY RUN - Список тестов ===")
        for i, test in enumerate(tests[:30], 1):
            print(f"{i}. [{test.get('category', 'unknown')}] {test['question']}")
        if len(tests) > 30:
            print(f"... и ещё {len(tests) - 30} тестов")
        return

    # Импортируем AI клиент
    print("\nИнициализация AI клиента...")
    from curator_bot.ai.prompts import get_curator_system_prompt, get_rag_instruction

    if args.yandex:
        from shared.ai_clients.yandexgpt_client import YandexGPTClient
        ai_client = YandexGPTClient()
        print("Используем YandexGPT")
    elif args.deepseek:
        from shared.ai_clients.deepseek_client import DeepseekClient
        ai_client = DeepseekClient()
        print("Используем Deepseek")
    else:
        from shared.ai_clients.anthropic_client import AnthropicClient
        ai_client = AnthropicClient()
        print("Используем Claude")

    # Получаем системный промпт куратора
    system_prompt = get_curator_system_prompt(
        user_name="Тестовый пользователь",
        qualification="M1",
        lessons_completed=0,
        current_goal=None
    )

    # Добавляем RAG инструкции для продуктов
    rag_instruction = get_rag_instruction()
    system_prompt = system_prompt + "\n\n" + rag_instruction

    print(f"Системный промпт: {len(system_prompt)} символов")
    print("\n" + "=" * 60)
    print("ЗАПУСК ТЕСТОВ НА ГАЛЛЮЦИНАЦИИ")
    print("=" * 60 + "\n")

    # Запускаем тесты
    results = []
    for i, test in enumerate(tests, 1):
        result = await run_single_test(ai_client, system_prompt, test, i, len(tests))
        results.append(result)

        # Небольшая пауза между запросами чтобы не превысить rate limit
        if i < len(tests):
            await asyncio.sleep(1)

    # Генерируем отчет
    report = generate_report(results)
    # Заменяем символы которые не отображаются в cp1251
    report_display = report.replace("₽", "руб").replace("❌", "[X]").replace("✅", "[OK]")
    print("\n" + report_display)

    # Сохраняем результаты если нужно
    if args.save:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = PROJECT_ROOT / "tests" / f"hallucination_results_{timestamp}.json"

        with open(results_file, "w", encoding="utf-8") as f:
            json.dump({
                "timestamp": timestamp,
                "total_tests": len(results),
                "results": results
            }, f, ensure_ascii=False, indent=2)

        print(f"\nРезультаты сохранены в: {results_file}")

        # Также сохраняем текстовый отчет
        report_file = PROJECT_ROOT / "tests" / f"hallucination_report_{timestamp}.txt"
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"Отчет сохранен в: {report_file}")


if __name__ == "__main__":
    asyncio.run(main())
