#!/usr/bin/env python3
"""
Скрипт для создания связей ДО/ПОСЛЕ в testimonials.

Анализирует metadata.json и находит пары фото:
- Соседние сообщения (id и id+1)
- В одной подкатегории
- Оба с фото

Создаёт файл pairs.json с описанием пар.

Использование:
    python scripts/create_testimonial_pairs.py
    python scripts/create_testimonial_pairs.py --dry-run  # только показать что будет создано
"""

import json
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional
from collections import defaultdict

# Путь к testimonials
PROJECT_ROOT = Path(__file__).parent.parent
TESTIMONIALS_DIR = PROJECT_ROOT / "content" / "testimonials"


def load_metadata(category: str) -> List[Dict[str, Any]]:
    """Загружает metadata.json для категории."""
    metadata_path = TESTIMONIALS_DIR / category / "metadata.json"
    if not metadata_path.exists():
        print(f"⚠️ Файл не найден: {metadata_path}")
        return []

    with open(metadata_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        return data.get('messages', [])


def find_pairs_in_category(messages: List[Dict[str, Any]], category: str) -> List[Dict[str, Any]]:
    """
    Находит пары ДО/ПОСЛЕ в списке сообщений.

    Логика:
    1. Группируем по subcategory
    2. Сортируем по id
    3. Находим пары соседних сообщений с фото
    """
    pairs = []

    # Группируем по subcategory
    by_subcategory = defaultdict(list)
    for msg in messages:
        subcat = msg.get('subcategory')
        if subcat and msg.get('has_photo'):
            by_subcategory[subcat].append(msg)

    # В каждой подкатегории ищем пары
    for subcategory, msgs in by_subcategory.items():
        # Сортируем по id
        sorted_msgs = sorted(msgs, key=lambda m: m.get('id', 0))

        # Ищем соседние пары (id и id+1)
        i = 0
        while i < len(sorted_msgs) - 1:
            msg1 = sorted_msgs[i]
            msg2 = sorted_msgs[i + 1]

            # Проверяем что id отличаются на 1-3 (могут быть пропуски)
            id_diff = msg2.get('id', 0) - msg1.get('id', 0)
            if 1 <= id_diff <= 3:
                # Это потенциальная пара!
                pair = {
                    "id": f"{subcategory}_{msg1['id']}_{msg2['id']}",
                    "category": category,
                    "subcategory": subcategory,
                    "before_msg_id": msg1['id'],
                    "after_msg_id": msg2['id'],
                    "before_file": get_first_photo(msg1),
                    "after_file": get_first_photo(msg2),
                    "description": f"{subcategory.replace('_', ' ').title()} — пара #{len(pairs) + 1}"
                }
                pairs.append(pair)
                i += 2  # Пропускаем оба сообщения
            else:
                i += 1

    return pairs


def get_first_photo(msg: Dict[str, Any]) -> Optional[str]:
    """Возвращает путь к первому фото из сообщения."""
    files = msg.get('files', [])
    for f in files:
        if f.get('type') == 'photo':
            return f.get('local_path')
    return None


def main():
    parser = argparse.ArgumentParser(description='Создание пар ДО/ПОСЛЕ для testimonials')
    parser.add_argument('--dry-run', action='store_true', help='Только показать, не сохранять')
    args = parser.parse_args()

    print("=" * 70)
    print("СОЗДАНИЕ ПАР ДО/ПОСЛЕ В TESTIMONIALS")
    print("=" * 70)
    print()

    all_pairs = []

    # Обрабатываем before_after (главная категория)
    print("📂 Обработка before_after...")
    messages = load_metadata("before_after")
    if messages:
        pairs = find_pairs_in_category(messages, "before_after")
        all_pairs.extend(pairs)
        print(f"   Найдено {len(pairs)} пар")

        # Статистика по подкатегориям
        by_subcat = defaultdict(int)
        for p in pairs:
            by_subcat[p['subcategory']] += 1
        for subcat, count in sorted(by_subcat.items(), key=lambda x: -x[1]):
            print(f"   • {subcat}: {count} пар")

    print()

    # Итоги
    print("-" * 70)
    print(f"ИТОГО: {len(all_pairs)} пар создано")
    print()

    # Примеры пар
    if all_pairs:
        print("Примеры пар:")
        for pair in all_pairs[:5]:
            print(f"  • {pair['id']}")
            print(f"    До: {pair['before_file']}")
            print(f"    После: {pair['after_file']}")
        if len(all_pairs) > 5:
            print(f"  ... и ещё {len(all_pairs) - 5} пар")
        print()

    # Сохранение
    if not args.dry_run:
        output_path = TESTIMONIALS_DIR / "before_after" / "pairs.json"

        pairs_data = {
            "description": "Связи между фото ДО и ПОСЛЕ",
            "created_by": "scripts/create_testimonial_pairs.py",
            "total_pairs": len(all_pairs),
            "pairs": all_pairs
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(pairs_data, f, ensure_ascii=False, indent=2)

        print(f"✅ Сохранено в: {output_path}")
    else:
        print("🔍 Dry-run режим — файл не сохранён")


if __name__ == "__main__":
    main()
