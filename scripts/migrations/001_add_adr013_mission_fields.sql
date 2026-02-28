-- Migration: Add ADR-013 mission fields
-- Date: 2026-02-18
-- Purpose: Add OpenCode session integration fields to missions table per ADR-013
--
-- This migration adds:
-- - opencode_session_id: Binds missions to OpenCode sessions
-- - mode: Tracks whether mission is interactive or desk mode
-- - last_activity_at: Tracks session activity for stale detection
-- - suspension_time: Records when mission was suspended
-- - suspension_reason: Records why mission was suspended
--
-- Related: EPC-H-0006, OPR-H-0138, ADR-013

-- Add new columns to missions table
-- Note: SQLite does not support adding UNIQUE constraint directly in ALTER TABLE
-- We add the column without UNIQUE, then create a unique index
ALTER TABLE missions ADD COLUMN opencode_session_id TEXT;
ALTER TABLE missions ADD COLUMN mode TEXT DEFAULT 'interactive';
ALTER TABLE missions ADD COLUMN last_activity_at TEXT;
ALTER TABLE missions ADD COLUMN suspension_time TEXT;
ALTER TABLE missions ADD COLUMN suspension_reason TEXT;

-- Create indexes for new columns
-- A unique index enforces the same constraint as UNIQUE column
CREATE UNIQUE INDEX idx_missions_session_id ON missions(opencode_session_id) WHERE opencode_session_id IS NOT NULL;
CREATE INDEX idx_missions_mode ON missions(mode);
CREATE INDEX idx_missions_suspended ON missions(status, suspension_time) WHERE status = 'SUSPENDED';
