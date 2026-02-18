"""Infrastructure and data integrity check functions.

Each check function returns either an InfraResult or a list of DiagnosticIssues.
The manager calls these and aggregates the results into a DiagnosticReport.
"""

from __future__ import annotations

import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

from site_nine.core.database import Database
from site_nine.core.paths import validate_path_within_project
from site_nine.core.utils import utc_now
from site_nine.doctor.models import DiagnosticIssue, InfraResult, Severity


# =============================================================================
# Infrastructure checks
# =============================================================================


def check_database_exists(db_path: Path) -> InfraResult:
    """Infra 1: Check that the database file exists."""
    if not db_path.exists():
        return InfraResult(
            name="1. Database File",
            passed=False,
            message=f"Database file not found: {db_path}\nRun 's9 init' to initialize the project.",
        )
    return InfraResult(
        name="1. Database File",
        passed=True,
        message=f"Database file exists: {db_path}",
    )


def check_database_integrity(db_path: Path) -> InfraResult:
    """Infra 2: Run SQLite PRAGMA integrity_check."""
    try:
        result = subprocess.run(
            ["sqlite3", str(db_path), "PRAGMA integrity_check;"],
            capture_output=True,
            text=True,
            check=True,
        )
        if result.stdout.strip() == "ok":
            return InfraResult(
                name="2. DB Integrity",
                passed=True,
                message="Database integrity check passed",
            )
        else:
            return InfraResult(
                name="2. DB Integrity",
                passed=False,
                message=f"Database integrity check failed: {result.stdout.strip()}\nYou may need to restore from backup.",
            )
    except subprocess.CalledProcessError as e:
        return InfraResult(
            name="2. DB Integrity",
            passed=False,
            message=f"Failed to run integrity check: {e}\nMake sure sqlite3 is installed.",
        )
    except FileNotFoundError:
        return InfraResult(
            name="2. DB Integrity",
            passed=False,
            warning=True,
            message="sqlite3 command not found - skipping integrity check.\nInstall sqlite3 to enable this check.",
        )


def check_gitignore(opencode_dir: Path, *, verbose: bool = False) -> InfraResult:
    """Infra 3: Check that .gitignore has recommended patterns."""
    gitignore_path = opencode_dir.parent / ".gitignore"

    if not gitignore_path.exists():
        return InfraResult(
            name="3. Gitignore",
            passed=True,
            warning=True,
            message="No .gitignore file found. Consider creating one to avoid committing database files.",
        )

    gitignore_content = gitignore_path.read_text()
    recommended_patterns = [".opencode/data/*.db", ".opencode/data/*.db-journal", ".opencode/data/*.db-wal"]
    missing_patterns = [p for p in recommended_patterns if p not in gitignore_content]

    if missing_patterns:
        detail_lines: list[str] = []
        body_lines = [f"Missing {len(missing_patterns)} recommended .gitignore patterns:"]
        for pattern in missing_patterns:
            body_lines.append(f"  {pattern}")
            if verbose:
                detail_lines.append(f"  Missing recommended pattern: {pattern}")
        return InfraResult(
            name="3. Gitignore",
            passed=True,
            warning=True,
            message="\n".join(body_lines),
            detail_lines=detail_lines,
        )

    return InfraResult(
        name="3. Gitignore",
        passed=True,
        message="All recommended .gitignore patterns present",
    )


def check_backups(opencode_dir: Path, *, verbose: bool = False) -> InfraResult:
    """Infra 4: Check for backup files."""
    backup_dir = opencode_dir / "data"
    backup_patterns = ["*.db.backup", "*.tar.gz", "*.zip"]
    backups_found: list[Path] = []
    for pattern in backup_patterns:
        backups_found.extend(backup_dir.glob(pattern))

    if backups_found:
        detail_lines: list[str] = []
        if verbose:
            for backup in backups_found:
                detail_lines.append(f"  {backup.name}")
        return InfraResult(
            name="4. Backups",
            passed=True,
            message=f"Found {len(backups_found)} backup file(s)",
            detail_lines=detail_lines,
        )

    return InfraResult(
        name="4. Backups",
        passed=True,
        warning=True,
        message="No backup files found. Consider creating regular backups of your database.",
    )


def check_temp_files(db_path: Path, *, verbose: bool = False) -> InfraResult:
    """Infra 5: Check for SQLite temporary files."""
    journal_file = db_path.parent / f"{db_path.name}-journal"
    wal_file = db_path.parent / f"{db_path.name}-wal"
    shm_file = db_path.parent / f"{db_path.name}-shm"

    temp_files = []
    if journal_file.exists():
        temp_files.append(journal_file.name)
    if wal_file.exists():
        temp_files.append(wal_file.name)
    if shm_file.exists():
        temp_files.append(shm_file.name)

    if temp_files:
        detail_lines: list[str] = []
        if verbose:
            for temp_file in temp_files:
                detail_lines.append(f"  {temp_file}")
        return InfraResult(
            name="5. SQLite Temp Files",
            passed=True,
            warning=True,
            message=f"Found SQLite temporary files: {', '.join(temp_files)}\nThis may indicate active transactions or improper shutdown.",
            detail_lines=detail_lines,
        )

    return InfraResult(
        name="5. SQLite Temp Files",
        passed=True,
        message="No SQLite temporary files present",
    )


# =============================================================================
# Data integrity checks
# =============================================================================


def check_mission_personas(db: Database, *, verbose: bool = False) -> tuple[str, list[DiagnosticIssue]]:
    """Check 6a: missions.persona_name -> personas.name foreign key."""
    invalid_missions = db.execute_query("""
        SELECT m.id, m.codename, m.persona_name
        FROM missions m
        LEFT JOIN personas p ON m.persona_name = p.name
        WHERE p.name IS NULL
    """)

    issues: list[DiagnosticIssue] = []
    if invalid_missions:
        for mission in invalid_missions:
            desc = (
                f"Mission #{mission['id']} ({mission['codename']}): "
                f"persona_name '{mission['persona_name']}' not found in personas"
            )
            issues.append(DiagnosticIssue(category="foreign_key", severity=Severity.ERROR, description=desc))

    label = "6a. Mission Personas"
    return label, issues


def check_task_mission_refs(db: Database, *, verbose: bool = False) -> tuple[str, list[DiagnosticIssue]]:
    """Check 6b: tasks.current_mission_id -> missions.id foreign key."""
    orphaned_tasks = db.execute_query("""
        SELECT t.id, t.title, t.current_mission_id
        FROM tasks t
        WHERE t.current_mission_id IS NOT NULL
        AND NOT EXISTS (SELECT 1 FROM missions WHERE id = t.current_mission_id)
    """)

    issues: list[DiagnosticIssue] = []
    if orphaned_tasks:
        for task in orphaned_tasks:
            desc = f"Task {task['id']}: references non-existent mission current_mission_id {task['current_mission_id']}"
            task_id = task["id"]

            def make_fix(tid: str = task_id) -> None:
                db.execute_update("UPDATE tasks SET current_mission_id = NULL WHERE id = :id", {"id": tid})

            issues.append(
                DiagnosticIssue(category="foreign_key", severity=Severity.FIXABLE, description=desc, fix_fn=make_fix)
            )

    label = "6b. Task Mission Refs"
    return label, issues


def check_task_dependencies(db: Database, *, verbose: bool = False) -> tuple[str, list[DiagnosticIssue]]:
    """Check 6c: task_dependencies referencing non-existent tasks."""
    invalid_deps = db.execute_query("""
        SELECT td.task_id, td.depends_on_task_id
        FROM task_dependencies td
        WHERE NOT EXISTS (SELECT 1 FROM tasks WHERE id = td.task_id)
           OR NOT EXISTS (SELECT 1 FROM tasks WHERE id = td.depends_on_task_id)
    """)

    issues: list[DiagnosticIssue] = []
    if invalid_deps:
        for dep in invalid_deps:
            desc = f"Dependency: {dep['task_id']} -> {dep['depends_on_task_id']} references non-existent task(s)"
            d_task_id = dep["task_id"]
            depends_on = dep["depends_on_task_id"]

            def make_fix(tid: str = d_task_id, dep_on: str = depends_on) -> None:
                db.execute_update(
                    "DELETE FROM task_dependencies WHERE task_id = :task_id AND depends_on_task_id = :depends_on",
                    {"task_id": tid, "depends_on": dep_on},
                )

            issues.append(
                DiagnosticIssue(category="foreign_key", severity=Severity.FIXABLE, description=desc, fix_fn=make_fix)
            )

    label = "6c. Task Dependencies"
    return label, issues


def check_closed_timestamps(db: Database, *, verbose: bool = False) -> tuple[str, list[DiagnosticIssue]]:
    """Check 7a: Tasks COMPLETE/ABORTED should have closed_at."""
    unclosed_tasks = db.execute_query("""
        SELECT id, title, status
        FROM tasks
        WHERE status IN ('COMPLETE', 'ABORTED')
        AND closed_at IS NULL
    """)

    issues: list[DiagnosticIssue] = []
    if unclosed_tasks:
        for task in unclosed_tasks:
            desc = f"Task {task['id']}: status is {task['status']} but missing closed_at timestamp"
            now = utc_now()
            task_id = task["id"]

            def make_fix(tid: str = task_id, ts: str = now) -> None:
                db.execute_update(
                    "UPDATE tasks SET closed_at = :timestamp WHERE id = :id",
                    {"timestamp": ts, "id": tid},
                )

            issues.append(
                DiagnosticIssue(category="task_state", severity=Severity.FIXABLE, description=desc, fix_fn=make_fix)
            )

    label = "7a. Closed Timestamps"
    return label, issues


def check_claimed_timestamps(db: Database, *, verbose: bool = False) -> tuple[str, list[DiagnosticIssue]]:
    """Check 7b: Tasks UNDERWAY should have claimed_at."""
    incomplete_underway = db.execute_query("""
        SELECT id, title, claimed_at
        FROM tasks
        WHERE status = 'UNDERWAY'
        AND claimed_at IS NULL
    """)

    issues: list[DiagnosticIssue] = []
    if incomplete_underway:
        for task in incomplete_underway:
            desc = f"Task {task['id']}: status is UNDERWAY but missing claimed_at timestamp"
            issues.append(DiagnosticIssue(category="task_state", severity=Severity.WARNING, description=desc))

    label = "7b. Claimed Timestamps"
    return label, issues


def check_mission_data(db: Database, *, verbose: bool = False) -> tuple[str, list[DiagnosticIssue]]:
    """Check 8a: All missions should have start_time."""
    all_missions = db.execute_query("""
        SELECT id, codename, persona_name, start_time, end_time
        FROM missions
    """)

    issues: list[DiagnosticIssue] = []
    for mission in all_missions:
        if not mission.get("start_time"):
            desc = f"Mission #{mission['id']} ({mission.get('codename', 'unknown')}): missing start_time"
            issues.append(DiagnosticIssue(category="mission_data", severity=Severity.ERROR, description=desc))

    label = "8a. Mission Data"
    return label, issues


def check_mission_files(
    db: Database, opencode_dir: Path, *, verbose: bool = False
) -> tuple[str, list[DiagnosticIssue]]:
    """Check 8b: Mission files should exist on disk."""
    all_missions_with_files = db.execute_query("SELECT id, codename, mission_file FROM missions")

    issues: list[DiagnosticIssue] = []
    for mission in all_missions_with_files:
        if mission.get("mission_file"):
            mission_path = opencode_dir / mission["mission_file"]
            if not mission_path.exists():
                desc = (
                    f"Mission #{mission['id']} ({mission['codename']}): "
                    f"mission file not found: {mission['mission_file']}"
                )
                issues.append(DiagnosticIssue(category="mission_data", severity=Severity.ERROR, description=desc))

    label = "8b. Mission Files"
    return label, issues


def check_mission_counts(db: Database, *, verbose: bool = False) -> tuple[str, list[DiagnosticIssue]]:
    """Check 9a: persona mission_count should match actual count."""
    wrong_counts = db.execute_query("""
        SELECT p.name, p.mission_count, COUNT(m.id) as actual_count
        FROM personas p
        LEFT JOIN missions m ON p.name = m.persona_name
        GROUP BY p.name
        HAVING p.mission_count != COUNT(m.id)
    """)

    issues: list[DiagnosticIssue] = []
    if wrong_counts:
        for name_info in wrong_counts:
            desc = (
                f"Persona '{name_info['name']}': mission_count is {name_info['mission_count']} "
                f"but actual count is {name_info['actual_count']}"
            )
            name = name_info["name"]
            count = name_info["actual_count"]

            def make_fix(n: str = name, c: int = count) -> None:
                db.execute_update(
                    "UPDATE personas SET mission_count = :count WHERE name = :name",
                    {"count": c, "name": n},
                )

            issues.append(
                DiagnosticIssue(category="mission_count", severity=Severity.FIXABLE, description=desc, fix_fn=make_fix)
            )

    label = "9a. Mission Counts"
    return label, issues


def check_last_mission_dates(db: Database, *, verbose: bool = False) -> tuple[str, list[DiagnosticIssue]]:
    """Check 9b: persona last_mission_at should match actual latest mission."""
    wrong_dates = db.execute_query("""
        SELECT p.name, p.last_mission_at, MAX(m.start_time) as actual_last_mission
        FROM personas p
        LEFT JOIN missions m ON p.name = m.persona_name
        GROUP BY p.name
        HAVING (p.last_mission_at IS NULL AND actual_last_mission IS NOT NULL)
            OR (p.last_mission_at IS NOT NULL AND p.last_mission_at != actual_last_mission)
    """)

    issues: list[DiagnosticIssue] = []
    if wrong_dates:
        for name_info in wrong_dates:
            desc = f"Persona '{name_info['name']}': last_mission_at doesn't match actual mission history"
            name = name_info["name"]
            date = name_info["actual_last_mission"]

            def make_fix(n: str = name, d: str = date) -> None:
                db.execute_update(
                    "UPDATE personas SET last_mission_at = :date WHERE name = :name",
                    {"date": d, "name": n},
                )

            issues.append(
                DiagnosticIssue(category="mission_count", severity=Severity.FIXABLE, description=desc, fix_fn=make_fix)
            )

    label = "9b. Last Mission Dates"
    return label, issues


def check_abandoned_tasks(db: Database, *, verbose: bool = False) -> tuple[str, list[DiagnosticIssue]]:
    """Check 10a: Tasks UNDERWAY but their mission has ended."""
    abandoned_tasks = db.execute_query("""
        SELECT t.id, t.title, t.current_mission_id, m.codename, m.persona_name, m.end_time
        FROM tasks t
        JOIN missions m ON t.current_mission_id = m.id
        WHERE t.status = 'UNDERWAY'
        AND m.end_time IS NOT NULL
    """)

    issues: list[DiagnosticIssue] = []
    if abandoned_tasks:
        for task in abandoned_tasks:
            desc = (
                f"Task {task['id']} ({task['title']}): status is UNDERWAY but mission "
                f"#{task['current_mission_id']} ({task['codename']}) has ended"
            )
            task_id = task["id"]

            def make_fix(tid: str = task_id) -> None:
                db.execute_update(
                    "UPDATE tasks SET current_mission_id = NULL WHERE id = :id",
                    {"id": tid},
                )

            issues.append(
                DiagnosticIssue(category="abandoned_work", severity=Severity.FIXABLE, description=desc, fix_fn=make_fix)
            )

    label = "10a. Abandoned Tasks"
    return label, issues


def check_orphaned_underway(db: Database, *, verbose: bool = False) -> tuple[str, list[DiagnosticIssue]]:
    """Check 10b: UNDERWAY tasks with no mission assignment."""
    orphaned_underway = db.execute_query("""
        SELECT id, title, claimed_at
        FROM tasks
        WHERE status = 'UNDERWAY'
        AND current_mission_id IS NULL
    """)

    issues: list[DiagnosticIssue] = []
    if orphaned_underway:
        for task in orphaned_underway:
            desc = f"Task {task['id']} ({task['title']}): status is UNDERWAY but not claimed by any mission"
            issues.append(DiagnosticIssue(category="abandoned_work", severity=Severity.WARNING, description=desc))

    label = "10b. Orphaned Tasks"
    return label, issues


def check_stale_missions(
    db: Database, opencode_dir: Path, *, verbose: bool = False
) -> tuple[str, list[DiagnosticIssue]]:
    """Check 10c: Active/idle missions with no recent heartbeat (>8h)."""
    from site_nine.missions import MissionManager

    mission_manager = MissionManager(db)

    active_missions = db.execute_query("""
        SELECT id, codename, persona_name, start_date, start_time, last_active_at, status
        FROM missions
        WHERE status IN ('ACTIVE', 'IDLE')
    """)

    stale_threshold = datetime.now(timezone.utc) - timedelta(hours=8)
    issues: list[DiagnosticIssue] = []

    for mission in active_missions:
        try:
            # Use last_active_at as the primary staleness signal
            last_active_str = mission.get("last_active_at")
            if last_active_str:
                last_active_dt = datetime.fromisoformat(last_active_str.replace("Z", "+00:00"))
                if last_active_dt.tzinfo is None:
                    last_active_dt = last_active_dt.replace(tzinfo=timezone.utc)
            else:
                # Fall back to start_date + start_time for missions without last_active_at
                start_datetime_str = f"{mission['start_date']}T{mission['start_time']}"
                last_active_dt = datetime.fromisoformat(start_datetime_str).replace(tzinfo=timezone.utc)

            if last_active_dt < stale_threshold:
                age_hours = (datetime.now(timezone.utc) - last_active_dt).total_seconds() / 3600
                age_days = int(age_hours / 24)
                mission_id = mission["id"]
                status = mission.get("status", "ACTIVE")

                if age_days > 0:
                    age_display = f"{age_days} day(s)"
                else:
                    age_display = f"{int(age_hours)} hour(s)"

                desc = (
                    f"Mission #{mission['id']} ({mission['codename']}, {mission['persona_name']}): "
                    f"status {status}, no heartbeat for {age_display}"
                )

                def make_fix(mid: int = mission_id) -> None:
                    mission_manager.end_mission(mid)

                issues.append(
                    DiagnosticIssue(
                        category="abandoned_work",
                        severity=Severity.FIXABLE,
                        description=desc,
                        fix_fn=make_fix,
                    )
                )

        except (ValueError, TypeError):
            continue

    label = "10c. Stale Missions"
    return label, issues


def check_task_files(db: Database, opencode_dir: Path, *, verbose: bool = False) -> tuple[str, list[DiagnosticIssue]]:
    """Check 11: Task files should exist on disk."""
    tasks_with_files = db.execute_query("SELECT id, title, file_path FROM tasks WHERE file_path IS NOT NULL")

    issues: list[DiagnosticIssue] = []
    for task in tasks_with_files:
        if task.get("file_path"):
            file_path_str = task["file_path"]
            if file_path_str.startswith(".opencode/"):
                task_path = Path(file_path_str)
            else:
                task_path = opencode_dir / file_path_str

            task_path = validate_path_within_project(task_path)

            if not task_path.exists():
                desc = f"Task {task['id']}: file not found: {task['file_path']}"
                issues.append(DiagnosticIssue(category="task_file", severity=Severity.WARNING, description=desc))

    label = "11. Task Files"
    return label, issues
