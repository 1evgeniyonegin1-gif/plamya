"""
Сервис для создания embeddings с использованием Sentence Transformers.
Полностью бесплатный, работает локально.
"""

import asyncio
from typing import List, Optional
from functools import lru_cache

from sentence_transformers import SentenceTransformer

from shared.utils.logger import get_logger

logger = get_logger(__name__)


class EmbeddingService:
    """
    Сервис для создания векторных представлений текста.
    Использует многоязычную модель, которая хорошо работает с русским языком.
    """

    # Рекомендуемые модели для русского языка:
    # - "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2" (~420MB, быстрая)
    # - "sentence-transformers/distiluse-base-multilingual-cased-v2" (~540MB, лучше качество)
    # - "intfloat/multilingual-e5-base" (~1.1GB, топ качество)

    DEFAULT_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

    _instance: Optional["EmbeddingService"] = None
    _model: Optional[SentenceTransformer] = None

    def __new__(cls, model_name: str = None):
        """Singleton pattern для переиспользования загруженной модели."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, model_name: str = None):
        if self._initialized:
            return

        self.model_name = model_name or self.DEFAULT_MODEL
        self._initialized = True
        logger.info(f"EmbeddingService инициализирован с моделью: {self.model_name}")

    def _load_model(self) -> SentenceTransformer:
        """Ленивая загрузка модели при первом использовании."""
        if self._model is None:
            logger.info(f"Загрузка модели {self.model_name}...")
            self._model = SentenceTransformer(self.model_name)
            logger.info("Модель загружена успешно!")
        return self._model

    def get_embedding(self, text: str) -> List[float]:
        """
        Получить embedding для одного текста.

        Args:
            text: Текст для векторизации

        Returns:
            Вектор embedding как список float
        """
        model = self._load_model()
        embedding = model.encode(text, convert_to_numpy=True)
        return embedding.tolist()

    def get_embeddings(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """
        Получить embeddings для списка текстов (пакетная обработка).

        Args:
            texts: Список текстов
            batch_size: Размер пакета для обработки

        Returns:
            Список векторов embeddings
        """
        model = self._load_model()
        embeddings = model.encode(texts, batch_size=batch_size, convert_to_numpy=True)
        return [emb.tolist() for emb in embeddings]

    async def aget_embedding(self, text: str) -> List[float]:
        """Асинхронная версия get_embedding."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.get_embedding, text)

    async def aget_embeddings(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """Асинхронная версия get_embeddings."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: self.get_embeddings(texts, batch_size))

    @property
    def embedding_dimension(self) -> int:
        """Размерность вектора embedding (зависит от модели)."""
        model = self._load_model()
        return model.get_sentence_embedding_dimension()

    def is_loaded(self) -> bool:
        """Проверить, загружена ли модель."""
        return self._model is not None


# Глобальный экземпляр для удобства использования
_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service(model_name: str = None) -> EmbeddingService:
    """Получить глобальный экземпляр EmbeddingService."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService(model_name)
    return _embedding_service
