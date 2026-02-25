-- Migration 006: Traffic Engine tables
-- Date: 2026-02-02
-- Description: Добавляет таблицы для отслеживания источников трафика

-- 1. Добавляем поле traffic_source в таблицу users
ALTER TABLE users
ADD COLUMN IF NOT EXISTS traffic_source VARCHAR(100);

CREATE INDEX IF NOT EXISTS idx_users_traffic_source ON users(traffic_source);

-- 2. Создаём таблицу источников трафика
CREATE TABLE IF NOT EXISTS traffic_sources (
    id SERIAL PRIMARY KEY,
    source_id VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    source_type VARCHAR(50) DEFAULT 'channel',
    segment VARCHAR(50),
    channel_username VARCHAR(100),
    persona_name VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    total_clicks INTEGER DEFAULT 0,
    total_registrations INTEGER DEFAULT 0,
    total_active_users INTEGER DEFAULT 0,
    total_partners INTEGER DEFAULT 0,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_traffic_sources_source_id ON traffic_sources(source_id);
CREATE INDEX IF NOT EXISTS idx_traffic_sources_segment ON traffic_sources(segment);
CREATE INDEX IF NOT EXISTS idx_traffic_sources_active ON traffic_sources(is_active);

-- 3. Создаём таблицу кликов (детальный трекинг)
CREATE TABLE IF NOT EXISTS traffic_clicks (
    id SERIAL PRIMARY KEY,
    source_id VARCHAR(100) NOT NULL,
    telegram_id BIGINT,
    ip_address VARCHAR(50),
    user_agent VARCHAR(500),
    converted BOOLEAN DEFAULT FALSE,
    converted_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_traffic_clicks_source_id ON traffic_clicks(source_id);
CREATE INDEX IF NOT EXISTS idx_traffic_clicks_telegram_id ON traffic_clicks(telegram_id);
CREATE INDEX IF NOT EXISTS idx_traffic_clicks_converted ON traffic_clicks(converted);

-- 4. Предзаполняем тестовые источники для пилота
INSERT INTO traffic_sources (source_id, name, source_type, segment, persona_name)
VALUES
    ('channel_zozh_1', 'ЗОЖ канал Марины', 'channel', 'zozh', 'Марина'),
    ('channel_zozh_2', 'ЗОЖ канал Алины', 'channel', 'zozh', 'Алина'),
    ('channel_mama_1', 'Канал для мам Анны', 'channel', 'mama', 'Анна'),
    ('channel_biz_1', 'Бизнес канал Киры', 'channel', 'business', 'Кира'),
    ('channel_biz_2', 'Бизнес канал Даши', 'channel', 'business', 'Даша')
ON CONFLICT (source_id) DO NOTHING;

-- 5. Комментарии к таблицам
COMMENT ON TABLE traffic_sources IS 'Источники трафика для Traffic Engine (каналы, группы, реклама)';
COMMENT ON TABLE traffic_clicks IS 'Детальный трекинг кликов по источникам';
COMMENT ON COLUMN users.traffic_source IS 'ID источника откуда пришёл пользователь (channel_zozh_1, etc.)';
