-- Migration: Add external_id, height, weight to players table
-- Run this against your PostgreSQL database

ALTER TABLE players ADD COLUMN IF NOT EXISTS external_id VARCHAR(50) UNIQUE;
ALTER TABLE players ADD COLUMN IF NOT EXISTS height INTEGER;
ALTER TABLE players ADD COLUMN IF NOT EXISTS weight INTEGER;

-- Create index on external_id for faster lookups
CREATE INDEX IF NOT EXISTS idx_players_external_id ON players(external_id);
