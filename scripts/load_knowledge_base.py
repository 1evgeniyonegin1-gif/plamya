"""
Скрипт для загрузки документов в базу знаний RAG.
Поддерживает .txt, .md, .pdf файлы.

Поддержка YAML frontmatter для датирования документов:
---
date_created: 2025-01-15
date_updated: 2026-01-20
expires: 2026-03-01  # опционально
---
"""

import asyncio
import os
import re
import sys
from datetime import datetime, date
from pathlib import Path
from typing import List, Optional, Dict, Any

import yaml

# Добавляем корневую директорию проекта в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.rag import VectorStore, EmbeddingService
from shared.rag.vector_store import get_vector_store
from shared.utils.logger import get_logger

logger = get_logger(__name__)


class DocumentLoader:
    """Загрузчик документов в базу знаний."""

    # Максимальный размер чанка (в символах)
    # Увеличено с 1000 до 2000 для лучшего контекста (2026-01-26)
    CHUNK_SIZE = 2000
    # Перекрытие между чанками
    # Увеличено с 200 до 300 для лучшей связности (2026-01-26)
    CHUNK_OVERLAP = 300

    # Регулярное выражение для YAML frontmatter
    FRONTMATTER_REGEX = re.compile(r'^---\s*\n(.*?)\n---\s*\n', re.DOTALL)

    def __init__(self, vector_store: VectorStore = None):
        self._vector_store = vector_store

    async def get_vector_store(self) -> VectorStore:
        if self._vector_store is None:
            self._vector_store = await get_vector_store()
        return self._vector_store

    def parse_frontmatter(self, text: str) -> tuple[Dict[str, Any], str]:
        """
        Извлечь YAML frontmatter из текста.

        Args:
            text: Текст документа с возможным frontmatter

        Returns:
            (metadata_dict, content_without_frontmatter)
        """
        match = self.FRONTMATTER_REGEX.match(text)
        if not match:
            return {}, text

        try:
            yaml_content = match.group(1)
            metadata = yaml.safe_load(yaml_content) or {}
            content = text[match.end():]
            return metadata, content
        except yaml.YAMLError as e:
            logger.warning(f"Ошибка парсинга frontmatter: {e}")
            return {}, text

    def parse_date(self, value: Any) -> Optional[date]:
        """Преобразовать значение в дату."""
        if value is None:
            return None
        if isinstance(value, date):
            return value
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, str):
            for fmt in ['%Y-%m-%d', '%d.%m.%Y', '%d/%m/%Y']:
                try:
                    return datetime.strptime(value, fmt).date()
                except ValueError:
                    continue
        return None

    def chunk_text(self, text: str, chunk_size: int = None, overlap: int = None) -> List[str]:
        """
        Разбить текст на чанки с перекрытием.
        Теперь с SEMANTIC CHUNKING — учитывает заголовки ## и Q&A пары.

        Args:
            text: Исходный текст
            chunk_size: Размер чанка
            overlap: Размер перекрытия

        Returns:
            Список чанков
        """
        chunk_size = chunk_size or self.CHUNK_SIZE
        overlap = overlap or self.CHUNK_OVERLAP

        # Чистим текст
        text = text.strip()
        if not text:
            return []

        # === SEMANTIC CHUNKING ===
        # Сначала пробуем разбить по заголовкам ##
        sections = self._split_by_headers(text)

        if len(sections) > 1:
            # Есть секции — обрабатываем каждую отдельно
            chunks = []
            for section_title, section_content in sections:
                section_chunks = self._chunk_section(
                    section_title, section_content, chunk_size
                )
                chunks.extend(section_chunks)
            return chunks

        # === FALLBACK: простое разбиение по параграфам ===
        return self._chunk_by_paragraphs(text, chunk_size)

    def _split_by_headers(self, text: str) -> List[tuple]:
        """
        Разбить текст по заголовкам ## (markdown h2).

        Returns:
            List[(title, content)] — список секций
        """
        # Паттерн для заголовков ## или === разделителей
        header_pattern = re.compile(r'^(?:##\s+|={3,}|#{2,}\s*Источник:)', re.MULTILINE)

        parts = header_pattern.split(text)
        headers = header_pattern.findall(text)

        if len(parts) <= 1:
            return [("", text)]

        sections = []
        # Первая часть — до первого заголовка (может быть пустой)
        if parts[0].strip():
            sections.append(("", parts[0].strip()))

        # Остальные части с заголовками
        for i, header in enumerate(headers):
            if i + 1 < len(parts):
                content = parts[i + 1].strip()
                if content:
                    # Извлекаем название из заголовка
                    title = header.replace("##", "").replace("=", "").strip()
                    sections.append((title, content))

        return sections

    def _chunk_section(self, title: str, content: str, chunk_size: int) -> List[str]:
        """
        Разбить секцию на чанки, сохраняя Q&A пары вместе.
        Добавляет контекст заголовка к каждому чанку.
        """
        chunks = []

        # Добавляем контекст заголовка если есть
        title_prefix = f"[{title}]\n\n" if title else ""
        effective_chunk_size = chunk_size - len(title_prefix)

        # Пробуем найти Q&A пары (вопрос + ответ)
        qa_pairs = self._extract_qa_pairs(content)

        if qa_pairs:
            # Есть Q&A структура — группируем вопросы с ответами
            current_chunk = ""
            for qa in qa_pairs:
                qa_text = qa.strip()
                if len(current_chunk) + len(qa_text) + 2 <= effective_chunk_size:
                    if current_chunk:
                        current_chunk += "\n\n" + qa_text
                    else:
                        current_chunk = qa_text
                else:
                    if current_chunk:
                        chunks.append(title_prefix + current_chunk)
                    # Если Q&A слишком большой — всё равно добавляем целиком
                    if len(qa_text) > effective_chunk_size:
                        chunks.append(title_prefix + qa_text[:effective_chunk_size])
                    else:
                        current_chunk = qa_text

            if current_chunk:
                chunks.append(title_prefix + current_chunk)
        else:
            # Нет Q&A — обычное разбиение по параграфам
            para_chunks = self._chunk_by_paragraphs(content, effective_chunk_size)
            for chunk in para_chunks:
                chunks.append(title_prefix + chunk)

        return chunks

    def _extract_qa_pairs(self, text: str) -> List[str]:
        """
        Извлечь пары Вопрос-Ответ из текста.
        Поддерживает форматы:
        - "1. Вопрос? Ответ..."
        - "Вопрос: ... Ответ: ..."
        - "Q: ... A: ..."
        """
        # Паттерн для нумерованных вопросов (1. 2. 3. ...)
        numbered_qa = re.compile(
            r'(\d+\.\s*[^\n]+\?[^0-9]*?)(?=\d+\.\s|\Z)',
            re.DOTALL
        )

        pairs = numbered_qa.findall(text)
        if pairs and len(pairs) > 2:  # Минимум 3 Q&A для уверенности
            return [p.strip() for p in pairs if p.strip()]

        # Паттерн для "Вопрос:" / "Ответ:" формата
        qa_labeled = re.compile(
            r'((?:Вопрос|Q|В)\s*[:\-]?\s*[^\n]+.*?)(?=(?:Вопрос|Q|В)\s*[:\-]|\Z)',
            re.DOTALL | re.IGNORECASE
        )

        pairs = qa_labeled.findall(text)
        if pairs and len(pairs) > 2:
            return [p.strip() for p in pairs if p.strip()]

        return []

    def _chunk_by_paragraphs(self, text: str, chunk_size: int) -> List[str]:
        """Fallback: простое разбиение по параграфам."""
        paragraphs = re.split(r'\n\n+', text)

        chunks = []
        current_chunk = ""

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            if len(current_chunk) + len(para) + 2 <= chunk_size:
                if current_chunk:
                    current_chunk += "\n\n" + para
                else:
                    current_chunk = para
            else:
                if current_chunk:
                    chunks.append(current_chunk)

                if len(para) > chunk_size:
                    sentences = re.split(r'(?<=[.!?])\s+', para)
                    current_chunk = ""
                    for sent in sentences:
                        if len(current_chunk) + len(sent) + 1 <= chunk_size:
                            if current_chunk:
                                current_chunk += " " + sent
                            else:
                                current_chunk = sent
                        else:
                            if current_chunk:
                                chunks.append(current_chunk)
                            current_chunk = sent
                else:
                    current_chunk = para

        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    def read_text_file(self, file_path: Path) -> str:
        """Прочитать текстовый файл."""
        encodings = ['utf-8', 'cp1251', 'latin-1']
        for encoding in encodings:
            try:
                return file_path.read_text(encoding=encoding)
            except UnicodeDecodeError:
                continue
        raise ValueError(f"Не удалось прочитать файл: {file_path}")

    def read_markdown(self, file_path: Path) -> tuple[str, Dict[str, Any]]:
        """
        Прочитать Markdown файл (убираем разметку).

        Returns:
            (text, frontmatter_metadata)
        """
        raw_text = self.read_text_file(file_path)

        # Извлекаем frontmatter
        frontmatter, text = self.parse_frontmatter(raw_text)

        # Убираем заголовки markdown
        text = re.sub(r'^#+\s*', '', text, flags=re.MULTILINE)
        # Убираем ссылки [text](url) -> text
        text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
        # Убираем жирный/курсив
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
        text = re.sub(r'\*([^*]+)\*', r'\1', text)
        text = re.sub(r'__([^_]+)__', r'\1', text)
        text = re.sub(r'_([^_]+)_', r'\1', text)
        # Убираем код блоки
        text = re.sub(r'```[^`]*```', '', text)
        text = re.sub(r'`([^`]+)`', r'\1', text)
        return text, frontmatter

    async def load_file(
        self,
        file_path: Path,
        category: str = None,
        metadata: dict = None
    ) -> int:
        """
        Загрузить один файл в базу знаний.

        Args:
            file_path: Путь к файлу
            category: Категория документа
            metadata: Дополнительные данные

        Returns:
            Количество добавленных чанков
        """
        file_path = Path(file_path)
        if not file_path.exists():
            logger.error(f"Файл не найден: {file_path}")
            return 0

        # Определяем тип файла
        suffix = file_path.suffix.lower()
        frontmatter = {}

        if suffix in ['.txt', '.text']:
            raw_text = self.read_text_file(file_path)
            frontmatter, text = self.parse_frontmatter(raw_text)
        elif suffix in ['.md', '.markdown']:
            text, frontmatter = self.read_markdown(file_path)
        else:
            logger.warning(f"Неподдерживаемый формат: {suffix}")
            return 0

        if not text.strip():
            logger.warning(f"Пустой файл: {file_path}")
            return 0

        # Извлекаем даты из frontmatter
        date_created = self.parse_date(frontmatter.get('date_created'))
        date_updated = self.parse_date(frontmatter.get('date_updated'))
        expires = self.parse_date(frontmatter.get('expires'))

        # Проверяем истёк ли документ
        today = date.today()
        if expires and expires < today:
            logger.warning(f"Документ истёк ({expires}): {file_path.name}")
            # Можно пропустить или пометить как устаревший
            # return 0  # Раскомментировать чтобы пропускать

        # Разбиваем на чанки
        chunks = self.chunk_text(text)

        if not chunks:
            logger.warning(f"Нет чанков для файла: {file_path}")
            return 0

        # Готовим документы для загрузки
        documents = []
        for i, chunk in enumerate(chunks):
            doc = {
                "content": chunk,
                "source": file_path.name,
                "category": category,
                "chunk_index": i,
                "metadata": {
                    **(metadata or {}),
                    "file_path": str(file_path),
                    "total_chunks": len(chunks),
                    # Даты из frontmatter
                    "date_created": date_created.isoformat() if date_created else None,
                    "date_updated": date_updated.isoformat() if date_updated else None,
                    "expires": expires.isoformat() if expires else None,
                    # Дополнительные метаданные из frontmatter
                    **{k: v for k, v in frontmatter.items()
                       if k not in ['date_created', 'date_updated', 'expires']}
                }
            }
            documents.append(doc)

        # Загружаем в базу
        store = await self.get_vector_store()
        await store.add_documents(documents)

        date_info = f" [updated: {date_updated}]" if date_updated else ""
        logger.info(f"Загружено {len(chunks)} чанков из {file_path.name}{date_info}")
        return len(chunks)

    async def load_directory(
        self,
        dir_path: Path,
        category: str = None,
        recursive: bool = True
    ) -> dict:
        """
        Загрузить все документы из директории.

        Args:
            dir_path: Путь к директории
            category: Категория по умолчанию
            recursive: Рекурсивный обход поддиректорий

        Returns:
            Статистика загрузки
        """
        dir_path = Path(dir_path)
        if not dir_path.is_dir():
            logger.error(f"Директория не найдена: {dir_path}")
            return {"error": "Directory not found"}

        stats = {
            "files_processed": 0,
            "chunks_added": 0,
            "errors": [],
            "files": []
        }

        # Находим все файлы
        patterns = ["*.txt", "*.md", "*.markdown"]
        files = []

        for pattern in patterns:
            if recursive:
                files.extend(dir_path.rglob(pattern))
            else:
                files.extend(dir_path.glob(pattern))

        logger.info(f"Найдено {len(files)} файлов в {dir_path}")

        for file_path in files:
            try:
                # Определяем категорию из имени поддиректории
                file_category = category
                if file_path.parent != dir_path:
                    file_category = file_path.parent.name

                chunks = await self.load_file(file_path, category=file_category)
                stats["files_processed"] += 1
                stats["chunks_added"] += chunks
                stats["files"].append({
                    "file": file_path.name,
                    "chunks": chunks,
                    "category": file_category
                })
            except Exception as e:
                logger.error(f"Ошибка при загрузке {file_path}: {e}")
                stats["errors"].append(str(file_path))

        return stats


async def main(clear_existing: bool = False):
    """
    Главная функция для загрузки базы знаний.

    Args:
        clear_existing: Очистить существующие документы перед загрузкой
    """
    print("=" * 60)
    print("[RAG] Zagruzka dokumentov v bazu znaniy")
    print("=" * 60)

    # Путь к папке с документами
    project_root = Path(__file__).parent.parent
    knowledge_base_path = project_root / "content" / "knowledge_base"

    if not knowledge_base_path.exists():
        print(f"\n[!] Papka ne naydena: {knowledge_base_path}")
        print("\n[i] Sozdayte papku i dobavte tuda dokumenty:")
        print(f"   {knowledge_base_path}")
        print("\nFormaty: .txt, .md")
        return

    # Проверяем есть ли файлы
    files = list(knowledge_base_path.rglob("*.txt")) + list(knowledge_base_path.rglob("*.md"))

    if not files:
        print(f"\n[!] Papka {knowledge_base_path} pusta!")
        print("\n[i] Dobavte dokumenty v papku")
        print("\nFormaty: .txt, .md")
        return

    # Показываем структуру папок
    print(f"\n[*] Naydeno {len(files)} faylov:")
    categories = {}
    for f in files:
        cat = f.parent.name if f.parent != knowledge_base_path else "root"
        categories[cat] = categories.get(cat, 0) + 1
    for cat, count in sorted(categories.items()):
        print(f"   [{cat}]: {count} faylov")

    # Очистка существующих документов если нужно
    if clear_existing or "--clear" in sys.argv:
        print("\n[*] Ochistka suschestvuyuschih dokumentov...")
        store = await get_vector_store()
        # Удаляем все документы через прямой SQL
        from shared.database.base import AsyncSessionLocal
        from sqlalchemy import text
        async with AsyncSessionLocal() as session:
            await session.execute(text("DELETE FROM knowledge_documents"))
            await session.commit()
        print("   Dokumenty udaleny")

    print("\n[*] Zagruzka dokumentov...")

    # Инициализируем загрузчик
    loader = DocumentLoader()

    # Загружаем все документы
    stats = await loader.load_directory(knowledge_base_path)

    print("\n" + "=" * 60)
    print("[RESULTS]")
    print("=" * 60)
    print(f"  Files processed: {stats['files_processed']}")
    print(f"  Chunks added:    {stats['chunks_added']}")

    if stats['errors']:
        print(f"\n[!] Errors ({len(stats['errors'])}):")
        for err in stats['errors']:
            print(f"   - {err}")

    if stats['files']:
        print("\n[*] Loaded files:")
        for f in stats['files']:
            print(f"   - {f['file']}: {f['chunks']} chunks [{f['category'] or 'no category'}]")

    # Показываем статистику базы
    store = await get_vector_store()
    db_stats = await store.get_stats()

    print("\n" + "=" * 60)
    print("[STATS]")
    print("=" * 60)
    print(f"  Total documents: {db_stats['total_documents']}")
    print(f"  Embedding dim:   {db_stats['embedding_dimension']}")

    if db_stats['by_category']:
        print("\n  By category:")
        for cat, count in db_stats['by_category'].items():
            print(f"    - {cat}: {count}")

    print("\n[OK] Loading complete!")
    print("\n[i] RAG system ready for AI-Curator!")


if __name__ == "__main__":
    if "--help" in sys.argv or "-h" in sys.argv:
        print("""
Скрипт загрузки базы знаний RAG

Использование:
    python scripts/load_knowledge_base.py [опции]

Опции:
    --clear     Очистить существующие документы перед загрузкой
    --help, -h  Показать эту справку

Пример:
    python scripts/load_knowledge_base.py --clear

Требования:
    1. PostgreSQL с расширением pgvector
    2. pip install sentence-transformers pgvector
    3. Настроенные переменные окружения для подключения к БД
        """)
    else:
        asyncio.run(main())
