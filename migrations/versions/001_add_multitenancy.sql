-- Migration: Add Multi-tenancy Support to MAX BOTS HUB
-- Created: 2026-02-04
-- Description: Добавляет таблицы tenants, bot_configs, subscriptions и tenant_id во все существующие таблицы

-- ====================================
-- 1. СОЗДАНИЕ НОВЫХ ТАБЛИЦ
-- ====================================

-- Таблица клиентов платформы (тенантов)
CREATE TABLE IF NOT EXISTS tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    status VARCHAR(20) DEFAULT 'TRIAL' CHECK (status IN ('TRIAL', 'ACTIVE', 'PAUSED', 'BANNED')),
    config JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Индекс для быстрого поиска по slug и email
CREATE INDEX idx_tenants_slug ON tenants(slug);
CREATE INDEX idx_tenants_email ON tenants(email);
CREATE INDEX idx_tenants_status ON tenants(status);

-- Таблица конфигов ботов клиентов
CREATE TABLE IF NOT EXISTS bot_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    bot_type VARCHAR(50) NOT NULL,
    bot_name VARCHAR(255) NOT NULL,
    bot_token VARCHAR(255) UNIQUE,
    bot_username VARCHAR(255),
    config JSONB NOT NULL DEFAULT '{}',
    status VARCHAR(20) DEFAULT 'DRAFT' CHECK (status IN ('DRAFT', 'ACTIVE', 'PAUSED', 'DELETED')),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Индексы для bot_configs
CREATE INDEX idx_bot_configs_tenant_id ON bot_configs(tenant_id);
CREATE INDEX idx_bot_configs_bot_token ON bot_configs(bot_token);
CREATE INDEX idx_bot_configs_status ON bot_configs(status);

-- Таблица подписок
CREATE TABLE IF NOT EXISTS subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    plan VARCHAR(50) NOT NULL,
    status VARCHAR(20) DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'PAUSED', 'CANCELLED', 'EXPIRED')),
    started_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP,
    auto_renew BOOLEAN DEFAULT TRUE,
    price DECIMAL(10, 2),
    currency VARCHAR(3) DEFAULT 'RUB',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Индексы для subscriptions
CREATE INDEX idx_subscriptions_tenant_id ON subscriptions(tenant_id);
CREATE INDEX idx_subscriptions_status ON subscriptions(status);
CREATE INDEX idx_subscriptions_expires_at ON subscriptions(expires_at);

-- Таблица статистики использования
CREATE TABLE IF NOT EXISTS usage_stats (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    bot_id UUID REFERENCES bot_configs(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    messages_count INT DEFAULT 0,
    ai_api_calls INT DEFAULT 0,
    ai_tokens_used INT DEFAULT 0,
    active_users INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Индексы для usage_stats
CREATE INDEX idx_usage_stats_tenant_id ON usage_stats(tenant_id);
CREATE INDEX idx_usage_stats_bot_id ON usage_stats(bot_id);
CREATE INDEX idx_usage_stats_date ON usage_stats(date);
CREATE UNIQUE INDEX idx_usage_stats_unique ON usage_stats(tenant_id, bot_id, date);

-- ====================================
-- 2. ДОБАВЛЕНИЕ tenant_id В СУЩЕСТВУЮЩИЕ ТАБЛИЦЫ
-- ====================================

-- Таблица пользователей (из curator_bot)
ALTER TABLE IF EXISTS users
ADD COLUMN IF NOT EXISTS tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS idx_users_tenant_id ON users(tenant_id);

-- Таблица сообщений в диалогах (из curator_bot)
ALTER TABLE IF EXISTS conversation_messages
ADD COLUMN IF NOT EXISTS tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS idx_conversation_messages_tenant_id ON conversation_messages(tenant_id);

-- Таблица контекстов диалогов (из curator_bot)
ALTER TABLE IF EXISTS conversation_contexts
ADD COLUMN IF NOT EXISTS tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS idx_conversation_contexts_tenant_id ON conversation_contexts(tenant_id);

-- Таблица источников трафика (из curator_bot)
ALTER TABLE IF EXISTS traffic_sources
ADD COLUMN IF NOT EXISTS tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS idx_traffic_sources_tenant_id ON traffic_sources(tenant_id);

-- Таблица кликов по трафику (из curator_bot)
ALTER TABLE IF EXISTS traffic_clicks
ADD COLUMN IF NOT EXISTS tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS idx_traffic_clicks_tenant_id ON traffic_clicks(tenant_id);

-- Таблица постов (из content_manager_bot)
ALTER TABLE IF EXISTS posts
ADD COLUMN IF NOT EXISTS tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS idx_posts_tenant_id ON posts(tenant_id);

-- Таблица расписания контента (из content_manager_bot)
ALTER TABLE IF EXISTS content_schedules
ADD COLUMN IF NOT EXISTS tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS idx_content_schedules_tenant_id ON content_schedules(tenant_id);

-- Таблица медиа-ассетов (из content_manager_bot)
ALTER TABLE IF EXISTS media_assets
ADD COLUMN IF NOT EXISTS tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS idx_media_assets_tenant_id ON media_assets(tenant_id);

-- Таблица серий контента (из content_manager_bot)
ALTER TABLE IF EXISTS content_series
ADD COLUMN IF NOT EXISTS tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS idx_content_series_tenant_id ON content_series(tenant_id);

-- Таблица эмоциональных состояний (из content_manager_bot)
ALTER TABLE IF EXISTS mood_states
ADD COLUMN IF NOT EXISTS tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS idx_mood_states_tenant_id ON mood_states(tenant_id);

-- Таблица партнёров (из partner_panel) - НЕ добавляем tenant_id, так как Partner Panel - отдельная админка

-- Таблица системных событий (shared)
ALTER TABLE IF EXISTS system_events
ADD COLUMN IF NOT EXISTS tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS idx_system_events_tenant_id ON system_events(tenant_id);

-- ====================================
-- 3. ROW LEVEL SECURITY (RLS)
-- ====================================

-- Включаем RLS для bot_configs
ALTER TABLE bot_configs ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_bot_configs ON bot_configs
    USING (tenant_id = current_setting('app.tenant_id', TRUE)::UUID);

-- Включаем RLS для users
ALTER TABLE IF EXISTS users ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_users ON users
    USING (tenant_id = current_setting('app.tenant_id', TRUE)::UUID);

-- Включаем RLS для conversation_messages
ALTER TABLE IF EXISTS conversation_messages ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_conversation_messages ON conversation_messages
    USING (tenant_id = current_setting('app.tenant_id', TRUE)::UUID);

-- Включаем RLS для posts
ALTER TABLE IF EXISTS posts ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_posts ON posts
    USING (tenant_id = current_setting('app.tenant_id', TRUE)::UUID);

-- Включаем RLS для media_assets
ALTER TABLE IF EXISTS media_assets ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_media_assets ON media_assets
    USING (tenant_id = current_setting('app.tenant_id', TRUE)::UUID);

-- ====================================
-- 4. ТРИГГЕР ДЛЯ АВТОМАТИЧЕСКОГО ОБНОВЛЕНИЯ updated_at
-- ====================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Применяем триггер к таблицам
CREATE TRIGGER update_tenants_updated_at BEFORE UPDATE ON tenants
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_bot_configs_updated_at BEFORE UPDATE ON bot_configs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_subscriptions_updated_at BEFORE UPDATE ON subscriptions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ====================================
-- 5. НАЧАЛЬНЫЕ ДАННЫЕ (для тестирования)
-- ====================================

-- Создаём тестового тенанта (NL International - из существующего проекта)
INSERT INTO tenants (slug, name, email, status, config)
VALUES (
    'nl_international',
    'NL International',
    'admin@nl-international.ru',
    'ACTIVE',
    '{
        "company": "NL International",
        "industry": "network_marketing",
        "timezone": "Europe/Moscow"
    }'::JSONB
)
ON CONFLICT (slug) DO NOTHING;

-- Создаём тестовую подписку для NL International
INSERT INTO subscriptions (tenant_id, plan, status, price, currency, expires_at)
SELECT
    id,
    'enterprise',
    'ACTIVE',
    0.00,
    'RUB',
    NOW() + INTERVAL '1 year'
FROM tenants
WHERE slug = 'nl_international'
ON CONFLICT DO NOTHING;

-- ====================================
-- 6. КОММЕНТАРИИ К ТАБЛИЦАМ
-- ====================================

COMMENT ON TABLE tenants IS 'Клиенты платформы MAX BOTS HUB (тенанты)';
COMMENT ON COLUMN tenants.slug IS 'Уникальный идентификатор тенанта (URL-friendly)';
COMMENT ON COLUMN tenants.status IS 'TRIAL - пробный период, ACTIVE - активен, PAUSED - приостановлен, BANNED - заблокирован';

COMMENT ON TABLE bot_configs IS 'Конфигурации ботов клиентов';
COMMENT ON COLUMN bot_configs.bot_type IS 'Тип бота: conversation, content_generator, gosuslugi, business_assistant, etc.';
COMMENT ON COLUMN bot_configs.config IS 'JSON конфигурация бота (промпты, настройки, интеграции)';

COMMENT ON TABLE subscriptions IS 'Подписки клиентов на платформу';
COMMENT ON COLUMN subscriptions.plan IS 'Тарифный план: start, business, pro, enterprise';

COMMENT ON TABLE usage_stats IS 'Статистика использования ботов (ежедневная)';
