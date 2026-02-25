-- Migration 016: Add linked channel fields to accounts
-- Links bot accounts to thematic channels (funnel level 2)

ALTER TABLE traffic_userbot_accounts
    ADD COLUMN IF NOT EXISTS linked_channel_id BIGINT,
    ADD COLUMN IF NOT EXISTS linked_channel_username VARCHAR(100);

COMMENT ON COLUMN traffic_userbot_accounts.linked_channel_id IS 'Telegram ID тематического канала, на который ведёт аккаунт';
COMMENT ON COLUMN traffic_userbot_accounts.linked_channel_username IS '@username тематического канала (для ссылки в био)';
