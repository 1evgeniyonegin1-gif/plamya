-- 015: Таблица конверсий воронки (публичный канал → VIP)
-- Трекинг: кто пришёл, через какую ссылку, верифицирован ли как партнёр NL

CREATE TABLE IF NOT EXISTS funnel_conversions (
    id SERIAL PRIMARY KEY,

    -- Пользователь
    user_id BIGINT NOT NULL,
    username VARCHAR(100),
    first_name VARCHAR(100),

    -- Источник конверсии
    invite_link_id INTEGER REFERENCES invite_links(id) ON DELETE SET NULL,
    source_channel_id INTEGER REFERENCES channel_tiers(id) ON DELETE SET NULL,
    source_post_id INTEGER,

    -- Верификация партнёра NL
    is_verified_partner BOOLEAN DEFAULT FALSE,
    verified_at TIMESTAMP,
    partner_level VARCHAR(20),

    -- Статус: joined, verified, rejected, left
    status VARCHAR(20) DEFAULT 'joined' NOT NULL,

    -- Активность после вступления
    messages_sent INTEGER DEFAULT 0,
    last_active_at TIMESTAMP,

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_fc_user_id ON funnel_conversions(user_id);
CREATE INDEX IF NOT EXISTS idx_fc_status ON funnel_conversions(status);
CREATE INDEX IF NOT EXISTS idx_fc_invite_link ON funnel_conversions(invite_link_id);

-- Trigger для updated_at
CREATE OR REPLACE FUNCTION update_funnel_conversions_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_funnel_conversions_updated ON funnel_conversions;
CREATE TRIGGER trg_funnel_conversions_updated
    BEFORE UPDATE ON funnel_conversions
    FOR EACH ROW
    EXECUTE FUNCTION update_funnel_conversions_updated_at();
