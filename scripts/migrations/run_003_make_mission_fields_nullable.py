#!/usr/bin/env python3
"""
Migration script: Make mission identity fields nullable

This script updates the missions table to allow NULL values for persona_name,
role, codename, mission_file, start_date, and start_time. This is required by
ADR-013's mission_init tool, which creates a mission record with ROLE_PENDING
status before role and persona are known.

Usage:
    python scripts/migrations/run_003_make_mission_fields_nullable.py

Related: EPC-H-0006, ENG-H-0143, ADR-013
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
    migration_sql_path = Path(__file__).parent / "003_make_mission_fields_nullable.sql"

    if not migration_sql_path.exists():
        logger.error(f"Migration SQL file not found: {migration_sql_path}")
        sys.exit(1)

    logger.info(f"Running migration on database: {db_path}")
    logger.info(f"Migration SQL: {migration_sql_path}")

    # Read migration SQL
    with open(migration_sql_path) as f:
        migration_sql = f.read()

    conn = sqlite3.connect(db_path)
    try:
        # Check if migration has already been run by inspecting persona_name nullability
        cursor = conn.execute("PRAGMA table_info(missions)")
        columns = {row[1]: row for row in cursor.fetchall()}

        # PRAGMA table_info column: (cid, name, type, notnull, dflt_value, pk)
        # notnull=1 means NOT NULL, notnull=0 means nullable
        persona_notnull = columns.get("persona_name", (None, None, None, 1))[3]
        if persona_notnull == 0:
            logger.warning("Migration appears to have already been run (persona_name is already nullable)")
            logger.info("Skipping migration")
            return

        logger.info("Running migration SQL...")
        conn.executescript(migration_sql)
        conn.commit()
        logger.success("Migration completed successfully")

        # Verify columns are now nullable
        cursor = conn.execute("PRAGMA table_info(missions)")
        columns = {row[1]: row for row in cursor.fetchall()}

        nullable_fields = ["persona_name", "role", "codename", "mission_file", "start_date", "start_time"]
        for field in nullable_fields:
            if field not in columns:
                logger.error(f"Column '{field}' not found after migration")
                sys.exit(1)
            notnull = columns[field][3]
            if notnull == 0:
                logger.debug(f"✓ Column '{field}' is nullable")
            else:
                logger.error(f"✗ Column '{field}' is still NOT NULL after migration")
                sys.exit(1)

        logger.success("All nullable fields verified")

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


def main():
    """Main entry point"""
    logger.info("Starting mission fields nullable migration")

    db_path = get_db_path()

    if not db_path.exists():
        logger.error(f"Database not found: {db_path}")
        logger.info("Please initialize the database first with: s9 init")
        sys.exit(1)

    run_migration(db_path)
    logger.info("Migration complete!")


if __name__ == "__main__":
    main()
