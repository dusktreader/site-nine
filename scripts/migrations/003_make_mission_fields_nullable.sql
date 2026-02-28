-- Migration: Make mission identity fields nullable for ROLE_PENDING/PERSONA_PENDING support
-- Date: 2026-02-19
-- Purpose: Allow mission_init tool to create missions before role/persona are known per ADR-013
--
-- Changes:
-- - persona_name: NOT NULL + CHECK(length > 0) → NULL allowed, FK enforced when present
-- - role: NOT NULL + CHECK(role IN ...) → NULL allowed, CHECK applied when not NULL
-- - codename: NOT NULL + CHECK(length > 0) → NULL allowed, CHECK applied when not NULL
-- - mission_file: NOT NULL + CHECK(length > 0) → NULL allowed, CHECK applied when not NULL
-- - start_date: NOT NULL → NULL allowed
-- - start_time: NOT NULL → NULL allowed
--
-- Rationale:
-- The mission lifecycle per ADR-013 begins with mission_init (status=ROLE_PENDING), which
-- creates a mission record before role or persona are selected. The current NOT NULL constraints
-- prevent this. Making these fields nullable allows the lifecycle to proceed step by step:
--   mission_init    → ROLE_PENDING    (no role, persona, file)
--   mission_role_record → PERSONA_PENDING (role set, still no persona)
--   mission_persona_record → ACTIVE   (persona set, file created, fully initialized)
--
-- Related: EPC-H-0006, ENG-H-0143, ADR-013

PRAGMA foreign_keys = OFF;

BEGIN TRANSACTION;

-- Step 1: Create new table with nullable identity fields
CREATE TABLE missions_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    persona_name TEXT,
    role TEXT
        CHECK(role IS NULL OR role IN ('Administrator', 'Architect', 'Engineer', 'Tester', 'Documentarian', 'Designer', 'Inspector', 'Operator', 'Historian')),
    codename TEXT,
    mission_file TEXT,
    start_date TEXT,
    start_time TEXT,
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
    CHECK(persona_name IS NULL OR length(persona_name) > 0),
    CHECK(codename IS NULL OR length(codename) > 0),
    CHECK(mission_file IS NULL OR length(mission_file) > 0),
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

PRAGMA foreign_keys = ON;
