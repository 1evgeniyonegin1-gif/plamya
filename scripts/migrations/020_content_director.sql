-- Migration 020: AI Content Director
-- Недельные планы, structured memory, self-review

-- Недельные планы контента
CREATE TABLE IF NOT EXISTS content_plans (
    id SERIAL PRIMARY KEY,
    segment VARCHAR(30) NOT NULL,
    week_start DATE NOT NULL,
    plan_data JSONB NOT NULL DEFAULT '[]',
    slots_used INTEGER DEFAULT 0,
    slots_total INTEGER DEFAULT 10,
    performance_snapshot JSONB,
    status VARCHAR(20) DEFAULT 'active',
    ai_model VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_content_plans_segment ON content_plans(segment, week_start);

-- Структурированная память канала
CREATE TABLE IF NOT EXISTS channel_memory (
    id SERIAL PRIMARY KEY,
    segment VARCHAR(30) UNIQUE NOT NULL,
    state_data JSONB NOT NULL DEFAULT '{}',
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Самоанализ контента
CREATE TABLE IF NOT EXISTS content_self_reviews (
    id SERIAL PRIMARY KEY,
    segment VARCHAR(30) NOT NULL,
    posts_reviewed INTEGER DEFAULT 0,
    review_data JSONB NOT NULL DEFAULT '{}',
    applied BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_content_reviews_segment ON content_self_reviews(segment, created_at);
