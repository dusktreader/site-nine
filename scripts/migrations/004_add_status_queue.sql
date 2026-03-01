-- Migration 004: Add status_queue table
--
-- Adds a lightweight queue for worker-to-director status toast notifications.
-- Workers push short status messages; the OpenCode plugin pops and toasts them
-- in the interactive (non-desk-mode) session. Cleared on s9 summon.

CREATE TABLE IF NOT EXISTS status_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mission_id INTEGER NOT NULL,
    message TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),

    FOREIGN KEY (mission_id) REFERENCES missions(id)
);

CREATE INDEX IF NOT EXISTS idx_status_queue_created ON status_queue(created_at);
