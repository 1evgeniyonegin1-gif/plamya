-- =====================================================
-- Миграция 003: System Events и Onboarding Fix
-- Дата: 2026-01-26
-- Описание: Добавляет таблицу system_events для событий между ботами
--          и проверяет/создаёт таблицу user_onboarding_progress
-- =====================================================

-- Таблица событий для коммуникации между ботами
CREATE TABLE IF NOT EXISTS system_events (
    id SERIAL PRIMARY KEY,
    event_type VARCHAR(50) NOT NULL,
    source VARCHAR(50) NOT NULL,
    payload JSONB NOT NULL,
    processed BOOLEAN DEFAULT FALSE,
    processed_at TIMESTAMP,
    target_module VARCHAR(50),
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Индексы для быстрого поиска событий
CREATE INDEX IF NOT EXISTS idx_system_events_type ON system_events(event_type);
CREATE INDEX IF NOT EXISTS idx_system_events_processed ON system_events(processed);
CREATE INDEX IF NOT EXISTS idx_system_events_expires ON system_events(expires_at);
CREATE INDEX IF NOT EXISTS idx_system_events_target ON system_events(target_module);

-- Таблица прогресса онбординга (должна существовать, но проверяем)
CREATE TABLE IF NOT EXISTS user_onboarding_progress (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    current_day INTEGER DEFAULT 1,
    completed_tasks TEXT[] DEFAULT ARRAY[]::TEXT[],
    started_at TIMESTAMP DEFAULT NOW(),
    last_activity TIMESTAMP DEFAULT NOW(),
    last_reminder_hours INTEGER DEFAULT 0,
    is_completed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id)
);

-- Индексы для онбординга
CREATE INDEX IF NOT EXISTS idx_user_onboarding_user_id ON user_onboarding_progress(user_id);
CREATE INDEX IF NOT EXISTS idx_user_onboarding_completed ON user_onboarding_progress(is_completed);

-- Комментарии для документации
COMMENT ON TABLE system_events IS 'События в системе для межмодульной коммуникации между curator_bot и content_manager_bot';
COMMENT ON COLUMN system_events.event_type IS 'Тип события: post_published, user_registered и т.д.';
COMMENT ON COLUMN system_events.source IS 'Источник события: content_manager, curator';
COMMENT ON COLUMN system_events.payload IS 'Данные события в JSON формате';
COMMENT ON COLUMN system_events.processed IS 'Обработано ли событие целевым модулем';
COMMENT ON COLUMN system_events.target_module IS 'Целевой модуль: curator, all, NULL (для всех)';
COMMENT ON COLUMN system_events.expires_at IS 'Время истечения события (TTL)';

COMMENT ON TABLE user_onboarding_progress IS '7-дневный чеклист онбординга для новых пользователей curator_bot';
COMMENT ON COLUMN user_onboarding_progress.current_day IS 'Текущий день онбординга (1-7)';
COMMENT ON COLUMN user_onboarding_progress.completed_tasks IS 'Массив ID выполненных задач (d1_catalog, d2_ed и т.д.)';
COMMENT ON COLUMN user_onboarding_progress.last_reminder_hours IS 'Пороговое значение последнего напоминания (4, 12, 24, 48, 168)';
