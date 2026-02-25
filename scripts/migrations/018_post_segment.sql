-- Migration 018: Add segment field to posts table for thematic channels
-- Run: psql -h localhost -U postgres -d nl_international < scripts/migrations/018_post_segment.sql

ALTER TABLE posts ADD COLUMN IF NOT EXISTS segment VARCHAR(30);
CREATE INDEX IF NOT EXISTS idx_posts_segment ON posts(segment);

-- Verify
SELECT column_name, data_type FROM information_schema.columns
WHERE table_name = 'posts' AND column_name = 'segment';
