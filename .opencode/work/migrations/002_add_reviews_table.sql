-- Migration 002: Add reviews table and task blocking
-- Date: 2026-02-03
-- Task: OPR-H-0043 - Implement review tracking system

-- ============================================================================
-- Step 1: Create reviews table
-- ============================================================================
CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL
        CHECK(type IN ('code', 'task_completion', 'design', 'general')),
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK(status IN ('pending', 'approved', 'rejected')),
    task_id TEXT,
    title TEXT NOT NULL,
    description TEXT,
    requested_by TEXT,
    requested_at TEXT NOT NULL DEFAULT (datetime('now')),
    reviewed_by TEXT,
    reviewed_at TEXT,
    outcome_reason TEXT,
    artifact_path TEXT,
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE SET NULL
);

-- ============================================================================
-- Step 2: Create indexes for reviews table
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_reviews_status ON reviews(status);
CREATE INDEX IF NOT EXISTS idx_reviews_type ON reviews(type);
CREATE INDEX IF NOT EXISTS idx_reviews_task_id ON reviews(task_id);
CREATE INDEX IF NOT EXISTS idx_reviews_requested_at ON reviews(requested_at);

-- ============================================================================
-- Step 3: Add blocks_on_review_id column to tasks table
-- ============================================================================
-- SQLite doesn't support ALTER TABLE ADD COLUMN with FOREIGN KEY constraints
-- We'll add the column first, then rely on application-level enforcement

-- Check if column already exists before adding
-- (This is a safety check - SQLite will error if column exists)
ALTER TABLE tasks ADD COLUMN blocks_on_review_id INTEGER;

-- ============================================================================
-- Step 4: Create index for task blocking
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_tasks_blocks_on_review ON tasks(blocks_on_review_id);

-- ============================================================================
-- Migration complete
-- ============================================================================
-- Updated schema to support review tracking for task approval workflow
-- Tasks can now be blocked by pending reviews
-- Reviews can be approved/rejected to unblock dependent tasks
