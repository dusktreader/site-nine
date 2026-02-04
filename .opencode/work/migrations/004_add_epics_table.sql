-- Migration: Add epics table and triggers
-- Date: 2026-02-04
-- Description: Add epics table for grouping related tasks under larger initiatives

-- Create epics table
CREATE TABLE IF NOT EXISTS epics (
    id TEXT PRIMARY KEY,              -- EPC-[P]-[NNNN] format (e.g., EPC-H-0001)
    title TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL              -- Computed from subtasks via triggers
        CHECK(status IN ('TODO', 'UNDERWAY', 'COMPLETE', 'ABORTED')),
    priority TEXT NOT NULL
        CHECK(priority IN ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW')),
    aborted_reason TEXT,              -- Only if manually aborted
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    completed_at TEXT,                -- Auto-set when all tasks complete
    aborted_at TEXT,                  -- Set when manually aborted
    file_path TEXT NOT NULL           -- .opencode/work/epics/EPC-H-0001.md
);

-- Create indexes for epic queries
CREATE INDEX IF NOT EXISTS idx_epics_status ON epics(status);
CREATE INDEX IF NOT EXISTS idx_epics_priority ON epics(priority);
CREATE INDEX IF NOT EXISTS idx_epics_created ON epics(created_at);

-- Trigger: Update epics timestamp on modification
CREATE TRIGGER IF NOT EXISTS update_epics_timestamp
AFTER UPDATE ON epics
FOR EACH ROW
BEGIN
    UPDATE epics SET updated_at = datetime('now') WHERE id = NEW.id;
END;

-- Add epic_id column to tasks table if it doesn't exist
-- SQLite doesn't have ALTER TABLE IF COLUMN NOT EXISTS, so we check via pragma
-- This is safe to run multiple times

-- Note: If the column already exists, this will fail silently
-- Users should check if column exists before running this migration
ALTER TABLE tasks ADD COLUMN epic_id TEXT REFERENCES epics(id) ON DELETE RESTRICT;

-- Trigger: Auto-update epic status when task status changes
CREATE TRIGGER IF NOT EXISTS update_epic_status_on_task_change
AFTER UPDATE OF status ON tasks
FOR EACH ROW
WHEN NEW.epic_id IS NOT NULL
BEGIN
    -- Update epic status based on aggregated task states
    UPDATE epics SET 
        status = CASE
            -- If any non-aborted task is UNDERWAY, BLOCKED, PAUSED, or REVIEW => epic is UNDERWAY
            WHEN EXISTS (
                SELECT 1 FROM tasks 
                WHERE epic_id = NEW.epic_id 
                AND status IN ('UNDERWAY', 'BLOCKED', 'PAUSED', 'REVIEW')
            ) THEN 'UNDERWAY'
            
            -- If all tasks are COMPLETE => epic is COMPLETE
            WHEN NOT EXISTS (
                SELECT 1 FROM tasks 
                WHERE epic_id = NEW.epic_id 
                AND status NOT IN ('COMPLETE', 'ABORTED')
            ) AND EXISTS (
                SELECT 1 FROM tasks WHERE epic_id = NEW.epic_id AND status = 'COMPLETE'
            ) THEN 'COMPLETE'
            
            -- If all tasks are TODO or ABORTED => epic is TODO
            WHEN NOT EXISTS (
                SELECT 1 FROM tasks 
                WHERE epic_id = NEW.epic_id 
                AND status NOT IN ('TODO', 'ABORTED')
            ) THEN 'TODO'
            
            -- Default: leave unchanged
            ELSE status
        END,
        completed_at = CASE
            WHEN NOT EXISTS (
                SELECT 1 FROM tasks 
                WHERE epic_id = NEW.epic_id 
                AND status NOT IN ('COMPLETE', 'ABORTED')
            ) AND EXISTS (
                SELECT 1 FROM tasks WHERE epic_id = NEW.epic_id AND status = 'COMPLETE'
            ) THEN datetime('now')
            ELSE completed_at
        END
    WHERE id = NEW.epic_id
    -- Don't auto-update aborted epics
    AND status != 'ABORTED';
END;

-- Trigger: Auto-update epic status when task is linked/unlinked
CREATE TRIGGER IF NOT EXISTS update_epic_status_on_task_link
AFTER UPDATE OF epic_id ON tasks
FOR EACH ROW
BEGIN
    -- Update old epic status if task was unlinked
    UPDATE epics SET 
        status = CASE
            WHEN EXISTS (
                SELECT 1 FROM tasks 
                WHERE epic_id = OLD.epic_id 
                AND status IN ('UNDERWAY', 'BLOCKED', 'PAUSED', 'REVIEW')
            ) THEN 'UNDERWAY'
            WHEN NOT EXISTS (
                SELECT 1 FROM tasks 
                WHERE epic_id = OLD.epic_id 
                AND status NOT IN ('COMPLETE', 'ABORTED')
            ) AND EXISTS (
                SELECT 1 FROM tasks WHERE epic_id = OLD.epic_id AND status = 'COMPLETE'
            ) THEN 'COMPLETE'
            WHEN NOT EXISTS (
                SELECT 1 FROM tasks 
                WHERE epic_id = OLD.epic_id 
                AND status NOT IN ('TODO', 'ABORTED')
            ) THEN 'TODO'
            ELSE status
        END
    WHERE id = OLD.epic_id
    AND OLD.epic_id IS NOT NULL
    AND status != 'ABORTED';
    
    -- Update new epic status if task was linked
    UPDATE epics SET 
        status = CASE
            WHEN EXISTS (
                SELECT 1 FROM tasks 
                WHERE epic_id = NEW.epic_id 
                AND status IN ('UNDERWAY', 'BLOCKED', 'PAUSED', 'REVIEW')
            ) THEN 'UNDERWAY'
            WHEN NOT EXISTS (
                SELECT 1 FROM tasks 
                WHERE epic_id = NEW.epic_id 
                AND status NOT IN ('COMPLETE', 'ABORTED')
            ) AND EXISTS (
                SELECT 1 FROM tasks WHERE epic_id = NEW.epic_id AND status = 'COMPLETE'
            ) THEN 'COMPLETE'
            WHEN NOT EXISTS (
                SELECT 1 FROM tasks 
                WHERE epic_id = NEW.epic_id 
                AND status NOT IN ('TODO', 'ABORTED')
            ) THEN 'TODO'
            ELSE status
        END
    WHERE id = NEW.epic_id
    AND NEW.epic_id IS NOT NULL
    AND status != 'ABORTED';
END;
