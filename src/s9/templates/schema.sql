-- Crol Troll Project Management Database Schema
-- Created: 2026-01-30
-- 
-- This database manages:
-- 1. Tasks - Development work tracking
-- 2. Names - Daemon names for agent sessions
-- 3. Agents - Agent session tracking

-- ============================================================================
-- DAEMON NAMES TABLE
-- ============================================================================
-- Stores daemon names from mythology organized by role
CREATE TABLE daemon_names (
    name TEXT PRIMARY KEY,                -- Daemon name (lowercase, e.g., 'atlas', 'terminus')
    role TEXT NOT NULL                    -- Primary role this name suits
        CHECK(role IN ('Administrator', 'Architect', 'Builder', 'Tester', 'Documentarian', 'Designer', 'Inspector', 'Operator', 'Historian')),
    mythology TEXT NOT NULL,              -- Mythology/religion origin (e.g., 'Greek', 'Roman', 'Norse')
    description TEXT NOT NULL,            -- Brief description of the deity/daemon
    usage_count INTEGER NOT NULL DEFAULT 0, -- How many times this name has been used
    last_used_at TEXT,                    -- ISO 8601 timestamp of last usage
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    
    -- Indexes
    CHECK(length(name) > 0)
);

CREATE INDEX idx_daemon_names_role ON daemon_names(role);
CREATE INDEX idx_daemon_names_usage ON daemon_names(usage_count);
CREATE INDEX idx_daemon_names_last_used ON daemon_names(last_used_at);

-- ============================================================================
-- AGENTS TABLE
-- ============================================================================
-- Tracks agent sessions
CREATE TABLE agents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,                   -- Full agent name with suffix (e.g., 'terminus', 'atlas-ii')
    base_name TEXT NOT NULL,              -- Base name without suffix (e.g., 'terminus', 'atlas')
    suffix TEXT,                          -- Roman numeral suffix (e.g., 'ii', 'iii') or NULL for first use
    role TEXT NOT NULL                    -- Agent role for this session
        CHECK(role IN ('Administrator', 'Architect', 'Builder', 'Tester', 'Documentarian', 'Designer', 'Inspector', 'Operator', 'Historian')),
    session_file TEXT NOT NULL,           -- Path to session file (e.g., '.opencode/sessions/2026-01-30.09:15:55.operator.terminus.expand-task-db.md')
    session_date TEXT NOT NULL,           -- Session date (YYYY-MM-DD)
    start_time TEXT NOT NULL,             -- Session start time (HH:MM:SS)
    end_time TEXT,                        -- Session end time (HH:MM:SS) or NULL if in progress
    status TEXT NOT NULL DEFAULT 'in-progress'  -- Session status
        CHECK(status IN ('in-progress', 'paused', 'completed', 'failed', 'aborted')),
    task_summary TEXT,                    -- Brief task summary
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    
    -- Constraints
    CHECK(length(name) > 0),
    CHECK(length(base_name) > 0),
    CHECK(length(session_file) > 0),
    
    -- Foreign key to daemon_names
    FOREIGN KEY (base_name) REFERENCES daemon_names(name) ON DELETE RESTRICT
);

CREATE INDEX idx_agents_name ON agents(name);
CREATE INDEX idx_agents_base_name ON agents(base_name);
CREATE INDEX idx_agents_role ON agents(role);
CREATE INDEX idx_agents_session_date ON agents(session_date);
CREATE INDEX idx_agents_status ON agents(status);

-- Trigger to update updated_at timestamp
CREATE TRIGGER update_agents_timestamp
AFTER UPDATE ON agents
FOR EACH ROW
BEGIN
    UPDATE agents SET updated_at = datetime('now') WHERE id = NEW.id;
END;

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

    -- Agent tracking
    agent_name TEXT,                      -- Agent name who claimed this task (e.g., 'goibniu', 'thoth-iii', 'terminus')
    agent_id INTEGER,                     -- Foreign key to agents table
    claimed_at TEXT,                      -- ISO 8601 timestamp when task was claimed
    closed_at TEXT,                       -- ISO 8601 timestamp when task was closed (COMPLETE/ABORTED/PAUSED)
    paused_at TEXT,                       -- ISO 8601 timestamp when work was paused

    -- Time tracking
    actual_hours REAL,                    -- Actual time spent in hours

    -- Content
    description TEXT,                     -- Detailed description of what needs to be done and why
    notes TEXT,                           -- Progress notes and updates

    -- Metadata
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),

    -- File path tracking
    file_path TEXT NOT NULL,              -- Path to markdown file (e.g., '.opencode/planning/OPR-H-0001.md')

    -- Constraints
    CHECK(claimed_at IS NULL OR status NOT IN ('TODO')),
    CHECK(closed_at IS NULL OR status IN ('COMPLETE', 'ABORTED', 'PAUSED')),
    CHECK(paused_at IS NULL OR status = 'PAUSED'),
    
    -- Foreign key to agents table
    FOREIGN KEY (agent_id) REFERENCES agents(id) ON DELETE SET NULL
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
CREATE INDEX idx_tasks_agent_name ON tasks(agent_name);
CREATE INDEX idx_tasks_agent_id ON tasks(agent_id);
CREATE INDEX idx_tasks_updated ON tasks(updated_at);
CREATE INDEX idx_tasks_created ON tasks(created_at);

-- Trigger to automatically update updated_at timestamp
CREATE TRIGGER update_tasks_timestamp
AFTER UPDATE ON tasks
FOR EACH ROW
BEGIN
    UPDATE tasks SET updated_at = datetime('now') WHERE id = NEW.id;
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
