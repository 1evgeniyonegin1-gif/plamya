#!/usr/bin/env python3
"""
Скрипт индексации медиа-библиотеки

Функции:
1. Сканирует unified_products/ и находит все фото
2. Вычисляет file_hash для дедупликации
3. Создаёт записи MediaAsset в БД
4. Парсит full_products_mapping.json
5. Создаёт индекс keywords в media_keyword_index

Использование:
    python scripts/index_media_library.py

Флаги:
    --force      Пересоздать все записи (удалить старые)
    --dry-run    Показать что будет сделано без записи в БД
"""

import asyncio
import json
import hashlib
import logging
import argparse
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

# Добавляем корень проекта в PYTHONPATH
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from content_manager_bot.database.models import MediaAsset, MediaKeywordIndex
from shared.database.base import AsyncSessionLocal, engine, Base

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


class MediaIndexer:
    """Индексатор медиа-библиотеки"""

    def __init__(self, base_path: Path, dry_run: bool = False):
        self.base_path = base_path
        self.mapping_file = base_path / "full_products_mapping.json"
        self.dry_run = dry_run

        # Статистика
        self.stats = {
            "files_scanned": 0,
            "assets_created": 0,
            "assets_updated": 0,
            "keywords_created": 0,
            "duplicates_found": 0,
            "errors": 0
        }

        # Кэш: file_hash -> asset_id (для дедупликации)
        self.hash_to_asset: Dict[str, int] = {}

    def calculate_file_hash(self, file_path: Path) -> str:
        """Вычисляет SHA256 хеш файла"""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(8192):
                sha256.update(chunk)
        return sha256.hexdigest()

    def extract_category_from_path(self, file_path: Path) -> str:
        """
        Извлекает категорию из пути к файлу

        Пример:
        greenflash/lymph_gyan/photos/photo_1.jpg -> greenflash
        omega/omega/photos/photo.jpg -> omega
        """
        parts = file_path.relative_to(self.base_path).parts
        if len(parts) > 0:
            return parts[0]
        return "unknown"

    def extract_product_from_path(self, file_path: Path) -> str:
        """
        Извлекает продукт из пути

        Пример:
        greenflash/lymph_gyan/photos/photo_1.jpg -> lymph_gyan
        nlka/happy_smile/photos/photo.jpg -> happy_smile
        """
        parts = file_path.relative_to(self.base_path).parts
        if len(parts) >= 2:
            return parts[1]
        return parts[0] if len(parts) > 0 else "unknown"

    def scan_photos(self) -> List[Tuple[Path, str, str, str]]:
        """
        Сканирует unified_products/ и находит все фото

        Returns:
            List[(file_path, file_hash, category, product)]
        """
        logger.info(f"Сканирование: {self.base_path}")

        photos = []
        extensions = {".jpg", ".jpeg", ".png", ".webp"}

        for file_path in self.base_path.rglob("*"):
            if file_path.suffix.lower() not in extensions:
                continue

            if file_path.is_file():
                self.stats["files_scanned"] += 1

                try:
                    file_hash = self.calculate_file_hash(file_path)
                    category = self.extract_category_from_path(file_path)
                    product = self.extract_product_from_path(file_path)

                    photos.append((file_path, file_hash, category, product))

                    if self.stats["files_scanned"] % 50 == 0:
                        logger.info(f"  Просканировано: {self.stats['files_scanned']} файлов...")

                except Exception as e:
                    logger.error(f"Ошибка при обработке {file_path}: {e}")
                    self.stats["errors"] += 1

        logger.info(f"✓ Найдено {len(photos)} фотографий")
        return photos

    def load_keywords_mapping(self) -> Dict[str, List[str]]:
        """
        Загружает маппинг keywords -> product_folder

        Returns:
            Dict[product_folder] -> List[keywords]

        Пример:
            {"greenflash/lymph_gyan": ["лимф гьян", "lymph gyan", "детокс"]}
        """
        if not self.mapping_file.exists():
            logger.warning(f"Файл маппинга не найден: {self.mapping_file}")
            return {}

        with open(self.mapping_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Инвертируем маппинг: folder -> [keywords]
        folder_to_keywords: Dict[str, List[str]] = {}

        for keyword, folder in data.get("keywords", {}).items():
            if folder not in folder_to_keywords:
                folder_to_keywords[folder] = []
            folder_to_keywords[folder].append(keyword)

        logger.info(f"✓ Загружено маппингов для {len(folder_to_keywords)} продуктов")
        return folder_to_keywords

    async def create_or_update_asset(
        self,
        session: AsyncSession,
        file_path: Path,
        file_hash: str,
        category: str,
        product: str,
        keywords: List[str]
    ) -> Optional[int]:
        """
        Создаёт или обновляет MediaAsset

        Returns:
            asset_id или None при ошибке
        """
        # Проверка на дубликат по hash
        if file_hash in self.hash_to_asset:
            self.stats["duplicates_found"] += 1
            logger.debug(f"Дубликат (hash): {file_path.name} -> asset_id={self.hash_to_asset[file_hash]}")
            return self.hash_to_asset[file_hash]

        # Проверка в БД
        result = await session.execute(
            select(MediaAsset).where(MediaAsset.file_hash == file_hash)
        )
        existing = result.scalar_one_or_none()

        if existing:
            # Обновляем keywords если нужно
            existing_kw = set(existing.keywords or [])
            new_kw = set(keywords)

            if new_kw - existing_kw:
                existing.keywords = list(existing_kw | new_kw)
                self.stats["assets_updated"] += 1
                logger.debug(f"Обновлён asset {existing.id}: добавлено {len(new_kw - existing_kw)} keywords")

            self.hash_to_asset[file_hash] = existing.id
            return existing.id

        # Создаём новый asset
        if self.dry_run:
            logger.info(f"[DRY-RUN] Создать asset: {file_path.name}, category={category}, keywords={len(keywords)}")
            return None

        asset = MediaAsset(
            asset_type="product",
            file_type="image",
            category=category,
            file_path=str(file_path),
            file_hash=file_hash,
            keywords=keywords,
            nl_products=[product] if product != "unknown" else [],
            description=f"Фото продукта {product}",
            usage_count=0
        )

        session.add(asset)
        await session.flush()  # Получаем ID

        self.hash_to_asset[file_hash] = asset.id
        self.stats["assets_created"] += 1

        logger.debug(f"Создан asset {asset.id}: {file_path.name}")
        return asset.id

    async def create_keyword_index(
        self,
        session: AsyncSession,
        asset_id: int,
        keywords: List[str]
    ):
        """Создаёт записи в media_keyword_index"""
        if self.dry_run:
            return

        for keyword in keywords:
            # Нормализация (lowercase + без спецсимволов)
            import re
            normalized = re.sub(r'[^а-яёa-z0-9 ]', '', keyword.lower()).strip()

            if not normalized:
                continue

            # Проверка существования
            result = await session.execute(
                select(MediaKeywordIndex).where(
                    MediaKeywordIndex.normalized_keyword == normalized,
                    MediaKeywordIndex.asset_id == asset_id
                )
            )

            if result.scalar_one_or_none():
                continue  # Уже есть

            # Создаём индекс
            kw_index = MediaKeywordIndex(
                keyword=keyword,
                normalized_keyword=normalized,
                asset_id=asset_id,
                priority=len(keyword)  # Приоритет = длина keyword (длинные = специфичнее)
            )

            session.add(kw_index)
            self.stats["keywords_created"] += 1

    async def run(self, force: bool = False):
        """
        Запускает индексацию

        Args:
            force: Удалить старые записи перед индексацией
        """
        logger.info("=" * 70)
        logger.info("ИНДЕКСАЦИЯ МЕДИА-БИБЛИОТЕКИ")
        logger.info("=" * 70)

        if self.dry_run:
            logger.warning("⚠ Режим DRY-RUN: изменения в БД НЕ будут сохранены")

        # 1. Сканирование фото
        photos = self.scan_photos()

        # 2. Загрузка маппинга keywords
        folder_to_keywords = self.load_keywords_mapping()

        # 3. Создание/обновление БД
        async with AsyncSessionLocal() as session:
            # Удаление старых записей (если force)
            if force and not self.dry_run:
                logger.warning("⚠ Force mode: удаление старых записей...")
                await session.execute(delete(MediaKeywordIndex))
                await session.execute(delete(MediaAsset).where(MediaAsset.asset_type == "product"))
                await session.commit()
                logger.info("✓ Старые записи удалены")

            # Обработка каждого фото
            for file_path, file_hash, category, product in photos:
                # Определяем ключевые слова для этого продукта
                product_folder = f"{category}/{product}"
                keywords = folder_to_keywords.get(product_folder, [])

                if not keywords:
                    # Попробуем найти по категории
                    keywords = folder_to_keywords.get(category, [])

                if not keywords:
                    # Fallback: используем название продукта
                    keywords = [product.replace("_", " ")]

                # Создаём/обновляем asset
                asset_id = await self.create_or_update_asset(
                    session, file_path, file_hash, category, product, keywords
                )

                # Создаём индекс keywords
                if asset_id:
                    await self.create_keyword_index(session, asset_id, keywords)

                # Периодический commit
                if self.stats["assets_created"] % 50 == 0 and not self.dry_run:
                    await session.commit()
                    logger.info(f"  Checkpoint: {self.stats['assets_created']} assets созданы...")

            # Финальный commit
            if not self.dry_run:
                await session.commit()

        # 4. Вывод статистики
        logger.info("=" * 70)
        logger.info("✓ ИНДЕКСАЦИЯ ЗАВЕРШЕНА")
        logger.info("=" * 70)
        logger.info(f"  Файлов просканировано: {self.stats['files_scanned']}")
        logger.info(f"  Assets создано: {self.stats['assets_created']}")
        logger.info(f"  Assets обновлено: {self.stats['assets_updated']}")
        logger.info(f"  Keywords создано: {self.stats['keywords_created']}")
        logger.info(f"  Дубликатов найдено: {self.stats['duplicates_found']}")
        logger.info(f"  Ошибок: {self.stats['errors']}")
        logger.info("=" * 70)


async def main():
    parser = argparse.ArgumentParser(description="Индексация медиа-библиотеки")
    parser.add_argument("--force", action="store_true", help="Удалить старые записи")
    parser.add_argument("--dry-run", action="store_true", help="Не записывать в БД")
    args = parser.parse_args()

    # Путь к unified_products
    base_path = Path(__file__).parent.parent / "content" / "unified_products"

    if not base_path.exists():
        logger.error(f"❌ Папка не найдена: {base_path}")
        return

    # Создание таблиц если нужно
    if not args.dry_run:
        logger.info("Проверка/создание таблиц БД...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✓ Таблицы готовы")

    # Запуск индексации
    indexer = MediaIndexer(base_path, dry_run=args.dry_run)
    await indexer.run(force=args.force)


if __name__ == "__main__":
    asyncio.run(main())
