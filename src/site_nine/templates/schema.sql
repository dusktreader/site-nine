-- Crol Troll Project Management Database Schema
-- Created: 2026-01-30
-- Updated: 2026-02-03 (Added epics, renamed to personas/missions per ADR-006)
-- 
-- This database manages:
-- 1. Tasks - Development work tracking
-- 2. Epics - Task grouping and organization
-- 3. Personas - Named identities with mythological backgrounds
-- 4. Missions - Work assignments using personas

-- ============================================================================
-- PERSONAS TABLE
-- ============================================================================
-- Stores persona names from mythology organized by role
CREATE TABLE personas (
    name TEXT PRIMARY KEY,                -- Persona name (lowercase, e.g., 'atlas', 'terminus')
    role TEXT NOT NULL                    -- Primary role this name suits
        CHECK(role IN ('Administrator', 'Architect', 'Builder', 'Tester', 'Documentarian', 'Designer', 'Inspector', 'Operator', 'Historian')),
    mythology TEXT NOT NULL,              -- Mythology/religion origin (e.g., 'Greek', 'Roman', 'Norse')
    description TEXT NOT NULL,            -- Brief description of the deity/daemon
    mission_count INTEGER NOT NULL DEFAULT 0, -- How many times this name has been used
    last_mission_at TEXT,                 -- ISO 8601 timestamp of last usage
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    
    -- Indexes
    CHECK(length(name) > 0)
);

CREATE INDEX idx_personas_role ON personas(role);
CREATE INDEX idx_personas_usage ON personas(mission_count);
CREATE INDEX idx_personas_last_used ON personas(last_mission_at);

-- ============================================================================
-- MISSIONS TABLE
-- ============================================================================
-- Tracks missions (work assignments using personas)
CREATE TABLE missions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    persona_name TEXT NOT NULL,           -- Persona name (e.g., 'terminus', 'atlas')
    role TEXT NOT NULL                    -- Persona role for this mission
        CHECK(role IN ('Administrator', 'Architect', 'Builder', 'Tester', 'Documentarian', 'Designer', 'Inspector', 'Operator', 'Historian')),
    codename TEXT NOT NULL,               -- Mission codename (e.g., 'silent-phoenix', 'bold-shadow')
    mission_file TEXT NOT NULL,           -- Path to mission file (e.g., '.opencode/work/missions/2026-01-30.09:15:55.operator.terminus.silent-phoenix.md')
    start_time TEXT NOT NULL,             -- Mission start time (ISO 8601)
    end_time TEXT,                        -- Mission end time (ISO 8601) or NULL if in progress
    objective TEXT,                       -- Brief mission objective
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    
    -- Constraints
    CHECK(length(persona_name) > 0),
    CHECK(length(codename) > 0),
    CHECK(length(mission_file) > 0),
    
    -- Foreign key to personas
    FOREIGN KEY (persona_name) REFERENCES personas(name) ON DELETE RESTRICT
);

CREATE INDEX idx_missions_persona_name ON missions(persona_name);
CREATE INDEX idx_missions_role ON missions(role);
CREATE INDEX idx_missions_codename ON missions(codename);
CREATE INDEX idx_missions_start_time ON missions(start_time);

-- Trigger to update updated_at timestamp
CREATE TRIGGER update_missions_timestamp
AFTER UPDATE ON missions
FOR EACH ROW
BEGIN
    UPDATE missions SET updated_at = datetime('now') WHERE id = NEW.id;
END;

-- ============================================================================
-- EPICS TABLE
-- ============================================================================
-- Epics are organizational containers for grouping related tasks
CREATE TABLE epics (
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

CREATE INDEX idx_epics_status ON epics(status);
CREATE INDEX idx_epics_priority ON epics(priority);
CREATE INDEX idx_epics_created ON epics(created_at);

-- Trigger to update updated_at timestamp
CREATE TRIGGER update_epics_timestamp
AFTER UPDATE ON epics
FOR EACH ROW
BEGIN
    UPDATE epics SET updated_at = datetime('now') WHERE id = NEW.id;
END;

-- ============================================================================
-- REVIEWS TABLE
-- ============================================================================
-- Tracks review requests for tasks, designs, code, and other artifacts
CREATE TABLE reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL                    -- Type of review
        CHECK(type IN ('code', 'task_completion', 'design', 'general')),
    status TEXT NOT NULL DEFAULT 'pending' -- Review status
        CHECK(status IN ('pending', 'approved', 'rejected')),
    task_id TEXT,                         -- Associated task (optional, not all reviews are task-related)
    title TEXT NOT NULL,                  -- Brief title of what's being reviewed
    description TEXT,                     -- Detailed description of review request
    requested_by TEXT,                    -- Daemon name who requested review
    requested_at TEXT NOT NULL DEFAULT (datetime('now')),
    reviewed_by TEXT,                     -- Who completed the review (e.g., 'Director')
    reviewed_at TEXT,                     -- When review was completed
    outcome_reason TEXT,                  -- Why approved/rejected
    artifact_path TEXT,                   -- Path to artifact being reviewed (PR, file, ADR, etc.)
    
    -- Foreign keys
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE SET NULL
);

-- Indexes for performance
CREATE INDEX idx_reviews_status ON reviews(status);
CREATE INDEX idx_reviews_type ON reviews(type);
CREATE INDEX idx_reviews_task_id ON reviews(task_id);
CREATE INDEX idx_reviews_requested_at ON reviews(requested_at);

-- ============================================================================
-- TASKS TABLE
-- ============================================================================
-- Main tasks table (ported from original task management system)
CREATE TABLE tasks (
    id TEXT PRIMARY KEY,                  -- e.g., 'OPR-H-0001', 'BLD-H-0003'
    title TEXT NOT NULL,                  -- Short task description
    status TEXT NOT NULL                  -- Task status
        CHECK(status IN ('TODO', 'UNDERWAY', 'BLOCKED', 'PAUSED', 'REVIEW', 'COMPLETE', 'ABORTED')),
    priority TEXT NOT NULL                -- Task priority
        CHECK(priority IN ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW')),
    role TEXT NOT NULL                    -- Required role for this task
        CHECK(role IN ('Administrator', 'Architect', 'Builder', 'Tester', 'Documentarian', 'Designer', 'Inspector', 'Operator', 'Historian')),
    category TEXT                         -- Task category (e.g., 'feature', 'bug-fix', 'documentation')
        CHECK(category IN ('feature', 'bug-fix', 'refactor', 'documentation', 'testing', 'infrastructure', 'security', 'performance', 'architecture', 'maintenance') OR category IS NULL),

    -- Mission tracking
    current_mission_id INTEGER,           -- Current mission working on this task (or NULL)
    claimed_at TEXT,                      -- ISO 8601 timestamp when task was claimed
    closed_at TEXT,                       -- ISO 8601 timestamp when task was closed (COMPLETE/ABORTED/PAUSED)
    paused_at TEXT,                       -- ISO 8601 timestamp when work was paused

    -- Time tracking
    actual_hours REAL,                    -- Actual time spent in hours

    -- Content
    description TEXT,                     -- Detailed description of what needs to be done and why
    notes TEXT,                           -- Progress notes and updates

    -- Epic relationship
    epic_id TEXT,                         -- Epic this task belongs to (or NULL if standalone)

    -- Review blocking
    blocks_on_review_id INTEGER,          -- Review that must be approved before task can be claimed

    -- Metadata
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),

    -- File path tracking
    file_path TEXT NOT NULL,              -- Path to markdown file (e.g., '.opencode/planning/OPR-H-0001.md')

    -- Constraints
    CHECK(claimed_at IS NULL OR status NOT IN ('TODO')),
    CHECK(closed_at IS NULL OR status IN ('COMPLETE', 'ABORTED', 'PAUSED')),
    CHECK(paused_at IS NULL OR status = 'PAUSED'),
    
    -- Foreign keys
    FOREIGN KEY (current_mission_id) REFERENCES missions(id) ON DELETE SET NULL,
    FOREIGN KEY (epic_id) REFERENCES epics(id) ON DELETE RESTRICT,
    FOREIGN KEY (blocks_on_review_id) REFERENCES reviews(id) ON DELETE SET NULL
);

-- Task dependencies
CREATE TABLE task_dependencies (
    task_id TEXT NOT NULL,
    depends_on_task_id TEXT NOT NULL,
    PRIMARY KEY (task_id, depends_on_task_id),
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
    FOREIGN KEY (depends_on_task_id) REFERENCES tasks(id) ON DELETE CASCADE
);

-- Indexes for performance
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_priority ON tasks(priority);
CREATE INDEX idx_tasks_role ON tasks(role);
CREATE INDEX idx_tasks_current_mission ON tasks(current_mission_id);
CREATE INDEX idx_tasks_epic_id ON tasks(epic_id);
CREATE INDEX idx_tasks_blocks_on_review ON tasks(blocks_on_review_id);
CREATE INDEX idx_tasks_updated ON tasks(updated_at);
CREATE INDEX idx_tasks_created ON tasks(created_at);

-- Trigger to automatically update updated_at timestamp
CREATE TRIGGER update_tasks_timestamp
AFTER UPDATE ON tasks
FOR EACH ROW
BEGIN
    UPDATE tasks SET updated_at = datetime('now') WHERE id = NEW.id;
END;

-- Trigger to update epic status when task status changes
CREATE TRIGGER update_epic_status_on_task_change
AFTER UPDATE OF status ON tasks
WHEN NEW.epic_id IS NOT NULL
BEGIN
    UPDATE epics SET 
        status = (
            CASE
                -- All tasks complete = epic complete
                WHEN NOT EXISTS (
                    SELECT 1 FROM tasks 
                    WHERE epic_id = NEW.epic_id AND status != 'COMPLETE'
                ) THEN 'COMPLETE'
                
                -- Any task active = epic underway
                WHEN EXISTS (
                    SELECT 1 FROM tasks 
                    WHERE epic_id = NEW.epic_id 
                    AND status IN ('UNDERWAY', 'BLOCKED', 'REVIEW', 'PAUSED')
                ) THEN 'UNDERWAY'
                
                -- All tasks TODO = epic todo
                ELSE 'TODO'
            END
        ),
        completed_at = (
            CASE 
                WHEN NOT EXISTS (
                    SELECT 1 FROM tasks 
                    WHERE epic_id = NEW.epic_id AND status != 'COMPLETE'
                ) THEN datetime('now')
                ELSE NULL
            END
        ),
        updated_at = datetime('now')
    WHERE id = NEW.epic_id AND status != 'ABORTED';
    -- Don't auto-update aborted epics
END;

-- Trigger to update epic status when task is inserted
CREATE TRIGGER update_epic_status_on_task_insert
AFTER INSERT ON tasks
WHEN NEW.epic_id IS NOT NULL
BEGIN
    UPDATE epics SET 
        status = (
            CASE
                WHEN NOT EXISTS (
                    SELECT 1 FROM tasks 
                    WHERE epic_id = NEW.epic_id AND status != 'COMPLETE'
                ) THEN 'COMPLETE'
                WHEN EXISTS (
                    SELECT 1 FROM tasks 
                    WHERE epic_id = NEW.epic_id 
                    AND status IN ('UNDERWAY', 'BLOCKED', 'REVIEW', 'PAUSED')
                ) THEN 'UNDERWAY'
                ELSE 'TODO'
            END
        ),
        updated_at = datetime('now')
    WHERE id = NEW.epic_id AND status != 'ABORTED';
END;

-- ============================================================================
-- TASK TEMPLATES TABLE
-- ============================================================================
-- Stores reusable task templates for common work patterns
CREATE TABLE task_templates (
    id TEXT PRIMARY KEY,                  -- Template ID (e.g., 'feature-impl', 'bug-fix')
    name TEXT NOT NULL,                   -- Display name
    description TEXT NOT NULL,            -- What this template is for
    
    -- Template fields (use {variable} for substitution)
    title_template TEXT NOT NULL,         -- e.g., "Implement {feature} for {component}"
    priority TEXT NOT NULL                -- Default priority
        CHECK(priority IN ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW')),
    role TEXT NOT NULL                    -- Default role
        CHECK(role IN ('Administrator', 'Architect', 'Builder', 'Tester', 'Documentarian', 'Designer', 'Inspector', 'Operator', 'Historian')),
    category TEXT,                        -- Default category
    objective_template TEXT NOT NULL,     -- e.g., "Implement {feature} functionality in {component}"
    description_template TEXT,            -- Long description with variables
    
    -- Variables expected in this template
    variables TEXT,                       -- JSON array of variable names, e.g., '["feature", "component"]'
    
    -- Metadata
    usage_count INTEGER NOT NULL DEFAULT 0, -- How many times used
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    
    CHECK(length(id) > 0),
    CHECK(length(name) > 0),
    CHECK(length(title_template) > 0),
    CHECK(length(objective_template) > 0)
);

CREATE INDEX idx_task_templates_role ON task_templates(role);
CREATE INDEX idx_task_templates_priority ON task_templates(priority);
CREATE INDEX idx_task_templates_usage ON task_templates(usage_count);

-- Trigger to update updated_at timestamp
CREATE TRIGGER update_task_templates_timestamp
AFTER UPDATE ON task_templates
FOR EACH ROW
BEGIN
    UPDATE task_templates SET updated_at = datetime('now') WHERE id = NEW.id;
END;
