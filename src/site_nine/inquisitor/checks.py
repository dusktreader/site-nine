"""Infrastructure and data integrity check functions.

Each check function returns either an InfraResult or a tuple of (label, list[DiagnosticIssue]).
The manager calls these and aggregates the results into a DiagnosticReport.
"""

from __future__ import annotations

import subprocess
from datetime import timedelta
from pathlib import Path

import pendulum

from site_nine.core.database import Database
from site_nine.core.paths import validate_path_within_project
from site_nine.core.utils import utc_now
from site_nine.inquisitor.models import DiagnosticIssue, InfraResult, Severity


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


def check_possession_daemons(db: Database, *, verbose: bool = False) -> tuple[str, list[DiagnosticIssue]]:
    """Check 6a: possessions.daemon_name -> daemons.name foreign key."""
    orphaned = db.execute_query("""
        SELECT p.id, p.daemon_name, p.role
        FROM possessions p
        WHERE p.daemon_name IS NOT NULL
        AND NOT EXISTS (SELECT 1 FROM daemons WHERE lower(name) = lower(p.daemon_name))
    """)

    issues: list[DiagnosticIssue] = []
    if orphaned:
        for row in orphaned:
            desc = f"Possession #{row['id']} ({row['role']}): references non-existent daemon '{row['daemon_name']}'"
            issues.append(DiagnosticIssue(category="foreign_key", severity=Severity.WARNING, description=desc))

    label = "6a. Possession Daemons"
    return label, issues


def check_task_possession_refs(db: Database, *, verbose: bool = False) -> tuple[str, list[DiagnosticIssue]]:
    """Check 6b: tasks.current_possession_id -> possessions.id foreign key."""
    orphaned_tasks = db.execute_query("""
        SELECT t.id, t.title, t.current_possession_id
        FROM tasks t
        WHERE t.current_possession_id IS NOT NULL
        AND NOT EXISTS (SELECT 1 FROM possessions WHERE id = t.current_possession_id)
    """)

    issues: list[DiagnosticIssue] = []
    if orphaned_tasks:
        for task in orphaned_tasks:
            desc = f"Task {task['id']}: references non-existent possession current_possession_id {task['current_possession_id']}"
            task_id = task["id"]

            def make_fix(tid: str = task_id) -> None:
                db.execute_update("UPDATE tasks SET current_possession_id = NULL WHERE id = :id", {"id": tid})

            issues.append(
                DiagnosticIssue(category="foreign_key", severity=Severity.FIXABLE, description=desc, fix_fn=make_fix)
            )

    label = "6b. Task Possession Refs"
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


def check_possession_data(db: Database, *, verbose: bool = False) -> tuple[str, list[DiagnosticIssue]]:
    """Check 8a: Possessions should have required fields (role, daemon_name, start_time)."""
    invalid = db.execute_query("""
        SELECT id, role, daemon_name, start_time, status
        FROM possessions
        WHERE role IS NULL OR role = ''
           OR daemon_name IS NULL OR daemon_name = ''
           OR start_time IS NULL
    """)

    issues: list[DiagnosticIssue] = []
    if invalid:
        for row in invalid:
            missing = []
            if not row.get("role"):
                missing.append("role")
            if not row.get("daemon_name"):
                missing.append("daemon_name")
            if not row.get("start_time"):
                missing.append("start_time")
            desc = f"Possession #{row['id']}: missing required field(s): {', '.join(missing)}"
            issues.append(DiagnosticIssue(category="possession_data", severity=Severity.WARNING, description=desc))

    label = "8a. Possession Data"
    return label, issues


def check_possession_logs(
    db: Database, opencode_dir: Path, *, verbose: bool = False
) -> tuple[str, list[DiagnosticIssue]]:
    """Check 8b: Possession log files should exist on disk for active possessions."""
    active_possessions = db.execute_query("""
        SELECT id, daemon_name, role, possession_log, status
        FROM possessions
        WHERE possession_log IS NOT NULL
        AND status IN ('ACTIVE', 'IDLE')
    """)

    issues: list[DiagnosticIssue] = []
    for row in active_possessions:
        log_path_str = row["possession_log"]
        if log_path_str:
            if log_path_str.startswith(".opencode/"):
                log_path = Path(log_path_str)
            else:
                log_path = opencode_dir / log_path_str

            try:
                log_path = validate_path_within_project(log_path)
            except Exception:
                pass  # If validation fails, skip this check

            if not log_path.exists():
                desc = (
                    f"Possession #{row['id']} ({row['daemon_name']}, {row['role']}): "
                    f"log file not found: {row['possession_log']}"
                )
                issues.append(DiagnosticIssue(category="possession_log", severity=Severity.WARNING, description=desc))

    label = "8b. Possession Logs"
    return label, issues


def check_daemon_incarnations(db: Database, *, verbose: bool = False) -> tuple[str, list[DiagnosticIssue]]:
    """Check 9a: Daemon incarnation counts should match actual possession count."""
    mismatched = db.execute_query("""
        SELECT d.name, d.incarnations,
               COUNT(p.id) AS actual_count
        FROM daemons d
        LEFT JOIN possessions p ON lower(p.daemon_name) = lower(d.name)
        GROUP BY d.name, d.incarnations
        HAVING d.incarnations != COUNT(p.id)
    """)

    issues: list[DiagnosticIssue] = []
    if mismatched:
        for row in mismatched:
            desc = (
                f"Daemon '{row['name']}': incarnations={row['incarnations']} "
                f"but actual possession count={row['actual_count']}"
            )
            daemon_name = row["name"]
            actual = row["actual_count"]

            def make_fix(name: str = daemon_name, count: int = actual) -> None:
                db.execute_update(
                    "UPDATE daemons SET incarnations = :count WHERE lower(name) = lower(:name)",
                    {"name": name, "count": count},
                )

            issues.append(
                DiagnosticIssue(category="daemon_data", severity=Severity.FIXABLE, description=desc, fix_fn=make_fix)
            )

    label = "9a. Daemon Incarnations"
    return label, issues


def check_daemon_last_possession(db: Database, *, verbose: bool = False) -> tuple[str, list[DiagnosticIssue]]:
    """Check 9b: Daemon last_possession should match their most recent possession's start_time."""
    mismatched = db.execute_query("""
        SELECT d.name, d.last_possession,
               MAX(p.start_time) AS latest_start
        FROM daemons d
        LEFT JOIN possessions p ON lower(p.daemon_name) = lower(d.name)
        GROUP BY d.name, d.last_possession
        HAVING latest_start IS NOT NULL
           AND (d.last_possession IS NULL OR d.last_possession < latest_start)
    """)

    issues: list[DiagnosticIssue] = []
    if mismatched:
        for row in mismatched:
            desc = (
                f"Daemon '{row['name']}': last_possession={row['last_possession']} "
                f"but latest possession started at {row['latest_start']}"
            )
            daemon_name = row["name"]
            latest = row["latest_start"]

            def make_fix(name: str = daemon_name, ts: str = latest) -> None:
                db.execute_update(
                    "UPDATE daemons SET last_possession = :ts WHERE lower(name) = lower(:name)",
                    {"name": name, "ts": ts},
                )

            issues.append(
                DiagnosticIssue(category="daemon_data", severity=Severity.FIXABLE, description=desc, fix_fn=make_fix)
            )

    label = "9b. Last Possession Dates"
    return label, issues


def check_abandoned_tasks(db: Database, *, verbose: bool = False) -> tuple[str, list[DiagnosticIssue]]:
    """Check 10a: Tasks UNDERWAY but their possession has been exorcised."""
    abandoned_tasks = db.execute_query("""
        SELECT t.id, t.title, t.current_possession_id, p.daemon_name, p.status
        FROM tasks t
        JOIN possessions p ON t.current_possession_id = p.id
        WHERE t.status = 'UNDERWAY'
        AND p.status = 'EXORCISED'
    """)

    issues: list[DiagnosticIssue] = []
    if abandoned_tasks:
        for task in abandoned_tasks:
            desc = (
                f"Task {task['id']} ({task['title']}): status is UNDERWAY but possession "
                f"#{task['current_possession_id']} ({task['daemon_name']}) has been exorcised"
            )
            task_id = task["id"]

            def make_fix(tid: str = task_id) -> None:
                db.execute_update(
                    "UPDATE tasks SET current_possession_id = NULL WHERE id = :id",
                    {"id": tid},
                )

            issues.append(
                DiagnosticIssue(category="abandoned_work", severity=Severity.FIXABLE, description=desc, fix_fn=make_fix)
            )

    label = "10a. Abandoned Tasks"
    return label, issues


def check_orphaned_underway(db: Database, *, verbose: bool = False) -> tuple[str, list[DiagnosticIssue]]:
    """Check 10b: UNDERWAY tasks with no possession assignment."""
    orphaned_underway = db.execute_query("""
        SELECT id, title, claimed_at
        FROM tasks
        WHERE status = 'UNDERWAY'
        AND current_possession_id IS NULL
    """)

    issues: list[DiagnosticIssue] = []
    if orphaned_underway:
        for task in orphaned_underway:
            desc = f"Task {task['id']} ({task['title']}): status is UNDERWAY but not claimed by any possession"
            issues.append(DiagnosticIssue(category="abandoned_work", severity=Severity.WARNING, description=desc))

    label = "10b. Orphaned Tasks"
    return label, issues


def check_rogue_possessions(
    db: Database,
    *,
    verbose: bool = False,
    stale_hours: int = 3,
) -> tuple[str, list[DiagnosticIssue]]:
    """Check 10c: ACTIVE/IDLE possessions with last_heartbeat_at older than stale_hours.

    These are "rogue" possessions — OpenCode sessions that ended without cleaning up.
    Auto-exorcises them: sets status to EXORCISED, records end_time, releases their tasks.
    """
    cutoff = pendulum.now("UTC").subtract(hours=stale_hours).isoformat()

    rogue = db.execute_query(
        """
        SELECT id, daemon_name, role, last_heartbeat_at, status
        FROM possessions
        WHERE status IN ('ACTIVE', 'IDLE')
        AND (
            last_heartbeat_at IS NULL
            OR last_heartbeat_at < :cutoff
        )
        """,
        {"cutoff": cutoff},
    )

    issues: list[DiagnosticIssue] = []
    if rogue:
        for row in rogue:
            heartbeat = row["last_heartbeat_at"] or "never"
            desc = (
                f"Possession #{row['id']} ({row['daemon_name']}, {row['role']}): "
                f"status is {row['status']} but last heartbeat was {heartbeat} "
                f"(older than {stale_hours}h) — rogue possession, auto-exorcising"
            )
            possession_id = row["id"]

            def make_fix(pid: int = possession_id) -> None:
                now = utc_now()
                db.execute_update(
                    """
                    UPDATE possessions
                    SET status = 'EXORCISED', end_time = :now, desk_mode_active = 0, updated_at = :now
                    WHERE id = :id
                    """,
                    {"id": pid, "now": now},
                )
                # Release any tasks this possession was holding
                db.execute_update(
                    """
                    UPDATE tasks
                    SET status = 'TODO', current_possession_id = NULL, claimed_at = NULL
                    WHERE current_possession_id = :id AND status = 'UNDERWAY'
                    """,
                    {"id": pid},
                )

            issues.append(
                DiagnosticIssue(
                    category="rogue_possession", severity=Severity.FIXABLE, description=desc, fix_fn=make_fix
                )
            )

    label = "10c. Rogue Possessions"
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
