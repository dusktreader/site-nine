#!/usr/bin/env python3
"""
Migrate tasks from old ID format to new format.

Old format: [ROLE_PREFIX][NUMBER] (e.g., OP001, ENG001)
New format: [ROLE_PREFIX]-[PRIORITY]-[NUMBER] (e.g., OPR-H-0001, ENG-H-0003)

This script:
1. Updates task IDs in database
2. Renames task artifact files
3. Updates references in .opencode/ directory
4. Updates CHECK constraint to include Historian role
"""

import os
import re
import sqlite3
from pathlib import Path

# Migration mapping
OLD_TO_NEW_PREFIX = {
    "OP": "OPR",
    "ENG": "ENG",
    "DOC": "DOC",
    "MAN": "MAN",
    "ARC": "ARC",
    "TST": "TST",
    "DES": "DES",
    "INS": "INS",
}

# Manual mapping for existing tasks (determined from database query)
TASK_MIGRATIONS = {
    "OP001": "OPR-H-0001",  # Operator, HIGH
    "DOC001": "DOC-M-0002",  # Documentarian, MEDIUM
    "ENG001": "ENG-H-0003",  # Engineer, HIGH
    "OP002": "OPR-H-0004",  # Operator, HIGH
    "OP003": "OPR-H-0005",  # Operator, HIGH
    "OP004": "OPR-H-0006",  # Operator, HIGH
}


def get_db_path() -> Path:
    """Get database path"""
    return Path(".opencode/data/project.db")


def migrate_database():
    """Migrate task IDs in database"""
    db_path = get_db_path()
    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        return False

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    print("📊 Migrating database...")

    try:
        # Get all tasks
        cursor.execute("SELECT id, role, priority, file_path FROM tasks")
        tasks = cursor.fetchall()

        print(f"   Found {len(tasks)} tasks to migrate")

        # Create new table with updated schema
        print("   Creating new tasks table with Historian role...")
        cursor.execute("""
            CREATE TABLE tasks_new (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                status TEXT NOT NULL
                    CHECK(status IN ('TODO', 'UNDERWAY', 'BLOCKED', 'PAUSED', 'REVIEW', 'COMPLETE', 'ABORTED')),
                priority TEXT NOT NULL
                    CHECK(priority IN ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW')),
                role TEXT NOT NULL
                    CHECK(role IN ('Manager', 'Architect', 'Engineer', 'Tester', 'Documentarian', 'Designer', 'Inspector', 'Operator', 'Historian')),
                category TEXT,
                agent_name TEXT,
                agent_id INTEGER,
                claimed_at TEXT,
                closed_at TEXT,
                paused_at TEXT,
                actual_hours REAL,
                objective TEXT NOT NULL,
                description TEXT,
                notes TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                file_path TEXT NOT NULL,
                CHECK(claimed_at IS NULL OR status NOT IN ('TODO')),
                CHECK(closed_at IS NULL OR status IN ('COMPLETE', 'ABORTED', 'PAUSED')),
                CHECK(paused_at IS NULL OR status = 'PAUSED'),
                FOREIGN KEY (agent_id) REFERENCES agents(id) ON DELETE SET NULL
            )
        """)

        # Migrate each task
        for task in tasks:
            old_id = task["id"]
            new_id = TASK_MIGRATIONS.get(old_id)

            if not new_id:
                print(f"   ⚠️  No migration mapping for task {old_id}, skipping")
                continue

            old_file_path = task["file_path"]
            new_file_path = old_file_path.replace(old_id, new_id) if old_file_path else None

            # Copy task to new table with new ID
            cursor.execute(
                """
                INSERT INTO tasks_new 
                SELECT :new_id, title, status, priority, role, category,
                       agent_name, agent_id, claimed_at, closed_at, paused_at,
                       actual_hours, objective, description, notes,
                       created_at, updated_at, :new_file_path
                FROM tasks
                WHERE id = :old_id
            """,
                {"new_id": new_id, "old_id": old_id, "new_file_path": new_file_path},
            )

            print(f"   ✓ Migrated {old_id} → {new_id}")

        # Update task_dependencies table
        print("   Updating task dependencies...")
        cursor.execute("SELECT task_id, depends_on_task_id FROM task_dependencies")
        dependencies = cursor.fetchall()

        for dep in dependencies:
            old_task_id = dep["task_id"]
            old_depends_on = dep["depends_on_task_id"]
            new_task_id = TASK_MIGRATIONS.get(old_task_id, old_task_id)
            new_depends_on = TASK_MIGRATIONS.get(old_depends_on, old_depends_on)

            cursor.execute(
                """
                UPDATE task_dependencies
                SET task_id = :new_task_id, depends_on_task_id = :new_depends_on
                WHERE task_id = :old_task_id AND depends_on_task_id = :old_depends_on
            """,
                {
                    "new_task_id": new_task_id,
                    "new_depends_on": new_depends_on,
                    "old_task_id": old_task_id,
                    "old_depends_on": old_depends_on,
                },
            )

        # Drop old table and rename new one
        print("   Replacing old tasks table...")
        cursor.execute("DROP TABLE tasks")
        cursor.execute("ALTER TABLE tasks_new RENAME TO tasks")

        # Recreate indexes
        print("   Recreating indexes...")
        cursor.execute("CREATE INDEX idx_tasks_status ON tasks(status)")
        cursor.execute("CREATE INDEX idx_tasks_priority ON tasks(priority)")
        cursor.execute("CREATE INDEX idx_tasks_role ON tasks(role)")
        cursor.execute("CREATE INDEX idx_tasks_agent_name ON tasks(agent_name)")
        cursor.execute("CREATE INDEX idx_tasks_agent_id ON tasks(agent_id)")
        cursor.execute("CREATE INDEX idx_tasks_updated ON tasks(updated_at)")
        cursor.execute("CREATE INDEX idx_tasks_created ON tasks(created_at)")

        # Recreate trigger
        cursor.execute("""
            CREATE TRIGGER update_tasks_timestamp
            AFTER UPDATE ON tasks
            FOR EACH ROW
            BEGIN
                UPDATE tasks SET updated_at = datetime('now') WHERE id = NEW.id;
            END
        """)

        conn.commit()
        print("   ✅ Database migration complete")
        return True

    except Exception as e:
        conn.rollback()
        print(f"   ❌ Error: {e}")
        return False
    finally:
        conn.close()


def migrate_files():
    """Rename task artifact files"""
    print("\n📁 Migrating task artifact files...")

    planning_dir = Path(".opencode/planning")
    if not planning_dir.exists():
        print(f"   ⚠️  Planning directory not found: {planning_dir}")
        return True

    for old_id, new_id in TASK_MIGRATIONS.items():
        old_file = planning_dir / f"{old_id}.md"
        new_file = planning_dir / f"{new_id}.md"

        if old_file.exists():
            old_file.rename(new_file)
            print(f"   ✓ Renamed {old_file.name} → {new_file.name}")
        else:
            print(f"   ⚠️  File not found: {old_file.name}")

    print("   ✅ File migration complete")
    return True


def update_references():
    """Update task ID references in .opencode/ directory"""
    print("\n🔍 Updating references in .opencode/...")

    opencode_dir = Path(".opencode")
    if not opencode_dir.exists():
        print(f"   ⚠️  .opencode directory not found")
        return True

    # File patterns to check
    patterns = ["**/*.md", "**/*.json", "**/*.yaml"]

    # Build regex pattern for all old IDs
    old_ids_pattern = "|".join(re.escape(old_id) for old_id in TASK_MIGRATIONS.keys())
    id_regex = re.compile(rf"\b({old_ids_pattern})\b")

    updated_files = []

    for pattern in patterns:
        for file_path in opencode_dir.glob(pattern):
            if file_path.is_file():
                try:
                    content = file_path.read_text()
                    original_content = content

                    # Replace all task ID references
                    def replace_id(match):
                        old_id = match.group(1)
                        return TASK_MIGRATIONS.get(old_id, old_id)

                    content = id_regex.sub(replace_id, content)

                    if content != original_content:
                        file_path.write_text(content)
                        updated_files.append(file_path.relative_to(opencode_dir))

                except Exception as e:
                    print(f"   ⚠️  Error processing {file_path}: {e}")

    if updated_files:
        print(f"   ✓ Updated {len(updated_files)} files:")
        for file in updated_files[:10]:  # Show first 10
            print(f"     - {file}")
        if len(updated_files) > 10:
            print(f"     ... and {len(updated_files) - 10} more")
    else:
        print("   ✓ No references found to update")

    print("   ✅ Reference update complete")
    return True


def main():
    """Run migration"""
    print("🚀 Starting task ID migration")
    print("=" * 60)
    print()
    print("This will migrate task IDs from old format to new format:")
    print("  Old: OP001, ENG001, DOC001")
    print("  New: OPR-H-0001, ENG-H-0003, DOC-M-0002")
    print()

    # Check if we're in the right directory
    if not Path(".opencode").exists():
        print("❌ Error: .opencode directory not found")
        print("   Please run this script from the project root")
        return 1

    # Run migration steps
    if not migrate_database():
        print("\n❌ Migration failed at database step")
        return 1

    if not migrate_files():
        print("\n❌ Migration failed at file step")
        return 1

    if not update_references():
        print("\n❌ Migration failed at reference update step")
        return 1

    print("\n" + "=" * 60)
    print("✅ Migration complete!")
    print()
    print("Summary:")
    print(f"  • Migrated {len(TASK_MIGRATIONS)} tasks in database")
    print(f"  • Renamed {len(TASK_MIGRATIONS)} task artifact files")
    print("  • Updated all references in .opencode/")
    print("  • Added Historian role to database schema")
    print()
    print("Next steps:")
    print("  1. Review changes: git status")
    print("  2. Test with: s9 task list")
    print("  3. Commit changes")

    return 0


if __name__ == "__main__":
    exit(main())
