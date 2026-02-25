-- Migration 019: Discipline Bot tables
-- Трекер дисциплины через Telethon-аккаунт
-- Run: psql -h localhost -U postgres -d nl_international < scripts/migrations/019_discipline_bot.sql

-- ═══════════════════════════════════════════════════
-- 1. discipline_config — настройки (1 строка на юзера)
-- ═══════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS discipline_config (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT NOT NULL UNIQUE,

    -- Сезонный подъём
    winter_morning TIME NOT NULL DEFAULT '06:00',    -- дек-фев
    summer_morning TIME NOT NULL DEFAULT '05:00',    -- мар-ноя
    morning_grace_minutes INT NOT NULL DEFAULT 30,

    -- Вечерний разбор
    evening_time TIME NOT NULL DEFAULT '22:00',

    -- Напоминание по рабочему плану
    work_reminder_time TIME NOT NULL DEFAULT '18:00',

    -- Тихие часы
    quiet_start TIME NOT NULL DEFAULT '23:00',
    quiet_end TIME NOT NULL DEFAULT '04:30',

    -- Фиксированный аккаунт (NULL = автовыбор)
    discipline_account_id INT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Дефолтная конфигурация для Данила
INSERT INTO discipline_config (telegram_id)
VALUES (756877849)
ON CONFLICT (telegram_id) DO NOTHING;

-- ═══════════════════════════════════════════════════
-- 2. discipline_habits — привычки
-- ═══════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS discipline_habits (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT NOT NULL,

    name VARCHAR(100) NOT NULL,
    emoji VARCHAR(10) DEFAULT '✅',

    -- Временное окно (MSK). NULL = в любое время
    window_start TIME,
    window_end TIME,

    sort_order INT NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,

    -- Стрики
    current_streak INT NOT NULL DEFAULT 0,
    best_streak INT NOT NULL DEFAULT 0,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_dh_telegram_active ON discipline_habits(telegram_id, is_active);

-- Дефолтные привычки для Данила
INSERT INTO discipline_habits (telegram_id, name, emoji, window_start, window_end, sort_order) VALUES
(756877849, 'Медитация', '🧘', '05:00', '08:00', 1),
(756877849, 'Холодный душ', '🚿', '05:00', '07:00', 2),
(756877849, 'Планёрка', '📓', '05:00', '09:00', 3),
(756877849, 'Тренировка', '💪', NULL, '20:00', 4)
ON CONFLICT DO NOTHING;

-- ═══════════════════════════════════════════════════
-- 3. discipline_habit_logs — ежедневные логи привычек
-- ═══════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS discipline_habit_logs (
    id SERIAL PRIMARY KEY,
    habit_id INT NOT NULL REFERENCES discipline_habits(id) ON DELETE CASCADE,
    log_date DATE NOT NULL,

    completed_at TIMESTAMPTZ,
    skipped BOOLEAN NOT NULL DEFAULT FALSE,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(habit_id, log_date)
);

CREATE INDEX IF NOT EXISTS idx_dhl_habit_date ON discipline_habit_logs(habit_id, log_date DESC);

-- ═══════════════════════════════════════════════════
-- 4. discipline_daily_plans — рабочие планы на день
-- ═══════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS discipline_daily_plans (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT NOT NULL,
    plan_date DATE NOT NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(telegram_id, plan_date)
);

-- ═══════════════════════════════════════════════════
-- 5. discipline_plan_tasks — задачи плана
-- ═══════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS discipline_plan_tasks (
    id SERIAL PRIMARY KEY,
    plan_id INT NOT NULL REFERENCES discipline_daily_plans(id) ON DELETE CASCADE,

    task_text TEXT NOT NULL,
    sort_order INT NOT NULL DEFAULT 0,
    completed_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_dpt_plan ON discipline_plan_tasks(plan_id);

-- ═══════════════════════════════════════════════════
-- 6. discipline_daily_reviews — вечерние AI-разборы
-- ═══════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS discipline_daily_reviews (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT NOT NULL,
    review_date DATE NOT NULL,

    reflection_text TEXT,
    ai_analysis TEXT,

    habits_completed INT NOT NULL DEFAULT 0,
    habits_total INT NOT NULL DEFAULT 0,
    tasks_completed INT NOT NULL DEFAULT 0,
    tasks_total INT NOT NULL DEFAULT 0,
    score FLOAT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(telegram_id, review_date)
);

-- ═══════════════════════════════════════════════════
-- 7. discipline_checkins — чек-ины с таймингом
-- ═══════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS discipline_checkins (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT NOT NULL,

    checkin_type VARCHAR(30) NOT NULL,  -- morning, evening, habit, work
    checkin_date DATE NOT NULL,
    response_time_seconds INT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_dc_type_date ON discipline_checkins(telegram_id, checkin_type, checkin_date DESC);
