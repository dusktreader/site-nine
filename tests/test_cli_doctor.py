"""Tests for doctor CLI commands"""

import sqlite3
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from typer.testing import CliRunner

from site_nine.__main__ import app
from site_nine.core.database import Database

runner = CliRunner()


@pytest.fixture
def project_dir(tmp_path: Path, monkeypatch):
    """Create a test project directory"""
    opencode_dir = tmp_path / ".opencode"
    opencode_dir.mkdir()
    data_dir = opencode_dir / "data"
    data_dir.mkdir()

    monkeypatch.chdir(tmp_path)
    return tmp_path


def _raw_execute(db_path: Path, sql: str, params: tuple = ()):
    """Execute SQL with FK checks disabled for seeding bad data."""
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys=OFF")
    conn.execute(sql, params)
    conn.commit()
    conn.close()


def _raw_query(db_path: Path, sql: str, params: tuple = ()):
    """Query with FK checks disabled."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.execute(sql, params)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


# =============================================================================
# Basic command tests
# =============================================================================


def test_doctor_without_init(tmp_path: Path, monkeypatch):
    """Test doctor command fails without initialization"""
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code != 0


def test_doctor_without_database(project_dir: Path):
    """Test doctor command fails without database"""
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code != 0


def test_doctor_basic_check(project_dir: Path, test_db):
    """Test basic doctor health check"""
    db_path = project_dir / ".opencode" / "data" / "project.db"
    import shutil

    shutil.copy(test_db.db_path, db_path)

    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0
    assert "Running diagnostics" in result.stdout


def test_doctor_verbose_mode(project_dir: Path, test_db):
    """Test doctor with verbose flag"""
    db_path = project_dir / ".opencode" / "data" / "project.db"
    import shutil

    shutil.copy(test_db.db_path, db_path)

    result = runner.invoke(app, ["doctor", "--verbose"])
    assert result.exit_code == 0
    assert "Running diagnostics" in result.stdout


def test_doctor_fix_mode(project_dir: Path, test_db):
    """Test doctor with fix flag"""
    db_path = project_dir / ".opencode" / "data" / "project.db"
    import shutil

    shutil.copy(test_db.db_path, db_path)

    result = runner.invoke(app, ["doctor", "--fix"])
    assert result.exit_code == 0
    assert "Running diagnostics" in result.stdout


def test_doctor_with_verbose_and_fix(project_dir: Path, test_db):
    """Test doctor with both verbose and fix flags"""
    db_path = project_dir / ".opencode" / "data" / "project.db"
    import shutil

    shutil.copy(test_db.db_path, db_path)

    result = runner.invoke(app, ["doctor", "--verbose", "--fix"])
    assert result.exit_code == 0


# =============================================================================
# Infrastructure check tests (merged from check.py)
# =============================================================================


def test_doctor_checks_database_exists(initialized_project: Path):
    """Test doctor reports database file existence"""
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0
    assert "Database file exists" in result.stdout


def test_doctor_database_integrity_passes(initialized_project: Path):
    """Test doctor runs SQLite PRAGMA integrity_check"""
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0
    assert "integrity check passed" in result.stdout


def test_doctor_handles_missing_sqlite3(initialized_project: Path):
    """Test doctor handles missing sqlite3 command gracefully"""
    with patch("site_nine.doctor.checks.subprocess.run", side_effect=FileNotFoundError("sqlite3 not found")):
        result = runner.invoke(app, ["doctor"])
        assert result.exit_code == 0
        assert "sqlite3 command not found" in result.stdout.lower()


def test_doctor_handles_sqlite3_errors(initialized_project: Path):
    """Test doctor handles sqlite3 errors gracefully"""
    import subprocess as sp

    with patch("site_nine.doctor.checks.subprocess.run", side_effect=sp.CalledProcessError(1, "sqlite3", "error")):
        result = runner.invoke(app, ["doctor"])
        assert "integrity check" in result.stdout.lower()


def test_doctor_database_integrity_failed(initialized_project: Path):
    """Test doctor reports integrity failure when sqlite3 returns non-ok result"""
    mock_result = Mock()
    mock_result.stdout = "database disk image is malformed\n"
    mock_result.returncode = 0

    with patch("site_nine.doctor.checks.subprocess.run", return_value=mock_result):
        result = runner.invoke(app, ["doctor"])

    normalized = " ".join(result.stdout.split())
    assert "integrity check failed" in normalized.lower()
    assert "restore from backup" in normalized.lower()


def test_doctor_detects_missing_gitignore_patterns(initialized_project: Path):
    """Test doctor detects missing .gitignore patterns"""
    gitignore = initialized_project / ".gitignore"
    gitignore.write_text("# Empty gitignore\n*.pyc\n")

    result = runner.invoke(app, ["doctor"])

    assert result.exit_code == 0
    normalized = " ".join(result.stdout.split())
    assert ".opencode/data/*.db" in normalized


def test_doctor_passes_with_correct_gitignore(initialized_project: Path):
    """Test doctor passes when .gitignore has recommended patterns"""
    gitignore = initialized_project / ".gitignore"
    gitignore.write_text(
        "# Database files\n.opencode/data/*.db\n.opencode/data/*.db-journal\n.opencode/data/*.db-wal\n"
    )

    result = runner.invoke(app, ["doctor"])

    assert result.exit_code == 0
    assert "All recommended .gitignore patterns present" in result.stdout


def test_doctor_warns_no_gitignore(in_temp_dir: Path):
    """Test doctor warns when no .gitignore exists"""
    runner.invoke(app, ["init"], input="\n" * 10)

    gitignore = in_temp_dir / ".gitignore"
    if gitignore.exists():
        gitignore.unlink()

    result = runner.invoke(app, ["doctor"])

    assert result.exit_code == 0
    assert "No .gitignore file found" in result.stdout


def test_doctor_warns_about_no_backups(initialized_project: Path):
    """Test doctor warns when no backups exist"""
    result = runner.invoke(app, ["doctor"])

    assert result.exit_code == 0
    assert "No backup files found" in result.stdout


def test_doctor_detects_backup_files(initialized_project: Path):
    """Test doctor detects existing backup files"""
    backup_dir = initialized_project / ".opencode" / "data"
    backup_file = backup_dir / "project.db.backup"
    backup_file.write_text("backup")

    result = runner.invoke(app, ["doctor"])

    assert result.exit_code == 0
    assert "Found 1 backup file" in result.stdout


def _create_temp_files_with_mock_db(initialized_project: Path, suffixes: list[str], invoke_args: list[str]) -> str:
    """Helper: create temp files and run doctor with mocked Database and subprocess.

    Both SQLAlchemy (via Database) and the sqlite3 subprocess call remove temp files
    when they open the database, so we must mock both to prevent cleanup.

    Returns the normalized stdout from the CLI invocation.
    """
    db_path = (initialized_project / ".opencode" / "data" / "project.db").resolve()
    for suffix in suffixes:
        (db_path.parent / f"{db_path.name}{suffix}").write_text("temp")

    mock_db = Mock()
    mock_db.execute_query.return_value = []
    mock_db.__enter__ = Mock(return_value=mock_db)
    mock_db.__exit__ = Mock(return_value=False)

    mock_proc = Mock()
    mock_proc.stdout = "ok\n"
    mock_proc.returncode = 0

    with (
        patch("site_nine.cli.doctor.Database", return_value=mock_db),
        patch("site_nine.doctor.checks.subprocess.run", return_value=mock_proc),
    ):
        result = runner.invoke(app, invoke_args)

    normalized = " ".join(result.stdout.split())
    assert result.exit_code == 0
    return normalized


def test_doctor_detects_journal_file(initialized_project: Path):
    """Test doctor detects project.db-journal temp file"""
    normalized = _create_temp_files_with_mock_db(initialized_project, ["-journal"], ["doctor"])
    assert "project.db-journal" in normalized


def test_doctor_detects_wal_file(initialized_project: Path):
    """Test doctor detects project.db-wal temp file"""
    normalized = _create_temp_files_with_mock_db(initialized_project, ["-wal"], ["doctor"])
    assert "project.db-wal" in normalized


def test_doctor_detects_shm_file(initialized_project: Path):
    """Test doctor detects project.db-shm temp file"""
    normalized = _create_temp_files_with_mock_db(initialized_project, ["-shm"], ["doctor"])
    assert "project.db-shm" in normalized


def test_doctor_detects_multiple_temp_files(initialized_project: Path):
    """Test doctor detects multiple SQLite temp files at once"""
    normalized = _create_temp_files_with_mock_db(initialized_project, ["-journal", "-wal", "-shm"], ["doctor"])
    assert "project.db-journal" in normalized
    assert "project.db-wal" in normalized
    assert "project.db-shm" in normalized


# =============================================================================
# Data integrity check tests
# =============================================================================


# --- Check 6a: Invalid mission persona ref ---


def test_doctor_detects_invalid_mission_persona(initialized_project: Path):
    """Doctor detects mission referencing non-existent persona."""
    db_path = initialized_project / ".opencode" / "data" / "project.db"

    _raw_execute(
        db_path,
        """
        INSERT INTO missions (id, persona_name, role, codename, mission_file, start_date, start_time, objective, created_at, updated_at)
        VALUES (900, 'ghost-persona', 'Engineer', 'bad-mission', '.opencode/work/missions/bad.md', '2026-01-01', '10:00:00', 'Test', datetime('now'), datetime('now'))
    """,
    )

    result = runner.invoke(app, ["doctor", "--verbose"])
    assert result.exit_code == 0
    output = " ".join(result.stdout.split())
    assert "ghost-persona" in output
    assert "not found" in output


# --- Check 6b: Orphaned task mission ref (fixable) ---


def test_doctor_detects_orphaned_task_mission_ref(initialized_project: Path):
    """Doctor detects task referencing non-existent mission."""
    db_path = initialized_project / ".opencode" / "data" / "project.db"

    _raw_execute(
        db_path,
        """
        INSERT INTO tasks (id, title, status, priority, role, current_mission_id, claimed_at, file_path, created_at, updated_at)
        VALUES ('ENG-H-0001', 'Orphan Task', 'UNDERWAY', 'HIGH', 'Engineer', 9999, datetime('now'), '.opencode/work/tasks/ENG-H-0001.md', datetime('now'), datetime('now'))
    """,
    )

    result = runner.invoke(app, ["doctor", "--verbose"])
    assert result.exit_code == 0
    assert "ENG-H-0001" in result.stdout
    assert "non-existent mission" in result.stdout


def test_doctor_fixes_orphaned_task_mission_ref(initialized_project: Path):
    """Doctor --fix nullifies orphaned task mission reference."""
    db_path = initialized_project / ".opencode" / "data" / "project.db"

    _raw_execute(
        db_path,
        """
        INSERT INTO tasks (id, title, status, priority, role, current_mission_id, claimed_at, file_path, created_at, updated_at)
        VALUES ('ENG-H-0002', 'Orphan Task', 'UNDERWAY', 'HIGH', 'Engineer', 9999, datetime('now'), '.opencode/work/tasks/ENG-H-0002.md', datetime('now'), datetime('now'))
    """,
    )

    result = runner.invoke(app, ["doctor", "--fix"])
    assert result.exit_code == 0
    assert "Applying fixes" in result.stdout
    assert "Fixed" in result.stdout

    rows = _raw_query(db_path, "SELECT current_mission_id FROM tasks WHERE id = 'ENG-H-0002'")
    assert rows[0]["current_mission_id"] is None


# --- Check 6c: Invalid task dependencies (fixable) ---


def test_doctor_detects_invalid_dependencies(initialized_project: Path):
    """Doctor detects task dependency referencing non-existent task."""
    db_path = initialized_project / ".opencode" / "data" / "project.db"

    _raw_execute(
        db_path,
        """
        INSERT INTO tasks (id, title, status, priority, role, file_path, created_at, updated_at)
        VALUES ('ENG-H-0001', 'Real Task', 'TODO', 'HIGH', 'Engineer', '.opencode/work/tasks/ENG-H-0001.md', datetime('now'), datetime('now'))
    """,
    )
    _raw_execute(
        db_path,
        """
        INSERT INTO task_dependencies (task_id, depends_on_task_id)
        VALUES ('ENG-H-0001', 'FAKE-H-9999')
    """,
    )

    result = runner.invoke(app, ["doctor", "--verbose"])
    assert result.exit_code == 0
    assert "non-existent task" in result.stdout
    assert "invalid dependencies" in result.stdout


def test_doctor_fixes_invalid_dependencies(initialized_project: Path):
    """Doctor --fix removes invalid dependencies."""
    db_path = initialized_project / ".opencode" / "data" / "project.db"

    _raw_execute(
        db_path,
        """
        INSERT INTO tasks (id, title, status, priority, role, file_path, created_at, updated_at)
        VALUES ('ENG-H-0003', 'Real Task', 'TODO', 'HIGH', 'Engineer', '.opencode/work/tasks/ENG-H-0003.md', datetime('now'), datetime('now'))
    """,
    )
    _raw_execute(
        db_path,
        """
        INSERT INTO task_dependencies (task_id, depends_on_task_id)
        VALUES ('ENG-H-0003', 'FAKE-H-9998')
    """,
    )

    result = runner.invoke(app, ["doctor", "--fix"])
    assert result.exit_code == 0
    assert "Fixed" in result.stdout

    rows = _raw_query(db_path, "SELECT * FROM task_dependencies WHERE task_id = 'ENG-H-0003'")
    assert len(rows) == 0


# --- Check 7a: COMPLETE without closed_at (fixable) ---


def test_doctor_detects_complete_without_closed_at(initialized_project: Path):
    """Doctor detects task marked COMPLETE but missing closed_at."""
    db_path = initialized_project / ".opencode" / "data" / "project.db"

    _raw_execute(
        db_path,
        """
        INSERT INTO tasks (id, title, status, priority, role, closed_at, file_path, created_at, updated_at)
        VALUES ('ENG-H-0004', 'Done Task', 'COMPLETE', 'HIGH', 'Engineer', NULL, '.opencode/work/tasks/ENG-H-0004.md', datetime('now'), datetime('now'))
    """,
    )

    result = runner.invoke(app, ["doctor", "--verbose"])
    assert result.exit_code == 0
    assert "ENG-H-0004" in result.stdout
    assert "missing closed_at" in result.stdout


def test_doctor_fixes_complete_without_closed_at(initialized_project: Path):
    """Doctor --fix adds closed_at timestamp to completed tasks."""
    db_path = initialized_project / ".opencode" / "data" / "project.db"

    _raw_execute(
        db_path,
        """
        INSERT INTO tasks (id, title, status, priority, role, closed_at, file_path, created_at, updated_at)
        VALUES ('ENG-H-0005', 'Done Task 2', 'COMPLETE', 'HIGH', 'Engineer', NULL, '.opencode/work/tasks/ENG-H-0005.md', datetime('now'), datetime('now'))
    """,
    )

    result = runner.invoke(app, ["doctor", "--fix"])
    assert result.exit_code == 0

    rows = _raw_query(db_path, "SELECT closed_at FROM tasks WHERE id = 'ENG-H-0005'")
    assert rows[0]["closed_at"] is not None


# --- Check 7b: UNDERWAY without claimed_at (warning) ---


def test_doctor_detects_underway_without_claimed_at(initialized_project: Path):
    """Doctor detects UNDERWAY task missing claimed_at."""
    db_path = initialized_project / ".opencode" / "data" / "project.db"

    _raw_execute(
        db_path,
        """
        INSERT INTO tasks (id, title, status, priority, role, claimed_at, current_mission_id, file_path, created_at, updated_at)
        VALUES ('ENG-H-0006', 'Working Task', 'UNDERWAY', 'HIGH', 'Engineer', NULL, NULL, '.opencode/work/tasks/ENG-H-0006.md', datetime('now'), datetime('now'))
    """,
    )

    result = runner.invoke(app, ["doctor", "--verbose"])
    assert result.exit_code == 0
    assert "ENG-H-0006" in result.stdout
    assert "missing claimed_at" in result.stdout


# --- Check 8a: Mission missing start_time (error) ---


def test_doctor_detects_mission_missing_start_time(initialized_project: Path):
    """Doctor detects mission with empty start_time."""
    db_path = initialized_project / ".opencode" / "data" / "project.db"

    personas = _raw_query(db_path, "SELECT name FROM personas LIMIT 1")
    persona_name = personas[0]["name"]

    _raw_execute(
        db_path,
        """
        INSERT INTO missions (id, persona_name, role, codename, mission_file, start_date, start_time, objective, created_at, updated_at)
        VALUES (901, ?, 'Engineer', 'missing-time', '.opencode/work/missions/missing.md', '2026-01-01', '', 'Test', datetime('now'), datetime('now'))
    """,
        (persona_name,),
    )

    result = runner.invoke(app, ["doctor", "--verbose"])
    assert result.exit_code == 0
    assert "missing start_time" in result.stdout


# --- Check 8b: Mission file missing (error) ---


def test_doctor_detects_missing_mission_file(initialized_project: Path):
    """Doctor detects mission referencing non-existent file."""
    db_path = initialized_project / ".opencode" / "data" / "project.db"

    personas = _raw_query(db_path, "SELECT name FROM personas LIMIT 1")
    persona_name = personas[0]["name"]

    _raw_execute(
        db_path,
        """
        INSERT INTO missions (id, persona_name, role, codename, mission_file, start_date, start_time, objective, created_at, updated_at)
        VALUES (902, ?, 'Engineer', 'no-file-mission', 'work/missions/nonexistent.md', '2026-01-01', '10:00:00', 'Test', datetime('now'), datetime('now'))
    """,
        (persona_name,),
    )

    result = runner.invoke(app, ["doctor", "--verbose"])
    assert result.exit_code == 0
    assert "mission file not found" in result.stdout


# --- Check 9a: Wrong mission_count (fixable) ---


def test_doctor_detects_wrong_mission_count(initialized_project: Path):
    """Doctor detects persona with incorrect mission_count."""
    db_path = initialized_project / ".opencode" / "data" / "project.db"

    personas = _raw_query(db_path, "SELECT name FROM personas LIMIT 1")
    persona_name = personas[0]["name"]

    _raw_execute(
        db_path,
        """
        INSERT INTO missions (id, persona_name, role, codename, mission_file, start_date, start_time, objective, created_at, updated_at)
        VALUES (903, ?, 'Engineer', 'count-test', '.opencode/work/missions/count.md', '2026-01-01', '10:00:00', 'Test', datetime('now'), datetime('now'))
    """,
        (persona_name,),
    )

    result = runner.invoke(app, ["doctor", "--verbose"])
    assert result.exit_code == 0
    assert "mission_count" in result.stdout


def test_doctor_fixes_wrong_mission_count(initialized_project: Path):
    """Doctor --fix corrects persona mission_count."""
    db_path = initialized_project / ".opencode" / "data" / "project.db"

    personas = _raw_query(db_path, "SELECT name FROM personas LIMIT 1")
    persona_name = personas[0]["name"]

    _raw_execute(
        db_path,
        """
        INSERT INTO missions (id, persona_name, role, codename, mission_file, start_date, start_time, objective, created_at, updated_at)
        VALUES (904, ?, 'Engineer', 'count-fix', '.opencode/work/missions/countfix.md', '2026-01-01', '10:00:00', 'Test', datetime('now'), datetime('now'))
    """,
        (persona_name,),
    )

    result = runner.invoke(app, ["doctor", "--fix"])
    assert result.exit_code == 0

    rows = _raw_query(db_path, "SELECT mission_count FROM personas WHERE name = ?", (persona_name,))
    assert rows[0]["mission_count"] >= 1


# --- Check 9b: Wrong last_mission_at (fixable) ---


def test_doctor_detects_wrong_last_mission_at(initialized_project: Path):
    """Doctor detects persona with incorrect last_mission_at."""
    db_path = initialized_project / ".opencode" / "data" / "project.db"

    personas = _raw_query(db_path, "SELECT name FROM personas LIMIT 1")
    persona_name = personas[0]["name"]

    _raw_execute(
        db_path,
        """
        INSERT INTO missions (id, persona_name, role, codename, mission_file, start_date, start_time, objective, created_at, updated_at)
        VALUES (905, ?, 'Engineer', 'date-test', '.opencode/work/missions/date.md', '2026-01-01', '10:00:00', 'Test', datetime('now'), datetime('now'))
    """,
        (persona_name,),
    )

    result = runner.invoke(app, ["doctor", "--verbose"])
    assert result.exit_code == 0
    assert "last_mission_at" in result.stdout


# --- Check 10a: Abandoned task (UNDERWAY on ended mission, fixable) ---


def test_doctor_detects_abandoned_task(initialized_project: Path):
    """Doctor detects UNDERWAY task on ended mission."""
    db_path = initialized_project / ".opencode" / "data" / "project.db"

    personas = _raw_query(db_path, "SELECT name FROM personas LIMIT 1")
    persona_name = personas[0]["name"]

    _raw_execute(
        db_path,
        """
        INSERT INTO missions (id, persona_name, role, codename, mission_file, start_date, start_time, end_time, objective, created_at, updated_at)
        VALUES (910, ?, 'Engineer', 'ended-op', '.opencode/work/missions/ended.md', '2026-01-01', '10:00:00', '12:00:00', 'Done', datetime('now'), datetime('now'))
    """,
        (persona_name,),
    )

    _raw_execute(
        db_path,
        """
        INSERT INTO tasks (id, title, status, priority, role, current_mission_id, claimed_at, file_path, created_at, updated_at)
        VALUES ('ENG-H-0007', 'Abandoned Task', 'UNDERWAY', 'HIGH', 'Engineer', 910, datetime('now'), '.opencode/work/tasks/ENG-H-0007.md', datetime('now'), datetime('now'))
    """,
    )

    result = runner.invoke(app, ["doctor", "--verbose"])
    assert result.exit_code == 0
    assert "ENG-H-0007" in result.stdout
    assert "has ended" in result.stdout


def test_doctor_fixes_abandoned_task(initialized_project: Path):
    """Doctor --fix nullifies mission reference for abandoned tasks."""
    db_path = initialized_project / ".opencode" / "data" / "project.db"

    personas = _raw_query(db_path, "SELECT name FROM personas LIMIT 1")
    persona_name = personas[0]["name"]

    _raw_execute(
        db_path,
        """
        INSERT INTO missions (id, persona_name, role, codename, mission_file, start_date, start_time, end_time, objective, created_at, updated_at)
        VALUES (911, ?, 'Engineer', 'ended-op2', '.opencode/work/missions/ended2.md', '2026-01-01', '10:00:00', '12:00:00', 'Done', datetime('now'), datetime('now'))
    """,
        (persona_name,),
    )

    _raw_execute(
        db_path,
        """
        INSERT INTO tasks (id, title, status, priority, role, current_mission_id, claimed_at, file_path, created_at, updated_at)
        VALUES ('ENG-H-0008', 'Abandoned Task 2', 'UNDERWAY', 'HIGH', 'Engineer', 911, datetime('now'), '.opencode/work/tasks/ENG-H-0008.md', datetime('now'), datetime('now'))
    """,
    )

    result = runner.invoke(app, ["doctor", "--fix"])
    assert result.exit_code == 0

    rows = _raw_query(db_path, "SELECT current_mission_id FROM tasks WHERE id = 'ENG-H-0008'")
    assert rows[0]["current_mission_id"] is None


# --- Check 10b: Orphaned UNDERWAY (warning) ---


def test_doctor_detects_orphaned_underway(initialized_project: Path):
    """Doctor detects UNDERWAY task not claimed by any mission."""
    db_path = initialized_project / ".opencode" / "data" / "project.db"

    _raw_execute(
        db_path,
        """
        INSERT INTO tasks (id, title, status, priority, role, current_mission_id, claimed_at, file_path, created_at, updated_at)
        VALUES ('ENG-H-0009', 'Orphan UNDERWAY', 'UNDERWAY', 'HIGH', 'Engineer', NULL, datetime('now'), '.opencode/work/tasks/ENG-H-0009.md', datetime('now'), datetime('now'))
    """,
    )

    result = runner.invoke(app, ["doctor", "--verbose"])
    assert result.exit_code == 0
    output = " ".join(result.stdout.split())
    assert "ENG-H-0009" in output
    assert "not claimed" in output


# --- Check 10c: Stale active mission (warning) ---


def test_doctor_detects_stale_mission(initialized_project: Path):
    """Doctor detects active mission with stale file (>24h old)."""
    import os
    import time

    db_path = initialized_project / ".opencode" / "data" / "project.db"

    personas = _raw_query(db_path, "SELECT name FROM personas LIMIT 1")
    persona_name = personas[0]["name"]

    mission_file_path = initialized_project / ".opencode" / "work" / "missions" / "stale.md"
    mission_file_path.parent.mkdir(parents=True, exist_ok=True)
    mission_file_path.write_text("# Stale Mission\n")

    old_time = time.time() - (72 * 3600)
    os.utime(str(mission_file_path), (old_time, old_time))

    _raw_execute(
        db_path,
        """
        INSERT INTO missions (id, persona_name, role, codename, mission_file, start_date, start_time, objective, created_at, updated_at)
        VALUES (920, ?, 'Engineer', 'stale-op', 'work/missions/stale.md', '2026-01-01', '10:00:00', 'Test', datetime('now'), datetime('now'))
    """,
        (persona_name,),
    )

    result = runner.invoke(app, ["doctor", "--verbose"])
    assert result.exit_code == 0
    assert "stale IDLE missions" in result.stdout


# --- Check 11: Missing task file (warning) ---


def test_doctor_detects_missing_task_file(initialized_project: Path):
    """Doctor detects task with non-existent file_path."""
    db_path = initialized_project / ".opencode" / "data" / "project.db"

    _raw_execute(
        db_path,
        """
        INSERT INTO tasks (id, title, status, priority, role, file_path, created_at, updated_at)
        VALUES ('ENG-H-0010', 'No File Task', 'TODO', 'HIGH', 'Engineer', '.opencode/work/tasks/ENG-H-0010.md', datetime('now'), datetime('now'))
    """,
    )

    result = runner.invoke(app, ["doctor", "--verbose"])
    assert result.exit_code == 0
    assert "missing task files" in result.stdout
    assert "ENG-H-0010" in result.stdout


# --- Summary and fix mode ---


def test_doctor_summary_with_issues(initialized_project: Path):
    """Doctor shows summary with fixable/warning/error counts."""
    db_path = initialized_project / ".opencode" / "data" / "project.db"

    _raw_execute(
        db_path,
        """
        INSERT INTO tasks (id, title, status, priority, role, closed_at, file_path, created_at, updated_at)
        VALUES ('ENG-H-0011', 'Summary Task', 'COMPLETE', 'HIGH', 'Engineer', NULL, '.opencode/work/tasks/ENG-H-0011.md', datetime('now'), datetime('now'))
    """,
    )

    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0
    assert "fixable issues" in result.stdout
    assert "--fix" in result.stdout


def test_doctor_summary_no_issues(initialized_project: Path):
    """Doctor shows all-clear when no issues found."""
    # Set up gitignore with all recommended patterns
    gitignore = initialized_project / ".gitignore"
    gitignore.write_text(".opencode/data/*.db\n.opencode/data/*.db-journal\n.opencode/data/*.db-wal\n")

    # Create a backup file so the backup check passes
    backup_dir = initialized_project / ".opencode" / "data"
    (backup_dir / "project.db.backup").write_text("backup")

    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0
    assert "All checks passed" in result.stdout


def test_doctor_fix_with_errors(initialized_project: Path):
    """Doctor --fix reports both successful and error issues."""
    db_path = initialized_project / ".opencode" / "data" / "project.db"

    _raw_execute(
        db_path,
        """
        INSERT INTO missions (id, persona_name, role, codename, mission_file, start_date, start_time, objective, created_at, updated_at)
        VALUES (930, 'error-persona', 'Engineer', 'error-op', '.opencode/work/missions/error.md', '2026-01-01', '10:00:00', 'Test', datetime('now'), datetime('now'))
    """,
    )

    _raw_execute(
        db_path,
        """
        INSERT INTO tasks (id, title, status, priority, role, closed_at, file_path, created_at, updated_at)
        VALUES ('ENG-H-0012', 'Fix Me', 'COMPLETE', 'HIGH', 'Engineer', NULL, '.opencode/work/tasks/ENG-H-0012.md', datetime('now'), datetime('now'))
    """,
    )

    result = runner.invoke(app, ["doctor", "--fix", "--verbose"])
    assert result.exit_code == 0
    assert "Applying fixes" in result.stdout
    assert "manual intervention" in result.stdout


def test_doctor_detects_orphaned_tasks(initialized_project: Path):
    """Test doctor runs successfully even with orphaned tasks"""
    db_path = initialized_project / ".opencode" / "data" / "project.db"

    _raw_execute(
        db_path,
        """
        INSERT INTO tasks (id, title, status, priority, role, file_path, created_at, updated_at)
        VALUES ('ENG-M-0001', 'Orphan task', 'TODO', 'MEDIUM', 'Engineer', '.opencode/work/tasks/ENG-M-0001.md', datetime('now'), datetime('now'))
    """,
    )

    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0


def test_doctor_detects_invalid_persona_refs(initialized_project: Path):
    """Test doctor runs successfully even with invalid persona references"""
    db_path = initialized_project / ".opencode" / "data" / "project.db"

    _raw_execute(
        db_path,
        """
        INSERT INTO missions (id, persona_name, role, codename, mission_file, start_date, start_time, objective, created_at, updated_at)
        VALUES (800, 'invalid-persona', 'Engineer', 'bad-ref', '.opencode/work/missions/bad-ref.md', '2026-01-01', '10:00:00', 'Test Mission', datetime('now'), datetime('now'))
    """,
    )

    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0


def test_doctor_checks_task_status_consistency(initialized_project: Path):
    """Test doctor runs successfully even with task status inconsistencies"""
    db_path = initialized_project / ".opencode" / "data" / "project.db"

    _raw_execute(
        db_path,
        """
        INSERT INTO tasks (id, title, status, priority, role, closed_at, file_path, created_at, updated_at)
        VALUES ('ENG-M-0002', 'Inconsistent task', 'COMPLETE', 'MEDIUM', 'Engineer', NULL, '.opencode/work/tasks/ENG-M-0002.md', datetime('now'), datetime('now'))
    """,
    )

    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0


def test_doctor_fix_repairs_issues(initialized_project: Path):
    """Test doctor --fix runs successfully"""
    db_path = initialized_project / ".opencode" / "data" / "project.db"

    _raw_execute(
        db_path,
        """
        INSERT INTO tasks (id, title, status, priority, role, closed_at, file_path, created_at, updated_at)
        VALUES ('ENG-M-0003', 'Fix me task', 'COMPLETE', 'MEDIUM', 'Engineer', NULL, '.opencode/work/tasks/ENG-M-0003.md', datetime('now'), datetime('now'))
    """,
    )

    result = runner.invoke(app, ["doctor", "--fix"])
    assert result.exit_code == 0
