#!/usr/bin/env python3
"""
Database migration: Add messaging tables for agent communication.

This migration adds the following tables per ADR-008:
1. conversations - Agent messaging: conversations (1-on-1) and discussions (scoped broadcasts)
2. messages - Messages within conversations and discussions
3. conversation_views - Tracks when missions last viewed conversations/discussions

Reference: ADR-008 (Agent Messaging System), lines 105-243

Run this script from the project root:
    python .opencode/scripts/migrate-add-messaging-tables.py [--dry-run]
"""

import sqlite3
import sys
from pathlib import Path


def get_project_root() -> Path:
    """Find project root by locating .opencode directory."""
    current = Path.cwd()
    while current != current.parent:
        if (current / ".opencode").exists():
            return current
        current = current.parent
    raise FileNotFoundError("Could not find .opencode directory. Run from project root.")


def check_tables_exist(conn: sqlite3.Connection) -> dict[str, bool]:
    """Check which messaging tables already exist."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name IN ('conversations', 'messages', 'conversation_views')
    """)
    existing = {row[0] for row in cursor.fetchall()}

    return {
        "conversations": "conversations" in existing,
        "messages": "messages" in existing,
        "conversation_views": "conversation_views" in existing,
    }


def migration_sql() -> str:
    """Return SQL for creating messaging tables."""
    return """
-- ============================================================================
-- CONVERSATIONS TABLE
-- ============================================================================
-- Agent messaging: conversations (1-on-1) and discussions (scoped broadcasts)
CREATE TABLE conversations (
    id TEXT PRIMARY KEY,                      -- CONV-[NNNN] format
    subject TEXT NOT NULL,                    -- Conversation subject
    type TEXT NOT NULL                        -- 'conversation' | 'discussion'
        CHECK(type IN ('conversation', 'discussion')),
    status TEXT NOT NULL DEFAULT 'open'
        CHECK(status IN ('open', 'closed')),
    
    -- For conversations (1-on-1) - explicit participants
    participant_1_id INTEGER,                 -- NULL for discussions
    participant_2_id INTEGER,                 -- NULL for discussions
    
    -- For discussions (scoped) - dynamic participants
    scope_type TEXT CHECK(scope_type IN ('role', 'epic', 'all') OR scope_type IS NULL),
    scope_role TEXT CHECK(scope_role IN ('Administrator', 'Architect', 'Engineer', 'Tester', 'Documentarian', 'Designer', 'Inspector', 'Operator', 'Historian') OR scope_role IS NULL),
    scope_epic_id TEXT,                       -- NULL unless scope_type='epic'
    
    -- Context links (optional)
    task_id TEXT,                             -- Related task
    epic_id TEXT,                             -- Related epic
    
    -- Timestamps
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    closed_at TEXT,                           -- NULL if open
    
    -- Constraints: Ensure conversations XOR discussions
    CHECK(
        (type = 'conversation' 
         AND participant_1_id IS NOT NULL 
         AND participant_2_id IS NOT NULL 
         AND scope_type IS NULL)
        OR
        (type = 'discussion' 
         AND participant_1_id IS NULL 
         AND participant_2_id IS NULL 
         AND scope_type IS NOT NULL)
    ),
    
    -- Foreign keys
    FOREIGN KEY (participant_1_id) REFERENCES missions(id) ON DELETE CASCADE,
    FOREIGN KEY (participant_2_id) REFERENCES missions(id) ON DELETE CASCADE,
    FOREIGN KEY (scope_epic_id) REFERENCES epics(id) ON DELETE CASCADE,
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE SET NULL,
    FOREIGN KEY (epic_id) REFERENCES epics(id) ON DELETE SET NULL
);

CREATE INDEX idx_conversations_type ON conversations(type);
CREATE INDEX idx_conversations_status ON conversations(status);
CREATE INDEX idx_conversations_participant_1 ON conversations(participant_1_id);
CREATE INDEX idx_conversations_participant_2 ON conversations(participant_2_id);
CREATE INDEX idx_conversations_scope_type ON conversations(scope_type);
CREATE INDEX idx_conversations_scope_role ON conversations(scope_role);
CREATE INDEX idx_conversations_scope_epic ON conversations(scope_epic_id);
CREATE INDEX idx_conversations_created ON conversations(created_at);

-- Trigger to update updated_at timestamp
CREATE TRIGGER update_conversations_timestamp
AFTER UPDATE ON conversations
FOR EACH ROW
BEGIN
    UPDATE conversations SET updated_at = datetime('now') WHERE id = NEW.id;
END;

-- ============================================================================
-- MESSAGES TABLE
-- ============================================================================
-- Messages within conversations and discussions
CREATE TABLE messages (
    id TEXT PRIMARY KEY,                      -- MSG-[P]-[NNNN] format (P = priority)
    conversation_id TEXT NOT NULL,            -- Parent conversation/discussion
    from_mission_id INTEGER NOT NULL,         -- Sender (0 = Director)
    
    -- Content
    subject TEXT NOT NULL,                    -- Message subject
    body TEXT NOT NULL,                       -- Markdown-formatted body
    priority TEXT NOT NULL DEFAULT 'MEDIUM'
        CHECK(priority IN ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW')),
    
    -- Threading (only for discussions)
    parent_message_id TEXT,                   -- NULL = root message
    thread_root_id TEXT,                      -- NULL = root or conversation
    
    -- Context links (optional)
    task_id TEXT,                             -- Related task
    epic_id TEXT,                             -- Related epic
    artifact_path TEXT,                       -- Related file/artifact
    
    -- Timestamps
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    expires_at TEXT,                          -- NULL = no expiration
    
    -- Constraints: Threading only in discussions
    CHECK(
        (parent_message_id IS NULL AND thread_root_id IS NULL)  -- Root or conversation
        OR
        (parent_message_id IS NOT NULL AND thread_root_id IS NOT NULL)  -- Threaded reply
    ),
    
    -- Foreign keys
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
    FOREIGN KEY (from_mission_id) REFERENCES missions(id) ON DELETE CASCADE,
    FOREIGN KEY (parent_message_id) REFERENCES messages(id) ON DELETE CASCADE,
    FOREIGN KEY (thread_root_id) REFERENCES messages(id) ON DELETE CASCADE,
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE SET NULL,
    FOREIGN KEY (epic_id) REFERENCES epics(id) ON DELETE SET NULL
);

CREATE INDEX idx_messages_conversation ON messages(conversation_id);
CREATE INDEX idx_messages_from_mission ON messages(from_mission_id);
CREATE INDEX idx_messages_priority ON messages(priority);
CREATE INDEX idx_messages_parent ON messages(parent_message_id);
CREATE INDEX idx_messages_thread_root ON messages(thread_root_id);
CREATE INDEX idx_messages_created ON messages(created_at);
CREATE INDEX idx_messages_expires ON messages(expires_at);

-- ============================================================================
-- CONVERSATION VIEWS TABLE
-- ============================================================================
-- Tracks when missions last viewed conversations/discussions (conversation-level)
CREATE TABLE conversation_views (
    conversation_id TEXT NOT NULL,            -- Which conversation/discussion
    mission_id INTEGER NOT NULL,              -- Which mission
    last_viewed_at TEXT NOT NULL DEFAULT (datetime('now')),
    
    PRIMARY KEY (conversation_id, mission_id),
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
    FOREIGN KEY (mission_id) REFERENCES missions(id) ON DELETE CASCADE
);

CREATE INDEX idx_conversation_views_mission ON conversation_views(mission_id);
CREATE INDEX idx_conversation_views_viewed_at ON conversation_views(last_viewed_at);
"""


def run_migration(db_path: Path, dry_run: bool = False) -> None:
    """Run the migration."""
    print(f"📍 Database: {db_path}")
    print()

    if not db_path.exists():
        print(f"❌ Error: Database not found at {db_path}")
        sys.exit(1)

    # Connect to database
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")

    try:
        # Check current state
        existing = check_tables_exist(conn)

        print("📊 Current state:")
        for table, exists in existing.items():
            status = "✅ EXISTS" if exists else "❌ MISSING"
            print(f"  {table}: {status}")
        print()

        # Check if migration needed
        if all(existing.values()):
            print("✅ All messaging tables already exist. No migration needed.")
            return

        # Check for partial migration
        if any(existing.values()):
            print("⚠️  WARNING: Some tables exist but not all!")
            print("   This suggests a partial migration. Please investigate before proceeding.")
            sys.exit(1)

        # Run migration
        if dry_run:
            print("🔍 DRY RUN MODE - No changes will be made")
            print()
            print("Would execute the following SQL:")
            print("=" * 80)
            print(migration_sql())
            print("=" * 80)
        else:
            print("🚀 Running migration...")
            conn.executescript(migration_sql())
            conn.commit()
            print("✅ Migration complete!")
            print()

            # Verify
            print("🔍 Verifying tables...")
            existing_after = check_tables_exist(conn)
            for table, exists in existing_after.items():
                status = "✅" if exists else "❌"
                print(f"  {status} {table}")
            print()

            if all(existing_after.values()):
                print("✅ All tables created successfully!")
            else:
                print("❌ Some tables failed to create. Check the logs above.")
                sys.exit(1)

    finally:
        conn.close()


def main():
    """Main entry point."""
    print("=" * 80)
    print("Database Migration: Add Messaging Tables (ADR-008)")
    print("=" * 80)
    print()

    # Parse arguments
    dry_run = "--dry-run" in sys.argv or "-n" in sys.argv

    try:
        # Find project root and database
        project_root = get_project_root()
        db_path = project_root / ".opencode" / "data" / "project.db"

        # Run migration
        run_migration(db_path, dry_run=dry_run)

    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
