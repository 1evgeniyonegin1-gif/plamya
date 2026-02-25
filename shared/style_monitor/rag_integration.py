"""
Модуль для интеграции постов из Telegram каналов в RAG базу знаний.

Конвертирует высококачественные посты в документы для семантического поиска.
"""

import re
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.models import StylePost, StyleChannel
from shared.rag.vector_store import Document
from shared.database.base import AsyncSessionLocal
from shared.rag import get_rag_engine

logger = logging.getLogger(__name__)


class RAGIntegrationService:
    """Сервис для конвертации постов каналов в RAG документы"""

    # Маппинг style_category → RAG category
    CATEGORY_MAPPING = {
        "motivation": "motivation",
        "product": "products",
        "business": "business",
        "lifestyle": "success_stories",
        "general": "training",
        "training": "training",
        "news": "news",
        "success_stories": "success_stories",
    }

    # Срок актуальности по категориям (дни)
    EXPIRES_AFTER = {
        "products": 90,          # Продукты меняются редко
        "motivation": 180,       # Мотивация вечна
        "business": 120,         # Бизнес-советы
        "success_stories": 365,  # Истории успеха
        "training": 120,         # Обучающие материалы
        "news": 30,              # Новости быстро устаревают
        "promo": 14,             # Акции кратковременны
    }

    def __init__(self):
        """Инициализация сервиса интеграции"""
        self._rag_engine = None

    async def convert_post_to_document(
        self,
        post: StylePost,
        channel: StyleChannel
    ) -> Dict:
        """
        Конвертировать StylePost в RAG Document.

        Args:
            post: Пост из канала
            channel: Канал, из которого пост

        Returns:
            {
                "content": str,
                "source": str,
                "category": str,
                "metadata": dict
            }
        """
        # Определяем RAG категорию
        rag_category = self.CATEGORY_MAPPING.get(
            channel.style_category or "general",
            "training"
        )

        # Очищаем текст
        content = self._clean_post_text(post.text or "")

        # Определяем срок актуальности
        expires_days = self.EXPIRES_AFTER.get(rag_category, 120)
        expires_date = post.post_date + timedelta(days=expires_days)

        # Формируем metadata
        metadata = {
            "source_channel": channel.title or channel.username,
            "channel_username": channel.username,
            "post_date": post.post_date.isoformat() if post.post_date else None,
            "quality_score": post.quality_score,
            "views_count": post.views_count,
            "reactions_count": post.reactions_count,
            "forwards_count": post.forwards_count,
            "date_created": post.post_date.date().isoformat() if post.post_date else datetime.now().date().isoformat(),
            "date_updated": post.post_date.date().isoformat() if post.post_date else datetime.now().date().isoformat(),
            "expires": expires_date.date().isoformat(),
            "style_tags": post.style_tags or {},
            "from_monitored_channel": True,
            "channel_id": channel.channel_id,
            "message_id": post.message_id,
        }

        return {
            "content": content,
            "source": f"{channel.title or channel.username} (Telegram)",
            "category": rag_category,
            "metadata": metadata
        }

    async def add_post_to_rag(
        self,
        post: StylePost,
        channel: StyleChannel,
        session: Optional[AsyncSession] = None
    ) -> Optional[int]:
        """
        Добавить пост в RAG базу знаний.

        Args:
            post: Пост для добавления
            channel: Канал поста
            session: Опциональная сессия БД

        Returns:
            ID документа или None если уже существует / ошибка
        """
        # Проверка дедупликации
        if post.added_to_rag:
            logger.debug(f"Post {post.id} already marked as added to RAG, skipping")
            return None

        if await self._is_already_in_rag(post, channel, session):
            logger.debug(f"Post {post.id} already in RAG (duplicate check), skipping")

            # Обновляем флаг
            should_close = False
            if session is None:
                session = AsyncSessionLocal()
                should_close = True

            try:
                post.added_to_rag = True
                await session.commit()
            finally:
                if should_close:
                    await session.close()

            return None

        # Конвертируем
        doc_data = await self.convert_post_to_document(post, channel)

        # Получаем RAG engine
        if self._rag_engine is None:
            self._rag_engine = await get_rag_engine()

        # Добавляем в RAG через VectorStore
        try:
            # VectorStore принимает отдельные параметры
            from shared.rag.vector_store import VectorStore
            vector_store = VectorStore()

            doc_id = await vector_store.add_document(
                content=doc_data["content"],
                source=doc_data["source"],
                category=doc_data["category"],
                metadata=doc_data["metadata"]
            )

            # Обновляем пост
            should_close = False
            if session is None:
                session = AsyncSessionLocal()
                should_close = True

            try:
                post.added_to_rag = True
                post.rag_document_id = doc_id
                await session.commit()

                logger.info(
                    f"Added post {post.id} from {channel.title or channel.username} to RAG "
                    f"(category: {doc_data['category']}, score: {post.quality_score}, doc_id: {doc_id})"
                )

                return doc_id

            finally:
                if should_close:
                    await session.close()

        except Exception as e:
            logger.error(f"Error adding post {post.id} to RAG: {e}", exc_info=True)
            return None

    async def _is_already_in_rag(
        self,
        post: StylePost,
        channel: StyleChannel,
        session: Optional[AsyncSession] = None
    ) -> bool:
        """
        Проверить не добавлен ли уже пост в RAG.

        Проверки:
        1. Флаг post.added_to_rag
        2. Поиск по metadata (source_channel + message_id)
        3. Semantic similarity check (≥0.95)
        """
        # 1. Проверяем флаг
        if post.added_to_rag:
            return True

        # 2. Проверяем по metadata в БД
        should_close = False
        if session is None:
            session = AsyncSessionLocal()
            should_close = True

        try:
            # Ищем документ с таким же channel_id и message_id
            result = await session.execute(
                select(Document)
                .where(
                    Document.extra_data["channel_id"].astext == str(channel.channel_id),
                    Document.extra_data["message_id"].astext == str(post.message_id)
                )
            )
            existing_doc = result.scalar_one_or_none()

            if existing_doc:
                logger.debug(f"Found existing document {existing_doc.id} for post {post.id}")
                return True

            # 3. Semantic similarity check (опционально, для надёжности)
            # Пропускаем для производительности, т.к. проверка по metadata достаточна

            return False

        finally:
            if should_close:
                await session.close()

    def _clean_post_text(self, text: str) -> str:
        """
        Очистить текст поста для RAG.

        Удаляет:
        - HTTP ссылки
        - @username упоминания
        - Множественные переносы строк
        """
        # Убираем HTTP ссылки
        text = re.sub(r'https?://\S+', '', text)

        # Убираем @username упоминания
        text = re.sub(r'@\w+', '', text)

        # Убираем множественные переносы (оставляем двойные для абзацев)
        text = re.sub(r'\n{3,}', '\n\n', text)

        # Убираем пробелы в начале и конце
        text = text.strip()

        return text

    async def sync_posts_to_rag(
        self,
        channel_id: Optional[int] = None,
        min_quality_score: float = 7.0,
        limit: int = 100
    ) -> Dict[str, int]:
        """
        Синхронизировать посты в RAG.

        Args:
            channel_id: ID канала (None = все каналы)
            min_quality_score: Минимальная оценка качества
            limit: Максимум постов за раз

        Returns:
            {"added": count, "skipped": count, "errors": count}
        """
        stats = {"added": 0, "skipped": 0, "errors": 0}

        async with AsyncSessionLocal() as session:
            # Запрос на посты для синхронизации
            query = (
                select(StylePost, StyleChannel)
                .join(StyleChannel, StylePost.channel_id == StyleChannel.id)
                .where(
                    StylePost.quality_score >= min_quality_score,
                    StylePost.added_to_rag == False,
                    StylePost.is_analyzed == True
                )
            )

            if channel_id:
                query = query.where(StyleChannel.id == channel_id)

            query = query.limit(limit)

            result = await session.execute(query)
            posts_with_channels = result.all()

            logger.info(f"Found {len(posts_with_channels)} posts to sync to RAG")

            # Синхронизируем каждый пост
            for post, channel in posts_with_channels:
                doc_id = await self.add_post_to_rag(post, channel, session)

                if doc_id:
                    stats["added"] += 1
                elif post.added_to_rag:
                    stats["skipped"] += 1
                else:
                    stats["errors"] += 1

        logger.info(
            f"RAG sync completed: {stats['added']} added, "
            f"{stats['skipped']} skipped, {stats['errors']} errors"
        )

        return stats

    async def remove_expired_documents(self) -> int:
        """
        Удалить истёкшие документы из RAG.

        Returns:
            Количество удалённых документов
        """
        from shared.rag.vector_store import VectorStore
        vector_store = VectorStore()

        # VectorStore должен иметь метод для удаления истёкших
        # Это обычно делается через SQL запрос к knowledge_documents
        async with AsyncSessionLocal() as session:
            # Находим истёкшие документы из мониторинга каналов
            result = await session.execute(
                select(Document)
                .where(
                    Document.extra_data["from_monitored_channel"].astext == "true",
                    Document.extra_data["expires"].astext < datetime.now().date().isoformat()
                )
            )
            expired_docs = result.scalars().all()

            count = 0
            for doc in expired_docs:
                try:
                    await session.delete(doc)
                    count += 1
                except Exception as e:
                    logger.error(f"Error deleting expired document {doc.id}: {e}")

            await session.commit()

            logger.info(f"Removed {count} expired documents from RAG")
            return count


# Singleton instance
_rag_integration_service: Optional[RAGIntegrationService] = None


def get_rag_integration_service() -> RAGIntegrationService:
    """Получить singleton instance RAGIntegrationService"""
    global _rag_integration_service
    if _rag_integration_service is None:
        _rag_integration_service = RAGIntegrationService()
    return _rag_integration_service
