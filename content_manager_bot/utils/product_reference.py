"""
Утилиты для работы с референсными изображениями продуктов
"""
import os
import json
import base64
from typing import Optional, Dict, Any, Tuple
from pathlib import Path
from loguru import logger


class ProductReferenceManager:
    """Менеджер для работы с референсными изображениями продуктов"""

    def __init__(self, base_path: Optional[str] = None):
        """
        Инициализация менеджера

        Args:
            base_path: Базовый путь к папке с изображениями продуктов
        """
        # Определяем путь относительно корня проекта
        project_root = Path(__file__).parent.parent.parent

        if base_path is None:
            # Используем unified_products для реальных фото
            base_path = project_root / "content" / "unified_products"

        self.base_path = Path(base_path)
        # Новый маппинг в unified_products с keywords
        self.mapping_file = project_root / "content" / "unified_products" / "full_products_mapping.json"
        self._mapping: Optional[Dict[str, Any]] = None
        self._photo_cache: Dict[str, str] = {}  # Кэш найденных фото

    def load_mapping(self) -> Dict[str, Any]:
        """
        Загружает маппинг продуктов из JSON файла

        Returns:
            Dict: Словарь с информацией о продуктах
        """
        if self._mapping is not None:
            return self._mapping

        if not self.mapping_file.exists():
            logger.warning(f"Product mapping file not found: {self.mapping_file}")
            return {}

        try:
            with open(self.mapping_file, 'r', encoding='utf-8') as f:
                self._mapping = json.load(f)
                logger.info(f"Loaded product mapping: {len(self._mapping)} categories")
                return self._mapping
        except Exception as e:
            logger.error(f"Error loading product mapping: {e}")
            return {}

    def get_product_info(self, product_key: str, category: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Получает информацию о продукте

        Args:
            product_key: Ключ продукта (например, "vision_plus")
            category: Категория (например, "greenflash"). Если None, ищет по всем категориям

        Returns:
            Dict: Информация о продукте или None
        """
        mapping = self.load_mapping()

        if category:
            # Поиск в конкретной категории
            # JSON структура: {"greenflash": {"products": {"omega3": {...}}}}
            if category in mapping:
                cat_data = mapping[category]
                # Если есть вложенность "products", берём её
                products = cat_data.get("products", cat_data)
                if product_key in products:
                    return products[product_key]
        else:
            # Поиск по всем категориям
            for cat_name, cat_data in mapping.items():
                # Если есть вложенность "products", берём её
                products = cat_data.get("products", cat_data) if isinstance(cat_data, dict) else {}
                if product_key in products:
                    return products[product_key]

        return None

    def get_product_image_base64(self, product_key: str, category: Optional[str] = None) -> Optional[str]:
        """
        Загружает изображение продукта в base64

        Args:
            product_key: Ключ продукта
            category: Категория (опционально)

        Returns:
            str: Base64-encoded изображение или None
        """
        # Проверяем кэш
        cache_key = f"{category}_{product_key}"
        if cache_key in self._photo_cache:
            return self._photo_cache[cache_key]

        product_info = self.get_product_info(product_key, category)
        if not product_info:
            logger.warning(f"Product not found: {product_key} in category {category}")
            return None

        # Ищем фото в unified_products структуре
        image_path = self._find_product_photo(product_key, category)
        if not image_path:
            logger.warning(f"Product image not found for: {product_key}")
            return None

        try:
            with open(image_path, 'rb') as f:
                image_data = f.read()
                image_base64 = base64.b64encode(image_data).decode('utf-8')
                self._photo_cache[cache_key] = image_base64
                logger.info(f"Loaded product image: {product_info['name']} from {image_path}")
                return image_base64
        except Exception as e:
            logger.error(f"Error loading product image: {e}")
            return None

    def _find_product_photo(self, product_key: str, category: Optional[str] = None) -> Optional[Path]:
        """
        Ищет фото продукта в структуре unified_products/

        Структура: unified_products/{brand}/{product}/photos/*.jpg

        Args:
            product_key: Ключ продукта
            category: Категория (бренд)

        Returns:
            Path: Путь к фото или None
        """
        search_paths = []

        if category:
            # Ищем в конкретной категории
            search_paths.append(self.base_path / category / product_key / "photos")
            # Альтернативные написания
            search_paths.append(self.base_path / category.lower() / product_key.lower() / "photos")
            search_paths.append(self.base_path / category / "*" / "photos")

        # Ищем по всем категориям
        for brand_dir in self.base_path.iterdir():
            if brand_dir.is_dir():
                product_dir = brand_dir / product_key / "photos"
                if product_dir.exists():
                    search_paths.insert(0, product_dir)

                # Ищем похожие названия
                for product_dir in brand_dir.iterdir():
                    if product_dir.is_dir() and product_key.lower() in product_dir.name.lower():
                        photos_dir = product_dir / "photos"
                        if photos_dir.exists():
                            search_paths.insert(0, photos_dir)

        # Ищем первое доступное фото
        for search_path in search_paths:
            if not search_path.exists():
                continue

            jpg_files = list(search_path.glob("*.jpg"))
            if jpg_files:
                # Берём первое фото
                return jpg_files[0]

            # Пробуем PNG
            png_files = list(search_path.glob("*.png"))
            if png_files:
                return png_files[0]

        return None

    def get_random_product_photo(self, category: Optional[str] = None) -> Optional[Tuple[str, Path]]:
        """
        Получает случайное фото продукта из unified_products/

        Args:
            category: Категория для фильтрации

        Returns:
            Tuple[str, Path]: (base64, путь к файлу) или None
        """
        import random

        all_photos = []

        search_path = self.base_path / category if category else self.base_path

        if search_path.exists():
            for photo in search_path.rglob("*.jpg"):
                all_photos.append(photo)

        if not all_photos:
            return None

        photo_path = random.choice(all_photos)

        try:
            with open(photo_path, 'rb') as f:
                image_base64 = base64.b64encode(f.read()).decode('utf-8')
                return image_base64, photo_path
        except Exception as e:
            logger.error(f"Error loading random photo: {e}")
            return None

    def find_product_by_name(self, product_name: str) -> Optional[tuple[str, str, Dict[str, Any]]]:
        """
        Ищет продукт по части названия

        Args:
            product_name: Название или часть названия продукта

        Returns:
            tuple: (category, product_key, product_info) или None
        """
        mapping = self.load_mapping()
        product_name_lower = product_name.lower()

        for category, products in mapping.items():
            for product_key, product_info in products.items():
                if (product_name_lower in product_info["name"].lower() or
                    product_name_lower in product_info["description"].lower() or
                    product_name_lower in product_key.lower()):
                    return category, product_key, product_info

        return None

    def list_all_products(self) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """
        Возвращает список всех доступных продуктов

        Returns:
            Dict: Полный маппинг продуктов
        """
        return self.load_mapping()

    def extract_product_from_content(self, content: str) -> Optional[tuple[str, str, Path]]:
        """
        Пытается извлечь упоминание продукта из текста контента
        Использует keywords из full_products_mapping.json

        Args:
            content: Текст поста

        Returns:
            tuple: (keyword, folder_path, photo_path) или None
        """
        mapping = self.load_mapping()
        keywords_map = mapping.get("keywords", {})

        if not keywords_map:
            logger.warning("No keywords found in mapping")
            return None

        content_lower = content.lower()

        # Сортируем по длине ключа (сначала более специфичные)
        sorted_keywords = sorted(keywords_map.keys(), key=len, reverse=True)

        for keyword in sorted_keywords:
            if keyword in content_lower:
                folder_path = keywords_map[keyword]
                # Ищем фото в папке
                photo_path = self._find_photo_in_folder(folder_path)
                if photo_path:
                    logger.info(f"Found product by keyword '{keyword}': {photo_path}")
                    return keyword, folder_path, photo_path
                else:
                    logger.warning(f"Keyword '{keyword}' found but no photo in {folder_path}")

        return None

    def _find_photo_in_folder(self, folder_path: str) -> Optional[Path]:
        """
        Ищет фото в папке unified_products/{folder_path}/photos/

        Args:
            folder_path: Путь относительно unified_products (например "omega/omega")

        Returns:
            Path к первому найденному фото или None
        """
        # Пробуем разные варианты структуры
        search_paths = [
            self.base_path / folder_path / "photos",
            self.base_path / folder_path,
        ]

        for search_path in search_paths:
            if not search_path.exists():
                continue

            # Ищем jpg
            jpg_files = list(search_path.glob("*.jpg"))
            if jpg_files:
                return jpg_files[0]

            # Ищем png
            png_files = list(search_path.glob("*.png"))
            if png_files:
                return png_files[0]

            # Ищем jpeg
            jpeg_files = list(search_path.glob("*.jpeg"))
            if jpeg_files:
                return jpeg_files[0]

        return None

    def generate_image_to_image_prompt(self, product_info: Dict[str, Any], original_prompt: str) -> str:
        """
        Генерирует промпт для image-to-image режима

        Args:
            product_info: Информация о продукте
            original_prompt: Оригинальный промпт

        Returns:
            str: Модифицированный промпт для улучшения фона
        """
        # Для image-to-image мы хотим сохранить продукт, но улучшить фон
        prompt = (
            f"Улучши фон этого изображения продукта {product_info['name']}. "
            f"Сохрани продукт без изменений, но создай профессиональный студийный фон. "
            f"{original_prompt}. "
            f"Продукт должен оставаться в центре внимания, фон - дополнять композицию."
        )

        return prompt
