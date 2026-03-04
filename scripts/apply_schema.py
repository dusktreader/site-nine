#!/usr/bin/env python3
"""
apply_schema.py — Rebuild the site-nine database with the canonical schema.

This script performs a destructive replacement of all daemon/possession-related
tables while preserving tasks, epics, ADRs, templates, and reviews.

Usage:
    python scripts/apply_schema.py [--db PATH] [--dry-run]

WARNING: Drops and recreates possessions, daemons, conversations, messages,
         conversation_views, message_acknowledgements, status_queue, and handoffs.
         All possession/daemon history is lost. Tasks and epics are preserved.
"""

import argparse
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
SCHEMA = ROOT / "src" / "site_nine" / "data" / "schema.sql"
DEFAULT_DB = ROOT / ".opencode" / "data" / "project.db"

# Tables to drop entirely (possession/daemon side + reviews which had column rename)
TABLES_TO_DROP = [
    "status_queue",
    "message_acknowledgements",
    "conversation_views",
    "messages",
    "conversations",
    "handoffs",
    "possessions",
    "daemons",
    "reviews",
    # Old names (may exist if upgrading from mission/persona model)
    "personas",
    "missions",
]

# Triggers to drop
TRIGGERS_TO_DROP = [
    "update_possessions_timestamp",
    "update_missions_timestamp",
    "update_conversations_timestamp",
    "update_conversation_on_message_insert",
]

# Views to drop
VIEWS_TO_DROP = [
    "task_status_view",
]

# Preserved tables — tasks, epics, ADRs, templates, reviews, blocks, dependencies
# We DO update tasks.current_possession_id from current_mission_id if it exists.


def load_schema(schema_path: Path) -> str:
    return schema_path.read_text()


def get_existing_tables(conn: sqlite3.Connection) -> set[str]:
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    return {row[0] for row in cur.fetchall()}


def get_existing_triggers(conn: sqlite3.Connection) -> set[str]:
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='trigger'")
    return {row[0] for row in cur.fetchall()}


def get_existing_views(conn: sqlite3.Connection) -> set[str]:
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='view'")
    return {row[0] for row in cur.fetchall()}


def migrate_tasks_column(conn: sqlite3.Connection, dry_run: bool) -> None:
    """Rename current_mission_id -> current_possession_id on tasks if needed.
    Also add new columns introduced in the daemon/possession schema redesign."""
    cur = conn.execute("PRAGMA table_info(tasks)")
    cols = {row[1] for row in cur.fetchall()}

    # Rename current_mission_id -> current_possession_id
    if "current_possession_id" not in cols:
        if "current_mission_id" in cols:
            print("  tasks: renaming current_mission_id -> current_possession_id")
            if not dry_run:
                conn.execute("ALTER TABLE tasks RENAME COLUMN current_mission_id TO current_possession_id")
        else:
            print("  tasks: adding current_possession_id column")
            if not dry_run:
                conn.execute("ALTER TABLE tasks ADD COLUMN current_possession_id INTEGER REFERENCES possessions(id)")
    else:
        print("  tasks.current_possession_id already exists")

    # Add paused_at if missing
    if "paused_at" not in cols:
        print("  tasks: adding paused_at column")
        if not dry_run:
            conn.execute("ALTER TABLE tasks ADD COLUMN paused_at TEXT")
    else:
        print("  tasks.paused_at already exists")

    # Add blocks_on_review_id if missing
    if "blocks_on_review_id" not in cols:
        print("  tasks: adding blocks_on_review_id column")
        if not dry_run:
            conn.execute("ALTER TABLE tasks ADD COLUMN blocks_on_review_id INTEGER")
    else:
        print("  tasks.blocks_on_review_id already exists")


def apply(db_path: Path, dry_run: bool) -> None:
    print(f"Database : {db_path}")
    print(f"Schema   : {SCHEMA}")
    print(f"Dry run  : {dry_run}")
    print()

    if not db_path.exists():
        print(f"ERROR: database not found at {db_path}", file=sys.stderr)
        sys.exit(1)

    schema_sql = load_schema(SCHEMA)

    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = OFF")

    try:
        existing_tables = get_existing_tables(conn)
        existing_triggers = get_existing_triggers(conn)
        existing_views = get_existing_views(conn)

        # --- Step 1: Release tasks claimed by active possessions/missions ---
        print("Step 1: Releasing claimed tasks...")
        if not dry_run:
            if "tasks" in existing_tables:
                if "current_mission_id" in {row[1] for row in conn.execute("PRAGMA table_info(tasks)").fetchall()}:
                    released = conn.execute(
                        "UPDATE tasks SET current_mission_id = NULL, claimed_at = NULL, status = 'TODO' "
                        "WHERE status = 'UNDERWAY'"
                    ).rowcount
                    print(f"  Released {released} UNDERWAY tasks (current_mission_id -> NULL)")
                elif "current_possession_id" in {row[1] for row in conn.execute("PRAGMA table_info(tasks)").fetchall()}:
                    released = conn.execute(
                        "UPDATE tasks SET current_possession_id = NULL, claimed_at = NULL, status = 'TODO' "
                        "WHERE status = 'UNDERWAY'"
                    ).rowcount
                    print(f"  Released {released} UNDERWAY tasks (current_possession_id -> NULL)")

        # --- Step 2: Drop views ---
        print("Step 2: Dropping views...")
        for view in VIEWS_TO_DROP:
            if view in existing_views:
                print(f"  DROP VIEW {view}")
                if not dry_run:
                    conn.execute(f"DROP VIEW IF EXISTS {view}")
            else:
                print(f"  (skip) {view} — not present")

        # --- Step 3: Drop triggers ---
        print("Step 3: Dropping triggers...")
        for trigger in TRIGGERS_TO_DROP:
            if trigger in existing_triggers:
                print(f"  DROP TRIGGER {trigger}")
                if not dry_run:
                    conn.execute(f"DROP TRIGGER IF EXISTS {trigger}")
            else:
                print(f"  (skip) {trigger} — not present")

        # --- Step 4: Drop tables (order matters for FK constraints) ---
        print("Step 4: Dropping tables...")
        for table in TABLES_TO_DROP:
            if table in existing_tables:
                print(f"  DROP TABLE {table}")
                if not dry_run:
                    conn.execute(f"DROP TABLE IF EXISTS {table}")
            else:
                print(f"  (skip) {table} — not present")

        # --- Step 5: Migrate tasks column ---
        print("Step 5: Migrating tasks column...")
        if not dry_run:
            migrate_tasks_column(conn, dry_run)
        else:
            print("  (dry run) would migrate current_mission_id -> current_possession_id if needed")

        # --- Step 6: Apply schema (creates new tables, seeds data) ---
        print("Step 6: Applying schema...")
        if not dry_run:
            # Split on semicolons and execute statement by statement,
            # skipping statements for tables that already exist (epics, tasks, etc.)
            conn.executescript(schema_sql)
            print("  Schema applied successfully")
        else:
            print("  (dry run) would apply schema.sql")

        if not dry_run:
            conn.commit()

        print()
        print("Done.")

        # --- Step 7: Verify ---
        print()
        print("Verification:")
        new_tables = get_existing_tables(conn)
        for t in [
            "daemons",
            "possessions",
            "conversations",
            "messages",
            "message_acknowledgements",
            "conversation_views",
            "status_queue",
            "handoffs",
        ]:
            status = "OK" if t in new_tables else "MISSING"
            print(f"  {t}: {status}")

        # Count daemon seed data
        if not dry_run:
            cur = conn.execute("SELECT role, COUNT(*) FROM daemons GROUP BY role ORDER BY role")
            print()
            print("Daemon roster:")
            for role, count in cur.fetchall():
                print(f"  {role}: {count}")

    except Exception as exc:
        conn.rollback()
        print(f"\nERROR: {exc}", file=sys.stderr)
        raise
    finally:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply site-nine canonical schema")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB, help="Path to SQLite database")
    parser.add_argument("--dry-run", action="store_true", help="Show what would happen without making changes")
    args = parser.parse_args()

    apply(args.db, args.dry_run)


if __name__ == "__main__":
    main()
