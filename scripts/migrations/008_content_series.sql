-- Миграция 008: Система серийного контента (cliffhangers)
-- Добавлено: 03.02.2026
-- Описание: Таблица для хранения серий постов с продолжением

-- Создаём таблицу content_series
CREATE TABLE IF NOT EXISTS content_series (
    id SERIAL PRIMARY KEY,

    -- Название/тема серии
    title VARCHAR(255) NOT NULL,
    topic TEXT NOT NULL,

    -- Персонаж серии (recurring character)
    character VARCHAR(100),

    -- Количество частей
    total_parts INTEGER NOT NULL DEFAULT 3,
    current_part INTEGER NOT NULL DEFAULT 0,

    -- Статус серии: draft, active, completed, cancelled
    status VARCHAR(20) NOT NULL DEFAULT 'draft',

    -- Связи с постами (массив post_id)
    post_ids JSONB DEFAULT '[]'::jsonb,

    -- Контекст для продолжения
    context_summary TEXT,

    -- Cliffhanger из последнего поста
    last_cliffhanger TEXT,

    -- Даты
    started_at TIMESTAMP,
    completed_at TIMESTAMP,

    -- Метрики серии
    total_views INTEGER NOT NULL DEFAULT 0,
    total_reactions INTEGER NOT NULL DEFAULT 0,

    -- Timestamps (стандартные)
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Индексы
CREATE INDEX IF NOT EXISTS idx_content_series_status ON content_series(status);
CREATE INDEX IF NOT EXISTS idx_content_series_created_at ON content_series(created_at DESC);

-- Триггер для updated_at
CREATE OR REPLACE FUNCTION update_content_series_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_content_series_updated_at ON content_series;
CREATE TRIGGER trigger_content_series_updated_at
    BEFORE UPDATE ON content_series
    FOR EACH ROW
    EXECUTE FUNCTION update_content_series_updated_at();

-- Комментарии
COMMENT ON TABLE content_series IS 'Серии постов с продолжением (cliffhangers)';
COMMENT ON COLUMN content_series.title IS 'Название серии для отображения';
COMMENT ON COLUMN content_series.topic IS 'Общая тема серии';
COMMENT ON COLUMN content_series.character IS 'Recurring character (Артём, Валентина Петровна и т.д.)';
COMMENT ON COLUMN content_series.status IS 'draft=черновик, active=в процессе, completed=завершена, cancelled=отменена';
COMMENT ON COLUMN content_series.post_ids IS 'Массив ID постов серии';
COMMENT ON COLUMN content_series.context_summary IS 'Краткое описание предыдущих частей';
COMMENT ON COLUMN content_series.last_cliffhanger IS 'Cliffhanger для следующей части';
