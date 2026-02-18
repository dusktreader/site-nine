#!/usr/bin/env python3
"""
Database migration: Add mission lifecycle status and heartbeat fields.

This migration adds:
1. `status` column (ACTIVE, IDLE, ENDED) - explicit lifecycle status
2. `last_active_at` column - timestamp of last agent activity (heartbeat)
3. Index on status column

Backfills existing data:
- Missions with end_time set -> status = 'ENDED'
- Missions without end_time -> status = 'ACTIVE'
- last_active_at -> set to updated_at for all existing missions

Run this script from the project root:
    python .opencode/scripts/migrate-add-mission-status.py [--dry-run]
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


def check_columns_exist(conn: sqlite3.Connection) -> dict[str, bool]:
    """Check which new columns already exist on the missions table."""
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(missions)")
    existing_columns = {row[1] for row in cursor.fetchall()}

    return {
        "status": "status" in existing_columns,
        "last_active_at": "last_active_at" in existing_columns,
    }


def check_index_exists(conn: sqlite3.Connection) -> bool:
    """Check if the status index already exists."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='index' AND name='idx_missions_status'
    """)
    return cursor.fetchone() is not None


def main() -> None:
    dry_run = "--dry-run" in sys.argv

    project_root = get_project_root()
    db_path = project_root / ".opencode" / "data" / "project.db"

    if not db_path.exists():
        print(f"ERROR: Database not found at {db_path}")
        sys.exit(1)

    print(f"Database: {db_path}")
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    print()

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    try:
        columns = check_columns_exist(conn)
        has_index = check_index_exists(conn)

        all_exist = all(columns.values()) and has_index
        if all_exist:
            print("All columns and indexes already exist. Nothing to do.")
            return

        some_exist = any(columns.values()) or has_index
        if some_exist:
            print("WARNING: Partial migration detected:")
            for col, exists in columns.items():
                print(f"  Column '{col}': {'EXISTS' if exists else 'MISSING'}")
            print(f"  Index 'idx_missions_status': {'EXISTS' if has_index else 'MISSING'}")
            print("Proceeding with missing items only...")
            print()

        steps = []

        if not columns["status"]:
            steps.append(
                (
                    "Add 'status' column",
                    """
                ALTER TABLE missions ADD COLUMN status TEXT NOT NULL DEFAULT 'ACTIVE'
                    CHECK(status IN ('ACTIVE', 'IDLE', 'ENDED'))
            """,
                )
            )

        if not columns["last_active_at"]:
            steps.append(
                (
                    "Add 'last_active_at' column",
                    """
                ALTER TABLE missions ADD COLUMN last_active_at TEXT
            """,
                )
            )

        for desc, sql in steps:
            print(f"  {desc}...")
            if not dry_run:
                conn.execute(sql)

        # Backfill existing data
        if not columns["status"]:
            print("  Backfilling status for ended missions...")
            if not dry_run:
                cursor = conn.execute("UPDATE missions SET status = 'ENDED' WHERE end_time IS NOT NULL")
                print(f"    Updated {cursor.rowcount} ended missions to ENDED")

                cursor = conn.execute("UPDATE missions SET status = 'ACTIVE' WHERE end_time IS NULL")
                print(f"    Updated {cursor.rowcount} active missions to ACTIVE")

        if not columns["last_active_at"]:
            print("  Backfilling last_active_at from updated_at...")
            if not dry_run:
                cursor = conn.execute("UPDATE missions SET last_active_at = updated_at")
                print(f"    Updated {cursor.rowcount} missions")

        if not has_index:
            print("  Creating index on status...")
            if not dry_run:
                conn.execute("CREATE INDEX idx_missions_status ON missions(status)")

        if not dry_run:
            conn.commit()
            print()
            print("Migration complete!")

            # Verify
            cursor = conn.execute("SELECT status, COUNT(*) as cnt FROM missions GROUP BY status")
            print()
            print("Mission status distribution:")
            for row in cursor:
                print(f"  {row['status']}: {row['cnt']}")
        else:
            print()
            print("DRY RUN complete. No changes made.")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
