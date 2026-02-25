-- Migration: 004_channel_monitoring_enhancements.sql
-- Description: Добавляет индексы и поля для системы мониторинга каналов
-- Date: 2026-01-27

-- === ИНДЕКСЫ ДЛЯ БЫСТРОГО ПОИСКА ===

-- Индекс для поиска неанализированных постов по качеству
CREATE INDEX IF NOT EXISTS idx_style_posts_quality_analyzed
ON style_posts(is_analyzed, quality_score);

-- Индекс для поиска постов по каналу и дате (сортировка)
CREATE INDEX IF NOT EXISTS idx_style_posts_channel_date
ON style_posts(channel_id, post_date DESC);

-- === НОВЫЕ ПОЛЯ ДЛЯ ОТСЛЕЖИВАНИЯ RAG СИНХРОНИЗАЦИИ ===

-- Флаг: добавлен ли пост в RAG базу знаний
ALTER TABLE style_posts
ADD COLUMN IF NOT EXISTS added_to_rag BOOLEAN DEFAULT FALSE;

-- ID документа в таблице knowledge_documents
ALTER TABLE style_posts
ADD COLUMN IF NOT EXISTS rag_document_id INTEGER;

-- Индекс для поиска постов для RAG синхронизации
CREATE INDEX IF NOT EXISTS idx_style_posts_rag
ON style_posts(added_to_rag, quality_score);

-- === СТАТИСТИКА В ТАБЛИЦЕ КАНАЛОВ ===

-- Средняя оценка качества постов канала
ALTER TABLE style_channels
ADD COLUMN IF NOT EXISTS avg_quality_score FLOAT;

-- Количество постов с высоким качеством (score >= 7)
ALTER TABLE style_channels
ADD COLUMN IF NOT EXISTS high_quality_count INTEGER DEFAULT 0;

-- === КОММЕНТАРИИ ===

COMMENT ON COLUMN style_posts.added_to_rag IS 'Добавлен ли пост в RAG базу знаний';
COMMENT ON COLUMN style_posts.rag_document_id IS 'ID документа в knowledge_documents (если добавлен в RAG)';
COMMENT ON COLUMN style_channels.avg_quality_score IS 'Средняя оценка качества постов канала (0-10)';
COMMENT ON COLUMN style_channels.high_quality_count IS 'Количество постов с quality_score >= 7';

-- === ЗАВЕРШЕНИЕ ===

-- Вывод информации об индексах
\echo 'Migration 004 completed successfully!'
\echo 'Created indexes: idx_style_posts_quality_analyzed, idx_style_posts_channel_date, idx_style_posts_rag'
\echo 'Added columns: style_posts.added_to_rag, style_posts.rag_document_id, style_channels.avg_quality_score, style_channels.high_quality_count'
