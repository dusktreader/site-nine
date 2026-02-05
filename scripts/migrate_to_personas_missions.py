#!/usr/bin/env python3
"""
Migrate agents to missions and daemon_names to personas.

This script implements ADR-006: Entity Model Clarity - Personas, Missions, and Agents

Key changes:
1. Rename daemon_names → personas (update field names)
2. Rename agents → missions (add codenames, remove status)
3. Update tasks table (add current_mission_id, remove agent_name/agent_id)
4. Generate deterministic codenames for all missions
5. Close abandoned "in-progress" missions using file mtime
6. Migrate 57 session files (frontmatter, filenames, content)

Usage:
    python scripts/migrate_to_personas_missions.py --dry-run    # Preview changes
    python scripts/migrate_to_personas_missions.py --execute    # Apply migration
"""

import argparse
import os
import re
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Prime-length word lists for deterministic codename generation
ADJECTIVES = [
    "swift",
    "silent",
    "bold",
    "clever",
    "quantum",
    "stellar",
    "epic",
    "crimson",
    "azure",
    "phantom",
    "iron",
    "silver",
    "rogue",
    "cosmic",
    "electric",
    "shadow",
    "titanium",
    "mystic",
    "storm",
    "ghost",
    "crystal",
    "rapid",
    "omega",
    "void",
    "neon",
    "plasma",
    "razor",
    "cyber",
    "dark",
    "chrome",
    "gamma",
]  # 31 entries (prime)

NOUNS = [
    "thunder",
    "phoenix",
    "shadow",
    "dragon",
    "nexus",
    "vortex",
    "cipher",
    "falcon",
    "sentinel",
    "tempest",
    "wraith",
    "cascade",
    "apex",
    "forge",
    "blade",
    "comet",
    "prism",
    "quasar",
    "raven",
    "typhoon",
    "vector",
    "aurora",
    "blaze",
    "echo",
    "griffin",
    "helix",
    "kraken",
    "nebula",
    "zenith",
    "matrix",
    "pulse",
    "specter",
    "vertex",
    "enigma",
    "hydra",
    "photon",
    "titan",
]  # 37 entries (prime)


def generate_mission_codename(mission_id: int) -> str:
    """
    Generate deterministic codename from mission ID using prime modulo.

    Using coprime prime numbers (31 and 37) ensures maximum distribution
    before collisions occur. First collision happens at mission #1,147.

    31 × 37 = 1,147 unique combinations
    """
    adjective = ADJECTIVES[mission_id % len(ADJECTIVES)]
    noun = NOUNS[mission_id % len(NOUNS)]
    return f"{adjective}-{noun}"


def get_db_path() -> Path:
    """Get database path"""
    return Path(".opencode/data/project.db")


def get_session_files_dir() -> Path:
    """Get session files directory"""
    return Path(".opencode/work/sessions")


def get_missions_dir() -> Path:
    """Get missions directory (new location)"""
    return Path(".opencode/work/missions")


def backup_database(db_path: Path) -> Path:
    """Create database backup"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = db_path.parent / f"project.db.backup_{timestamp}"
    shutil.copy2(db_path, backup_path)
    return backup_path


def get_file_mtime(file_path: str) -> Optional[str]:
    """Get file modification time in ISO format"""
    if not os.path.exists(file_path):
        return None
    mtime = os.path.getmtime(file_path)
    return datetime.fromtimestamp(mtime).strftime("%H:%M:%S")


def analyze_current_state(conn: sqlite3.Connection) -> Dict:
    """Analyze current database state"""
    cursor = conn.cursor()

    # Count agents by status
    cursor.execute("""
        SELECT status, COUNT(*) as count
        FROM agents
        GROUP BY status
    """)
    agent_status_counts = dict(cursor.fetchall())

    # Get total agents
    cursor.execute("SELECT COUNT(*) FROM agents")
    total_agents = cursor.fetchone()[0]

    # Get in-progress agents
    cursor.execute("""
        SELECT id, name, session_file, session_date, start_time, end_time
        FROM agents
        WHERE status = 'in-progress'
        ORDER BY id
    """)
    in_progress_agents = cursor.fetchall()

    # Count tasks with agent references
    cursor.execute("""
        SELECT COUNT(*) FROM tasks
        WHERE agent_name IS NOT NULL OR agent_id IS NOT NULL
    """)
    tasks_with_agents = cursor.fetchone()[0]

    # Count session files
    sessions_dir = get_session_files_dir()
    session_files = list(sessions_dir.glob("*.md")) if sessions_dir.exists() else []

    return {
        "total_agents": total_agents,
        "agent_status_counts": agent_status_counts,
        "in_progress_agents": in_progress_agents,
        "tasks_with_agents": tasks_with_agents,
        "session_files": session_files,
        "session_file_count": len(session_files),
    }


def migrate_database(conn: sqlite3.Connection, dry_run: bool = True) -> Dict:
    """Migrate database schema and data"""
    cursor = conn.cursor()
    changes = {
        "personas_renamed": False,
        "missions_created": False,
        "tasks_updated": False,
        "codenames_generated": 0,
        "missions_closed": 0,
    }

    print("\n" + "=" * 80)
    print("DATABASE MIGRATION")
    print("=" * 80)

    # Step 1: Rename daemon_names → personas
    print("\n📋 Step 1: Rename daemon_names → personas")
    print("   - Rename table")
    print("   - Rename fields: usage_count → mission_count, last_used_at → last_mission_at")

    if not dry_run:
        # Create new personas table
        cursor.execute("""
            CREATE TABLE personas (
                name TEXT PRIMARY KEY,
                role TEXT NOT NULL
                    CHECK(role IN ('Administrator', 'Architect', 'Engineer', 'Tester', 'Documentarian', 'Designer', 'Inspector', 'Operator', 'Historian')),
                mythology TEXT NOT NULL,
                description TEXT NOT NULL,
                mission_count INTEGER NOT NULL DEFAULT 0,
                last_mission_at TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                CHECK(length(name) > 0)
            )
        """)

        # Copy data
        cursor.execute("""
            INSERT INTO personas (name, role, mythology, description, mission_count, last_mission_at, created_at)
            SELECT name, role, mythology, description, usage_count, last_used_at, created_at
            FROM daemon_names
        """)

        # Create indices
        cursor.execute("CREATE INDEX idx_personas_role ON personas(role)")
        cursor.execute("CREATE INDEX idx_personas_mission_count ON personas(mission_count)")
        cursor.execute("CREATE INDEX idx_personas_last_mission ON personas(last_mission_at)")

        # Drop old table
        cursor.execute("DROP TABLE daemon_names")

        changes["personas_renamed"] = True
        print("   ✅ Personas table created")

    # Step 2: Rename agents → missions and restructure
    print("\n📋 Step 2: Rename agents → missions")
    print("   - Add codename field")
    print("   - Remove status field")
    print("   - Rename fields: session_file → mission_file, session_date → start_date, task_summary → objective")
    print("   - Generate codenames for all missions")
    print("   - Close abandoned in-progress missions")

    if not dry_run:
        # Get all agents first
        cursor.execute("SELECT * FROM agents ORDER BY id")
        agents = cursor.fetchall()

        # Create new missions table
        cursor.execute("""
            CREATE TABLE missions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                persona_name TEXT NOT NULL,
                role TEXT NOT NULL
                    CHECK(role IN ('Administrator', 'Architect', 'Engineer', 'Tester', 'Documentarian', 'Designer', 'Inspector', 'Operator', 'Historian')),
                codename TEXT NOT NULL,
                mission_file TEXT NOT NULL,
                start_date TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT,
                objective TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                CHECK(length(persona_name) > 0),
                CHECK(length(mission_file) > 0),
                FOREIGN KEY (persona_name) REFERENCES personas(name) ON DELETE RESTRICT
            )
        """)

        # Migrate each agent
        for agent in agents:
            agent_id = agent[0]
            base_name = agent[2]
            role = agent[4]
            session_file = agent[5]
            session_date = agent[6]
            start_time = agent[7]
            end_time = agent[8]
            status = agent[9]
            task_summary = agent[10]
            created_at = agent[11]
            updated_at = agent[12]

            # Generate codename
            codename = generate_mission_codename(agent_id)
            changes["codenames_generated"] += 1

            # Determine end_time
            final_end_time = end_time
            if status == "in-progress" and not end_time:
                # Use file mtime to close abandoned missions
                file_end_time = get_file_mtime(session_file)
                if file_end_time:
                    final_end_time = file_end_time
                    changes["missions_closed"] += 1
                    print(f"   📝 Closing mission #{agent_id} ({base_name}) with mtime: {file_end_time}")

            # Insert into missions
            cursor.execute(
                """
                INSERT INTO missions (id, persona_name, role, codename, mission_file, start_date, start_time, end_time, objective, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    agent_id,
                    base_name,
                    role,
                    codename,
                    session_file,
                    session_date,
                    start_time,
                    final_end_time,
                    task_summary,
                    created_at,
                    updated_at,
                ),
            )

        # Create indices
        cursor.execute("CREATE INDEX idx_missions_persona_name ON missions(persona_name)")
        cursor.execute("CREATE INDEX idx_missions_role ON missions(role)")
        cursor.execute("CREATE INDEX idx_missions_start_date ON missions(start_date)")
        cursor.execute("CREATE INDEX idx_missions_codename ON missions(codename)")

        # Create trigger
        cursor.execute("""
            CREATE TRIGGER update_missions_timestamp
            AFTER UPDATE ON missions
            FOR EACH ROW
            BEGIN
                UPDATE missions SET updated_at = datetime('now') WHERE id = NEW.id;
            END
        """)

        # Drop old table
        cursor.execute("DROP TABLE agents")

        changes["missions_created"] = True
        print(f"   ✅ Missions table created with {changes['codenames_generated']} codenames")
        print(f"   ✅ Closed {changes['missions_closed']} abandoned missions")

    # Step 3: Update tasks table
    print("\n📋 Step 3: Update tasks table")
    print("   - Add current_mission_id field")
    print("   - Remove agent_name and agent_id fields")
    print("   - Migrate agent_id → current_mission_id for active tasks")

    if not dry_run:
        # Get all tasks
        cursor.execute("SELECT * FROM tasks ORDER BY id")
        tasks = cursor.fetchall()

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
                    CHECK(role IN ('Administrator', 'Architect', 'Engineer', 'Tester', 'Documentarian', 'Designer', 'Inspector', 'Operator', 'Historian')),
                category TEXT
                    CHECK(category IN ('feature', 'bug-fix', 'refactor', 'documentation', 'testing', 'infrastructure', 'security', 'performance', 'architecture', 'maintenance') OR category IS NULL),
                current_mission_id INTEGER,
                claimed_at TEXT,
                closed_at TEXT,
                paused_at TEXT,
                actual_hours REAL,
                description TEXT,
                notes TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                file_path TEXT NOT NULL,
                blocks_on_review_id INTEGER,
                CHECK(claimed_at IS NULL OR status NOT IN ('TODO')),
                CHECK(closed_at IS NULL OR status IN ('COMPLETE', 'ABORTED', 'PAUSED')),
                CHECK(paused_at IS NULL OR status = 'PAUSED'),
                FOREIGN KEY (current_mission_id) REFERENCES missions(id) ON DELETE SET NULL
            )
        """)

        # Migrate each task
        for task in tasks:
            task_id = task[0]
            title = task[1]
            status = task[2]
            priority = task[3]
            role = task[4]
            category = task[5]
            agent_name = task[6]
            agent_id = task[7]
            claimed_at = task[8]
            closed_at = task[9]
            paused_at = task[10]
            actual_hours = task[11]
            description = task[12]
            notes = task[13]
            created_at = task[14]
            updated_at = task[15]
            file_path = task[16]
            blocks_on_review_id = task[17] if len(task) > 17 else None

            # Migrate agent_id to current_mission_id only if task is UNDERWAY
            current_mission_id = agent_id if status == "UNDERWAY" else None

            cursor.execute(
                """
                INSERT INTO tasks_new (id, title, status, priority, role, category, current_mission_id, 
                                      claimed_at, closed_at, paused_at, actual_hours, description, notes,
                                      created_at, updated_at, file_path, blocks_on_review_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    task_id,
                    title,
                    status,
                    priority,
                    role,
                    category,
                    current_mission_id,
                    claimed_at,
                    closed_at,
                    paused_at,
                    actual_hours,
                    description,
                    notes,
                    created_at,
                    updated_at,
                    file_path,
                    blocks_on_review_id,
                ),
            )

        # Drop old table and rename new one
        cursor.execute("DROP TABLE tasks")
        cursor.execute("ALTER TABLE tasks_new RENAME TO tasks")

        # Create indices
        cursor.execute("CREATE INDEX idx_tasks_status ON tasks(status)")
        cursor.execute("CREATE INDEX idx_tasks_priority ON tasks(priority)")
        cursor.execute("CREATE INDEX idx_tasks_role ON tasks(role)")
        cursor.execute("CREATE INDEX idx_tasks_current_mission ON tasks(current_mission_id)")

        # Create trigger
        cursor.execute("""
            CREATE TRIGGER update_tasks_timestamp
            AFTER UPDATE ON tasks
            FOR EACH ROW
            BEGIN
                UPDATE tasks SET updated_at = datetime('now') WHERE id = NEW.id;
            END
        """)

        changes["tasks_updated"] = True
        print("   ✅ Tasks table updated")

    return changes


def migrate_session_files(conn: sqlite3.Connection, dry_run: bool = True) -> Dict:
    """Migrate session markdown files"""
    cursor = conn.cursor()
    changes = {
        "directory_renamed": False,
        "files_updated": 0,
        "files_renamed": 0,
        "content_updated": 0,
    }

    print("\n" + "=" * 80)
    print("SESSION FILE MIGRATION")
    print("=" * 80)

    sessions_dir = get_session_files_dir()
    missions_dir = get_missions_dir()

    if not sessions_dir.exists():
        print(f"❌ Sessions directory not found: {sessions_dir}")
        return changes

    # Get all missions with their codenames
    # In dry-run mode, query from agents table and generate codenames
    if dry_run:
        cursor.execute("SELECT id, base_name, session_file FROM agents ORDER BY id")
        agents = cursor.fetchall()
        missions = [(agent[0], agent[1], generate_mission_codename(agent[0]), agent[2]) for agent in agents]
    else:
        cursor.execute("SELECT id, persona_name, codename, mission_file FROM missions ORDER BY id")
        missions = cursor.fetchall()

    print(f"\n📋 Migrating {len(missions)} session files")
    print(f"   Source: {sessions_dir}")
    print(f"   Dest: {missions_dir}")

    if not dry_run:
        # Create missions directory
        missions_dir.mkdir(parents=True, exist_ok=True)

    for mission_id, persona_name, codename, old_file_path in missions:
        old_path = Path(old_file_path)

        # If file doesn't exist at exact path, try to find it by pattern
        if not old_path.exists():
            # Extract date, role, and name from filename
            filename = old_path.name
            # Pattern: YYYY-MM-DD.HH:MM:SS.role.name.*
            parts = filename.split(".")
            if len(parts) >= 4:
                date_str = parts[0]  # YYYY-MM-DD
                time_prefix = parts[1][:5]  # HH:MM (without seconds)
                role = parts[2]
                name = parts[3]

                # Search for matching file
                pattern = f"{date_str}.{time_prefix}*.{role}.{name}.*.md"
                matches = list(sessions_dir.glob(pattern))

                if matches:
                    old_path = matches[0]
                    if dry_run:
                        print(f"   📝 Mission #{mission_id}: Found {old_path.name} (matched pattern)")
                else:
                    print(f"   ⚠️  Mission #{mission_id}: File not found: {old_file_path}")
                    continue
            else:
                print(f"   ⚠️  Mission #{mission_id}: File not found: {old_file_path}")
                continue

        if not old_path.exists():
            print(f"   ⚠️  Mission #{mission_id}: File not found: {old_path}")
            continue

        # Read file content
        with open(old_path, "r") as f:
            content = f.read()

        # Update frontmatter
        # Replace: name: → persona:
        content = re.sub(r"^name:", "persona:", content, flags=re.MULTILINE)

        # Replace: task_summary: → objective:
        content = re.sub(r"^task_summary:", "objective:", content, flags=re.MULTILINE)

        # Remove: status: line
        content = re.sub(r"^status:.*\n", "", content, flags=re.MULTILINE)

        # Add codename and mission_id after persona
        content = re.sub(
            r"(^persona:.*\n)", f"\\1codename: {codename}\nmission_id: {mission_id}\n", content, flags=re.MULTILINE
        )

        # Update content terminology
        content = content.replace("Agent:", "Persona:")
        content = content.replace("agent session", "mission")
        content = content.replace("Session started", "Mission started")
        content = content.replace("Session completed", "Mission completed")
        content = content.replace("Agent name", "Persona name")

        # Determine new filename with codename
        old_filename = old_path.name
        # Pattern: YYYY-MM-DD.HH:MM:SS.role.name.task-summary.md
        # New: YYYY-MM-DD.HH:MM:SS.role.name.codename.md
        parts = old_filename.rsplit(".", 2)  # Split from right: [base, task-summary, 'md']
        if len(parts) == 3:
            base_parts = parts[0].split(".")
            if len(base_parts) >= 4:
                # base_parts = [date, time, role, name, ...]
                new_filename = f"{'.'.join(base_parts[:4])}.{codename}.md"
            else:
                new_filename = f"{parts[0]}.{codename}.md"
        else:
            new_filename = f"{parts[0]}.{codename}.md"

        new_path = missions_dir / new_filename

        if dry_run:
            print(f"   📝 Mission #{mission_id}: {old_path.name} → {new_filename}")
        else:
            # Write updated content to new location
            with open(new_path, "w") as f:
                f.write(content)

            changes["files_updated"] += 1
            changes["files_renamed"] += 1
            changes["content_updated"] += 1

            # Update mission_file in database
            cursor.execute("UPDATE missions SET mission_file = ? WHERE id = ?", (str(new_path), mission_id))

    if not dry_run:
        changes["directory_renamed"] = True
        print(f"   ✅ Migrated {changes['files_updated']} files")
        print(f"   ✅ Renamed {changes['files_renamed']} files with codenames")
        print(f"   ✅ Updated content in {changes['content_updated']} files")

    return changes


def print_summary(state: Dict, db_changes: Dict, file_changes: Dict, dry_run: bool):
    """Print migration summary"""
    print("\n" + "=" * 80)
    print("MIGRATION SUMMARY")
    print("=" * 80)

    print("\n📊 Current State:")
    print(f"   Total agents: {state['total_agents']}")
    print(f"   Agent status breakdown:")
    for status, count in state["agent_status_counts"].items():
        print(f"      {status}: {count}")
    print(f"   In-progress agents: {len(state['in_progress_agents'])}")
    print(f"   Tasks with agent references: {state['tasks_with_agents']}")
    print(f"   Session files: {state['session_file_count']}")

    if dry_run:
        print("\n⚠️  DRY RUN - No changes applied")
        print("\nTo execute migration, run:")
        print("   python scripts/migrate_to_personas_missions.py --execute")
    else:
        print("\n✅ Migration Applied:")
        print(f"   Personas table: {'✅ Created' if db_changes['personas_renamed'] else '❌ Failed'}")
        print(f"   Missions table: {'✅ Created' if db_changes['missions_created'] else '❌ Failed'}")
        print(f"   Tasks table: {'✅ Updated' if db_changes['tasks_updated'] else '❌ Failed'}")
        print(f"   Codenames generated: {db_changes['codenames_generated']}")
        print(f"   Abandoned missions closed: {db_changes['missions_closed']}")
        print(f"   Session files migrated: {file_changes['files_updated']}")
        print(f"   Files renamed: {file_changes['files_renamed']}")
        print(f"   Content updated: {file_changes['content_updated']}")


def main():
    parser = argparse.ArgumentParser(description="Migrate agents to missions and daemon_names to personas")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without applying them")
    parser.add_argument("--execute", action="store_true", help="Execute the migration")
    args = parser.parse_args()

    if not args.dry_run and not args.execute:
        print("❌ Must specify either --dry-run or --execute")
        parser.print_help()
        return 1

    dry_run = args.dry_run

    db_path = get_db_path()
    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        return 1

    # Backup database (even for dry-run, for safety)
    if not dry_run:
        backup_path = backup_database(db_path)
        print(f"✅ Database backed up to: {backup_path}")

    # Connect to database
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    try:
        # Analyze current state
        state = analyze_current_state(conn)

        # Migrate database
        db_changes = migrate_database(conn, dry_run=dry_run)

        # Migrate session files
        file_changes = migrate_session_files(conn, dry_run=dry_run)

        # Commit changes
        if not dry_run:
            conn.commit()
            print("\n✅ Database changes committed")

        # Print summary
        print_summary(state, db_changes, file_changes, dry_run)

        return 0

    except Exception as e:
        conn.rollback()
        print(f"\n❌ Migration failed: {e}")
        import traceback

        traceback.print_exc()
        return 1

    finally:
        conn.close()


if __name__ == "__main__":
    exit(main())
