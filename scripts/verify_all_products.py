#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт тестирования RAG: проверяет что ВСЕ продукты NL находятся в базе знаний.

Использование:
    python scripts/verify_all_products.py

Выводит:
    - Список найденных продуктов [OK]
    - Список НЕ найденных продуктов [FAIL]
    - Процент покрытия
"""

import asyncio
import sys
import os
from pathlib import Path
from typing import List, Tuple

# Фикс для Windows консоли
if sys.platform == 'win32':
    os.system('chcp 65001 >nul 2>&1')
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Добавляем корень проекта в PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.rag import get_rag_engine


# Список тестовых запросов для проверки
# Формат: (запрос, ожидаемые ключевые слова в ответе)
TEST_QUERIES = [
    # === КОСМЕТИКА ===
    ("мужская косметика NL", ["the lab", "мужск", "бритье", "бальзам"]),
    ("The LAB мужская линейка", ["the lab", "мужск"]),
    ("гель для бритья NL", ["бритье", "the lab"]),
    ("косметика Be Loved", ["be loved", "beloved", "косметик"]),
    ("шампунь для волос NL", ["шампунь", "волос"]),

    # === ПИТАНИЕ ===
    ("Energy Diet Smart", ["energy diet", "ed smart", "коктейль"]),
    ("ED Smart для похудения", ["energy", "похуд", "smart"]),
    ("протеиновый коктейль NL", ["протеин", "коктейль", "energy"]),
    ("как готовить Energy Diet", ["energy", "приготов", "рецепт"]),

    # === КОЛЛАГЕН ===
    ("коллаген NL International", ["коллаген", "collagen", "кожа"]),
    ("коллаген для кожи", ["коллаген", "кожа"]),
    ("морщины убрать", ["морщин", "коллаген", "кожа"]),

    # === ДРАЙН ЭФФЕКТ ===
    ("DrainEffect NL", ["drain", "драйн", "отек"]),
    ("драйн эффект от отеков", ["drain", "драйн", "отек"]),

    # === БАДы ===
    ("витамины Greenflash", ["greenflash", "витамин"]),
    ("адаптогены NL", ["адаптоген", "greenflash"]),
    ("Omega 3 NL", ["omega", "омега"]),

    # === ДЕТСКАЯ ЛИНЕЙКА ===
    ("детские витамины NL", ["детск", "nlka", "витамин"]),
    ("NLKA детская линейка", ["nlka", "детск"]),

    # === БИЗНЕС ===
    ("как стать партнером NL", ["партнер", "регистрац"]),
    ("маркетинг план NL", ["маркетинг", "план", "вознагражден"]),
    ("квалификации NL", ["квалификац", "директор", "менеджер"]),

    # === СТАРТОВЫЕ НАБОРЫ ===
    ("стартовый набор NL", ["стартов", "набор"]),
    ("с чего начать в NL", ["начать", "старт", "первый"]),
]


async def test_single_query(rag_engine, query: str, expected_keywords: List[str]) -> Tuple[bool, str]:
    """
    Тестирует один запрос к RAG.

    Returns:
        (success, details): успех и детали
    """
    try:
        results = await rag_engine.retrieve(
            query=query,
            top_k=3,
            min_similarity=0.45
        )

        if not results:
            return False, "Нет результатов"

        # Проверяем что хотя бы одно ключевое слово найдено в результатах
        combined_text = " ".join([r.content.lower() for r in results])
        found_keywords = [kw for kw in expected_keywords if kw.lower() in combined_text]

        if found_keywords:
            sources = ", ".join(set([r.source for r in results[:2]]))
            return True, f"Найдено в: {sources}"
        else:
            return False, f"Ожидались: {expected_keywords}, не найдено"

    except Exception as e:
        return False, f"Ошибка: {str(e)}"


async def main():
    print("=" * 70)
    print("ТЕСТИРОВАНИЕ RAG: ПРОВЕРКА ВСЕХ ПРОДУКТОВ NL")
    print("=" * 70)
    print()

    # Инициализация RAG
    print("Инициализация RAG...")
    rag_engine = await get_rag_engine()

    # Результаты
    passed = []
    failed = []

    print(f"\nЗапускаю {len(TEST_QUERIES)} тестов...\n")
    print("-" * 70)

    for query, expected in TEST_QUERIES:
        success, details = await test_single_query(rag_engine, query, expected)

        if success:
            passed.append((query, details))
            print(f"[OK]   {query[:50]:<50} | {details[:30]}")
        else:
            failed.append((query, details))
            print(f"[FAIL] {query[:50]:<50} | {details[:30]}")

    print("-" * 70)
    print()

    # Итоги
    total = len(TEST_QUERIES)
    passed_count = len(passed)
    failed_count = len(failed)
    percent = (passed_count / total) * 100 if total > 0 else 0

    print("=" * 70)
    print("ИТОГИ")
    print("=" * 70)
    print(f"[OK]   Пройдено: {passed_count}/{total} ({percent:.1f}%)")
    print(f"[FAIL] Провалено: {failed_count}/{total}")
    print()

    if failed:
        print("ПРОВАЛЕННЫЕ ТЕСТЫ:")
        print("-" * 70)
        for query, details in failed:
            print(f"  - {query}")
            print(f"    Причина: {details}")
        print()

    # Код возврата
    if failed_count > 0:
        print(f"[!] {failed_count} тестов провалено! Нужно исправить.")
        return 1
    else:
        print("[*] Все тесты пройдены! RAG работает корректно.")
        return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
