"""
Скрипт для разбиения больших файлов базы знаний на отдельные файлы.

Задачи:
1. Разбить general_from_pdf.txt по источникам PDF -> отдельные файлы
2. Разбить kosmetika_nl.md по категориям продуктов
3. Добавить метаданные (tags, keywords) к каждому файлу
"""

import os
import re
from pathlib import Path
from collections import defaultdict
from datetime import datetime

# Пути
BASE_DIR = Path(__file__).parent.parent
KNOWLEDGE_BASE = BASE_DIR / "content" / "knowledge_base"
FROM_PDF_DIR = KNOWLEDGE_BASE / "from_pdf"
PRODUCTS_DIR = KNOWLEDGE_BASE / "products"

# Маппинг PDF файлов на категории продуктов
PDF_CATEGORIES = {
    # БАДы и витамины
    "biotuning": ("supplements", "БАДы", ["адаптоген", "молозиво", "иммунитет"]),
    "biodrone": ("supplements", "БАДы", ["дрон", "молозиво", "пребиотик"]),
    "biosetting": ("supplements", "БАДы", ["настройка", "адаптоген"]),
    "lactoferra": ("supplements", "БАДы", ["лактоферра", "железо", "анемия"]),
    "iron_fe": ("supplements", "БАДы", ["железо", "анемия", "гемоглобин"]),
    "magnesium": ("supplements", "БАДы", ["магний", "стресс", "нервы"]),
    "zinc": ("supplements", "БАДы", ["цинк", "иммунитет", "кожа"]),
    "vitamin_b9b12": ("supplements", "БАДы", ["витамин B", "фолиевая", "B12"]),
    "k2d3": ("supplements", "БАДы", ["витамин D", "витамин K", "кости"]),
    "5-htp": ("supplements", "БАДы", ["5-HTP", "серотонин", "настроение"]),
    "metabrain": ("supplements", "БАДы", ["мозг", "память", "концентрация"]),
    "nejromedium": ("supplements", "БАДы", ["нейромедиум", "мозг", "нервы"]),
    "metaboost": ("supplements", "БАДы", ["метаболизм", "энергия", "жиросжигание"]),
    "vitamian": ("supplements", "БАДы", ["витамины", "иммунитет"]),
    "mgb6_kids": ("supplements", "БАДы", ["магний", "дети", "нервы"]),

    # Спортивное питание
    "energy_pro": ("sports", "Спортивное питание", ["батончик", "протеин", "энергия"]),
    "energy_life": ("sports", "Спортивное питание", ["батончик", "перекус", "энергия"]),
    "batonchiki": ("sports", "Спортивное питание", ["батончик", "протеин"]),
    "chicken": ("sports", "Спортивное питание", ["курица", "белок", "протеин"]),

    # Детокс и похудение
    "detox": ("detox", "Детокс", ["детокс", "очищение", "draineffect"]),
    "3d_slim": ("detox", "Детокс", ["slim", "похудение", "целлюлит"]),

    # Косметика
    "biome": ("cosmetics", "Косметика", ["биом", "микробиом", "кожа"]),
    "bl_body": ("cosmetics", "Косметика", ["тело", "уход", "кожа"]),
    "bl_oriental": ("cosmetics", "Косметика", ["oriental", "азиатская", "корейская"]),
    "patchi": ("cosmetics", "Косметика", ["патчи", "глаза", "увлажнение"]),
    "liquid_patches": ("cosmetics", "Косметика", ["патчи", "жидкие", "увлажнение"]),
    "gidrogelevyie_patchi": ("cosmetics", "Косметика", ["патчи", "гидрогель", "глаза"]),
    "solntsezaschitnaya": ("cosmetics", "Косметика", ["SPF", "солнцезащита", "UV"]),
    "dezodorant": ("cosmetics", "Косметика", ["дезодорант", "пот", "запах"]),

    # Детская косметика
    "det_kosmetika": ("kids_cosmetics", "Детская косметика", ["дети", "косметика", "уход"]),
    "det_zub_pasta": ("kids_cosmetics", "Детская косметика", ["дети", "зубная паста"]),

    # Бытовая химия
    "akvapudra": ("household", "Бытовая химия", ["стирка", "порошок", "fineffect"]),
    "stirka": ("household", "Бытовая химия", ["стирка", "порошок"]),
    "myilo": ("household", "Бытовая химия", ["мыло", "руки"]),
    "gel_dlya_myitya_posudyi": ("household", "Бытовая химия", ["посуда", "гель", "мытье"]),
    "sweet_home": ("household", "Бытовая химия", ["дом", "ароматизатор"]),

    # Здоровье полости рта
    "zubnyie_pastyi": ("oral_care", "Уход за полостью рта", ["зубы", "паста", "sklaer"]),
    "happy_smile": ("oral_care", "Уход за полостью рта", ["зубы", "отбеливание"]),

    # Чаи и напитки
    "enerwood": ("drinks", "Чаи и напитки", ["чай", "enerwood", "энергия"]),
    "white_tea": ("drinks", "Чаи и напитки", ["чай", "белый", "антиоксидант"]),
    "malina": ("drinks", "Чаи и напитки", ["малина", "горячий напиток", "иммунитет"]),

    # Еда
    "pechene": ("food", "Еда", ["печенье", "суфле", "перекус"]),

    # Стартовые наборы
    "startovyie_naboryi": ("starter_kits", "Стартовые наборы", ["старт", "набор", "новичок"]),

    # The LAB (мужская косметика)
    "lab": ("the_lab", "The LAB", ["мужская", "бритье", "уход"]),

    # Be Best (витамины для мужчин/женщин)
    "be_best_male": ("supplements", "БАДы", ["мужские витамины", "энергия", "потенция"]),
    "be_best__female": ("supplements", "БАДы", ["женские витамины", "красота", "гормоны"]),
}

# Категории для косметики — расширенный список
COSMETICS_CATEGORIES = {
    # Уход за телом
    "Масло для душа": "body_care",
    "Гель для душа": "body_care",
    "Крем для тела": "body_care",
    "Молочко для тела": "body_care",
    "Скраб для тела": "body_care",
    "Антицеллюлит": "body_care",
    "Cellufight": "body_care",
    "Body": "body_care",
    "Массаж": "body_care",
    "Дезодорант": "body_care",
    "Intimate": "body_care",
    "Интим": "body_care",

    # Уход за волосами
    "Набор для волос": "hair_care",
    "Silky Hair": "hair_care",
    "Шампунь": "hair_care",
    "Кондиционер": "hair_care",
    "Маска для волос": "hair_care",
    "Бальзам для волос": "hair_care",
    "Hair": "hair_care",
    "Волос": "hair_care",

    # Уход за лицом
    "Бабл-пудра": "face_care",
    "Creamy Bubble": "face_care",
    "Bubble": "face_care",
    "Диски для лица": "face_care",
    "Exfoliating": "face_care",
    "Biome": "face_care",
    "Сыворотка": "face_care",
    "Serum": "face_care",
    "Тоник": "face_care",
    "Toner": "face_care",
    "Мицеллярная": "face_care",
    "Micellar": "face_care",
    "Гидрофильное": "face_care",
    "Cleansing": "face_care",
    "Пенка": "face_care",
    "Foam": "face_care",
    "Крем для лица": "face_care",
    "Face Cream": "face_care",
    "Маска для лица": "face_care",
    "Face Mask": "face_care",
    "BB-крем": "face_care",
    "Консилер": "face_care",
    "Пилинг": "face_care",
    "Peeling": "face_care",
    "Скраб для лица": "face_care",
    "Гель для умывания": "face_care",
    "Oriental": "face_care",
    "BL Oriental": "face_care",
    "Mist": "face_care",
    "Essence": "face_care",
    "Эссенция": "face_care",
    "Эмульсия": "face_care",
    "Emulsion": "face_care",
    "Ночной": "face_care",
    "Night": "face_care",
    "Дневной": "face_care",
    "Day": "face_care",
    "Увлажняющий крем": "face_care",
    "Moisturizing": "face_care",
    "Aqua": "face_care",
    "Hyaluronic": "face_care",
    "Гиалурон": "face_care",
    "Коллаген": "face_care",
    "Collagen": "face_care",
    "Ампула": "face_care",
    "Ampoule": "face_care",

    # Уход вокруг глаз
    "Крем для ухода за кожей вокруг глаз": "eye_care",
    "Eye cream": "eye_care",
    "Eye Cream": "eye_care",
    "Патчи": "eye_care",
    "Patches": "eye_care",
    "Гидрогелевые": "eye_care",
    "Gel pads": "eye_care",
    "Вокруг глаз": "eye_care",

    # The LAB (мужская косметика)
    "The LAB": "the_lab",
    "LAB": "the_lab",
    "Гель для бритья": "the_lab",
    "Универсальный бальзам": "the_lab",
    "Мужской": "the_lab",
    "Shaving": "the_lab",

    # Солнцезащита
    "SPF": "sun_care",
    "Солнцезащитный": "sun_care",
    "Sun": "sun_care",
    "UV": "sun_care",

    # Декоративная косметика
    "Помада": "makeup",
    "Lipstick": "makeup",
    "Тушь": "makeup",
    "Mascara": "makeup",
    "Тени": "makeup",
    "Eyeshadow": "makeup",
    "Румяна": "makeup",
    "Blush": "makeup",
    "Пудра": "makeup",
    "Powder": "makeup",
    "Блеск": "makeup",
    "Gloss": "makeup",
    "Бальзам для губ": "makeup",
    "Lip": "makeup",
    "Губ": "makeup",
    "Карандаш": "makeup",
    "Pencil": "makeup",
    "Подводка": "makeup",
    "Eyeliner": "makeup",
    "Бровь": "makeup",
    "Brow": "makeup",
    "Тональный": "makeup",
    "Foundation": "makeup",
    "Хайлайтер": "makeup",
    "Highlighter": "makeup",
    "Контуринг": "makeup",
    "Contour": "makeup",
    "Палетка": "makeup",
    "Palette": "makeup",
    "Праймер": "makeup",
    "Primer": "makeup",
    "Base": "makeup",

    # Уход за ногтями
    "Лак для ногтей": "nails",
    "Nail": "nails",
    "Ноготь": "nails",
    "Маникюр": "nails",

    # Уход за руками
    "Крем для рук": "hand_care",
    "Hand": "hand_care",
    "Руки": "hand_care",

    # Уход за ногами
    "Крем для ног": "foot_care",
    "Foot": "foot_care",
    "Ноги": "foot_care",
    "Стоп": "foot_care",
}

CATEGORY_NAMES = {
    "body_care": "Уход за телом",
    "hair_care": "Уход за волосами",
    "face_care": "Уход за лицом",
    "eye_care": "Уход за кожей вокруг глаз",
    "the_lab": "The LAB (мужская косметика)",
    "sun_care": "Солнцезащита",
    "makeup": "Макияж",
    "nails": "Уход за ногтями",
    "hand_care": "Уход за руками",
    "foot_care": "Уход за ногами",
    "other": "Другое",
}


def get_category_for_pdf(filename: str) -> tuple:
    """Определяет категорию для PDF файла."""
    filename_lower = filename.lower()

    for key, (folder, category, keywords) in PDF_CATEGORIES.items():
        if key in filename_lower:
            return folder, category, keywords

    # Дефолтная категория
    return "other", "Другое", []


def get_category_for_product(product_text: str) -> str:
    """Определяет категорию косметического продукта по тексту."""
    for keyword, category in COSMETICS_CATEGORIES.items():
        if keyword.lower() in product_text.lower():
            return category
    return "other"


def extract_keywords_from_text(text: str) -> list:
    """Извлекает ключевые слова из текста продукта."""
    keywords = []

    # Ищем компоненты состава
    if "🧪 Состав:" in text:
        composition_start = text.find("🧪 Состав:")
        composition_end = text.find("📝", composition_start)
        if composition_end == -1:
            composition_end = len(text)
        composition = text[composition_start:composition_end]

        # Извлекаем ключевые ингредиенты
        ingredients = re.findall(r'[А-Яа-яA-Za-z]+(?:\s+[А-Яа-яA-Za-z]+)?', composition)
        important_ingredients = [
            "коллаген", "гиалуроновая", "пантенол", "витамин", "алоэ",
            "ретинол", "ниацинамид", "кислота", "масло", "экстракт",
            "пептид", "керамид", "SPF", "UV"
        ]
        for ing in ingredients:
            if any(imp.lower() in ing.lower() for imp in important_ingredients):
                keywords.append(ing.lower())

    # Ищем назначение
    if "🎯 Для чего применяется:" in text:
        purpose_start = text.find("🎯 Для чего применяется:")
        purpose_end = text.find("🧪", purpose_start)
        if purpose_end == -1:
            purpose_end = len(text)
        purpose = text[purpose_start:purpose_end]

        purpose_keywords = [
            "увлажнение", "очищение", "питание", "восстановление",
            "защита", "омоложение", "отбеливание", "матирование",
            "сужение пор", "антивозрастной", "против морщин"
        ]
        for kw in purpose_keywords:
            if kw.lower() in purpose.lower():
                keywords.append(kw)

    return list(set(keywords))[:10]  # Уникальные, максимум 10


def create_metadata(category: str, keywords: list, source: str = None) -> str:
    """Создает YAML frontmatter с метаданными."""
    today = datetime.now().strftime("%Y-%m-%d")

    meta = f"""---
date_created: {today}
date_updated: {today}
category: {category}
"""

    if source:
        meta += f"source: {source}\n"

    if keywords:
        meta += f"tags: [{', '.join(keywords)}]\n"

        # Добавляем query_examples на основе keywords
        query_examples = []
        for kw in keywords[:3]:
            query_examples.append(f'"{kw} NL"')
        if query_examples:
            meta += f"query_examples:\n"
            for qe in query_examples:
                meta += f"  - {qe}\n"

    meta += "---\n\n"
    return meta


def split_general_pdf():
    """Razbivaet general_from_pdf.txt na otdelnye fajly po istochnikam."""
    print("=" * 60)
    print("Splitting general_from_pdf.txt")
    print("=" * 60)

    input_file = FROM_PDF_DIR / "general_from_pdf.txt"
    output_dir = FROM_PDF_DIR / "split"
    output_dir.mkdir(exist_ok=True)

    with open(input_file, "r", encoding="utf-8") as f:
        content = f.read()

    # Парсим секции по источникам
    sections = re.split(r'\n## Источник: ', content)

    # Первая секция - заголовок файла, пропускаем
    header = sections[0]

    # Группируем по категориям
    categories = defaultdict(list)

    for section in sections[1:]:
        # Получаем имя файла
        lines = section.split('\n', 1)
        if len(lines) < 2:
            continue

        filename = lines[0].strip()
        content = lines[1] if len(lines) > 1 else ""

        # Определяем категорию
        folder, category, keywords = get_category_for_pdf(filename)

        categories[folder].append({
            "filename": filename,
            "content": content,
            "category": category,
            "keywords": keywords
        })

    # Создаем файлы по категориям
    created_files = []

    for folder, items in categories.items():
        folder_path = output_dir / folder
        folder_path.mkdir(exist_ok=True)

        # Объединяем дубликаты
        seen_files = set()
        unique_items = []
        for item in items:
            if item["filename"] not in seen_files:
                seen_files.add(item["filename"])
                unique_items.append(item)

        # Группируем по продуктам (если несколько PDF про один продукт)
        for item in unique_items:
            # Создаем имя выходного файла
            out_filename = re.sub(r'[^\w\-]', '_', item["filename"].replace(".pdf", ""))
            out_filename = re.sub(r'_+', '_', out_filename).strip('_').lower()
            out_path = folder_path / f"{out_filename}.md"

            # Создаем контент с метаданными
            metadata = create_metadata(
                category=item["category"],
                keywords=item["keywords"],
                source=f"PDF: {item['filename']}"
            )

            # Заголовок
            title = f"# {item['category']}: {item['filename'].replace('.pdf', '')}\n\n"

            full_content = metadata + title + item["content"].strip()

            with open(out_path, "w", encoding="utf-8") as f:
                f.write(full_content)

            created_files.append(out_path)
            print(f"  + {folder}/{out_filename}.md")

    print(f"\nCreated {len(created_files)} files")
    return created_files


def split_kosmetika():
    """Razbivaet kosmetika_nl.md na fajly po kategoriyam."""
    print("\n" + "=" * 60)
    print("Splitting kosmetika_nl.md")
    print("=" * 60)

    input_file = PRODUCTS_DIR / "kosmetika_nl.md"
    output_dir = PRODUCTS_DIR / "cosmetics"
    output_dir.mkdir(exist_ok=True)

    with open(input_file, "r", encoding="utf-8") as f:
        content = f.read()

    # Убираем YAML frontmatter
    if content.startswith("---"):
        end_yaml = content.find("---", 3)
        if end_yaml != -1:
            content = content[end_yaml + 3:].strip()

    # Паттерн для поиска начала продукта: эмодзи + название + цена в рублях + PV
    # Примеры:
    # 🧴 Универсальный бальзам The LAB 750 ₽ 5.1 PV
    # 👁️ Крем для ухода за кожей вокруг глаз Biome Eye cream 1 590 ₽ 10.3 PV
    product_start_pattern = r'([✨💇👁️🧴🧼🧔💆💄💅🌸🌟💎🎀💫✨🌙⭐🔥💚💜💛🧪🎯📝💡🧴‍♂️‍♀️]+[^\n]*\d+\s*₽[^\n]*PV[^\n]*)'

    # Разбиваем контент на продукты
    # Ищем все строки с ценой и PV
    lines = content.split('\n')
    products = []
    current_product = []

    for line in lines:
        # Проверяем, это начало нового продукта (строка с ценой и PV)
        if re.search(r'\d+\s*₽.*\d+[\.,]?\d*\s*PV', line) and len(line) > 30:
            # Сохраняем предыдущий продукт
            if current_product:
                products.append('\n'.join(current_product))
            current_product = [line]
        else:
            current_product.append(line)

    # Добавляем последний продукт
    if current_product:
        products.append('\n'.join(current_product))

    print(f"  Found {len(products)} products")

    # Группируем по категориям
    categories = defaultdict(list)

    for product in products:
        product = product.strip()
        if not product or len(product) < 50:
            continue

        # Определяем категорию по первой строке (название продукта)
        first_line = product.split('\n')[0]
        category = get_category_for_product(first_line)

        # Если не нашли по первой строке, пробуем по всему тексту
        if category == "other":
            category = get_category_for_product(product)

        keywords = extract_keywords_from_text(product)

        # Извлекаем название продукта
        product_name = re.sub(r'[✨💇👁️🧴🧼🧔💆💄💅🌸🌟💎🎀💫✨🌙⭐🔥💚💜💛🧪🎯📝💡‍♂️‍♀️]+', '', first_line)
        product_name = re.sub(r'\d+\s*₽.*', '', product_name).strip()

        categories[category].append({
            "name": product_name,
            "content": product,
            "keywords": keywords
        })

    # Создаем файлы по категориям
    created_files = []

    for category, products in categories.items():
        category_name = CATEGORY_NAMES.get(category, category)

        # Создаем один файл на категорию
        out_path = output_dir / f"{category}.md"

        # Собираем контент
        all_keywords = set()
        for p in products:
            all_keywords.update(p["keywords"])

        metadata = create_metadata(
            category=f"cosmetics/{category}",
            keywords=list(all_keywords)[:15],
            source="kosmetika_nl.md"
        )

        title = f"# {category_name}\n\n"

        products_content = "\n\n---\n\n".join([p["content"] for p in products])

        full_content = metadata + title + products_content

        with open(out_path, "w", encoding="utf-8") as f:
            f.write(full_content)

        created_files.append(out_path)
        print(f"  + cosmetics/{category}.md ({len(products)} products)")

    print(f"\nCreated {len(created_files)} files")
    return created_files


def main():
    # Fix Windows console encoding
    import sys
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

    print("Razbienje bazy znanij NL International")
    print("=" * 60)

    # 1. Razbivaem PDF fajl
    pdf_files = split_general_pdf()

    # 2. Razbivaem kosmetiku
    cosmetics_files = split_kosmetika()

    print("\n" + "=" * 60)
    print("DONE!")
    print(f"PDF files: {len(pdf_files)}")
    print(f"Cosmetics files: {len(cosmetics_files)}")
    print("=" * 60)

    print("\nNext steps:")
    print("1. Check created files")
    print("2. Delete original large files (optional)")
    print("3. Reload knowledge base: python scripts/load_knowledge_base.py")


if __name__ == "__main__":
    main()
