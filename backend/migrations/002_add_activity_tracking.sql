-- Migration: Add visit_count and last_active_at to users table
-- Tracks actual site usage (throttled to 15-min windows) vs login-only tracking

ALTER TABLE users ADD COLUMN IF NOT EXISTS last_active_at TIMESTAMP;
ALTER TABLE users ADD COLUMN IF NOT EXISTS visit_count INTEGER NOT NULL DEFAULT 0;
