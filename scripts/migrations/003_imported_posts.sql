-- Миграция 003: Таблица для импортированных постов из Telegram экспорта
-- Автор: Claude Code
-- Дата: 2026-01-26
-- Описание: Хранит посты из экспортов Telegram-каналов для использования как темы/вдохновение

-- Создаём таблицу imported_posts
CREATE TABLE IF NOT EXISTS content_imported_posts (
    id SERIAL PRIMARY KEY,

    -- Источник
    source_id INTEGER NOT NULL,              -- Оригинальный ID сообщения в Telegram
    source_channel VARCHAR(200) NOT NULL,    -- Название канала-источника

    -- Контент
    text TEXT NOT NULL,                       -- Текст поста
    category VARCHAR(50) NOT NULL,            -- Категория: product, motivation, business, success, tips, news, lifestyle

    -- Метрики качества
    reactions_count INTEGER DEFAULT 0,        -- Общее количество реакций (для приоритизации)
    char_count INTEGER DEFAULT 0,             -- Длина текста
    has_formatting BOOLEAN DEFAULT FALSE,     -- Есть ли форматирование (bold, lists)
    quality_score FLOAT DEFAULT 0,            -- Рассчитанный score качества

    -- Дата оригинального поста
    original_date TIMESTAMP,

    -- Статус использования
    is_used BOOLEAN DEFAULT FALSE,            -- Флаг: использован ли уже
    used_at TIMESTAMP,                        -- Когда использован
    used_for_post_id INTEGER,                 -- ID сгенерированного поста (FK на content_posts)

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    -- Уникальность по (канал + id сообщения)
    UNIQUE(source_channel, source_id)
);

-- Индексы для быстрого поиска
CREATE INDEX IF NOT EXISTS idx_imported_posts_category ON content_imported_posts(category);
CREATE INDEX IF NOT EXISTS idx_imported_posts_is_used ON content_imported_posts(is_used);
CREATE INDEX IF NOT EXISTS idx_imported_posts_quality ON content_imported_posts(quality_score DESC);
CREATE INDEX IF NOT EXISTS idx_imported_posts_category_unused ON content_imported_posts(category, is_used) WHERE is_used = FALSE;

-- Комментарии
COMMENT ON TABLE content_imported_posts IS 'Импортированные посты из Telegram для вдохновения';
COMMENT ON COLUMN content_imported_posts.category IS 'Категория: product, motivation, business, success, tips, news, lifestyle';
COMMENT ON COLUMN content_imported_posts.quality_score IS 'Score = reactions_count * 0.3 + log(char_count) * 0.3 + has_formatting * 0.4';
COMMENT ON COLUMN content_imported_posts.is_used IS 'TRUE когда пост уже был использован для генерации контента';
