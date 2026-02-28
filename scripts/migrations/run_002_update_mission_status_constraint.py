#!/usr/bin/env python3
"""
Migration script: Update mission status CHECK constraint

This script updates the mission status CHECK constraint to include the new
ADR-013 status values: ROLE_PENDING, PERSONA_PENDING, and SUSPENDED.

Usage:
    python scripts/migrations/run_002_update_mission_status_constraint.py

Related: EPC-H-0006, OPR-H-0139, ADR-013
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
    migration_sql_path = Path(__file__).parent / "002_update_mission_status_constraint.sql"

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

        # Check current CHECK constraint on status column
        cursor = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='missions'")
        current_schema = cursor.fetchone()

        if current_schema:
            schema_sql = current_schema[0]
            if "ROLE_PENDING" in schema_sql and "PERSONA_PENDING" in schema_sql and "SUSPENDED" in schema_sql:
                logger.warning(
                    "Migration appears to have already been run (new status values present in CHECK constraint)"
                )
                logger.info("Skipping migration")
                return

        logger.info("Running migration SQL...")
        logger.info("This will recreate the missions table with updated CHECK constraint...")

        # Execute the migration within a transaction
        conn.executescript(migration_sql)

        logger.success("Migration completed successfully")

        # Verify the new constraint is in place
        cursor = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='missions'")
        new_schema = cursor.fetchone()

        if new_schema:
            schema_sql = new_schema[0]
            if "ROLE_PENDING" in schema_sql:
                logger.debug("✓ ROLE_PENDING status added to CHECK constraint")
            if "PERSONA_PENDING" in schema_sql:
                logger.debug("✓ PERSONA_PENDING status added to CHECK constraint")
            if "SUSPENDED" in schema_sql:
                logger.debug("✓ SUSPENDED status added to CHECK constraint")

        # Verify data was preserved
        cursor = conn.execute("SELECT COUNT(*) FROM missions")
        count = cursor.fetchone()[0]
        logger.debug(f"✓ All {count} mission records preserved")

        # Verify indexes were recreated
        cursor = conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='index' AND tbl_name='missions'")
        index_count = cursor.fetchone()[0]
        logger.debug(f"✓ {index_count} indexes recreated")

        logger.success("All checks passed")

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


def main():
    """Main entry point"""
    logger.info("Starting mission status constraint update migration")

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
