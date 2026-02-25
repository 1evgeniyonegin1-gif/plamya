"""
Тесты для RAG системы
"""
import pytest
from curator_bot.database.models import KnowledgeBaseChunk


class TestKnowledgeBaseChunk:
    """Тесты для модели KnowledgeBaseChunk"""
    
    @pytest.mark.asyncio
    async def test_create_chunk(self, test_session):
        """Тест создания фрагмента базы знаний"""
        chunk = KnowledgeBaseChunk(
            source_file="energy_diet.md",
            chunk_text="Energy Diet - это функциональное питание",
            category="products",
            meta_data={"product": "Energy Diet", "section": "description"}
        )
        test_session.add(chunk)
        await test_session.commit()
        
        assert chunk.id is not None
        assert chunk.source_file == "energy_diet.md"
        assert chunk.category == "products"
    
    @pytest.mark.asyncio
    async def test_chunk_with_embedding(self, test_session, mock_ai_client):
        """Тест создания фрагмента с векторным представлением"""
        # Генерируем embedding
        text = "Коллаген NL - это продукт для красоты и здоровья"
        embedding = await mock_ai_client.generate_embedding(text)
        
        chunk = KnowledgeBaseChunk(
            source_file="collagen.md",
            chunk_text=text,
            category="products",
            embedding=embedding,
            meta_data={"product": "Collagen"}
        )
        test_session.add(chunk)
        await test_session.commit()
        
        assert chunk.embedding is not None
        assert len(chunk.embedding) == 384
        assert all(isinstance(x, float) for x in chunk.embedding)
    
    @pytest.mark.asyncio
    async def test_search_by_category(self, test_session):
        """Тест поиска фрагментов по категории"""
        # Создаём фрагменты разных категорий
        categories = ["products", "business", "faq"]
        for category in categories:
            chunk = KnowledgeBaseChunk(
                source_file=f"{category}.md",
                chunk_text=f"Текст о {category}",
                category=category
            )
            test_session.add(chunk)
        
        await test_session.commit()
        
        # Ищем только продукты
        from sqlalchemy import select
        result = await test_session.execute(
            select(KnowledgeBaseChunk).where(KnowledgeBaseChunk.category == "products")
        )
        products = result.scalars().all()
        
        assert len(products) == 1
        assert products[0].category == "products"


class TestRAGSearch:
    """Тесты для поиска в RAG системе"""
    
    @pytest.mark.asyncio
    async def test_text_search(self, test_session):
        """Тест текстового поиска"""
        # Создаём несколько фрагментов
        chunks_data = [
            ("Energy Diet помогает контролировать вес", "products"),
            ("Коллаген улучшает состояние кожи", "products"),
            ("План вознаграждения NL International", "business"),
        ]
        
        for text, category in chunks_data:
            chunk = KnowledgeBaseChunk(
                source_file=f"{category}.md",
                chunk_text=text,
                category=category
            )
            test_session.add(chunk)
        
        await test_session.commit()
        
        # Простой текстовый поиск (без векторов)
        from sqlalchemy import select
        search_term = "Energy"
        result = await test_session.execute(
            select(KnowledgeBaseChunk).where(
                KnowledgeBaseChunk.chunk_text.contains(search_term)
            )
        )
        found_chunks = result.scalars().all()
        
        assert len(found_chunks) == 1
        assert "Energy Diet" in found_chunks[0].chunk_text
    
    @pytest.mark.asyncio
    async def test_multiple_chunks_from_same_file(self, test_session):
        """Тест создания нескольких фрагментов из одного файла"""
        source_file = "energy_diet.md"
        
        # Создаём несколько фрагментов из одного файла
        for i in range(3):
            chunk = KnowledgeBaseChunk(
                source_file=source_file,
                chunk_text=f"Фрагмент {i} о Energy Diet",
                category="products",
                meta_data={"chunk_number": i}
            )
            test_session.add(chunk)
        
        await test_session.commit()
        
        # Проверяем что все фрагменты созданы
        from sqlalchemy import select
        result = await test_session.execute(
            select(KnowledgeBaseChunk).where(
                KnowledgeBaseChunk.source_file == source_file
            )
        )
        chunks = result.scalars().all()
        
        assert len(chunks) == 3
        assert all(c.source_file == source_file for c in chunks)


class TestEmbeddingOperations:
    """Тесты для операций с векторными представлениями"""
    
    @pytest.mark.asyncio
    async def test_update_embedding(self, test_session, test_knowledge_chunk, mock_ai_client):
        """Тест обновления embedding"""
        # Генерируем новый embedding
        new_embedding = await mock_ai_client.generate_embedding(test_knowledge_chunk.chunk_text)
        
        # Обновляем
        test_knowledge_chunk.embedding = new_embedding
        await test_session.commit()
        
        # Проверяем
        from sqlalchemy import select
        result = await test_session.execute(
            select(KnowledgeBaseChunk).where(
                KnowledgeBaseChunk.id == test_knowledge_chunk.id
            )
        )
        updated_chunk = result.scalar_one()
        
        assert updated_chunk.embedding is not None
        assert len(updated_chunk.embedding) == 384
    
    @pytest.mark.asyncio
    async def test_chunk_without_embedding(self, test_session):
        """Тест создания фрагмента без embedding (nullable=True)"""
        chunk = KnowledgeBaseChunk(
            source_file="test.md",
            chunk_text="Тестовый текст без embedding",
            category="test",
            embedding=None  # Явно указываем None
        )
        test_session.add(chunk)
        await test_session.commit()
        
        assert chunk.id is not None
        assert chunk.embedding is None
