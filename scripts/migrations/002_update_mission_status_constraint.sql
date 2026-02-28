-- Migration: Update mission status CHECK constraint for ADR-013
-- Date: 2026-02-18
-- Purpose: Add ROLE_PENDING, PERSONA_PENDING, and SUSPENDED to allowed status values
--
-- SQLite doesn't support altering CHECK constraints, so we need to:
-- 1. Create a new table with the updated constraint
-- 2. Copy all data from the old table
-- 3. Drop the old table
-- 4. Rename the new table
-- 5. Recreate all indexes and triggers
--
-- Related: EPC-H-0006, OPR-H-0139, ADR-013

-- Note: This migration assumes the table already has the ADR-013 columns added by migration 001

-- Disable foreign key constraints temporarily
PRAGMA foreign_keys = OFF;

BEGIN TRANSACTION;

-- Step 1: Create new table with updated CHECK constraint
CREATE TABLE missions_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    persona_name TEXT NOT NULL,
    role TEXT NOT NULL
        CHECK(role IN ('Administrator', 'Architect', 'Engineer', 'Tester', 'Documentarian', 'Designer', 'Inspector', 'Operator', 'Historian')),
    codename TEXT NOT NULL,
    mission_file TEXT NOT NULL,
    start_date TEXT NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT,
    objective TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    epic_id TEXT REFERENCES epics(id) ON DELETE SET NULL,
    desk_mode_active INTEGER DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'ACTIVE'
        CHECK(status IN ('ACTIVE', 'IDLE', 'ENDED', 'SUSPENDED', 'ROLE_PENDING', 'PERSONA_PENDING')),
    last_active_at TEXT,
    opencode_session_id TEXT,
    mode TEXT DEFAULT 'interactive',
    last_activity_at TEXT,
    suspension_time TEXT,
    suspension_reason TEXT,
    CHECK(length(persona_name) > 0),
    CHECK(length(mission_file) > 0),
    FOREIGN KEY (persona_name) REFERENCES personas(name) ON DELETE RESTRICT
);

-- Step 2: Copy all data from old table to new table
INSERT INTO missions_new (
    id, persona_name, role, codename, mission_file, start_date, start_time, end_time, objective,
    created_at, updated_at, epic_id, desk_mode_active, status, last_active_at,
    opencode_session_id, mode, last_activity_at, suspension_time, suspension_reason
)
SELECT 
    id, persona_name, role, codename, mission_file, start_date, start_time, end_time, objective,
    created_at, updated_at, epic_id, desk_mode_active, status, last_active_at,
    opencode_session_id, mode, last_activity_at, suspension_time, suspension_reason
FROM missions;

-- Step 3: Drop old table
DROP TABLE missions;

-- Step 4: Rename new table to original name
ALTER TABLE missions_new RENAME TO missions;

-- Step 5: Recreate all indexes
CREATE INDEX idx_missions_persona_name ON missions(persona_name);
CREATE INDEX idx_missions_role ON missions(role);
CREATE INDEX idx_missions_start_date ON missions(start_date);
CREATE INDEX idx_missions_codename ON missions(codename);
CREATE INDEX idx_missions_epic_id ON missions(epic_id);
CREATE INDEX idx_missions_desk_mode ON missions(desk_mode_active);
CREATE INDEX idx_missions_status ON missions(status);
CREATE UNIQUE INDEX idx_missions_session_id ON missions(opencode_session_id) WHERE opencode_session_id IS NOT NULL;
CREATE INDEX idx_missions_mode ON missions(mode);
CREATE INDEX idx_missions_suspended ON missions(status, suspension_time) WHERE status = 'SUSPENDED';

-- Step 6: Recreate trigger
CREATE TRIGGER update_missions_timestamp
AFTER UPDATE ON missions
FOR EACH ROW
BEGIN
    UPDATE missions SET updated_at = datetime('now') WHERE id = NEW.id;
END;

COMMIT;

-- Re-enable foreign key constraints
PRAGMA foreign_keys = ON;
