-- Создание таблицы для прогресса онбординга
-- Выполнить на сервере: psql -U postgres -d nl_international -f create_onboarding_table.sql

CREATE TABLE IF NOT EXISTS user_onboarding_progress (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    current_day INTEGER NOT NULL DEFAULT 1,
    completed_tasks TEXT[] DEFAULT '{}',
    started_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    last_activity TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    last_reminder_hours INTEGER DEFAULT 0,
    is_completed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

-- Индекс для быстрого поиска по user_id
CREATE INDEX IF NOT EXISTS idx_onboarding_user_id ON user_onboarding_progress(user_id);

-- Индекс для поиска неактивных пользователей
CREATE INDEX IF NOT EXISTS idx_onboarding_last_activity ON user_onboarding_progress(last_activity);

-- Индекс для поиска незавершённых онбордингов
CREATE INDEX IF NOT EXISTS idx_onboarding_not_completed ON user_onboarding_progress(is_completed) WHERE is_completed = FALSE;

-- Комментарий к таблице
COMMENT ON TABLE user_onboarding_progress IS 'Прогресс 7-дневного онбординга пользователей';
COMMENT ON COLUMN user_onboarding_progress.current_day IS 'Текущий день онбординга (1-7)';
COMMENT ON COLUMN user_onboarding_progress.completed_tasks IS 'Массив ID выполненных задач';
COMMENT ON COLUMN user_onboarding_progress.last_reminder_hours IS 'На каком пороге часов неактивности отправлено последнее напоминание';
