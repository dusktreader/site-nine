#!/usr/bin/env python3
"""
Database migration: Fix tasks table FK: current_possession_id REFERENCES missions -> possessions.

The tasks table was originally created with:
    FOREIGN KEY (current_possession_id) REFERENCES missions(id) ON DELETE SET NULL

After the missions->possessions rename, the missions table was dropped, but the tasks
table still holds the old FK. Since SQLite doesn't support ALTER TABLE to change FKs,
we recreate the tasks table with the correct FK.

Run this script from the project root:
    uv run python .opencode/scripts/migrate-fix-tasks-fk.py [--dry-run]
"""

import sqlite3
import sys
from pathlib import Path


def get_db_path() -> Path:
    """Find the database path by locating .opencode directory."""
    current = Path.cwd()
    while current != current.parent:
        candidate = current / ".opencode" / "data" / "project.db"
        if candidate.exists():
            return candidate
        current = current.parent
    raise FileNotFoundError("Could not find .opencode/data/project.db. Run from project root.")


def check_partial_migration(conn: sqlite3.Connection) -> bool:
    """Check if a previous failed migration left tasks_old but an empty tasks table."""
    cursor = conn.cursor()
    tables = {row[0] for row in cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    return "tasks_old" in tables and "tasks" in tables


def cleanup_partial_migration(conn: sqlite3.Connection) -> None:
    """Clean up a partial migration by dropping the empty tasks table and renaming tasks_old back."""
    cursor = conn.cursor()
    print("Detected partial migration — cleaning up (dropping empty tasks, renaming tasks_old -> tasks)...")
    cursor.execute("PRAGMA foreign_keys = OFF")
    cursor.execute("DROP TABLE tasks")
    cursor.execute("ALTER TABLE tasks_old RENAME TO tasks")
    cursor.execute("PRAGMA foreign_keys = ON")
    conn.commit()
    print("Cleanup done.")


def check_fk_needs_fix(conn: sqlite3.Connection) -> bool:
    """Check if tasks table FK still references the old 'missions' table."""
    cursor = conn.cursor()
    cursor.execute("SELECT sql FROM sqlite_master WHERE name='tasks' AND type='table'")
    row = cursor.fetchone()
    if not row:
        print("ERROR: tasks table not found!")
        return False
    sql = row[0]
    return "REFERENCES missions" in sql


def migrate(conn: sqlite3.Connection, dry_run: bool = False) -> None:
    """Recreate the tasks table with the corrected FK."""
    cursor = conn.cursor()

    print("Recreating tasks table with corrected FK (missions -> possessions)...")

    statements = [
        # Step 1: Disable FK enforcement temporarily
        "PRAGMA foreign_keys = OFF",
        # Step 2: Rename old tasks table
        "ALTER TABLE tasks RENAME TO tasks_old",
        # Step 3: Create new tasks table with correct FK
        # NOTE: category CHECK constraint is intentionally dropped — live data has freeform
        # category values that don't conform to the strict constraint in schema.sql. The
        # constraint can be re-added once all data is normalized in a future migration.
        """CREATE TABLE tasks (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    status TEXT NOT NULL
        CHECK(status IN ('TODO', 'UNDERWAY', 'BLOCKED', 'PAUSED', 'REVIEW', 'COMPLETE', 'ABORTED')),
    priority TEXT NOT NULL
        CHECK(priority IN ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW')),
    role TEXT NOT NULL
        CHECK(role IN ('Administrator', 'Architect', 'Engineer', 'Tester', 'Documentarian', 'Designer', 'Inspector', 'Operator', 'Historian')),
    category TEXT,

    current_possession_id INTEGER,
    claimed_at TEXT,
    closed_at TEXT,
    paused_at TEXT,

    actual_hours REAL,

    description TEXT,
    notes TEXT,

    epic_id TEXT,

    blocks_on_review_id INTEGER,

    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),

    file_path TEXT NOT NULL,

    CHECK(claimed_at IS NULL OR status NOT IN ('TODO')),
    CHECK(closed_at IS NULL OR status IN ('COMPLETE', 'ABORTED', 'PAUSED')),
    CHECK(paused_at IS NULL OR status = 'PAUSED'),

    FOREIGN KEY (current_possession_id) REFERENCES possessions(id) ON DELETE SET NULL,
    FOREIGN KEY (epic_id) REFERENCES epics(id) ON DELETE RESTRICT,
    FOREIGN KEY (blocks_on_review_id) REFERENCES reviews(id) ON DELETE SET NULL
)""",
        # Step 4: Copy data
        """INSERT INTO tasks (
    id, title, status, priority, role, category,
    current_possession_id, claimed_at, closed_at, paused_at,
    actual_hours, description, notes, epic_id, blocks_on_review_id,
    created_at, updated_at, file_path
)
SELECT
    id, title, status, priority, role, category,
    current_possession_id, claimed_at, closed_at, paused_at,
    actual_hours, description, notes, epic_id, blocks_on_review_id,
    created_at, updated_at, file_path
FROM tasks_old""",
        # Step 5: Drop old table
        "DROP TABLE tasks_old",
        # Step 6: Recreate indexes
        "CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)",
        "CREATE INDEX IF NOT EXISTS idx_tasks_role ON tasks(role)",
        "CREATE INDEX IF NOT EXISTS idx_tasks_epic ON tasks(epic_id)",
        "CREATE INDEX IF NOT EXISTS idx_tasks_current_possession ON tasks(current_possession_id)",
        # Step 7: Re-enable FK enforcement
        "PRAGMA foreign_keys = ON",
    ]

    for stmt in statements:
        preview = stmt.split("\n")[0][:80]
        print(f"  {'[DRY RUN] ' if dry_run else ''}Executing: {preview}...")
        if not dry_run:
            cursor.execute(stmt)

    if not dry_run:
        conn.commit()
        print("✅ Migration complete: tasks FK now references possessions(id)")
    else:
        print("✅ Dry run complete. No changes made.")


def main() -> int:
    dry_run = "--dry-run" in sys.argv

    try:
        db_path = get_db_path()
        print(f"Database: {db_path}")
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        return 1

    conn = sqlite3.connect(db_path)
    try:
        # Handle partial migration state from a previous failed run
        if check_partial_migration(conn):
            cleanup_partial_migration(conn)

        if not check_fk_needs_fix(conn):
            print("✅ tasks table FK already points to possessions. No migration needed.")
            return 0

        print("⚠️  tasks table FK still references 'missions'. Migration needed.")

        if dry_run:
            print("Running in dry-run mode...")

        migrate(conn, dry_run=dry_run)
        return 0

    except Exception as e:
        conn.rollback()
        print(f"ERROR: Migration failed: {e}")
        import traceback

        traceback.print_exc()
        return 1
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
