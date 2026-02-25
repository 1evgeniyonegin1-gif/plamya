#!/usr/bin/env python3
"""
Скрипт для маппинга фото к продуктам на основе контекста из Telegram экспорта NL Assistant AI.

Паттерн в экспорте:
1. Название продукта (например: "🌱Экопенка для мытья рук HERBAL Hand foam")
2. Текст описания, состав, применение
3. Кнопка "📷Фото для соцсетей"
4. Несколько фото подряд

Скрипт находит этот паттерн и перемещает фото из unified_products/general/
в правильные папки продуктов.
"""

import json
import shutil
from pathlib import Path
from typing import Dict, List, Set
import re
from collections import defaultdict

# Путь к проекту
PROJECT_ROOT = Path(__file__).parent.parent

# Путь к unified_products
UNIFIED_PRODUCTS = PROJECT_ROOT / "content" / "unified_products"

# Маппинг названий продуктов на папки
PRODUCT_MAPPING = {
    "herbal hand foam": "beloved",
    "floral hand foam": "beloved",
    "dish wash": "beloved",
    "laundry": "beloved",
    "be loved": "beloved",
    "energy diet": "energy_diet",
    "ed smart": "ed_smart",
    "collagen": "collagen",
    "greenflash": "greenflash",
    "green flash": "greenflash",
    "draineffect": "draineffect",
    "drain effect": "draineffect",
    "3d slim": "3d_slim",
    "occuba": "occuba",
    "prohelper": "prohelper",
    "pro helper": "prohelper",
    "omega": "omega",
    "calcium": "calcium",
    "nlka": "nlka",
    "nlка": "nlka",
    "sport": "sport",
    "happy smile": "happy_smile",
    "antiage": "antiage",
    "anti age": "antiage",
    "biodrone": "biodrone",
    "biotuning": "biotuning",
    "enerwood": "enerwood",
    "vitamin d": "vitamin_d",
    "starter": "starter_kit",
    "стартер": "starter_kit",
}


def normalize_product_name(text: str) -> str | None:
    """Нормализует название продукта и возвращает папку."""
    text_lower = text.lower()

    # Убираем эмодзи и спецсимволы
    text_clean = re.sub(r'[🌱🌀📌🖥❔⬅📷💊🍃✨💚🌿🔥💪]', '', text_lower).strip()

    # Ищем совпадения
    for key, folder in PRODUCT_MAPPING.items():
        if key in text_clean:
            return folder

    return None


def parse_telegram_export(export_path: Path) -> Dict[str, str]:
    """
    Парсит Telegram экспорт и возвращает маппинг: {photo_filename: product_folder}.

    Логика:
    1. Ищем сообщения с текстом (потенциальное название продукта)
    2. Проверяем следующие сообщения на наличие "📷Фото для соцсетей"
    3. После этого текста собираем все фото до следующего текстового сообщения
    """
    result_json = export_path / "result.json"

    if not result_json.exists():
        print(f"❌ Файл {result_json} не найден")
        return {}

    with open(result_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    messages = data.get("messages", [])
    photo_mapping = {}

    current_product = None
    collecting_photos = False

    for i, msg in enumerate(messages):
        msg_type = msg.get("type", "")
        text = msg.get("text", "")

        # Если текст - это строка
        if isinstance(text, str):
            text_str = text
        # Если текст - это список (может быть с форматированием)
        elif isinstance(text, list):
            text_str = " ".join([item if isinstance(item, str) else item.get("text", "")
                                for item in text])
        else:
            text_str = ""

        # 1. Проверяем, не новое ли это название продукта
        if text_str and not text_str.startswith(("⬅", "🖥", "📌", "🌀", "❔")):
            product_folder = normalize_product_name(text_str)
            if product_folder:
                current_product = product_folder
                collecting_photos = False
                print(f"📦 Найден продукт: {text_str[:50]} -> {product_folder}")

        # 2. Проверяем кнопку "Фото для соцсетей"
        if "📷" in text_str and ("фото" in text_str.lower() or "соцсет" in text_str.lower()):
            if current_product:
                collecting_photos = True
                print(f"   📷 Начинаем сбор фото для {current_product}")

        # 3. Собираем фото
        if collecting_photos and msg_type == "message":
            photo = msg.get("photo")
            if photo:
                # Извлекаем имя файла
                if isinstance(photo, str):
                    photo_file = Path(photo).name
                    photo_mapping[photo_file] = current_product
                    print(f"      ✅ {photo_file} -> {current_product}")

        # 4. Останавливаем сбор при следующем текстовом сообщении (кроме коротких)
        if collecting_photos and text_str and len(text_str) > 10:
            if not ("фото" in text_str.lower() or text_str.startswith("NL Assistant")):
                collecting_photos = False
                print(f"   ⏹ Завершен сбор для {current_product}")

    return photo_mapping


def move_photos(photo_mapping: Dict[str, str], dry_run: bool = True):
    """
    Перемещает фото из general/ в правильные папки продуктов.

    Args:
        photo_mapping: Словарь {photo_filename: product_folder}
        dry_run: Если True, только показывает что будет сделано
    """
    general_dir = UNIFIED_PRODUCTS / "general" / "photos"

    if not general_dir.exists():
        print(f"❌ Папка {general_dir} не найдена")
        return

    stats = defaultdict(int)
    moved_count = 0
    not_found_count = 0

    for photo_file, product_folder in photo_mapping.items():
        source = general_dir / photo_file

        if not source.exists():
            not_found_count += 1
            continue

        # Целевая папка
        target_dir = UNIFIED_PRODUCTS / product_folder / "photos"
        target_dir.mkdir(parents=True, exist_ok=True)

        target = target_dir / photo_file

        if dry_run:
            print(f"[DRY RUN] {photo_file} -> {product_folder}/")
        else:
            shutil.move(str(source), str(target))
            print(f"✅ {photo_file} -> {product_folder}/")

        stats[product_folder] += 1
        moved_count += 1

    print("\n" + "="*60)
    print("СТАТИСТИКА")
    print("="*60)
    print(f"Всего маппингов: {len(photo_mapping)}")
    print(f"Перемещено: {moved_count}")
    print(f"Не найдено: {not_found_count}")
    print()
    print("По продуктам:")
    for product, count in sorted(stats.items(), key=lambda x: -x[1]):
        print(f"  {product}: {count} фото")


def main():
    import sys

    if len(sys.argv) < 2:
        print("Usage: python map_photos_to_products.py <path_to_telegram_export> [--execute]")
        print()
        print("Аргументы:")
        print("  <path_to_telegram_export>  Путь к папке с result.json")
        print("  --execute                  Выполнить перемещение (без флага - dry run)")
        print()
        print("Пример:")
        print('  python map_photos_to_products.py "C:/Users/mafio/Downloads/NL Assistant AI"')
        print('  python map_photos_to_products.py "C:/Users/mafio/Downloads/NL Assistant AI" --execute')
        return

    export_path = Path(sys.argv[1])
    dry_run = "--execute" not in sys.argv

    if not export_path.exists():
        print(f"❌ Папка {export_path} не найдена")
        return

    print("="*60)
    print("ПАРСИНГ TELEGRAM ЭКСПОРТА")
    print("="*60)
    print(f"Экспорт: {export_path}")
    print(f"Режим: {'DRY RUN (только показ)' if dry_run else 'ВЫПОЛНЕНИЕ'}")
    print()

    # Парсим экспорт
    photo_mapping = parse_telegram_export(export_path)

    if not photo_mapping:
        print("\n❌ Не найдено ни одного маппинга фото -> продукт")
        return

    print(f"\n✅ Найдено {len(photo_mapping)} маппингов")
    print()

    # Перемещаем фото
    if dry_run:
        print("⚠️  DRY RUN MODE - файлы НЕ будут перемещены")
        print("    Для выполнения добавьте флаг --execute")
        print()

    move_photos(photo_mapping, dry_run=dry_run)

    if dry_run:
        print("\n⚠️  Это был DRY RUN. Для реального перемещения запустите с --execute")


if __name__ == "__main__":
    main()
