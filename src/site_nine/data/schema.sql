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
        CHECK(role IN ('Administrator', 'Architect', 'Engineer', 'Tester', 'Documentarian', 'Designer', 'Inspector', 'Operator', 'Historian')),
    mythology TEXT NOT NULL,              -- Mythology/religion origin (e.g., 'Greek', 'Roman', 'Norse')
    description TEXT NOT NULL,            -- Brief description of the deity/daemon
    whimsical_bio TEXT,                   -- Whimsical first-person bio (3-5 sentences, generated lazily)
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
    persona_name TEXT,                    -- Persona name (e.g., 'terminus', 'atlas'); NULL during ROLE_PENDING/PERSONA_PENDING
    role TEXT                             -- Persona role for this mission; NULL during ROLE_PENDING
        CHECK(role IS NULL OR role IN ('Administrator', 'Architect', 'Engineer', 'Tester', 'Documentarian', 'Designer', 'Inspector', 'Operator', 'Historian')),
    codename TEXT,                        -- Mission codename (e.g., 'silent-phoenix', 'bold-shadow'); set by mission_init
    mission_file TEXT,                    -- Path to mission file; NULL until persona is set
    start_date TEXT,                      -- Mission start date (YYYY-MM-DD); NULL until persona is set
    start_time TEXT,                      -- Mission start time (ISO 8601); NULL until persona is set
    end_time TEXT,                        -- Mission end time (ISO 8601) or NULL if in progress
    objective TEXT,                       -- Brief mission objective
    
    -- Mission status and tracking
    epic_id TEXT,                         -- Epic this mission is associated with
    desk_mode_active INTEGER DEFAULT 0,   -- Whether desk mode is active (0 or 1)
    status TEXT NOT NULL DEFAULT 'ACTIVE' -- Mission status: ACTIVE, IDLE, ENDED, SUSPENDED, etc.
        CHECK(status IN ('ACTIVE', 'IDLE', 'ENDED', 'SUSPENDED', 'ROLE_PENDING', 'PERSONA_PENDING')),
    last_active_at TEXT,                  -- Legacy: Last activity timestamp (kept for backward compatibility)
    
    -- OpenCode integration fields (ADR-013)
    opencode_session_id TEXT,             -- OpenCode session ID (binds mission to session)
    mode TEXT DEFAULT 'interactive',      -- Mission mode: 'interactive' or 'desk'
    last_activity_at TEXT,                -- Last activity timestamp (plugin-managed, for stale detection)
    suspension_time TEXT,                 -- When mission was suspended (ISO 8601)
    suspension_reason TEXT,               -- Why mission was suspended
    
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    
    -- Constraints
    CHECK(persona_name IS NULL OR length(persona_name) > 0),
    CHECK(codename IS NULL OR length(codename) > 0),
    CHECK(mission_file IS NULL OR length(mission_file) > 0),

    -- Foreign keys
    FOREIGN KEY (persona_name) REFERENCES personas(name) ON DELETE RESTRICT,
    FOREIGN KEY (epic_id) REFERENCES epics(id) ON DELETE SET NULL
);

CREATE INDEX idx_missions_persona_name ON missions(persona_name);
CREATE INDEX idx_missions_role ON missions(role);
CREATE INDEX idx_missions_codename ON missions(codename);
CREATE INDEX idx_missions_start_date ON missions(start_date);
CREATE INDEX idx_missions_epic_id ON missions(epic_id);
CREATE INDEX idx_missions_desk_mode ON missions(desk_mode_active);
CREATE INDEX idx_missions_status ON missions(status);
-- ADR-013 indexes
CREATE UNIQUE INDEX idx_missions_session_id ON missions(opencode_session_id) WHERE opencode_session_id IS NOT NULL;
CREATE INDEX idx_missions_mode ON missions(mode);
CREATE INDEX idx_missions_suspended ON missions(status, suspension_time) WHERE status = 'SUSPENDED';

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
    status TEXT NOT NULL DEFAULT 'TODO' -- Computed from subtasks via triggers
        CHECK(status IN ('TODO', 'UNDERWAY', 'COMPLETE', 'ABORTED')),
    priority TEXT NOT NULL
        CHECK(priority IN ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW')),
    aborted_reason TEXT,              -- Only if manually aborted
    locked INTEGER NOT NULL DEFAULT 0, -- 1 if epic is locked (Director-only to set)
    locked_at TEXT,                   -- ISO 8601 timestamp when epic was locked
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
-- HANDOFFS TABLE
-- ============================================================================
-- Tracks work handoffs between missions and roles
CREATE TABLE handoffs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,                    -- Associated task being handed off
    from_mission_id INTEGER NOT NULL,         -- Mission handing off the work
    to_role TEXT NOT NULL                     -- Role receiving the handoff
        CHECK(to_role IN ('Administrator', 'Architect', 'Engineer', 'Tester', 'Documentarian', 'Designer', 'Inspector', 'Operator', 'Historian')),
    
    -- Handoff content
    summary TEXT NOT NULL,                    -- Brief summary of what's being handed off
    files TEXT,                               -- JSON array of relevant file paths
    acceptance_criteria TEXT,                 -- What defines completion
    notes TEXT,                               -- Additional context or instructions
    
    -- Timestamps
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    deleted_at TEXT,                          -- Soft delete timestamp (NULL if active)
    
    -- Foreign keys
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
    FOREIGN KEY (from_mission_id) REFERENCES missions(id) ON DELETE CASCADE
);

-- Indexes for performance
CREATE INDEX idx_handoffs_task_id ON handoffs(task_id);
CREATE INDEX idx_handoffs_from_mission ON handoffs(from_mission_id);
CREATE INDEX idx_handoffs_to_role ON handoffs(to_role);
CREATE INDEX idx_handoffs_deleted ON handoffs(deleted_at);

-- ============================================================================
-- TASKS TABLE
-- ============================================================================
-- Main tasks table (ported from original task management system)
CREATE TABLE tasks (
    id TEXT PRIMARY KEY,                  -- e.g., 'OPR-H-0001', 'ENG-H-0003'
    title TEXT NOT NULL,                  -- Short task description
    status TEXT NOT NULL                  -- Task status
        CHECK(status IN ('TODO', 'UNDERWAY', 'BLOCKED', 'PAUSED', 'REVIEW', 'COMPLETE', 'ABORTED')),
    priority TEXT NOT NULL                -- Task priority
        CHECK(priority IN ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW')),
    role TEXT NOT NULL                    -- Required role for this task
        CHECK(role IN ('Administrator', 'Architect', 'Engineer', 'Tester', 'Documentarian', 'Designer', 'Inspector', 'Operator', 'Historian')),
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

-- Task blocks
CREATE TABLE blocks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,
    block_type TEXT NOT NULL,
    description TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    resolved_at TEXT,
    
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
);

CREATE INDEX idx_blocks_task_id ON blocks(task_id);
CREATE INDEX idx_blocks_resolved ON blocks(resolved_at);

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
        CHECK(role IN ('Administrator', 'Architect', 'Engineer', 'Tester', 'Documentarian', 'Designer', 'Inspector', 'Operator', 'Historian')),
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

-- ============================================================================
-- ARCHITECTURE DOCUMENTS (ADRs) TABLE
-- ============================================================================
-- Tracks Architecture Decision Records (ADRs) as database-backed entities
CREATE TABLE architecture_docs (
    id TEXT PRIMARY KEY,                  -- ADR ID (e.g., 'ADR-001', 'ADR-002')
    title TEXT NOT NULL,                  -- ADR title
    status TEXT NOT NULL                  -- ADR status
        CHECK(status IN ('PROPOSED', 'ACCEPTED', 'REJECTED', 'SUPERSEDED', 'DEPRECATED')),
    file_path TEXT NOT NULL,              -- Path to markdown file (e.g., '.opencode/docs/adrs/ADR-001-adapter-pattern.md')
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_architecture_docs_status ON architecture_docs(status);
CREATE INDEX idx_architecture_docs_created ON architecture_docs(created_at);

-- Trigger to update updated_at timestamp
CREATE TRIGGER update_architecture_docs_timestamp
AFTER UPDATE ON architecture_docs
FOR EACH ROW
BEGIN
    UPDATE architecture_docs SET updated_at = datetime('now') WHERE id = NEW.id;
END;

-- ============================================================================
-- EPIC-ADR LINKING TABLE
-- ============================================================================
-- Links epics to architecture documents
CREATE TABLE epic_architecture_docs (
    epic_id TEXT NOT NULL,
    adr_id TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (epic_id, adr_id),
    FOREIGN KEY (epic_id) REFERENCES epics(id) ON DELETE CASCADE,
    FOREIGN KEY (adr_id) REFERENCES architecture_docs(id) ON DELETE CASCADE
);

CREATE INDEX idx_epic_architecture_docs_epic ON epic_architecture_docs(epic_id);
CREATE INDEX idx_epic_architecture_docs_adr ON epic_architecture_docs(adr_id);

-- ============================================================================
-- TASK-ADR LINKING TABLE
-- ============================================================================
-- Links tasks to architecture documents
CREATE TABLE task_architecture_docs (
    task_id TEXT NOT NULL,
    adr_id TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (task_id, adr_id),
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
    FOREIGN KEY (adr_id) REFERENCES architecture_docs(id) ON DELETE CASCADE
);

CREATE INDEX idx_task_architecture_docs_task ON task_architecture_docs(task_id);
CREATE INDEX idx_task_architecture_docs_adr ON task_architecture_docs(adr_id);

-- ============================================================================
-- MESSAGING TABLES
-- ============================================================================
-- Agent-to-agent communication system (ADR-008, ADR-009)

-- Conversations and discussions
CREATE TABLE conversations (
    id TEXT PRIMARY KEY,                  -- CONV-[NNNN] format
    subject TEXT NOT NULL,                -- Conversation subject
    type TEXT NOT NULL                    -- 'conversation' (1-on-1) or 'discussion' (scoped)
        CHECK(type IN ('conversation', 'discussion')),
    status TEXT NOT NULL DEFAULT 'open'   -- 'open' or 'closed'
        CHECK(status IN ('open', 'closed')),

    -- Participants (for type='conversation')
    participant_1_id INTEGER,             -- First participant mission ID
    participant_2_id INTEGER,             -- Second participant mission ID

    -- Scope (for type='discussion')
    scope_type TEXT                       -- 'role', 'epic', or 'all'
        CHECK(scope_type IN ('role', 'epic', 'all') OR scope_type IS NULL),
    scope_role TEXT,                      -- Role name if scope_type='role'
    scope_epic_id TEXT,                   -- Epic ID if scope_type='epic'

    -- Optional context links
    task_id TEXT,
    epic_id TEXT,

    -- Timestamps
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    closed_at TEXT,

    FOREIGN KEY (participant_1_id) REFERENCES missions(id),
    FOREIGN KEY (participant_2_id) REFERENCES missions(id),
    FOREIGN KEY (scope_epic_id) REFERENCES epics(id),
    FOREIGN KEY (task_id) REFERENCES tasks(id),
    FOREIGN KEY (epic_id) REFERENCES epics(id)
);

CREATE INDEX idx_conversations_type ON conversations(type);
CREATE INDEX idx_conversations_status ON conversations(status);
CREATE INDEX idx_conversations_participant_1 ON conversations(participant_1_id);
CREATE INDEX idx_conversations_participant_2 ON conversations(participant_2_id);
CREATE INDEX idx_conversations_updated ON conversations(updated_at);

-- Trigger to update updated_at on conversations
CREATE TRIGGER update_conversations_timestamp
AFTER UPDATE ON conversations
FOR EACH ROW
BEGIN
    UPDATE conversations SET updated_at = datetime('now') WHERE id = NEW.id;
END;

-- Messages within conversations or discussions
CREATE TABLE messages (
    id TEXT PRIMARY KEY,                  -- MSG-[P]-[NNNN] format (P = priority code)
    conversation_id TEXT NOT NULL,        -- Parent conversation/discussion
    from_mission_id INTEGER NOT NULL,     -- Sender mission ID
    subject TEXT NOT NULL,                -- Message subject
    body TEXT NOT NULL,                   -- Markdown-formatted body
    priority TEXT NOT NULL DEFAULT 'MEDIUM'
        CHECK(priority IN ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW')),

    -- Threading (discussions only)
    parent_message_id TEXT,               -- Parent message for threading (NULL = root)
    thread_root_id TEXT,                  -- Root of thread tree (NULL if not threaded)

    -- Optional context links
    task_id TEXT,
    epic_id TEXT,
    artifact_path TEXT,                   -- Optional related file/artifact

    -- Timestamps
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    expires_at TEXT,                      -- Optional expiration timestamp

    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
    FOREIGN KEY (from_mission_id) REFERENCES missions(id),
    FOREIGN KEY (parent_message_id) REFERENCES messages(id),
    FOREIGN KEY (thread_root_id) REFERENCES messages(id),
    FOREIGN KEY (task_id) REFERENCES tasks(id),
    FOREIGN KEY (epic_id) REFERENCES epics(id)
);

CREATE INDEX idx_messages_conversation ON messages(conversation_id);
CREATE INDEX idx_messages_from_mission ON messages(from_mission_id);
CREATE INDEX idx_messages_priority ON messages(priority);
CREATE INDEX idx_messages_created ON messages(created_at);
CREATE INDEX idx_messages_thread_root ON messages(thread_root_id);

-- Trigger to update parent conversation updated_at when a message is added
CREATE TRIGGER update_conversation_on_message_insert
AFTER INSERT ON messages
FOR EACH ROW
BEGIN
    UPDATE conversations SET updated_at = datetime('now') WHERE id = NEW.conversation_id;
END;

-- Tracks when each mission last viewed a conversation (for unread detection)
CREATE TABLE conversation_views (
    conversation_id TEXT NOT NULL,
    mission_id INTEGER NOT NULL,
    last_viewed_at TEXT NOT NULL DEFAULT (datetime('now')),

    PRIMARY KEY (conversation_id, mission_id),
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
    FOREIGN KEY (mission_id) REFERENCES missions(id)
);

CREATE INDEX idx_conversation_views_mission ON conversation_views(mission_id);

-- Tracks when each mission acknowledges/processes a specific message
CREATE TABLE message_acknowledgements (
    message_id TEXT NOT NULL,
    mission_id INTEGER NOT NULL,
    acknowledged_at TEXT NOT NULL DEFAULT (datetime('now')),

    PRIMARY KEY (message_id, mission_id),
    FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE,
    FOREIGN KEY (mission_id) REFERENCES missions(id)
);

CREATE INDEX idx_message_acks_message ON message_acknowledgements(message_id);
CREATE INDEX idx_message_acks_mission ON message_acknowledgements(mission_id);
