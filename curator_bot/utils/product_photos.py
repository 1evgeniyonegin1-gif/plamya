"""
Утилита для работы с фото продуктов NL International.
Находит и отправляет фото продуктов клиентам.

Использует полный маппинг из full_products_mapping.json (~200 продуктов)
"""
import os
import json
import random
from pathlib import Path
from typing import Optional, List
from loguru import logger

# Базовый путь к фото продуктов
UNIFIED_PRODUCTS_PATH = Path(__file__).parent.parent.parent / "content" / "unified_products"

# Загружаем полный маппинг из JSON
MAPPING_FILE = UNIFIED_PRODUCTS_PATH / "full_products_mapping.json"

# Кэш маппинга
_keywords_cache: Optional[dict] = None
_categories_cache: Optional[dict] = None


def _load_mapping():
    """Загружает маппинг из JSON файла"""
    global _keywords_cache, _categories_cache

    if _keywords_cache is not None:
        return

    try:
        with open(MAPPING_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            _keywords_cache = data.get("keywords", {})
            _categories_cache = data.get("categories", {})
            logger.info(f"Loaded product mapping: {len(_keywords_cache)} keywords, {len(_categories_cache)} categories")
    except Exception as e:
        logger.error(f"Failed to load product mapping: {e}")
        _keywords_cache = {}
        _categories_cache = {}


def find_product_photos(product_name: str, limit: int = 5) -> List[str]:
    """
    Ищет фото продукта по названию.

    Args:
        product_name: Название или ключевое слово продукта
        limit: Максимальное количество фото

    Returns:
        Список путей к фото
    """
    _load_mapping()

    photos = []
    product_lower = product_name.lower().strip()

    # Сначала ищем точное совпадение в маппинге
    folder_path = None

    # Пробуем найти точное ключевое слово
    if product_lower in _keywords_cache:
        folder_path = _keywords_cache[product_lower]
        logger.info(f"Exact match for '{product_lower}' -> {folder_path}")
    else:
        # Ищем частичное совпадение
        for keyword, path in _keywords_cache.items():
            if keyword in product_lower or product_lower in keyword:
                folder_path = path
                logger.info(f"Partial match '{keyword}' in '{product_lower}' -> {folder_path}")
                break

    # Если нашли папку - ищем в ней фото
    if folder_path:
        full_path = UNIFIED_PRODUCTS_PATH / folder_path / "photos"
        if full_path.exists():
            for photo_path in full_path.glob("*.jpg"):
                photos.append(str(photo_path))
            for photo_path in full_path.glob("*.png"):
                photos.append(str(photo_path))

            logger.info(f"Found {len(photos)} photos in {full_path}")

    # Если ничего не нашли - пробуем fallback на general
    if not photos:
        general_path = UNIFIED_PRODUCTS_PATH / "general" / "photos"
        if general_path.exists():
            for photo_path in list(general_path.glob("*.jpg"))[:limit * 3]:
                photos.append(str(photo_path))
            logger.warning(f"No specific photos for '{product_name}', using general")

    # Перемешиваем и возвращаем
    if photos:
        random.shuffle(photos)
        return photos[:limit]

    logger.warning(f"No photos found for product: {product_name}")
    return []


def get_random_product_photo(product_name: str) -> Optional[str]:
    """
    Возвращает случайное фото продукта.

    Args:
        product_name: Название продукта

    Returns:
        Путь к фото или None
    """
    photos = find_product_photos(product_name, limit=10)
    if photos:
        return random.choice(photos)
    return None


def get_photo_for_pain(pain: str) -> Optional[str]:
    """
    Возвращает фото продукта для конкретной боли.

    Args:
        pain: Боль клиента (weight, energy, immunity, beauty, kids, sport)

    Returns:
        Путь к фото или None
    """
    pain_to_product = {
        "weight": "ed smart",
        "energy": "greenflash",
        "immunity": "vitamin d",
        "beauty": "collagen",
        "skin": "occuba",
        "kids": "happy smile",
        "sport": "energy pro",
        "detox": "draineffect",
        "sleep": "magnesium marine",
    }

    product_hint = pain_to_product.get(pain, "ed smart")
    return get_random_product_photo(product_hint)


# Маппинг категорий на фото для быстрого доступа
CATEGORY_PHOTO_MAP = {
    "Energy Diet": "ed_smart",
    "Greenflash БАД": "greenflash",
    "Косметика Be Loved": "beloved",
    "Для детей NLka": "nlka",
    "3D Slim": "3d_slim",
    "Уход за волосами": "occuba",
    "Чай и напитки": "enerwood",
    "Коллаген": "collagen",
    "Омега-3": "omega",
    "Витамин D": "vitamin_d",
    "Спорт": "sport",
}


def get_photo_by_category(category: str) -> Optional[str]:
    """
    Возвращает фото по категории продукта.

    Args:
        category: Название категории

    Returns:
        Путь к фото или None
    """
    _load_mapping()

    # Проверяем в старом маппинге
    folder = CATEGORY_PHOTO_MAP.get(category)
    if folder:
        return get_random_product_photo(folder)

    # Проверяем в новом маппинге категорий
    category_lower = category.lower()
    if category_lower in _categories_cache:
        paths = _categories_cache[category_lower]
        if paths:
            # Берём первый путь из категории
            folder_path = paths[0]
            full_path = UNIFIED_PRODUCTS_PATH / folder_path / "photos"
            if full_path.exists():
                photos = list(full_path.glob("*.jpg")) + list(full_path.glob("*.png"))
                if photos:
                    return str(random.choice(photos))

    return None


def get_all_photos_for_category(category: str, limit: int = 20) -> List[str]:
    """
    Возвращает все фото для категории.

    Args:
        category: Название категории
        limit: Максимум фото

    Returns:
        Список путей к фото
    """
    _load_mapping()

    photos = []
    category_lower = category.lower()

    if category_lower in _categories_cache:
        for folder_path in _categories_cache[category_lower]:
            full_path = UNIFIED_PRODUCTS_PATH / folder_path / "photos"
            if full_path.exists():
                for photo in full_path.glob("*.jpg"):
                    photos.append(str(photo))
                    if len(photos) >= limit:
                        break
                for photo in full_path.glob("*.png"):
                    photos.append(str(photo))
                    if len(photos) >= limit:
                        break

    random.shuffle(photos)
    return photos[:limit]


# Проверка наличия фото при импорте
if UNIFIED_PRODUCTS_PATH.exists():
    _load_mapping()
    total_photos = sum(1 for _ in UNIFIED_PRODUCTS_PATH.rglob("*.jpg"))
    logger.info(f"Product photos loaded: {total_photos} photos in {UNIFIED_PRODUCTS_PATH}")
else:
    logger.warning(f"Product photos path not found: {UNIFIED_PRODUCTS_PATH}")
