-- Migration 017: Channel posts and stories queue
-- Auto-posting content to thematic channels + story publishing

CREATE TABLE IF NOT EXISTS traffic_channel_posts (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER REFERENCES traffic_tenants(id),
    channel_id BIGINT NOT NULL,
    account_id INTEGER REFERENCES traffic_userbot_accounts(id),

    -- Content
    post_type VARCHAR(30) NOT NULL,  -- lifestyle, tips, motivation, product_mention, channel_promo
    content TEXT NOT NULL,
    media_file_id TEXT,
    media_type VARCHAR(20),  -- photo, video

    -- Story fields
    is_story BOOLEAN DEFAULT FALSE,
    story_privacy VARCHAR(20) DEFAULT 'public',  -- public, contacts, close_friends

    -- Status
    status VARCHAR(20) DEFAULT 'pending',  -- pending, published, failed, cancelled
    scheduled_at TIMESTAMPTZ,
    published_at TIMESTAMPTZ,

    -- Result
    message_id BIGINT,
    error_message TEXT,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_channel_post_status_scheduled ON traffic_channel_posts (status, scheduled_at);
CREATE INDEX IF NOT EXISTS idx_channel_post_account ON traffic_channel_posts (account_id);
CREATE INDEX IF NOT EXISTS idx_channel_post_tenant ON traffic_channel_posts (tenant_id);
