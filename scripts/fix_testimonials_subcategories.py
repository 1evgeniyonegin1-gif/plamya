#!/usr/bin/env python3
"""
Скрипт для добавления subcategory в products и checks.

Проблема: 890 продуктов и 428 чеков имеют subcategory=None.
Это не позволяет боту выбирать релевантный контент.

Решение:
1. Для products — определяем subcategory по topic
2. Для checks — определяем по тексту сообщения

Использование:
    python scripts/fix_testimonials_subcategories.py
    python scripts/fix_testimonials_subcategories.py --dry-run  # только показать
"""

import json
import argparse
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from collections import Counter

# Путь к testimonials
PROJECT_ROOT = Path(__file__).parent.parent
TESTIMONIALS_DIR = PROJECT_ROOT / "content" / "testimonials"


# Маппинг topic → subcategory для products
PRODUCTS_TOPIC_MAP = {
    "КАРТОЧКИ ПРОДУКТОВ": "product_cards",
    "ИНСТРУКЦИИ К ПРОДУКТАМ": "product_instructions",
    "РЕЦЕПТЫ ДЛЯ ЧАТА КЛИЕНТОВ": "product_recipes",
    "ПРОГРЕВЫ К МАРАФОНАМ": "marathon_warmup",
}


def detect_check_type(text: str) -> str:
    """
    Определяет тип чека по тексту сообщения.

    Возвращает:
        - first_check: первый чек
        - qualification_check: квалификация
        - leader_check: лидер/директор
        - big_check: большая сумма (>50К)
        - regular_check: обычный чек
    """
    text_lower = text.lower() if text else ""

    # Первый чек
    if any(kw in text_lower for kw in ['первый чек', 'первые деньги', 'первый заработок']):
        return 'first_check'

    # Квалификация
    if any(kw in text_lower for kw in ['квалификац', 'qualification', 'закрыл', 'закрыла']):
        return 'qualification_check'

    # Лидер/директор
    if any(kw in text_lower for kw in ['лидер', 'директор', 'leader', 'director', 'топ']):
        return 'leader_check'

    # Большая сумма (ищем числа > 50000)
    numbers = re.findall(r'(\d[\d\s]*)', text)
    for num_str in numbers:
        try:
            num = int(num_str.replace(' ', ''))
            if num >= 50000:
                return 'big_check'
        except ValueError:
            continue

    return 'regular_check'


def process_products(dry_run: bool = False) -> Dict[str, int]:
    """Обрабатывает products категорию."""
    metadata_path = TESTIMONIALS_DIR / "products" / "metadata.json"

    if not metadata_path.exists():
        print(f"⚠️ Файл не найден: {metadata_path}")
        return {}

    with open(metadata_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    messages = data.get('messages', [])
    stats = Counter()
    updated = 0

    for msg in messages:
        topic = msg.get('topic', '')

        # Определяем subcategory по topic
        subcategory = None
        for topic_pattern, subcat in PRODUCTS_TOPIC_MAP.items():
            if topic_pattern.lower() in topic.lower():
                subcategory = subcat
                break

        if subcategory and msg.get('subcategory') != subcategory:
            msg['subcategory'] = subcategory
            updated += 1
            stats[subcategory] += 1

    # Сохраняем
    if not dry_run and updated > 0:
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    return dict(stats)


def process_checks(dry_run: bool = False) -> Dict[str, int]:
    """Обрабатывает checks категорию."""
    metadata_path = TESTIMONIALS_DIR / "checks" / "metadata.json"

    if not metadata_path.exists():
        print(f"⚠️ Файл не найден: {metadata_path}")
        return {}

    with open(metadata_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    messages = data.get('messages', [])
    stats = Counter()
    updated = 0

    for msg in messages:
        text = msg.get('full_text', msg.get('text', ''))

        # Определяем тип чека
        subcategory = detect_check_type(text)

        if msg.get('subcategory') != subcategory:
            msg['subcategory'] = subcategory
            updated += 1
            stats[subcategory] += 1

    # Сохраняем
    if not dry_run and updated > 0:
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    return dict(stats)


def process_success_stories(dry_run: bool = False) -> Dict[str, int]:
    """Обрабатывает success_stories категорию."""
    metadata_path = TESTIMONIALS_DIR / "success_stories" / "metadata.json"

    if not metadata_path.exists():
        print(f"⚠️ Файл не найден: {metadata_path}")
        return {}

    with open(metadata_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    messages = data.get('messages', [])
    stats = Counter()
    updated = 0

    # Маппинг topic → subcategory
    topic_map = {
        "ПРО АДАПТОГЕНЫ": "adaptogens",
        "ПРО БАДЫ": "supplements",
        "ВОЗРАЖЕНИЯ": "objection_handling",
    }

    for msg in messages:
        topic = msg.get('topic', '')

        subcategory = None
        for topic_pattern, subcat in topic_map.items():
            if topic_pattern.lower() in topic.lower():
                subcategory = subcat
                break

        if subcategory and msg.get('subcategory') != subcategory:
            msg['subcategory'] = subcategory
            updated += 1
            stats[subcategory] += 1

    # Сохраняем
    if not dry_run and updated > 0:
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    return dict(stats)


def main():
    parser = argparse.ArgumentParser(description='Добавление subcategory в testimonials')
    parser.add_argument('--dry-run', action='store_true', help='Только показать, не сохранять')
    args = parser.parse_args()

    print("=" * 70)
    print("ДОБАВЛЕНИЕ SUBCATEGORY В TESTIMONIALS")
    print("=" * 70)
    print()

    if args.dry_run:
        print("🔍 Режим dry-run — файлы не будут изменены")
        print()

    # Products
    print("📂 Обработка products...")
    products_stats = process_products(dry_run=args.dry_run)
    if products_stats:
        for subcat, count in sorted(products_stats.items(), key=lambda x: -x[1]):
            print(f"   • {subcat}: {count}")
    else:
        print("   Нечего обновлять")
    print()

    # Checks
    print("📂 Обработка checks...")
    checks_stats = process_checks(dry_run=args.dry_run)
    if checks_stats:
        for subcat, count in sorted(checks_stats.items(), key=lambda x: -x[1]):
            print(f"   • {subcat}: {count}")
    else:
        print("   Нечего обновлять")
    print()

    # Success stories
    print("📂 Обработка success_stories...")
    stories_stats = process_success_stories(dry_run=args.dry_run)
    if stories_stats:
        for subcat, count in sorted(stories_stats.items(), key=lambda x: -x[1]):
            print(f"   • {subcat}: {count}")
    else:
        print("   Нечего обновлять")
    print()

    # Итоги
    total = sum(products_stats.values()) + sum(checks_stats.values()) + sum(stories_stats.values())
    print("-" * 70)
    print(f"ИТОГО: {total} записей обновлено")

    if args.dry_run:
        print()
        print("Для применения изменений запустите без --dry-run:")
        print("  python scripts/fix_testimonials_subcategories.py")
    else:
        print()
        print("✅ Изменения сохранены!")


if __name__ == "__main__":
    main()
