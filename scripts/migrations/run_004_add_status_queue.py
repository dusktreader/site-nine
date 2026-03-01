#!/usr/bin/env python3
"""
Migration script: Add status_queue table

Adds a lightweight queue for worker-to-director status toast notifications.
Workers push short status messages here; the OpenCode plugin pops and toasts
them in the interactive (non-desk-mode) session. Cleared on s9 summon.

Usage:
    python scripts/migrations/run_004_add_status_queue.py
"""

import sqlite3
import sys
from pathlib import Path

from loguru import logger

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from site_nine.core.paths import get_db_path


def run_migration(db_path: Path) -> None:
    migration_sql_path = Path(__file__).parent / "004_add_status_queue.sql"

    if not migration_sql_path.exists():
        logger.error(f"Migration SQL file not found: {migration_sql_path}")
        sys.exit(1)

    logger.info(f"Running migration on database: {db_path}")

    with open(migration_sql_path) as f:
        migration_sql = f.read()

    conn = sqlite3.connect(db_path)
    try:
        # Idempotency check: skip if table already exists
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='status_queue'")
        if cursor.fetchone():
            logger.warning("status_queue table already exists — skipping migration")
            return

        logger.info("Running migration SQL...")
        conn.executescript(migration_sql)
        conn.commit()
        logger.success("Migration completed successfully")

        # Verify
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='status_queue'")
        if cursor.fetchone():
            logger.success("✓ status_queue table created")
        else:
            logger.error("✗ status_queue table not found after migration")
            sys.exit(1)

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


def main():
    logger.info("Starting status_queue migration")

    db_path = get_db_path()
    if not db_path.exists():
        logger.error(f"Database not found: {db_path}")
        sys.exit(1)

    run_migration(db_path)
    logger.info("Migration complete!")


if __name__ == "__main__":
    main()
