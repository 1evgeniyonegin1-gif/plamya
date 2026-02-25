-- Миграция 005: Персистентное хранение контекста диалоговой воронки
-- Дата: 2026-02-02
-- Описание: Добавляет поля для хранения состояния воронки в БД (раньше было в RAM)

-- Добавляем новые поля в таблицу conversation_contexts
-- Если таблица уже существует с базовыми полями

ALTER TABLE conversation_contexts
    ADD COLUMN IF NOT EXISTS funnel_stage VARCHAR(50) DEFAULT 'greeting',
    ADD COLUMN IF NOT EXISTS funnel_intent VARCHAR(50) DEFAULT 'unknown',
    ADD COLUMN IF NOT EXISTS lead_temperature VARCHAR(20) DEFAULT 'warm',
    ADD COLUMN IF NOT EXISTS pains TEXT[] DEFAULT '{}',
    ADD COLUMN IF NOT EXISTS needs TEXT[] DEFAULT '{}',
    ADD COLUMN IF NOT EXISTS objections TEXT[] DEFAULT '{}',
    ADD COLUMN IF NOT EXISTS engagement_score INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS trust_score INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS objection_count INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS messages_count INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS suggested_products TEXT[] DEFAULT '{}',
    ADD COLUMN IF NOT EXISTS suggested_business BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS link_provided BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS conversation_started_at TIMESTAMP,
    ADD COLUMN IF NOT EXISTS last_funnel_activity TIMESTAMP;

-- Комментарии для документации
COMMENT ON COLUMN conversation_contexts.funnel_stage IS 'Этап воронки: greeting, discovery, deepening, solution_hint, solution, objection, closing, follow_up';
COMMENT ON COLUMN conversation_contexts.funnel_intent IS 'Намерение пользователя: product, business, skeptic, curious, support, unknown';
COMMENT ON COLUMN conversation_contexts.lead_temperature IS 'Температура лида: hot (сразу ссылки), warm (стандартный прогрев), cold (длинный прогрев)';
COMMENT ON COLUMN conversation_contexts.pains IS 'Выявленные боли: energy, weight, skin, immunity, sleep, sport, kids, money';
COMMENT ON COLUMN conversation_contexts.objections IS 'Возражения: price, trust, time, delay';
COMMENT ON COLUMN conversation_contexts.engagement_score IS 'Уровень вовлечённости 0-10';
COMMENT ON COLUMN conversation_contexts.trust_score IS 'Уровень доверия 0-5';
COMMENT ON COLUMN conversation_contexts.link_provided IS 'Была ли уже дана ссылка (чтобы не дублировать)';

-- Индекс для быстрого поиска пользователей по этапу воронки
CREATE INDEX IF NOT EXISTS idx_conversation_contexts_funnel_stage
    ON conversation_contexts(funnel_stage);

-- Индекс для поиска по намерению
CREATE INDEX IF NOT EXISTS idx_conversation_contexts_funnel_intent
    ON conversation_contexts(funnel_intent);

-- Индекс для поиска по температуре лида
CREATE INDEX IF NOT EXISTS idx_conversation_contexts_lead_temperature
    ON conversation_contexts(lead_temperature);
