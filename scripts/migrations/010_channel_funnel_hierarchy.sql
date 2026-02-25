-- Channel Funnel Hierarchy Migration
-- 5 февраля 2026
-- Двухуровневая воронка каналов: публичные (прогрев) → закрытый VIP

-- ===========================================
-- 1. CHANNEL_TIERS (Иерархия каналов)
-- ===========================================
CREATE TABLE IF NOT EXISTS channel_tiers (
    id SERIAL PRIMARY KEY,

    -- Основная информация
    channel_id BIGINT UNIQUE NOT NULL,
    channel_username VARCHAR(100),
    channel_title VARCHAR(200) NOT NULL,
    channel_description TEXT,

    -- Уровень воронки: 'public_warmup' | 'private_vip'
    tier_level VARCHAR(20) NOT NULL,

    -- Сегмент: 'zozh', 'mama', 'business', 'universal'
    segment VARCHAR(20) NOT NULL DEFAULT 'universal',

    -- Статус: 'active', 'paused', 'archived'
    status VARCHAR(20) DEFAULT 'active',

    -- Владелец (NULL = системный канал, ID = канал партнёра)
    owner_partner_id INTEGER REFERENCES partners(id) ON DELETE SET NULL,

    -- Настройки для публичных каналов (tier_level = 'public_warmup')
    is_traffic_source BOOLEAN DEFAULT FALSE,       -- Использовать для Traffic Engine
    allow_invite_posts BOOLEAN DEFAULT TRUE,       -- Разрешить публикацию инвайт-постов
    invite_post_frequency_days INTEGER DEFAULT 3,  -- Как часто публиковать инвайты (дней)

    -- Ссылка на VIP канал (для публичных каналов)
    vip_channel_id INTEGER REFERENCES channel_tiers(id) ON DELETE SET NULL,

    -- Статистика
    total_posts INTEGER DEFAULT 0,
    total_subscribers INTEGER DEFAULT 0,
    avg_engagement_rate FLOAT DEFAULT 0.0,
    last_invite_post_at TIMESTAMP,

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_channel_tiers_tier_level ON channel_tiers(tier_level);
CREATE INDEX IF NOT EXISTS idx_channel_tiers_segment ON channel_tiers(segment);
CREATE INDEX IF NOT EXISTS idx_channel_tiers_status ON channel_tiers(status);
CREATE INDEX IF NOT EXISTS idx_channel_tiers_is_traffic_source ON channel_tiers(is_traffic_source);
CREATE INDEX IF NOT EXISTS idx_channel_tiers_vip_channel ON channel_tiers(vip_channel_id);

-- ===========================================
-- 2. INVITE_LINKS (Временные инвайт-ссылки)
-- ===========================================
CREATE TABLE IF NOT EXISTS invite_links (
    id SERIAL PRIMARY KEY,

    -- Канал к которому ведёт ссылка (VIP канал)
    target_channel_id INTEGER NOT NULL REFERENCES channel_tiers(id) ON DELETE CASCADE,

    -- Telegram invite link
    invite_link VARCHAR(255) UNIQUE NOT NULL,
    telegram_invite_hash VARCHAR(100),  -- Хеш инвайта из Telegram API
    invite_title VARCHAR(100),          -- Название ссылки для аналитики

    -- Ограничения
    expire_date TIMESTAMP,              -- Дата истечения
    usage_limit INTEGER,                -- Лимит использований (NULL = безлимит)

    -- Статус: 'active', 'expired', 'revoked', 'exhausted'
    status VARCHAR(20) DEFAULT 'active',

    -- Связанный пост с инвайтом
    invite_post_id INTEGER,             -- FK добавим после ALTER content_posts
    published_channel_id INTEGER REFERENCES channel_tiers(id) ON DELETE SET NULL,

    -- Статистика
    total_uses INTEGER DEFAULT 0,
    total_joins INTEGER DEFAULT 0,

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    revoked_at TIMESTAMP,
    last_used_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_invite_links_target_channel ON invite_links(target_channel_id);
CREATE INDEX IF NOT EXISTS idx_invite_links_status ON invite_links(status);
CREATE INDEX IF NOT EXISTS idx_invite_links_expire_date ON invite_links(expire_date);

-- ===========================================
-- 3. РАСШИРЕНИЕ CONTENT_POSTS
-- ===========================================
-- Добавить целевой канал (вместо hardcoded @nl_international_partners)
ALTER TABLE content_posts ADD COLUMN IF NOT EXISTS target_channel_id INTEGER REFERENCES channel_tiers(id);

-- Флаг инвайт-поста
ALTER TABLE content_posts ADD COLUMN IF NOT EXISTS is_invite_post BOOLEAN DEFAULT FALSE;

-- Связь с инвайт-ссылкой
ALTER TABLE content_posts ADD COLUMN IF NOT EXISTS invite_link_id INTEGER REFERENCES invite_links(id);

-- Время автоудаления (для инвайт-постов)
ALTER TABLE content_posts ADD COLUMN IF NOT EXISTS auto_delete_at TIMESTAMP;

-- Индексы
CREATE INDEX IF NOT EXISTS idx_content_posts_target_channel ON content_posts(target_channel_id);
CREATE INDEX IF NOT EXISTS idx_content_posts_is_invite_post ON content_posts(is_invite_post);
CREATE INDEX IF NOT EXISTS idx_content_posts_auto_delete_at ON content_posts(auto_delete_at);

-- ===========================================
-- 4. FK для invite_links.invite_post_id
-- ===========================================
ALTER TABLE invite_links ADD CONSTRAINT fk_invite_links_post
    FOREIGN KEY (invite_post_id) REFERENCES content_posts(id) ON DELETE SET NULL;

-- ===========================================
-- 5. РАСШИРЕНИЕ PARTNERS (VIP доступ)
-- ===========================================
ALTER TABLE partners ADD COLUMN IF NOT EXISTS vip_access_granted BOOLEAN DEFAULT FALSE;
ALTER TABLE partners ADD COLUMN IF NOT EXISTS vip_joined_at TIMESTAMP;
ALTER TABLE partners ADD COLUMN IF NOT EXISTS registration_source VARCHAR(50);  -- 'vip_channel', 'direct', 'referral'

CREATE INDEX IF NOT EXISTS idx_partners_vip_access ON partners(vip_access_granted);
CREATE INDEX IF NOT EXISTS idx_partners_registration_source ON partners(registration_source);

-- ===========================================
-- 6. ТРИГГЕР ДЛЯ UPDATED_AT
-- ===========================================
DROP TRIGGER IF EXISTS update_channel_tiers_updated_at ON channel_tiers;
CREATE TRIGGER update_channel_tiers_updated_at
    BEFORE UPDATE ON channel_tiers
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ===========================================
-- 7. КОММЕНТАРИИ
-- ===========================================
COMMENT ON TABLE channel_tiers IS 'Иерархия каналов воронки: публичные (прогрев) → закрытый VIP';
COMMENT ON TABLE invite_links IS 'Временные инвайт-ссылки для доступа в VIP канал';
COMMENT ON COLUMN channel_tiers.tier_level IS 'public_warmup = публичный канал для прогрева, private_vip = закрытый VIP канал';
COMMENT ON COLUMN channel_tiers.is_traffic_source IS 'TRUE = использовать для автокомментирования в Traffic Engine';
COMMENT ON COLUMN invite_links.expire_date IS 'Дата истечения ссылки (обычно через 2-6 часов)';
COMMENT ON COLUMN content_posts.auto_delete_at IS 'Когда автоудалить пост (для инвайт-постов после истечения ссылки)';
