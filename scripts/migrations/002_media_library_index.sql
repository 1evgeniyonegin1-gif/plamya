-- ================================================================
-- Миграция: Индексация медиа-библиотеки для быстрого поиска
-- Дата: 2026-01-26
-- Описание: Расширяет MediaAsset для индексированного поиска фото
--           продуктов, чеков партнёров и стикеров/гифок
-- ================================================================

-- ================================================================
-- Шаг 1: Расширение существующей таблицы content_media_assets
-- ================================================================

-- Добавляем новые колонки (с IF NOT EXISTS для безопасности)
ALTER TABLE content_media_assets
ADD COLUMN IF NOT EXISTS asset_type VARCHAR(50) DEFAULT 'sticker',
ADD COLUMN IF NOT EXISTS keywords JSONB DEFAULT '[]',
ADD COLUMN IF NOT EXISTS description TEXT,
ADD COLUMN IF NOT EXISTS nl_products JSONB DEFAULT '[]',
ADD COLUMN IF NOT EXISTS file_hash VARCHAR(64),
ADD COLUMN IF NOT EXISTS tags JSONB DEFAULT '[]';

-- Обновляем существующие записи: устанавливаем asset_type
UPDATE content_media_assets
SET asset_type = 'sticker'
WHERE asset_type IS NULL;

-- Делаем asset_type NOT NULL после заполнения
ALTER TABLE content_media_assets
ALTER COLUMN asset_type SET NOT NULL;

-- Комментарии к новым колонкам
COMMENT ON COLUMN content_media_assets.asset_type IS 'Тип ресурса: product, testimonial, sticker, gif';
COMMENT ON COLUMN content_media_assets.keywords IS 'Список ключевых слов для поиска ["коллаген", "collagen"]';
COMMENT ON COLUMN content_media_assets.description IS 'Описание медиа (особенно для testimonials)';
COMMENT ON COLUMN content_media_assets.nl_products IS 'Связанные продукты NL ["3d_slim", "omega"]';
COMMENT ON COLUMN content_media_assets.file_hash IS 'SHA256 хеш файла для дедупликации';
COMMENT ON COLUMN content_media_assets.tags IS 'Дополнительные теги ["семья", "успех"]';

-- ================================================================
-- Шаг 2: Создание индексной таблицы для O(1) поиска
-- ================================================================

CREATE TABLE IF NOT EXISTS media_keyword_index (
    id SERIAL PRIMARY KEY,
    keyword VARCHAR(255) NOT NULL,
    normalized_keyword VARCHAR(255) NOT NULL,  -- lowercase, без спецсимволов
    asset_id INTEGER NOT NULL REFERENCES content_media_assets(id) ON DELETE CASCADE,
    priority INTEGER DEFAULT 1,  -- для выбора при конфликтах (выше = приоритетнее)

    UNIQUE(normalized_keyword, asset_id)
);

-- Комментарии к таблице
COMMENT ON TABLE media_keyword_index IS 'Индекс для быстрого O(1) поиска медиа по ключевым словам';
COMMENT ON COLUMN media_keyword_index.keyword IS 'Оригинальное ключевое слово';
COMMENT ON COLUMN media_keyword_index.normalized_keyword IS 'Нормализованное для поиска (lowercase)';
COMMENT ON COLUMN media_keyword_index.priority IS 'Приоритет при множественных совпадениях (1-10)';

-- ================================================================
-- Шаг 3: Создание индексов для быстрого поиска
-- ================================================================

-- GIN индекс для поиска по keywords в JSONB
CREATE INDEX IF NOT EXISTS idx_media_keywords
ON content_media_assets USING GIN (keywords);

-- GIN индекс для поиска по nl_products
CREATE INDEX IF NOT EXISTS idx_media_nl_products
ON content_media_assets USING GIN (nl_products);

-- GIN индекс для поиска по tags
CREATE INDEX IF NOT EXISTS idx_media_tags
ON content_media_assets USING GIN (tags);

-- B-tree индекс для поиска по типу и категории
CREATE INDEX IF NOT EXISTS idx_media_type_category
ON content_media_assets(asset_type, category)
WHERE file_id IS NOT NULL OR file_path IS NOT NULL;

-- Уникальный индекс для дедупликации по хешу
CREATE UNIQUE INDEX IF NOT EXISTS idx_media_file_hash
ON content_media_assets(file_hash)
WHERE file_hash IS NOT NULL;

-- КРИТИЧЕСКИЙ индекс для O(1) поиска по нормализованному keyword
CREATE INDEX IF NOT EXISTS idx_keyword_lookup
ON media_keyword_index(normalized_keyword);

-- Индекс для обратного поиска (все keywords для asset_id)
CREATE INDEX IF NOT EXISTS idx_keyword_asset
ON media_keyword_index(asset_id);

-- ================================================================
-- Шаг 4: Создание функций для нормализации
-- ================================================================

-- Функция нормализации ключевого слова
CREATE OR REPLACE FUNCTION normalize_keyword(keyword TEXT)
RETURNS TEXT AS $$
BEGIN
    -- lowercase + удаление спецсимволов + trim
    RETURN LOWER(TRIM(REGEXP_REPLACE(keyword, '[^а-яёa-z0-9 ]', '', 'gi')));
END;
$$ LANGUAGE plpgsql IMMUTABLE;

COMMENT ON FUNCTION normalize_keyword IS 'Нормализует ключевое слово для индексации (lowercase, без спецсимволов)';

-- ================================================================
-- Шаг 5: Создание триггеров для автоматической нормализации
-- ================================================================

-- Функция триггера для автоматического заполнения normalized_keyword
CREATE OR REPLACE FUNCTION trigger_normalize_keyword()
RETURNS TRIGGER AS $$
BEGIN
    NEW.normalized_keyword := normalize_keyword(NEW.keyword);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Триггер для автоматической нормализации при INSERT/UPDATE
DROP TRIGGER IF EXISTS normalize_keyword_trigger ON media_keyword_index;
CREATE TRIGGER normalize_keyword_trigger
    BEFORE INSERT OR UPDATE OF keyword
    ON media_keyword_index
    FOR EACH ROW
    EXECUTE FUNCTION trigger_normalize_keyword();

-- ================================================================
-- Шаг 6: Создание вспомогательных представлений
-- ================================================================

-- Представление для быстрого просмотра всех keywords по asset
CREATE OR REPLACE VIEW v_media_keywords AS
SELECT
    ma.id as asset_id,
    ma.asset_type,
    ma.category,
    ma.file_path,
    ma.description,
    ARRAY_AGG(DISTINCT mki.keyword) as keywords,
    ma.nl_products,
    ma.tags,
    ma.usage_count,
    ma.last_used_at
FROM content_media_assets ma
LEFT JOIN media_keyword_index mki ON ma.id = mki.asset_id
WHERE ma.file_id IS NOT NULL OR ma.file_path IS NOT NULL
GROUP BY ma.id, ma.asset_type, ma.category, ma.file_path, ma.description,
         ma.nl_products, ma.tags, ma.usage_count, ma.last_used_at;

COMMENT ON VIEW v_media_keywords IS 'Удобное представление медиа-активов со всеми их keywords';

-- ================================================================
-- Шаг 7: Статистика и проверка
-- ================================================================

-- Выводим статистику
DO $$
DECLARE
    total_assets INT;
    total_keywords INT;
    total_products INT;
    total_testimonials INT;
BEGIN
    SELECT COUNT(*) INTO total_assets FROM content_media_assets;
    SELECT COUNT(*) INTO total_keywords FROM media_keyword_index;
    SELECT COUNT(*) INTO total_products FROM content_media_assets WHERE asset_type = 'product';
    SELECT COUNT(*) INTO total_testimonials FROM content_media_assets WHERE asset_type = 'testimonial';

    RAISE NOTICE '✓ Миграция завершена успешно';
    RAISE NOTICE '  - Всего медиа-активов: %', total_assets;
    RAISE NOTICE '  - Всего keywords в индексе: %', total_keywords;
    RAISE NOTICE '  - Фото продуктов: %', total_products;
    RAISE NOTICE '  - Чеки/истории: %', total_testimonials;
END $$;

-- Проверка дубликатов по file_hash
SELECT file_hash, COUNT(*) as duplicates
FROM content_media_assets
WHERE file_hash IS NOT NULL
GROUP BY file_hash
HAVING COUNT(*) > 1;

-- Если есть дубликаты, выводим предупреждение
DO $$
DECLARE
    dup_count INT;
BEGIN
    SELECT COUNT(*) INTO dup_count
    FROM (
        SELECT file_hash
        FROM content_media_assets
        WHERE file_hash IS NOT NULL
        GROUP BY file_hash
        HAVING COUNT(*) > 1
    ) t;

    IF dup_count > 0 THEN
        RAISE WARNING '⚠ Найдено % групп дубликатов. Запустите скрипт дедупликации.', dup_count;
    ELSE
        RAISE NOTICE '✓ Дубликаты не найдены';
    END IF;
END $$;
