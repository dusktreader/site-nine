#!/usr/bin/env python3
"""
Migration script to rename Manager role to Administrator.

This script:
1. Creates new tables with updated CHECK constraints
2. Copies data from old tables
3. Drops old tables
4. Renames new tables to original names

SQLite doesn't support ALTER TABLE to modify CHECK constraints,
so we need to recreate the tables.
"""

import sqlite3
from pathlib import Path


def migrate_database(db_path: Path) -> None:
    """Migrate Manager role to Administrator in the database"""

    if not db_path.exists():
        print(f"❌ Error: Database not found at {db_path}")
        return

    print(f"🔄 Migrating database: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Count records before migration
        cursor.execute("SELECT COUNT(*) FROM daemon_names WHERE role = 'Manager'")
        names_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM agents WHERE role = 'Manager'")
        agents_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM tasks WHERE role = 'Manager'")
        tasks_count = cursor.fetchone()[0]

        print(f"\n📊 Records to migrate:")
        print(f"   - daemon_names: {names_count}")
        print(f"   - agents: {agents_count}")
        print(f"   - tasks: {tasks_count}")

        print(f"\n🔧 Step 1: Migrating daemon_names table...")

        # Create new daemon_names table with updated CHECK constraint
        cursor.execute("""
            CREATE TABLE daemon_names_new (
                name TEXT PRIMARY KEY,
                role TEXT NOT NULL
                    CHECK(role IN ('Administrator', 'Architect', 'Builder', 'Tester', 'Documentarian', 'Designer', 'Inspector', 'Operator', 'Historian')),
                mythology TEXT NOT NULL,
                description TEXT NOT NULL,
                usage_count INTEGER NOT NULL DEFAULT 0,
                last_used_at TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                CHECK(length(name) > 0)
            )
        """)

        # Copy data, converting Manager to Administrator
        cursor.execute("""
            INSERT INTO daemon_names_new
            SELECT name,
                   CASE WHEN role = 'Manager' THEN 'Administrator' ELSE role END as role,
                   mythology,
                   description,
                   usage_count,
                   last_used_at,
                   created_at
            FROM daemon_names
        """)

        # Drop old table and rename new one
        cursor.execute("DROP TABLE daemon_names")
        cursor.execute("ALTER TABLE daemon_names_new RENAME TO daemon_names")

        # Recreate indexes
        cursor.execute("CREATE INDEX idx_daemon_names_role ON daemon_names(role)")
        cursor.execute("CREATE INDEX idx_daemon_names_usage ON daemon_names(usage_count)")
        cursor.execute("CREATE INDEX idx_daemon_names_last_used ON daemon_names(last_used_at)")

        print(f"   ✓ daemon_names table migrated")

        print(f"\n🔧 Step 2: Migrating agents table...")

        # Create new agents table
        cursor.execute("""
            CREATE TABLE agents_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                base_name TEXT NOT NULL,
                suffix TEXT,
                role TEXT NOT NULL
                    CHECK(role IN ('Administrator', 'Architect', 'Builder', 'Tester', 'Documentarian', 'Designer', 'Inspector', 'Operator', 'Historian')),
                session_file TEXT NOT NULL,
                session_date TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT,
                status TEXT NOT NULL DEFAULT 'in-progress'
                    CHECK(status IN ('in-progress', 'paused', 'completed', 'failed', 'aborted')),
                task_summary TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                CHECK(length(name) > 0),
                CHECK(length(base_name) > 0),
                CHECK(length(session_file) > 0),
                FOREIGN KEY (base_name) REFERENCES daemon_names(name) ON DELETE RESTRICT
            )
        """)

        # Copy data, converting Manager to Administrator
        cursor.execute("""
            INSERT INTO agents_new
            SELECT id, name, base_name, suffix,
                   CASE WHEN role = 'Manager' THEN 'Administrator' ELSE role END as role,
                   session_file, session_date, start_time, end_time, status,
                   task_summary, created_at, updated_at
            FROM agents
        """)

        # Drop old table and rename new one
        cursor.execute("DROP TABLE agents")
        cursor.execute("ALTER TABLE agents_new RENAME TO agents")

        # Recreate indexes
        cursor.execute("CREATE INDEX idx_agents_name ON agents(name)")
        cursor.execute("CREATE INDEX idx_agents_base_name ON agents(base_name)")
        cursor.execute("CREATE INDEX idx_agents_role ON agents(role)")
        cursor.execute("CREATE INDEX idx_agents_session_date ON agents(session_date)")
        cursor.execute("CREATE INDEX idx_agents_status ON agents(status)")

        # Recreate trigger
        cursor.execute("""
            CREATE TRIGGER update_agents_timestamp
            AFTER UPDATE ON agents
            FOR EACH ROW
            BEGIN
                UPDATE agents SET updated_at = datetime('now') WHERE id = NEW.id;
            END
        """)

        print(f"   ✓ agents table migrated")

        print(f"\n🔧 Step 3: Migrating tasks table...")

        # Create new tasks table
        cursor.execute("""
            CREATE TABLE tasks_new (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                status TEXT NOT NULL
                    CHECK(status IN ('TODO', 'UNDERWAY', 'BLOCKED', 'PAUSED', 'REVIEW', 'COMPLETE', 'ABORTED')),
                priority TEXT NOT NULL
                    CHECK(priority IN ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW')),
                role TEXT NOT NULL
                    CHECK(role IN ('Administrator', 'Architect', 'Builder', 'Tester', 'Documentarian', 'Designer', 'Inspector', 'Operator', 'Historian')),
                category TEXT
                    CHECK(category IN ('feature', 'bug-fix', 'refactor', 'documentation', 'testing', 'infrastructure', 'security', 'performance', 'architecture', 'maintenance') OR category IS NULL),
                agent_name TEXT,
                agent_id INTEGER,
                claimed_at TEXT,
                closed_at TEXT,
                paused_at TEXT,
                actual_hours REAL,
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

        # Copy data, converting Manager to Administrator
        cursor.execute("""
            INSERT INTO tasks_new
            SELECT id, title, status, priority,
                   CASE WHEN role = 'Manager' THEN 'Administrator' ELSE role END as role,
                   category, agent_name, agent_id, claimed_at, closed_at, paused_at,
                   actual_hours, description, notes, created_at, updated_at, file_path
            FROM tasks
        """)

        # Drop old table and rename new one
        cursor.execute("DROP TABLE tasks")
        cursor.execute("ALTER TABLE tasks_new RENAME TO tasks")

        # Recreate indexes
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

        print(f"   ✓ tasks table migrated")

        print(f"\n🔧 Step 4: Migrating task_templates table...")

        # Create new task_templates table
        cursor.execute("""
            CREATE TABLE task_templates_new (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                title_template TEXT NOT NULL,
                priority TEXT NOT NULL
                    CHECK(priority IN ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW')),
                role TEXT NOT NULL
                    CHECK(role IN ('Administrator', 'Architect', 'Builder', 'Tester', 'Documentarian', 'Designer', 'Inspector', 'Operator', 'Historian')),
                category TEXT,
                objective_template TEXT NOT NULL,
                description_template TEXT,
                variables TEXT,
                usage_count INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                CHECK(length(id) > 0),
                CHECK(length(name) > 0),
                CHECK(length(title_template) > 0),
                CHECK(length(objective_template) > 0)
            )
        """)

        # Copy data, converting Manager to Administrator
        cursor.execute("""
            INSERT INTO task_templates_new
            SELECT id, name, description, title_template, priority,
                   CASE WHEN role = 'Manager' THEN 'Administrator' ELSE role END as role,
                   category, objective_template, description_template, variables,
                   usage_count, created_at, updated_at
            FROM task_templates
        """)

        # Drop old table and rename new one
        cursor.execute("DROP TABLE task_templates")
        cursor.execute("ALTER TABLE task_templates_new RENAME TO task_templates")

        # Recreate indexes
        cursor.execute("CREATE INDEX idx_task_templates_role ON task_templates(role)")
        cursor.execute("CREATE INDEX idx_task_templates_priority ON task_templates(priority)")
        cursor.execute("CREATE INDEX idx_task_templates_usage ON task_templates(usage_count)")

        # Recreate trigger
        cursor.execute("""
            CREATE TRIGGER update_task_templates_timestamp
            AFTER UPDATE ON task_templates
            FOR EACH ROW
            BEGIN
                UPDATE task_templates SET updated_at = datetime('now') WHERE id = NEW.id;
            END
        """)

        print(f"   ✓ task_templates table migrated")

        # Commit changes
        conn.commit()

        # Verify migration
        print(f"\n✅ Verifying migration...")

        cursor.execute("SELECT COUNT(*) FROM daemon_names WHERE role = 'Manager'")
        remaining_names = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM agents WHERE role = 'Manager'")
        remaining_agents = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM tasks WHERE role = 'Manager'")
        remaining_tasks = cursor.fetchone()[0]

        if remaining_names == 0 and remaining_agents == 0 and remaining_tasks == 0:
            print(f"   ✓ Migration successful! No 'Manager' records remain.")
        else:
            print(f"   ⚠️  Warning: Some 'Manager' records still exist:")
            print(f"      - daemon_names: {remaining_names}")
            print(f"      - agents: {remaining_agents}")
            print(f"      - tasks: {remaining_tasks}")

        # Show Administrator records
        cursor.execute("SELECT COUNT(*) FROM daemon_names WHERE role = 'Administrator'")
        admin_names = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM agents WHERE role = 'Administrator'")
        admin_agents = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM tasks WHERE role = 'Administrator'")
        admin_tasks = cursor.fetchone()[0]

        print(f"\n📈 Administrator records after migration:")
        print(f"   - daemon_names: {admin_names}")
        print(f"   - agents: {admin_agents}")
        print(f"   - tasks: {admin_tasks}")

    except Exception as e:
        conn.rollback()
        print(f"❌ Migration failed: {e}")
        raise
    finally:
        conn.close()

    print(f"\n✅ Migration complete!")


if __name__ == "__main__":
    # Find .opencode directory
    current = Path.cwd()
    opencode_dir = None

    # Look for .opencode in current directory or parents
    for path in [current] + list(current.parents):
        candidate = path / ".opencode"
        if candidate.exists() and candidate.is_dir():
            opencode_dir = candidate
            break

    if not opencode_dir:
        print("❌ Error: .opencode directory not found")
        print("   Run this script from the project root or a subdirectory")
        exit(1)

    db_path = opencode_dir / "data" / "project.db"
    migrate_database(db_path)
