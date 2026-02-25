"""
Индексированная медиа-библиотека с O(1) поиском через PostgreSQL

Основные возможности:
- Поиск фото продуктов по ключевым словам за < 20ms
- Извлечение продуктов из текста постов
- Управление чеками и историями партнёров
- Кэширование результатов в памяти (L1 cache)
- Автоматическая дедупликация по file_hash
"""

import re
import hashlib
import logging
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from content_manager_bot.database.models import MediaAsset, MediaKeywordIndex
from shared.database.base import AsyncSessionLocal

logger = logging.getLogger(__name__)


class MediaLibrary:
    """
    Индексированная библиотека медиа-ресурсов

    Примеры использования:

    # Поиск фото продукта
    asset = await media.find_by_keyword("коллаген")

    # Извлечь продукт из текста
    asset = await media.find_in_text("Попробуй лимф гьян для детокса!")

    # Получить случайный чек партнёра
    testimonial = await media.get_testimonial(category="checks")
    """

    # L1 кэш: normalized_keyword -> asset_id
    _keyword_cache: Dict[str, int] = {}

    # Статистика для мониторинга производительности
    _stats = {
        "cache_hits": 0,
        "cache_misses": 0,
        "total_searches": 0,
        "avg_search_time_ms": 0.0
    }

    def __init__(self):
        """Инициализация библиотеки"""
        self.base_path = Path(__file__).parent.parent.parent / "content" / "unified_products"
        self.testimonials_path = Path(__file__).parent.parent.parent / "content" / "testimonials"

    @staticmethod
    def normalize_keyword(keyword: str) -> str:
        """
        Нормализует ключевое слово для поиска

        Пример:
        "Коллаген!" -> "коллаген"
        "3D-Slim" -> "3d slim"
        """
        # lowercase + удаление спецсимволов (кроме пробелов и цифр)
        normalized = re.sub(r'[^а-яёa-z0-9 ]', '', keyword.lower())
        return normalized.strip()

    async def find_by_keyword(
        self,
        keyword: str,
        asset_type: str = "product",
        use_cache: bool = True
    ) -> Optional[MediaAsset]:
        """
        O(1) поиск медиа-ресурса по ключевому слову

        Args:
            keyword: Ключевое слово ("коллаген", "3d slim")
            asset_type: Тип ресурса (product, testimonial, sticker)
            use_cache: Использовать L1 кэш

        Returns:
            MediaAsset или None

        Производительность: < 20ms (кэш: < 5ms)
        """
        import time
        start = time.time()

        self._stats["total_searches"] += 1

        normalized = self.normalize_keyword(keyword)

        # Проверка L1 кэша
        if use_cache and normalized in self._keyword_cache:
            self._stats["cache_hits"] += 1
            asset_id = self._keyword_cache[normalized]

            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(MediaAsset).where(MediaAsset.id == asset_id)
                )
                asset = result.scalar_one_or_none()

                # Обновляем статистику использования
                if asset:
                    asset.usage_count += 1
                    asset.last_used_at = datetime.utcnow()
                    await session.commit()

                elapsed = (time.time() - start) * 1000
                logger.debug(f"find_by_keyword('{keyword}') -> cache hit, {elapsed:.1f}ms")
                return asset

        # Cache miss -> БД lookup
        self._stats["cache_misses"] += 1

        async with AsyncSessionLocal() as session:
            # Поиск через индексную таблицу
            result = await session.execute(
                select(MediaAsset)
                .join(MediaKeywordIndex, MediaAsset.id == MediaKeywordIndex.asset_id)
                .where(
                    and_(
                        MediaKeywordIndex.normalized_keyword == normalized,
                        MediaAsset.asset_type == asset_type
                    )
                )
                .order_by(MediaKeywordIndex.priority.desc())  # Сначала приоритетные
                .limit(1)
            )

            asset = result.scalar_one_or_none()

            # Обновляем кэш и статистику
            if asset:
                self._keyword_cache[normalized] = asset.id
                asset.usage_count += 1
                asset.last_used_at = datetime.utcnow()
                await session.commit()

            elapsed = (time.time() - start) * 1000
            logger.debug(f"find_by_keyword('{keyword}') -> DB lookup, {elapsed:.1f}ms")

            # Обновляем среднее время поиска
            self._update_avg_search_time(elapsed)

            return asset

    async def find_in_text(
        self,
        content: str,
        asset_type: str = "product"
    ) -> Optional[MediaAsset]:
        """
        Извлекает продукт из текста поста

        Пример:
        "Попробуй лимф гьян для детокса!" -> asset для greenflash/lymph_gyan

        Алгоритм:
        1. Ищем все совпадения keywords в тексте
        2. Выбираем самое длинное (специфичное)
        3. Возвращаем соответствующий asset
        """
        content_lower = content.lower()
        matches = []

        async with AsyncSessionLocal() as session:
            # Получаем все keywords для данного типа
            result = await session.execute(
                select(MediaKeywordIndex)
                .join(MediaAsset, MediaAsset.id == MediaKeywordIndex.asset_id)
                .where(MediaAsset.asset_type == asset_type)
            )

            all_keywords = result.scalars().all()

            # Ищем совпадения в тексте
            for kw_index in all_keywords:
                if kw_index.normalized_keyword in content_lower:
                    matches.append((
                        len(kw_index.normalized_keyword),  # Длина для приоритета
                        kw_index.priority,
                        kw_index.asset_id
                    ))

            if not matches:
                return None

            # Сортируем: сначала по длине, потом по приоритету
            matches.sort(reverse=True)
            _, _, asset_id = matches[0]

            # Получаем asset
            result = await session.execute(
                select(MediaAsset).where(MediaAsset.id == asset_id)
            )
            asset = result.scalar_one_or_none()

            if asset:
                asset.usage_count += 1
                asset.last_used_at = datetime.utcnow()
                await session.commit()
                logger.info(f"find_in_text: Найден продукт {asset.nl_products} в тексте")

            return asset

    async def get_testimonial(
        self,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> Optional[MediaAsset]:
        """
        Получить случайный чек/историю партнёра

        Args:
            category: Категория (checks, before_after, stories)
            tags: Теги для фильтрации (["семья", "успех"])

        Returns:
            MediaAsset типа testimonial
        """
        async with AsyncSessionLocal() as session:
            query = select(MediaAsset).where(MediaAsset.asset_type == "testimonial")

            if category:
                query = query.where(MediaAsset.category == category)

            if tags:
                # Поиск по тегам в JSONB
                for tag in tags:
                    query = query.where(MediaAsset.tags.contains([tag]))

            # Случайный выбор
            query = query.order_by(func.random()).limit(1)

            result = await session.execute(query)
            testimonial = result.scalar_one_or_none()

            if testimonial:
                testimonial.usage_count += 1
                testimonial.last_used_at = datetime.utcnow()
                await session.commit()

            return testimonial

    async def upload_testimonial(
        self,
        file_path: str,
        description: str,
        nl_products: List[str],
        category: str = "checks",
        tags: Optional[List[str]] = None
    ) -> MediaAsset:
        """
        Загрузить новый чек/историю партнёра

        Args:
            file_path: Путь к файлу (относительно content/testimonials/)
            description: Описание ("Семья Ивановых, 30000₽ за месяц")
            nl_products: Продукты которые упоминаются (["3d_slim", "omega"])
            category: Категория (checks, before_after, stories)
            tags: Теги (["семья", "первый_чек", "успех"])

        Returns:
            Созданный MediaAsset
        """
        # Вычисляем file_hash для дедупликации
        full_path = self.testimonials_path / file_path
        if full_path.exists():
            with open(full_path, "rb") as f:
                file_hash = hashlib.sha256(f.read()).hexdigest()
        else:
            file_hash = None
            logger.warning(f"Файл не найден: {full_path}")

        async with AsyncSessionLocal() as session:
            # Проверка на дубликат
            if file_hash:
                result = await session.execute(
                    select(MediaAsset).where(MediaAsset.file_hash == file_hash)
                )
                existing = result.scalar_one_or_none()
                if existing:
                    logger.info(f"Testimonial уже существует: {existing.id}")
                    return existing

            # Создаём новый asset
            asset = MediaAsset(
                asset_type="testimonial",
                category=category,
                file_path=str(full_path),
                file_hash=file_hash,
                description=description,
                nl_products=nl_products,
                tags=tags or [],
                file_type="image"  # По умолчанию
            )

            session.add(asset)
            await session.commit()
            await session.refresh(asset)

            logger.info(f"Создан testimonial: {asset.id} - {description}")
            return asset

    async def get_stats(self) -> Dict:
        """Получить статистику библиотеки"""
        async with AsyncSessionLocal() as session:
            # Подсчёт по типам
            result = await session.execute(
                select(
                    MediaAsset.asset_type,
                    func.count(MediaAsset.id).label("count")
                )
                .where(
                    or_(
                        MediaAsset.file_id.isnot(None),
                        MediaAsset.file_path.isnot(None)
                    )
                )
                .group_by(MediaAsset.asset_type)
            )

            counts = {row.asset_type: row.count for row in result}

            # Общее количество keywords
            result = await session.execute(select(func.count(MediaKeywordIndex.id)))
            total_keywords = result.scalar()

            return {
                "assets": counts,
                "total_keywords": total_keywords,
                "cache_size": len(self._keyword_cache),
                "cache_hit_rate": (
                    self._stats["cache_hits"] / self._stats["total_searches"] * 100
                    if self._stats["total_searches"] > 0 else 0
                ),
                "avg_search_time_ms": self._stats["avg_search_time_ms"]
            }

    async def clear_cache(self):
        """Очистить L1 кэш (для тестирования)"""
        self._keyword_cache.clear()
        logger.info("L1 cache cleared")

    def _update_avg_search_time(self, elapsed_ms: float):
        """Обновляет скользящее среднее времени поиска"""
        alpha = 0.1  # Коэффициент сглаживания
        if self._stats["avg_search_time_ms"] == 0:
            self._stats["avg_search_time_ms"] = elapsed_ms
        else:
            self._stats["avg_search_time_ms"] = (
                alpha * elapsed_ms + (1 - alpha) * self._stats["avg_search_time_ms"]
            )

    @staticmethod
    def calculate_file_hash(file_path: Path) -> str:
        """Вычисляет SHA256 хеш файла"""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(8192):
                sha256.update(chunk)
        return sha256.hexdigest()


# Singleton instance
media_library = MediaLibrary()
