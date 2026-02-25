-- Partner Panel Tables Migration
-- 3 февраля 2026

-- ===========================================
-- 1. PARTNERS (партнёры NL International)
-- ===========================================
CREATE TABLE IF NOT EXISTS partners (
    id SERIAL PRIMARY KEY,

    -- Telegram данные (из Mini App)
    telegram_id BIGINT UNIQUE NOT NULL,
    telegram_username VARCHAR(100),
    telegram_first_name VARCHAR(100),
    telegram_last_name VARCHAR(100),
    telegram_photo_url VARCHAR(500),

    -- NL данные (опционально)
    nl_partner_id VARCHAR(50),
    nl_qualification VARCHAR(20),  -- M1, B1, etc.

    -- Статус: pending, connecting, active, paused, error, banned
    status VARCHAR(20) DEFAULT 'pending' NOT NULL,

    -- Сегмент контента: zozh, mama, business
    segment VARCHAR(20) DEFAULT 'zozh' NOT NULL,

    -- Статистика (агрегированная)
    total_channels INTEGER DEFAULT 0,
    total_posts INTEGER DEFAULT 0,
    total_subscribers INTEGER DEFAULT 0,
    total_leads INTEGER DEFAULT 0,

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    last_activity_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_partners_telegram_id ON partners(telegram_id);
CREATE INDEX IF NOT EXISTS idx_partners_status ON partners(status);

-- ===========================================
-- 2. PARTNER_CREDENTIALS (Telegram аккаунты)
-- ===========================================
CREATE TABLE IF NOT EXISTS partner_credentials (
    id SERIAL PRIMARY KEY,
    partner_id INTEGER NOT NULL REFERENCES partners(id) ON DELETE CASCADE,

    -- Telegram credentials
    phone VARCHAR(20) UNIQUE NOT NULL,
    session_string TEXT NOT NULL,  -- Telethon session (зашифровано)

    -- Telethon API (опционально)
    api_id INTEGER,
    api_hash VARCHAR(50),

    -- Proxy (опционально)
    proxy_type VARCHAR(10),        -- socks5, http
    proxy_host VARCHAR(100),
    proxy_port INTEGER,
    proxy_username VARCHAR(100),
    proxy_password VARCHAR(100),

    -- Статус аккаунта
    is_active BOOLEAN DEFAULT TRUE,
    is_banned BOOLEAN DEFAULT FALSE,
    ban_reason VARCHAR(500),

    -- Прогрев
    warmup_day INTEGER DEFAULT 0,
    warmup_completed BOOLEAN DEFAULT FALSE,

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    last_used_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_partner_credentials_partner_id ON partner_credentials(partner_id);
CREATE INDEX IF NOT EXISTS idx_partner_credentials_phone ON partner_credentials(phone);
CREATE INDEX IF NOT EXISTS idx_partner_credentials_is_active ON partner_credentials(is_active);

-- ===========================================
-- 3. PARTNER_CHANNELS (Telegram каналы)
-- ===========================================
CREATE TABLE IF NOT EXISTS partner_channels (
    id SERIAL PRIMARY KEY,
    partner_id INTEGER NOT NULL REFERENCES partners(id) ON DELETE CASCADE,
    credentials_id INTEGER NOT NULL REFERENCES partner_credentials(id) ON DELETE CASCADE,

    -- Telegram канал
    channel_id BIGINT UNIQUE NOT NULL,
    channel_username VARCHAR(100),
    channel_title VARCHAR(200) NOT NULL,
    channel_description TEXT,

    -- Настройки
    segment VARCHAR(20) NOT NULL,         -- zozh, mama, business
    persona_name VARCHAR(50) NOT NULL,    -- Марина, Анна, etc.

    -- Статус: creating, warming, active, paused, banned
    status VARCHAR(20) DEFAULT 'creating' NOT NULL,

    -- Автопостинг
    posting_enabled BOOLEAN DEFAULT FALSE,
    posts_per_day INTEGER DEFAULT 2,
    posting_times JSONB,  -- ["10:00", "18:00"]

    -- Реферальные ссылки
    referral_link VARCHAR(200),
    curator_deeplink VARCHAR(200),  -- t.me/bot?start=partner_123

    -- Статистика
    subscribers_count INTEGER DEFAULT 0,
    posts_count INTEGER DEFAULT 0,
    avg_views INTEGER DEFAULT 0,
    total_clicks INTEGER DEFAULT 0,

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    last_post_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_partner_channels_partner_id ON partner_channels(partner_id);
CREATE INDEX IF NOT EXISTS idx_partner_channels_credentials_id ON partner_channels(credentials_id);
CREATE INDEX IF NOT EXISTS idx_partner_channels_channel_id ON partner_channels(channel_id);
CREATE INDEX IF NOT EXISTS idx_partner_channels_status ON partner_channels(status);

-- ===========================================
-- 4. Триггер для updated_at
-- ===========================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_partners_updated_at ON partners;
CREATE TRIGGER update_partners_updated_at
    BEFORE UPDATE ON partners
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_partner_channels_updated_at ON partner_channels;
CREATE TRIGGER update_partner_channels_updated_at
    BEFORE UPDATE ON partner_channels
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ===========================================
-- Комментарии
-- ===========================================
COMMENT ON TABLE partners IS 'Партнёры NL International с доступом к Partner Panel';
COMMENT ON TABLE partner_credentials IS 'Telegram аккаунты партнёров для Telethon';
COMMENT ON TABLE partner_channels IS 'Telegram каналы партнёров для автопостинга';
