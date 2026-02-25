"""
Vector Store с использованием PostgreSQL + pgvector.
Хранит документы и их embeddings для семантического поиска.

Поддержка датирования документов:
- date_updated в metadata для определения актуальности
- expires для автоматической фильтрации устаревших документов
- Приоритизация свежих документов при поиске
"""

from datetime import datetime, date
from typing import List, Optional, Tuple
from dataclasses import dataclass, field

from sqlalchemy import Column, Integer, String, Text, DateTime, func, text, Index
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from pgvector.sqlalchemy import Vector

from shared.database.base import Base, AsyncSessionLocal, engine
from shared.utils.logger import get_logger
from .embeddings import get_embedding_service, EmbeddingService

logger = get_logger(__name__)


@dataclass
class SearchResult:
    """Результат поиска в базе знаний."""
    id: int
    content: str
    source: str
    category: str
    similarity: float
    metadata: dict
    # Дата актуальности контента (из metadata)
    date_updated: Optional[date] = None
    # Флаг истечения срока
    is_expired: bool = False

    @property
    def freshness_info(self) -> str:
        """Информация о свежести документа."""
        if self.is_expired:
            return "⚠️ УСТАРЕЛ"
        if self.date_updated:
            days_ago = (date.today() - self.date_updated).days
            if days_ago == 0:
                return "Сегодня"
            elif days_ago == 1:
                return "Вчера"
            elif days_ago < 7:
                return f"{days_ago} дн. назад"
            elif days_ago < 30:
                return f"{days_ago // 7} нед. назад"
            elif days_ago < 365:
                return f"{days_ago // 30} мес. назад"
            else:
                return f"{days_ago // 365} г. назад"
        return "Дата неизвестна"


class Document(Base):
    """Модель документа в базе знаний."""
    __tablename__ = "knowledge_documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    content = Column(Text, nullable=False)
    source = Column(String(500), nullable=True)  # Источник: файл, URL и т.д.
    category = Column(String(100), nullable=True)  # Категория: продукты, бизнес-план и т.д.
    chunk_index = Column(Integer, default=0)  # Индекс чанка если документ разбит
    embedding = Column(Vector(384), nullable=True)  # 384 = размерность MiniLM
    extra_data = Column(JSONB, default={})  # Дополнительные данные (metadata зарезервировано)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Индекс для быстрого поиска по категории
    __table_args__ = (
        Index("idx_documents_category", "category"),
        Index("idx_documents_source", "source"),
    )


class VectorStore:
    """
    Хранилище векторов с поддержкой семантического поиска.
    """

    def __init__(self, embedding_service: EmbeddingService = None):
        self.embedding_service = embedding_service or get_embedding_service()
        self._pgvector_enabled = None

    async def ensure_pgvector(self) -> bool:
        """
        Проверить и включить расширение pgvector.
        Возвращает True если pgvector доступен.
        """
        if self._pgvector_enabled is not None:
            return self._pgvector_enabled

        try:
            async with engine.begin() as conn:
                # Пробуем создать расширение
                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                self._pgvector_enabled = True
                logger.info("pgvector расширение включено")
        except Exception as e:
            logger.warning(f"pgvector недоступен: {e}")
            logger.warning("Будет использоваться поиск без векторов (медленнее)")
            self._pgvector_enabled = False

        return self._pgvector_enabled

    async def init_tables(self):
        """Создать таблицы для хранения документов."""
        await self.ensure_pgvector()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Таблицы для RAG созданы")

    async def add_document(
        self,
        content: str,
        source: str = None,
        category: str = None,
        chunk_index: int = 0,
        metadata: dict = None
    ) -> int:
        """
        Добавить документ в базу знаний.

        Args:
            content: Текст документа
            source: Источник (файл, URL и т.д.)
            category: Категория документа
            chunk_index: Индекс чанка если разбит
            metadata: Дополнительные данные

        Returns:
            ID созданного документа
        """
        # Получаем embedding
        embedding = await self.embedding_service.aget_embedding(content)

        async with AsyncSessionLocal() as session:
            doc = Document(
                content=content,
                source=source,
                category=category,
                chunk_index=chunk_index,
                embedding=embedding,
                extra_data=metadata or {}
            )
            session.add(doc)
            await session.commit()
            await session.refresh(doc)
            logger.debug(f"Документ добавлен: id={doc.id}, source={source}")
            return doc.id

    async def add_documents(
        self,
        documents: List[dict],
        batch_size: int = 32
    ) -> List[int]:
        """
        Добавить несколько документов пакетом.

        Args:
            documents: Список словарей с ключами: content, source, category, metadata
            batch_size: Размер пакета для embeddings

        Returns:
            Список ID созданных документов
        """
        if not documents:
            return []

        # Получаем embeddings пакетом
        contents = [doc["content"] for doc in documents]
        embeddings = await self.embedding_service.aget_embeddings(contents, batch_size)

        doc_ids = []
        async with AsyncSessionLocal() as session:
            for i, doc_data in enumerate(documents):
                doc = Document(
                    content=doc_data["content"],
                    source=doc_data.get("source"),
                    category=doc_data.get("category"),
                    chunk_index=doc_data.get("chunk_index", 0),
                    embedding=embeddings[i],
                    extra_data=doc_data.get("metadata", {})
                )
                session.add(doc)
                doc_ids.append(doc)

            await session.commit()
            for doc in doc_ids:
                await session.refresh(doc)

            result_ids = [doc.id for doc in doc_ids]
            logger.info(f"Добавлено {len(result_ids)} документов")
            return result_ids

    def _parse_date_from_metadata(self, metadata: dict, key: str) -> Optional[date]:
        """Извлечь дату из metadata."""
        if not metadata:
            return None
        value = metadata.get(key)
        if value is None:
            return None
        if isinstance(value, date):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value).date()
            except ValueError:
                return None
        return None

    async def search(
        self,
        query: str,
        top_k: int = 5,
        category: str = None,
        min_similarity: float = 0.4,  # Повышено с 0.3 для лучшей релевантности (2026-01-26)
        exclude_expired: bool = True,
        prefer_recent: bool = True,
        max_age_days: Optional[int] = None
    ) -> List[SearchResult]:
        """
        Семантический поиск по базе знаний с учётом актуальности.

        Args:
            query: Поисковый запрос
            top_k: Количество результатов
            category: Фильтр по категории
            min_similarity: Минимальный порог схожести (0-1)
            exclude_expired: Исключить документы с истекшим сроком
            prefer_recent: Приоритизировать свежие документы
            max_age_days: Максимальный возраст документа в днях (None = без ограничений)

        Returns:
            Список результатов поиска
        """
        # Получаем embedding запроса
        query_embedding = await self.embedding_service.aget_embedding(query)
        today = date.today()

        async with AsyncSessionLocal() as session:
            # Используем косинусное расстояние pgvector
            # 1 - distance = similarity (чем ближе к 1, тем более похоже)
            distance_expr = Document.embedding.cosine_distance(query_embedding)

            query_stmt = (
                select(
                    Document.id,
                    Document.content,
                    Document.source,
                    Document.category,
                    Document.extra_data,
                    (1 - distance_expr).label("similarity")
                )
                .where(Document.embedding.isnot(None))
                .order_by(distance_expr)
                .limit(top_k * 3)  # Берем больше для фильтрации по дате
            )

            if category:
                query_stmt = query_stmt.where(Document.category == category)

            result = await session.execute(query_stmt)
            rows = result.fetchall()

            results = []
            for row in rows:
                similarity = float(row.similarity)
                if similarity < min_similarity:
                    continue

                metadata = row.extra_data or {}

                # Извлекаем даты из metadata
                date_updated = self._parse_date_from_metadata(metadata, 'date_updated')
                expires = self._parse_date_from_metadata(metadata, 'expires')

                # Проверяем истечение срока
                is_expired = expires is not None and expires < today
                if exclude_expired and is_expired:
                    logger.debug(f"Пропускаем истекший документ: {row.source}")
                    continue

                # Проверяем максимальный возраст
                if max_age_days is not None and date_updated:
                    age_days = (today - date_updated).days
                    if age_days > max_age_days:
                        logger.debug(f"Пропускаем старый документ ({age_days} дн.): {row.source}")
                        continue

                results.append(SearchResult(
                    id=row.id,
                    content=row.content,
                    source=row.source,
                    category=row.category,
                    similarity=similarity,
                    metadata=metadata,
                    date_updated=date_updated,
                    is_expired=is_expired
                ))

            # Приоритизируем свежие документы (если включено)
            if prefer_recent and len(results) > 1:
                # Комбинируем similarity и freshness
                def combined_score(r: SearchResult) -> float:
                    base_score = r.similarity
                    if r.date_updated:
                        days_old = (today - r.date_updated).days
                        # Бонус за свежесть: до +0.1 для документов < 30 дней
                        freshness_bonus = max(0, 0.1 * (1 - days_old / 365))
                        return base_score + freshness_bonus
                    return base_score

                results.sort(key=combined_score, reverse=True)

            return results[:top_k]

    async def get_document(self, doc_id: int) -> Optional[Document]:
        """Получить документ по ID."""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Document).where(Document.id == doc_id)
            )
            return result.scalar_one_or_none()

    async def delete_document(self, doc_id: int) -> bool:
        """Удалить документ по ID."""
        async with AsyncSessionLocal() as session:
            doc = await session.get(Document, doc_id)
            if doc:
                await session.delete(doc)
                await session.commit()
                return True
            return False

    async def delete_by_source(self, source: str) -> int:
        """Удалить все документы из указанного источника."""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Document).where(Document.source == source)
            )
            docs = result.scalars().all()
            count = len(docs)
            for doc in docs:
                await session.delete(doc)
            await session.commit()
            logger.info(f"Удалено {count} документов из источника: {source}")
            return count

    async def get_stats(self) -> dict:
        """Получить статистику базы знаний."""
        async with AsyncSessionLocal() as session:
            # Общее количество документов
            total = await session.execute(select(func.count(Document.id)))
            total_count = total.scalar()

            # По категориям
            categories = await session.execute(
                select(Document.category, func.count(Document.id))
                .group_by(Document.category)
            )
            category_counts = {row[0] or "Без категории": row[1] for row in categories.fetchall()}

            # По источникам
            sources = await session.execute(
                select(Document.source, func.count(Document.id))
                .group_by(Document.source)
            )
            source_counts = {row[0] or "Неизвестно": row[1] for row in sources.fetchall()}

            return {
                "total_documents": total_count,
                "by_category": category_counts,
                "by_source": source_counts,
                "embedding_dimension": self.embedding_service.embedding_dimension
            }


# Глобальный экземпляр
_vector_store: Optional[VectorStore] = None


async def get_vector_store() -> VectorStore:
    """Получить глобальный экземпляр VectorStore."""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
        await _vector_store.init_tables()
    return _vector_store
