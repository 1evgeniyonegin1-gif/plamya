"""
RAG (Retrieval-Augmented Generation) модуль для NL International AI Bots.
Использует Sentence Transformers для локальных embeddings (бесплатно).
"""

from .embeddings import EmbeddingService, get_embedding_service
from .vector_store import VectorStore, get_vector_store, SearchResult
from .rag_engine import RAGEngine, RAGContext, get_rag_engine

__all__ = [
    "EmbeddingService",
    "get_embedding_service",
    "VectorStore",
    "get_vector_store",
    "SearchResult",
    "RAGEngine",
    "RAGContext",
    "get_rag_engine",
]
