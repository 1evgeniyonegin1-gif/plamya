-- Migration 013: Smart Comments + Content Factory fields
-- Traffic Engine: сегменты, умные комменты, reply tracking, anti-spam
-- Date: 2026-02-10

-- ===========================================
-- 1. UserBotAccount: сегмент + пол
-- ===========================================
ALTER TABLE traffic_userbot_accounts
    ADD COLUMN IF NOT EXISTS gender VARCHAR(10),
    ADD COLUMN IF NOT EXISTS segment VARCHAR(20);

CREATE INDEX IF NOT EXISTS idx_account_segment
    ON traffic_userbot_accounts(segment);

-- ===========================================
-- 2. TargetChannel: сегмент + anti-spam
-- ===========================================
ALTER TABLE traffic_target_channels
    ADD COLUMN IF NOT EXISTS segment VARCHAR(20),
    ADD COLUMN IF NOT EXISTS joined_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS has_antibot BOOLEAN DEFAULT FALSE;

-- ===========================================
-- 3. TrafficAction: smart comment metadata + reply tracking
-- ===========================================
ALTER TABLE traffic_actions
    ADD COLUMN IF NOT EXISTS comment_message_id BIGINT,
    ADD COLUMN IF NOT EXISTS strategy_used VARCHAR(50),
    ADD COLUMN IF NOT EXISTS relevance_score FLOAT,
    ADD COLUMN IF NOT EXISTS post_topic VARCHAR(200),
    ADD COLUMN IF NOT EXISTS got_reply BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS reply_count INTEGER DEFAULT 0;

CREATE INDEX IF NOT EXISTS idx_action_comment_msg
    ON traffic_actions(comment_message_id)
    WHERE comment_message_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_action_got_reply
    ON traffic_actions(got_reply)
    WHERE got_reply = TRUE;

-- ===========================================
-- 4. Strategy Effectiveness (MAB self-evolution)
-- ===========================================
CREATE TABLE IF NOT EXISTS traffic_strategy_effectiveness (
    id SERIAL PRIMARY KEY,
    segment VARCHAR(20) NOT NULL,
    channel_username VARCHAR(100),
    comment_strategy VARCHAR(50) NOT NULL,
    time_slot VARCHAR(20),           -- morning (6-12), afternoon (12-18), evening (18-24)
    post_topic VARCHAR(100),
    attempts INTEGER DEFAULT 0,
    successes FLOAT DEFAULT 0,       -- weighted: reply=1.0, reaction=0.5
    score FLOAT DEFAULT 0.5,         -- computed: successes/attempts
    last_updated TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_strategy_eff_lookup
    ON traffic_strategy_effectiveness(segment, channel_username, comment_strategy);

-- ===========================================
-- 5. Деактивировать мёртвые каналы
-- ===========================================
UPDATE traffic_target_channels
SET is_active = FALSE
WHERE username IN ('getleanru', 'fitnessmania', 'dnevnik_pitaniya', 'fediatrics');

-- ===========================================
-- 6. Сегменты для существующих каналов (по тематике)
-- ===========================================
-- ЗОЖ / Питание каналы
UPDATE traffic_target_channels
SET segment = 'zozh'
WHERE username IN (
    'rpn_zdorovoepitanie', 'sektaschool', 'ppfoodrecept',
    'doctor_annamama', 'budniploxoimateri'
) AND segment IS NULL;

-- Мамские каналы
UPDATE traffic_target_channels
SET segment = 'mama'
WHERE username IN (
    'doctor_annamama', 'budniploxoimateri', '3moms'
) AND segment IS NULL;

-- Универсальные (подходят для всех)
UPDATE traffic_target_channels
SET segment = 'universal'
WHERE segment IS NULL AND is_active = TRUE;
