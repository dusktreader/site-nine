-- Migration: Add handoffs table
-- Date: 2026-02-04
-- Purpose: Track work handoffs between missions and roles

CREATE TABLE IF NOT EXISTS handoffs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,                    -- Associated task being handed off
    from_mission_id INTEGER NOT NULL,         -- Mission handing off the work
    to_role TEXT NOT NULL                     -- Role receiving the handoff
        CHECK(to_role IN ('Administrator', 'Architect', 'Engineer', 'Tester', 'Documentarian', 'Designer', 'Inspector', 'Operator', 'Historian')),
    to_mission_id INTEGER,                    -- Mission that accepted the handoff (NULL if pending)
    status TEXT NOT NULL DEFAULT 'pending'    -- Handoff status
        CHECK(status IN ('pending', 'accepted', 'completed', 'cancelled')),
    
    -- Handoff content
    summary TEXT NOT NULL,                    -- Brief summary of what's being handed off
    files TEXT,                               -- JSON array of relevant file paths
    acceptance_criteria TEXT,                 -- What defines completion
    notes TEXT,                               -- Additional context or instructions
    
    -- Timestamps
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    accepted_at TEXT,                         -- When handoff was accepted
    completed_at TEXT,                        -- When work was completed
    
    -- Foreign keys
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
    FOREIGN KEY (from_mission_id) REFERENCES missions(id) ON DELETE CASCADE,
    FOREIGN KEY (to_mission_id) REFERENCES missions(id) ON DELETE SET NULL
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_handoffs_task_id ON handoffs(task_id);
CREATE INDEX IF NOT EXISTS idx_handoffs_from_mission ON handoffs(from_mission_id);
CREATE INDEX IF NOT EXISTS idx_handoffs_to_mission ON handoffs(to_mission_id);
CREATE INDEX IF NOT EXISTS idx_handoffs_to_role ON handoffs(to_role);
CREATE INDEX IF NOT EXISTS idx_handoffs_status ON handoffs(status);
CREATE INDEX IF NOT EXISTS idx_handoffs_created_at ON handoffs(created_at);
