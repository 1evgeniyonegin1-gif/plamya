-- Миграция: Curator Mini App
-- Дата: 2026-02-05
-- Описание: Таблицы для Mini App куратора (каталог продуктов + бизнес-раздел)

-- =====================================================
-- Таблица пользователей Mini App
-- =====================================================
CREATE TABLE IF NOT EXISTS curator_miniapp_users (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    telegram_username VARCHAR(255),
    telegram_first_name VARCHAR(255),
    telegram_last_name VARCHAR(255),
    telegram_photo_url VARCHAR(500),

    -- Статус партнёра
    is_partner BOOLEAN DEFAULT FALSE,
    partner_registered_at TIMESTAMP,

    -- Трекинг активности
    products_viewed INTEGER DEFAULT 0,
    business_section_viewed BOOLEAN DEFAULT FALSE,
    last_visit_at TIMESTAMP,
    visits_count INTEGER DEFAULT 0,

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_curator_users_telegram ON curator_miniapp_users(telegram_id);
CREATE INDEX IF NOT EXISTS idx_curator_users_partner ON curator_miniapp_users(is_partner);

-- =====================================================
-- Таблица просмотров продуктов
-- =====================================================
CREATE TABLE IF NOT EXISTS curator_product_views (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES curator_miniapp_users(id),
    telegram_id BIGINT NOT NULL,
    product_key VARCHAR(200) NOT NULL,
    category VARCHAR(100),
    clicked_link BOOLEAN DEFAULT FALSE,
    viewed_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_product_views_user ON curator_product_views(user_id);
CREATE INDEX IF NOT EXISTS idx_product_views_telegram ON curator_product_views(telegram_id);
CREATE INDEX IF NOT EXISTS idx_product_views_product ON curator_product_views(product_key);
CREATE INDEX IF NOT EXISTS idx_product_views_date ON curator_product_views(viewed_at);

-- =====================================================
-- Таблица интересов к бизнесу
-- =====================================================
CREATE TABLE IF NOT EXISTS curator_business_interests (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES curator_miniapp_users(id),
    telegram_id BIGINT NOT NULL,
    action VARCHAR(50) NOT NULL,  -- 'telegram_chat', 'registration', 'view_business', 'became_partner'
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_business_interests_user ON curator_business_interests(user_id);
CREATE INDEX IF NOT EXISTS idx_business_interests_telegram ON curator_business_interests(telegram_id);
CREATE INDEX IF NOT EXISTS idx_business_interests_action ON curator_business_interests(action);
CREATE INDEX IF NOT EXISTS idx_business_interests_date ON curator_business_interests(created_at);

-- =====================================================
-- Функция автообновления updated_at
-- =====================================================
CREATE OR REPLACE FUNCTION update_curator_miniapp_users_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_curator_users ON curator_miniapp_users;
CREATE TRIGGER trigger_update_curator_users
    BEFORE UPDATE ON curator_miniapp_users
    FOR EACH ROW
    EXECUTE FUNCTION update_curator_miniapp_users_updated_at();

-- =====================================================
-- Представления для аналитики
-- =====================================================

-- Топ просматриваемых продуктов
CREATE OR REPLACE VIEW curator_top_products AS
SELECT
    product_key,
    category,
    COUNT(*) as view_count,
    COUNT(DISTINCT telegram_id) as unique_viewers,
    SUM(CASE WHEN clicked_link THEN 1 ELSE 0 END) as link_clicks,
    ROUND(100.0 * SUM(CASE WHEN clicked_link THEN 1 ELSE 0 END) / COUNT(*), 2) as click_rate
FROM curator_product_views
GROUP BY product_key, category
ORDER BY view_count DESC;

-- Статистика по дням
CREATE OR REPLACE VIEW curator_daily_stats AS
SELECT
    DATE(pv.viewed_at) as date,
    COUNT(DISTINCT pv.telegram_id) as unique_users,
    COUNT(*) as product_views,
    SUM(CASE WHEN pv.clicked_link THEN 1 ELSE 0 END) as link_clicks,
    COUNT(DISTINCT bi.telegram_id) as business_interests
FROM curator_product_views pv
LEFT JOIN curator_business_interests bi
    ON DATE(bi.created_at) = DATE(pv.viewed_at)
GROUP BY DATE(pv.viewed_at)
ORDER BY date DESC;

-- =====================================================
-- Комментарии
-- =====================================================
COMMENT ON TABLE curator_miniapp_users IS 'Пользователи Curator Mini App';
COMMENT ON TABLE curator_product_views IS 'Просмотры продуктов в каталоге';
COMMENT ON TABLE curator_business_interests IS 'Интерес к бизнесу (CTA клики)';

COMMENT ON COLUMN curator_miniapp_users.is_partner IS 'Является ли пользователь партнёром NL';
COMMENT ON COLUMN curator_business_interests.action IS 'Тип действия: telegram_chat, registration, view_business, became_partner';
COMMENT ON COLUMN curator_product_views.clicked_link IS 'Перешёл ли по реферальной ссылке';
