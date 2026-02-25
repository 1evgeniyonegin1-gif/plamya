-- Migration 007: Traffic Accounts and Warmup System
-- Date: 2026-02-03
-- Description: Tables for managing multiple Telegram accounts, warmup process, and channel management

-- =====================================================
-- TRAFFIC ACCOUNTS - управление аккаунтами Telegram
-- =====================================================
CREATE TABLE IF NOT EXISTS traffic_accounts (
    id SERIAL PRIMARY KEY,
    phone VARCHAR(20) UNIQUE NOT NULL,
    session_string TEXT,  -- Telethon session string

    -- Прокси настройки
    proxy_type VARCHAR(10) DEFAULT 'socks5',  -- socks5, http, mtproto
    proxy_host VARCHAR(255),
    proxy_port INTEGER,
    proxy_username VARCHAR(255),
    proxy_password VARCHAR(255),

    -- Статус прогрева
    warmup_day INTEGER DEFAULT 0,
    warmup_started_at TIMESTAMP,
    warmup_completed BOOLEAN DEFAULT FALSE,
    warmup_phase VARCHAR(20) DEFAULT 'not_started',  -- not_started, phase1, phase2, phase3, phase4, completed

    -- Статус аккаунта
    status VARCHAR(20) DEFAULT 'new',  -- new, warming, active, paused, banned, backup
    last_activity_at TIMESTAMP,
    spam_bot_status VARCHAR(50),  -- ok, limited, banned
    spam_bot_checked_at TIMESTAMP,
    ban_reason TEXT,

    -- Персона
    persona_name VARCHAR(100),
    persona_last_name VARCHAR(100),
    username VARCHAR(100),
    bio TEXT,
    avatar_file_id VARCHAR(255),
    segment VARCHAR(20),  -- zozh, mama, business

    -- Связь с продюсером
    producer_agent_id INTEGER,

    -- Метаданные
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE traffic_accounts IS 'Telegram аккаунты для Traffic Engine';
COMMENT ON COLUMN traffic_accounts.warmup_phase IS 'Фаза прогрева: phase1 (1-7 дни), phase2 (8-14), phase3 (15-21), phase4 (22-30)';
COMMENT ON COLUMN traffic_accounts.status IS 'new=только создан, warming=в процессе прогрева, active=работает, paused=приостановлен, banned=забанен, backup=резервный';

-- =====================================================
-- TRAFFIC CHANNELS - каналы привязанные к аккаунтам
-- =====================================================
CREATE TABLE IF NOT EXISTS traffic_channels (
    id SERIAL PRIMARY KEY,
    account_id INTEGER REFERENCES traffic_accounts(id) ON DELETE CASCADE,

    -- Данные канала
    channel_id BIGINT UNIQUE,
    channel_username VARCHAR(100),
    channel_title VARCHAR(255),
    channel_description TEXT,

    -- Метрики
    subscribers_count INTEGER DEFAULT 0,
    posts_count INTEGER DEFAULT 0,
    avg_views INTEGER DEFAULT 0,

    -- Статус
    status VARCHAR(20) DEFAULT 'active',  -- active, paused, banned

    -- Настройки постинга
    posting_enabled BOOLEAN DEFAULT TRUE,
    posts_per_day INTEGER DEFAULT 2,
    posting_times JSONB DEFAULT '["10:00", "18:00"]'::jsonb,

    -- Привязка к источнику трафика
    traffic_source_id INTEGER,  -- Связь с traffic_sources

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE traffic_channels IS 'Telegram каналы для трафик-системы';
CREATE INDEX IF NOT EXISTS idx_traffic_channels_account ON traffic_channels(account_id);
CREATE INDEX IF NOT EXISTS idx_traffic_channels_status ON traffic_channels(status);

-- =====================================================
-- TRAFFIC CONTENT SCHEDULE - расписание постов
-- =====================================================
CREATE TABLE IF NOT EXISTS traffic_content_schedule (
    id SERIAL PRIMARY KEY,
    channel_id INTEGER REFERENCES traffic_channels(id) ON DELETE CASCADE,

    -- Контент
    post_type VARCHAR(50),  -- intro, product, success_story, motivation, cta, life_moment
    content TEXT,
    media_file_id VARCHAR(255),
    media_type VARCHAR(20),  -- photo, video

    -- Расписание
    scheduled_at TIMESTAMP NOT NULL,
    published_at TIMESTAMP,

    -- Статус
    status VARCHAR(20) DEFAULT 'pending',  -- pending, published, failed, cancelled
    error_message TEXT,

    -- Метрики после публикации
    views_count INTEGER DEFAULT 0,
    reactions_count INTEGER DEFAULT 0,

    created_at TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE traffic_content_schedule IS 'Очередь контента для автопостинга в каналы';
CREATE INDEX IF NOT EXISTS idx_content_schedule_channel ON traffic_content_schedule(channel_id);
CREATE INDEX IF NOT EXISTS idx_content_schedule_scheduled ON traffic_content_schedule(scheduled_at);
CREATE INDEX IF NOT EXISTS idx_content_schedule_status ON traffic_content_schedule(status);

-- =====================================================
-- WARMUP LOGS - логи прогрева аккаунтов
-- =====================================================
CREATE TABLE IF NOT EXISTS warmup_logs (
    id SERIAL PRIMARY KEY,
    account_id INTEGER REFERENCES traffic_accounts(id) ON DELETE CASCADE,

    -- Действие
    day INTEGER NOT NULL,
    phase INTEGER,  -- 1, 2, 3, 4
    action_type VARCHAR(50) NOT NULL,  -- message, reaction, subscribe, read, comment, create_channel, post
    action_target TEXT,  -- куда направлено действие (канал, чат, пользователь)
    action_count INTEGER DEFAULT 1,

    -- Результат
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,

    completed_at TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE warmup_logs IS 'Логи прогревочных действий аккаунтов';
CREATE INDEX IF NOT EXISTS idx_warmup_logs_account ON warmup_logs(account_id);
CREATE INDEX IF NOT EXISTS idx_warmup_logs_day ON warmup_logs(day);

-- =====================================================
-- WARMUP DAILY LIMITS - дневные лимиты по фазам
-- =====================================================
CREATE TABLE IF NOT EXISTS warmup_daily_limits (
    id SERIAL PRIMARY KEY,
    phase INTEGER NOT NULL,  -- 1, 2, 3, 4
    day_in_phase INTEGER NOT NULL,  -- 1-7 для каждой фазы

    -- Лимиты действий
    max_messages INTEGER DEFAULT 0,
    max_reactions INTEGER DEFAULT 0,
    max_subscriptions INTEGER DEFAULT 0,
    max_comments INTEGER DEFAULT 0,
    max_posts INTEGER DEFAULT 0,
    min_delay_seconds INTEGER DEFAULT 30,
    max_delay_seconds INTEGER DEFAULT 120,

    -- Описание
    description TEXT,

    UNIQUE(phase, day_in_phase)
);

COMMENT ON TABLE warmup_daily_limits IS 'Дневные лимиты действий по фазам прогрева';

-- Заполняем дефолтные лимиты (согласно 30-дневному плану)
INSERT INTO warmup_daily_limits (phase, day_in_phase, max_messages, max_reactions, max_subscriptions, max_comments, max_posts, min_delay_seconds, description)
VALUES
    -- ФАЗА 1: Дни 1-7 (Базовый траст)
    (1, 1, 0, 0, 0, 0, 0, 60, 'Настройка профиля, 2FA'),
    (1, 2, 0, 0, 7, 0, 0, 45, 'Подписка на 5-7 каналов'),
    (1, 3, 0, 0, 3, 0, 0, 45, 'Вступить в 2-3 чата'),
    (1, 4, 2, 0, 0, 0, 0, 60, 'Добавить контакты, 1-2 сообщения'),
    (1, 5, 5, 0, 0, 0, 0, 45, 'Ответить на сообщения'),
    (1, 6, 0, 10, 0, 0, 0, 30, 'Реакции в каналах'),
    (1, 7, 5, 0, 0, 3, 0, 30, 'Комментарии в чатах'),

    -- ФАЗА 2: Дни 8-14 (Наращивание)
    (2, 1, 10, 5, 5, 0, 0, 30, 'Подписки + комментарии'),
    (2, 2, 10, 0, 0, 0, 0, 30, 'Переписка, голосовые'),
    (2, 3, 15, 0, 0, 5, 0, 30, 'Активность в чатах'),
    (2, 4, 15, 0, 5, 0, 0, 30, 'Добавить контакты'),
    (2, 5, 10, 0, 0, 0, 0, 30, 'Репосты друзьям'),
    (2, 6, 0, 0, 0, 0, 1, 30, 'Создать приватный канал'),
    (2, 7, 0, 0, 0, 0, 3, 30, 'Пригласить друзей в канал'),

    -- ФАЗА 3: Дни 15-21 (Контент)
    (3, 1, 15, 5, 0, 0, 1, 30, 'Пост в личный канал'),
    (3, 2, 20, 5, 0, 0, 2, 30, 'Активность + посты'),
    (3, 3, 20, 5, 0, 0, 2, 30, 'Активность + посты'),
    (3, 4, 10, 0, 0, 0, 1, 30, 'Создать РАБОЧИЙ канал'),
    (3, 5, 10, 0, 0, 0, 3, 30, 'Опубликовать посты'),
    (3, 6, 10, 0, 0, 0, 1, 30, 'Прикрепить канал к профилю'),
    (3, 7, 10, 0, 0, 0, 1, 30, 'Закрепить пост'),

    -- ФАЗА 4: Дни 22-30 (Полноценная работа)
    (4, 1, 20, 10, 0, 5, 2, 30, 'Полноценный режим'),
    (4, 2, 20, 10, 0, 5, 2, 30, 'Полноценный режим'),
    (4, 3, 20, 10, 0, 5, 2, 30, 'Полноценный режим'),
    (4, 4, 20, 10, 0, 5, 3, 30, 'Полноценный режим'),
    (4, 5, 25, 10, 0, 5, 3, 30, 'Запуск рекламы'),
    (4, 6, 25, 10, 0, 5, 3, 30, 'Запуск рекламы'),
    (4, 7, 25, 10, 0, 5, 3, 30, 'Запуск рекламы'),
    (4, 8, 30, 15, 0, 10, 5, 30, 'Полноценный режим'),
    (4, 9, 30, 15, 0, 10, 5, 30, 'Полноценный режим')
ON CONFLICT (phase, day_in_phase) DO NOTHING;

-- =====================================================
-- PRODUCER AGENTS - агенты-продюсеры по сегментам
-- =====================================================
CREATE TABLE IF NOT EXISTS producer_agents (
    id SERIAL PRIMARY KEY,

    -- Настройки агента
    name VARCHAR(100) NOT NULL,
    segment VARCHAR(20) NOT NULL,  -- zozh, mama, business

    -- Статус
    status VARCHAR(20) DEFAULT 'active',  -- active, paused

    -- Настройки
    max_accounts INTEGER DEFAULT 10,
    max_channels_per_account INTEGER DEFAULT 2,

    -- Метрики
    total_subscribers INTEGER DEFAULT 0,
    total_clicks INTEGER DEFAULT 0,
    total_registrations INTEGER DEFAULT 0,

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE producer_agents IS 'Агенты-продюсеры для управления сегментами каналов';

-- Создаём 3 дефолтных агента по сегментам
INSERT INTO producer_agents (name, segment)
VALUES
    ('ЗОЖ Продюсер', 'zozh'),
    ('Мамы Продюсер', 'mama'),
    ('Бизнес Продюсер', 'business')
ON CONFLICT DO NOTHING;

-- =====================================================
-- ИНДЕКСЫ ДЛЯ ПРОИЗВОДИТЕЛЬНОСТИ
-- =====================================================
CREATE INDEX IF NOT EXISTS idx_traffic_accounts_status ON traffic_accounts(status);
CREATE INDEX IF NOT EXISTS idx_traffic_accounts_segment ON traffic_accounts(segment);
CREATE INDEX IF NOT EXISTS idx_traffic_accounts_warmup ON traffic_accounts(warmup_completed, warmup_day);

-- Функция автообновления updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Триггеры для автообновления
DROP TRIGGER IF EXISTS update_traffic_accounts_updated_at ON traffic_accounts;
CREATE TRIGGER update_traffic_accounts_updated_at
    BEFORE UPDATE ON traffic_accounts
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_traffic_channels_updated_at ON traffic_channels;
CREATE TRIGGER update_traffic_channels_updated_at
    BEFORE UPDATE ON traffic_channels
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_producer_agents_updated_at ON producer_agents;
CREATE TRIGGER update_producer_agents_updated_at
    BEFORE UPDATE ON producer_agents
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
