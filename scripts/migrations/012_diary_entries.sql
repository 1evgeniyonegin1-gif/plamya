-- Diary Entries — дневник админа
-- Дата: 09.02.2026

CREATE TABLE IF NOT EXISTS diary_entries (
    id SERIAL PRIMARY KEY,
    admin_id BIGINT NOT NULL,
    entry_text TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_diary_admin_id ON diary_entries(admin_id);
CREATE INDEX IF NOT EXISTS idx_diary_created_at ON diary_entries(created_at DESC);

-- Триггер обновления updated_at
CREATE OR REPLACE FUNCTION update_diary_entries_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_diary_entries_updated_at ON diary_entries;
CREATE TRIGGER trigger_diary_entries_updated_at
    BEFORE UPDATE ON diary_entries
    FOR EACH ROW
    EXECUTE FUNCTION update_diary_entries_updated_at();
