-- Add fantasy_points column to club_stats table
ALTER TABLE club_stats ADD COLUMN IF NOT EXISTS fantasy_points NUMERIC(6, 2);
