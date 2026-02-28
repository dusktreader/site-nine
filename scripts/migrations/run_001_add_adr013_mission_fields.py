#!/usr/bin/env python3
"""
Migration script: Add ADR-013 mission fields

This script adds the OpenCode session integration fields to the missions table
per ADR-013. It can be run on an existing database without affecting existing missions.

Usage:
    python scripts/migrations/run_001_add_adr013_mission_fields.py

Related: EPC-H-0006, OPR-H-0138, ADR-013
"""

import sqlite3
import sys
from pathlib import Path

from loguru import logger

# Add project root to path so we can import site_nine
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from site_nine.core.paths import get_db_path


def run_migration(db_path: Path) -> None:
    """Run the migration on the specified database"""
    migration_sql_path = Path(__file__).parent / "001_add_adr013_mission_fields.sql"

    if not migration_sql_path.exists():
        logger.error(f"Migration SQL file not found: {migration_sql_path}")
        sys.exit(1)

    logger.info(f"Running migration on database: {db_path}")
    logger.info(f"Migration SQL: {migration_sql_path}")

    # Read migration SQL
    with open(migration_sql_path) as f:
        migration_sql = f.read()

    # Connect to database and run migration
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA foreign_keys = ON")

        # Check if migration has already been run
        cursor = conn.execute("PRAGMA table_info(missions)")
        columns = [row[1] for row in cursor.fetchall()]

        if "opencode_session_id" in columns:
            logger.warning("Migration appears to have already been run (opencode_session_id column exists)")
            logger.info("Skipping migration")
            return

        logger.info("Running migration SQL...")
        conn.executescript(migration_sql)
        conn.commit()
        logger.success("Migration completed successfully")

        # Verify columns were added
        cursor = conn.execute("PRAGMA table_info(missions)")
        columns = [row[1] for row in cursor.fetchall()]

        expected_columns = [
            "opencode_session_id",
            "mode",
            "last_activity_at",
            "suspension_time",
            "suspension_reason",
        ]

        for col in expected_columns:
            if col in columns:
                logger.debug(f"✓ Column '{col}' added successfully")
            else:
                logger.error(f"✗ Column '{col}' not found after migration")
                sys.exit(1)

        # Verify indexes were created
        cursor = conn.execute("PRAGMA index_list(missions)")
        indexes = [row[1] for row in cursor.fetchall()]

        expected_indexes = [
            "idx_missions_session_id",
            "idx_missions_mode",
            "idx_missions_suspended",
        ]

        for idx in expected_indexes:
            if idx in indexes:
                logger.debug(f"✓ Index '{idx}' created successfully")
            else:
                logger.error(f"✗ Index '{idx}' not found after migration")
                sys.exit(1)

        logger.success("All columns and indexes verified")

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


def main():
    """Main entry point"""
    logger.info("Starting ADR-013 mission fields migration")

    # Get database path
    db_path = get_db_path()

    if not db_path.exists():
        logger.error(f"Database not found: {db_path}")
        logger.info("Please initialize the database first with: s9 init")
        sys.exit(1)

    # Run migration
    run_migration(db_path)

    logger.info("Migration complete!")


if __name__ == "__main__":
    main()
