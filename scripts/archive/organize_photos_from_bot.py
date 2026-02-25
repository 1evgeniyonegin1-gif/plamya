#!/usr/bin/env python3
"""
Скрипт для организации фото из экспорта NL Assistant AI бота по КОНКРЕТНЫМ продуктам.

Создаёт структуру: линейка/конкретный_продукт/photos/
Пример: occuba/active_serum/photos/, nlka/happy_smile/photos/

Логика:
- Отслеживаем текущий продукт по контексту
- Короткие названия = продукты (LYMPH GYAN, Active Serum)
- Фото привязываются к последнему продукту в контексте
"""

import json
import shutil
import re
from pathlib import Path
from collections import Counter, defaultdict
import sys


PROJECT_ROOT = Path(__file__).parent.parent
UNIFIED_PRODUCTS = PROJECT_ROOT / "content" / "unified_products"

# Известные продукты NL (для точного маппинга)
KNOWN_PRODUCTS = {
    # GreenFlash GYAN серия
    "lymph gyan": ("greenflash", "lymph_gyan"),
    "lux gyan": ("greenflash", "lux_gyan"),
    "uri gyan": ("greenflash", "uri_gyan"),
    "livo gyan": ("greenflash", "livo_gyan"),
    "gut vigyan": ("greenflash", "gut_vigyan"),

    # GreenFlash другие
    "metaboost": ("greenflash", "metaboost"),
    "lactoferra": ("greenflash", "lactoferra"),
    "food control": ("greenflash", "food_control"),
    "gelm cleanse": ("greenflash", "gelm_cleanse"),
    "soft sorb": ("greenflash", "soft_sorb"),
    "no yo-yo effect": ("greenflash", "no_yoyo_effect"),
    "draineffect": ("greenflash", "draineffect"),

    # Energy Diet
    "ed smart": ("energy_diet", "ed_smart"),
    "energy diet": ("energy_diet", "energy_diet"),
    "ed баланс": ("energy_diet", "ed_balance"),
    "ed старт": ("energy_diet", "ed_start"),

    # NLка
    "happy smile": ("nlka", "happy_smile"),
    "nlka baby": ("nlka", "nlka_baby"),
    "nlка baby": ("nlka", "nlka_baby"),
    "nlka kids": ("nlka", "nlka_kids"),
    "nlка kids": ("nlka", "nlka_kids"),
    "omega-3 dha": ("nlka", "omega3_dha"),
    "liquid ca+": ("nlka", "liquid_ca"),
    "liquid ca+ for kids": ("nlka", "liquid_ca"),
    "vision lecithin": ("nlka", "vision_lecithin"),
    "probiotic": ("nlka", "probiotic"),

    # Collagen
    "collagen peptides": ("collagen", "collagen_peptides"),
    "collagen marine": ("collagen", "collagen_marine"),
    "collagen trinity": ("collagen", "collagen_trinity"),

    # Occuba для волос
    "active serum": ("occuba", "active_serum"),
    "сыворотка active serum": ("occuba", "active_serum"),
    "маска мгновенного действия": ("occuba", "maska_instant"),
    "крем-блеск для волос": ("occuba", "cream_shine"),
    "филлер-термозащита master hair": ("occuba", "filler_master_hair"),
    "спрей-кондиционер для волос 3-in-1": ("occuba", "spray_conditioner_3in1"),
    "шампунь восстанавливающий": ("occuba", "shampoo_repair"),
    "кондиционер восстанавливающий": ("occuba", "conditioner_repair"),
    "маска восстанавливающая": ("occuba", "mask_repair"),
    "шампунь объем и сила": ("occuba", "shampoo_volume"),
    "кондиционер объем и сила": ("occuba", "conditioner_volume"),
    "шампунь балансирующий": ("occuba", "shampoo_balance"),
    "кондиционер балансирующий": ("occuba", "conditioner_balance"),

    # Occuba Oriental (уход за лицом)
    "bl oriental": ("occuba", "bl_oriental"),
    "гидрофильный бальзам": ("occuba", "hydrophilic_balm"),
    "бабл-пудра": ("occuba", "bubble_powder"),
    "ночная увлажняющая маска": ("occuba", "night_mask"),
    "патчи magic glitter": ("occuba", "patches_magic_glitter"),
    "сыворотка vitalize moisturizing serum": ("occuba", "serum_vitalize"),
    "патчи pink glow": ("occuba", "patches_pink_glow"),
    "пенка для умывания": ("occuba", "foam_cleanse"),
    "энзимная пудра": ("occuba", "enzyme_powder"),
    "диски для очищения": ("occuba", "cleansing_discs"),
    "увлажняющий мист": ("occuba", "moisturizing_mist"),
    "гидрофильное масло": ("occuba", "hydrophilic_oil"),
    "гидрогелевая маска detox hydrogel mask": ("occuba", "mask_detox"),
    "жидкие патчи anti-dark circles": ("occuba", "patches_anti_dark"),
    "жидкие патчи shine & antistress": ("occuba", "patches_shine"),

    # Occuba Biome
    "biome 2 in 1 face cream": ("occuba", "biome_face_cream"),
    "biome eye cream": ("occuba", "biome_eye_cream"),
    "biome serum": ("occuba", "biome_serum"),
    "cc dull cream": ("occuba", "cc_dull_cream"),
    "легкий увлажняющий крем-гель": ("occuba", "light_cream_gel"),
    "насыщенный крем-баттер для тела": ("occuba", "body_butter"),
    "восстанавливающая ночная сыворотка для лица": ("occuba", "night_serum_face"),
    "восстанавливающий крем для контура глаз": ("occuba", "eye_contour_cream"),
    "обогащенный ночной крем": ("occuba", "enriched_night_cream"),

    # Occuba The LAB (мужская)
    "гель для бритья the lab": ("occuba", "thelab_shave_gel"),
    "гель для душа и шампунь 2 в 1 the lab": ("occuba", "thelab_shower_2in1"),
    "гель для умывания the lab": ("occuba", "thelab_face_gel"),
    "дезодорант мужской the lab": ("occuba", "thelab_deodorant"),

    # BeLoved парфюмерия
    "donna bella": ("beloved", "donna_bella"),
    "gentleman": ("beloved", "gentleman"),
    "valery": ("beloved", "valery"),
    "liverpool": ("beloved", "liverpool"),
    "vodoley": ("beloved", "vodoley"),
    "every black": ("beloved", "every_black"),
    "every deep black": ("beloved", "every_deep_black"),
    "every green": ("beloved", "every_green"),
    "every mix": ("beloved", "every_mix"),
    "every red": ("beloved", "every_red"),
    "prana": ("beloved", "prana"),
    "white tea": ("beloved", "white_tea"),

    # Enerwood чаи
    "herbal tea": ("enerwood", "herbal_tea"),
    "herbal tea new": ("enerwood", "herbal_tea_new"),
    "imperial herb": ("enerwood", "imperial_herb"),
    "зеленый чай": ("enerwood", "green_tea"),
    "горячий напиток «малина»": ("enerwood", "hot_raspberry"),

    # Sport
    "energy pro": ("sport", "energy_pro"),

    # Omega
    "omega": ("omega", "omega"),
    "magnesium marine": ("omega", "magnesium_marine"),

    # 3D Slim
    "3d slim": ("3d_slim", "3d_slim"),

    # Prohelper
    "prohelper": ("prohelper", "prohelper"),

    # BioDrone
    "biodrone": ("biodrone", "biodrone"),

    # BioTuning
    "biotuning": ("biotuning", "biotuning"),
    "metabiotic": ("biotuning", "metabiotic"),

    # Fineffect
    "fineffect textile": ("fineffect", "textile"),
    "protect": ("fineffect", "protect"),
    "sensitive": ("fineffect", "sensitive"),
    "active plus": ("fineffect", "active_plus"),

    # Стартовые наборы
    "стартовые наборы": ("starter_kit", "starter_kit"),
}

# Маппинг названий линеек для фото коллекций
LINE_NAMES = {
    "imperial herb": "enerwood",
    "occuba для волос": "occuba",
    "occuba": "occuba",
    "bl oriental": "occuba",
    "biome": "occuba",
    "the lab": "occuba",
    "beloved": "beloved",
    "be best": "beloved",
    "nlка": "nlka",
    "nlka": "nlka",
    "nlка мерч": "nlka",
    "energy diet": "energy_diet",
    "ed smart": "energy_diet",
    "greenflash": "greenflash",
    "gyan": "greenflash",
    "collagen": "collagen",
    "fineffect": "fineffect",
    "textile": "fineffect",
    "концентраты для стирки": "fineffect",
    "sklaer": "fineffect",
    "зубные пасты": "fineffect",
    "omega": "omega",
    "3d slim": "3d_slim",
    "prohelper": "prohelper",
    "biodrone": "biodrone",
    "biotuning": "biotuning",
    "enerwood": "enerwood",
    "sport": "sport",
    "energy pro": "sport",
    "уходовая косметика": "occuba",
}

# Паттерны кнопок меню (НЕ названия продуктов)
MENU_PATTERNS = [
    "назад", "коллекция", "фото для соц", "декларация", "продукция",
    "выберите", "главное меню", "модельные фото", "другие вкусы",
    "про какой", "что выбрать", "применение", "состав", "вопрос",
    "ответ", "инструкци", "скачать", "презентац", "для детей",
    "уходовая косметика", "бад", "фото с людьми", "произошла ошибка",
    "lux", "uri", "livo"  # убираем короткие слова без контекста
]


def normalize_text(text: str) -> str:
    """Нормализует текст для поиска"""
    # Убираем эмодзи
    text = re.sub(r'[^\w\s\-а-яёА-ЯЁa-zA-Z0-9+]', '', text)
    return text.strip().lower()


def find_product(text: str) -> tuple[str, str] | None:
    """Ищет известный продукт в тексте"""
    text_norm = normalize_text(text)

    # Сначала проверяем полные совпадения
    for product_name, (line, slug) in KNOWN_PRODUCTS.items():
        if product_name in text_norm:
            return (line, slug)

    return None


def is_menu_button(text: str) -> bool:
    """Проверяет что это кнопка меню, а не название продукта"""
    text_lower = text.lower()
    for pattern in MENU_PATTERNS:
        if pattern in text_lower:
            return True
    return False


def detect_line_from_context(text: str) -> str | None:
    """Определяет линейку по контексту (для фото коллекций)"""
    text_lower = normalize_text(text)
    for name, line in LINE_NAMES.items():
        if name in text_lower:
            return line
    return None


def is_collection_trigger(text: str) -> bool:
    """Проверяет что это триггер 'Коллекция'"""
    text_lower = text.lower()
    return "коллекция" in text_lower and len(text) < 30


def process_export(export_path: Path, dry_run: bool = True):
    """Обрабатывает экспорт и копирует фото по продуктам"""

    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

    result_json = export_path / "result.json"
    photos_dir = export_path / "photos"

    if not result_json.exists():
        print(f"[X] Файл {result_json} не найден")
        return

    with open(result_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"[*] Чат: {data.get('name', 'не указано')}")
    print(f"[*] Тип: {data.get('type', 'не указан')}")

    messages = data.get("messages", [])
    print(f"[*] Сообщений: {len(messages)}")

    # Собираем фото с привязкой к продуктам
    photo_mappings = []
    collection_mappings = []  # Фото коллекций линеек
    current_product = None  # (line, slug)
    current_line_context = None  # Текущая линейка для коллекций
    pending_collection = False  # Флаг: следующее фото - это коллекция

    for i, m in enumerate(messages):
        text = m.get("text", "")
        if isinstance(text, list):
            text = " ".join([t if isinstance(t, str) else t.get("text", "") for t in text])

        # Обновляем контекст линейки
        line_ctx = detect_line_from_context(text)
        if line_ctx:
            current_line_context = line_ctx

        # Проверяем триггер "Коллекция"
        if is_collection_trigger(text):
            pending_collection = True

        # Проверяем не кнопка ли это меню
        if text and not is_menu_button(text):
            # Ищем продукт в тексте
            found = find_product(text)
            if found:
                current_product = found
                pending_collection = False  # Сбрасываем флаг коллекции

        # Если это фото
        photo = m.get("photo", "")
        if photo:
            photo_name = Path(photo).name

            # Это фото коллекции?
            if pending_collection and current_line_context:
                collection_mappings.append({
                    "photo": photo_name,
                    "line": current_line_context,
                    "source": photos_dir / photo_name
                })
                pending_collection = False
            # Или фото продукта
            elif current_product:
                line, slug = current_product
                photo_mappings.append({
                    "photo": photo_name,
                    "line": line,
                    "slug": slug,
                    "source": photos_dir / photo_name
                })

    print(f"\n[OK] Привязано фото к продуктам: {len(photo_mappings)}")
    print(f"[OK] Фото коллекций линеек: {len(collection_mappings)}")

    # Статистика по коллекциям
    coll_counts = Counter(p["line"] for p in collection_mappings)
    print("\n[STATS] Коллекции линеек:")
    for line, cnt in coll_counts.most_common():
        print(f"   {line}/_collection: {cnt} фото")

    # Статистика по линейкам
    line_counts = Counter(p["line"] for p in photo_mappings)
    print("\n[STATS] По линейкам (продукты):")
    for line, cnt in line_counts.most_common():
        print(f"   {line}: {cnt} фото")

    # Статистика по продуктам
    product_counts = Counter(p["slug"] for p in photo_mappings)
    print(f"\n[STATS] Уникальных продуктов: {len(product_counts)}")
    print("Топ-30 продуктов:")
    for slug, cnt in product_counts.most_common(30):
        print(f"   {slug}: {cnt} фото")

    # Копирование
    print(f"\n{'[DRY RUN] Показ без копирования' if dry_run else '[COPY] Копирование файлов...'}\n")

    copied = 0
    skipped = 0
    not_found = 0
    shown = 0
    coll_copied = 0

    # Сначала копируем фото коллекций
    print("--- Коллекции линеек ---")
    for mapping in collection_mappings:
        source = mapping["source"]
        line = mapping["line"]
        photo_name = mapping["photo"]

        # Целевая папка: линейка/_collection/photos/
        target_dir = UNIFIED_PRODUCTS / line / "_collection" / "photos"
        target = target_dir / photo_name

        if not source.exists():
            not_found += 1
            continue

        if target.exists():
            skipped += 1
            continue

        if dry_run:
            if shown < 20:
                print(f"  {photo_name} -> {line}/_collection/")
                shown += 1
            coll_copied += 1
        else:
            target_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            coll_copied += 1

    # Теперь копируем фото продуктов
    print("\n--- Продукты ---")
    shown = 0
    for mapping in photo_mappings:
        source = mapping["source"]
        line = mapping["line"]
        slug = mapping["slug"]
        photo_name = mapping["photo"]

        # Целевая папка: линейка/продукт/photos/
        target_dir = UNIFIED_PRODUCTS / line / slug / "photos"
        target = target_dir / photo_name

        if not source.exists():
            not_found += 1
            continue

        if target.exists():
            skipped += 1
            continue

        if dry_run:
            if shown < 30:
                print(f"  {photo_name} -> {line}/{slug}/")
                shown += 1
            copied += 1
        else:
            target_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            copied += 1

    print(f"\n{'=' * 50}")
    print("ИТОГО:")
    print(f"  {'Будет скопировано' if dry_run else 'Скопировано'} коллекций: {coll_copied}")
    print(f"  {'Будет скопировано' if dry_run else 'Скопировано'} продуктов: {copied}")
    print(f"  Пропущено (уже есть): {skipped}")
    print(f"  Не найдено в экспорте: {not_found}")

    if dry_run:
        print(f"\n[!] Это DRY RUN. Для реального копирования запустите с --execute")
    else:
        # Показываем созданную структуру
        print("\n[STRUCTURE] Созданные папки:")
        for line_dir in sorted(UNIFIED_PRODUCTS.iterdir()):
            if line_dir.is_dir():
                products = [p for p in line_dir.iterdir() if p.is_dir() and (p / "photos").exists()]
                if products:
                    print(f"\n  {line_dir.name}/")
                    for prod in sorted(products):
                        photos_count = len(list((prod / "photos").glob("*.jpg")))
                        if photos_count > 0:
                            print(f"    {prod.name}/ ({photos_count} фото)")


def main():
    if len(sys.argv) < 2:
        print("Usage: python organize_photos_from_bot.py <path_to_export> [--execute]")
        print()
        print("Создаёт структуру: линейка/конкретный_продукт/photos/")
        print()
        print("Пример:")
        print('  python organize_photos_from_bot.py "C:/Users/mafio/Downloads/Telegram Desktop/ChatExport_2026-01-23"')
        print('  python organize_photos_from_bot.py "C:/Users/mafio/Downloads/Telegram Desktop/ChatExport_2026-01-23" --execute')
        return

    export_path = Path(sys.argv[1])
    dry_run = "--execute" not in sys.argv

    if not export_path.exists():
        print(f"[X] Папка {export_path} не найдена")
        return

    print("=" * 60)
    print("ОРГАНИЗАЦИЯ ФОТО ПО КОНКРЕТНЫМ ПРОДУКТАМ")
    print("Структура: линейка/продукт/photos/")
    print("=" * 60)

    process_export(export_path, dry_run=dry_run)


if __name__ == "__main__":
    main()
