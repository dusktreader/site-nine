"""Integration tests for check CLI command"""

import subprocess
from pathlib import Path
from unittest.mock import patch

from site_nine.agents.sessions import AgentSessionManager
from site_nine.cli.main import app
from site_nine.core.database import Database
from typer.testing import CliRunner

runner = CliRunner()


def test_check_fails_without_init(in_temp_dir: Path):
    """Test that check command fails if project not initialized"""
    result = runner.invoke(
        app,
        ["check"],
    )

    assert result.exit_code != 0
    assert ".opencode" in result.stdout or "init" in result.stdout.lower()


def test_check_passes_on_fresh_project(initialized_project: Path):
    """Test check command on a freshly initialized project"""
    result = runner.invoke(
        app,
        ["check"],
    )

    assert result.exit_code == 0, f"Command failed: {result.stdout}"
    assert "Running infrastructure checks" in result.stdout
    assert "Database file exists" in result.stdout
    assert "Database integrity check passed" in result.stdout


def test_check_detects_missing_session_files(initialized_project: Path):
    """Test that check detects missing session files"""
    # Create an agent session with a file reference
    db_path = initialized_project / ".opencode" / "data" / "project.db"
    db = Database(db_path)
    manager = AgentSessionManager(db)

    session_id = manager.start_session(
        name="test-agent",
        role="Engineer",
        task_summary="test-task",
    )

    # Get the session file path and delete it
    session = manager.get_session(session_id)
    if session:
        session_file = Path(session.session_file)
        if session_file.exists():
            session_file.unlink()

    result = runner.invoke(
        app,
        ["check"],
    )

    # Should still pass but with warnings
    assert result.exit_code == 0, f"Command failed: {result.stdout}"
    assert "missing session files" in result.stdout.lower()
    assert "non-critical" in result.stdout.lower()


def test_check_verbose_shows_details(initialized_project: Path):
    """Test check --verbose flag shows detailed output"""
    # Create an agent with missing session file
    db_path = initialized_project / ".opencode" / "data" / "project.db"
    db = Database(db_path)
    manager = AgentSessionManager(db)

    session_id = manager.start_session(
        name="test-agent",
        role="Engineer",
        task_summary="test-task",
    )

    # Delete the session file
    session = manager.get_session(session_id)
    if session:
        session_file = Path(session.session_file)
        if session_file.exists():
            session_file.unlink()

    result = runner.invoke(
        app,
        ["check", "--verbose"],
    )

    assert result.exit_code == 0, f"Command failed: {result.stdout}"
    # Verbose mode should show individual session file warnings
    assert "test-agent" in result.stdout or "session file not found" in result.stdout


def test_check_detects_missing_gitignore_patterns(initialized_project: Path):
    """Test that check detects missing .gitignore patterns"""
    # Create a .gitignore without recommended patterns
    gitignore = initialized_project / ".gitignore"
    gitignore.write_text("# Empty gitignore\n*.pyc\n")

    result = runner.invoke(
        app,
        ["check"],
    )

    assert result.exit_code == 0, f"Command failed: {result.stdout}"
    assert "gitignore" in result.stdout.lower()
    assert ".opencode/data/*.db" in result.stdout


def test_check_passes_with_correct_gitignore(initialized_project: Path):
    """Test that check passes when .gitignore has recommended patterns"""
    # Create a .gitignore with all recommended patterns
    gitignore = initialized_project / ".gitignore"
    gitignore.write_text(
        "# Database files\n.opencode/data/*.db\n.opencode/data/*.db-journal\n.opencode/data/*.db-wal\n"
    )

    result = runner.invoke(
        app,
        ["check"],
    )

    assert result.exit_code == 0, f"Command failed: {result.stdout}"
    assert "All recommended .gitignore patterns present" in result.stdout


def test_check_warns_about_no_backups(initialized_project: Path):
    """Test that check warns when no backups exist"""
    result = runner.invoke(
        app,
        ["check"],
    )

    assert result.exit_code == 0, f"Command failed: {result.stdout}"
    assert "No backup files found" in result.stdout
    assert "backup" in result.stdout.lower()


def test_check_detects_backup_files(initialized_project: Path):
    """Test that check detects existing backup files"""
    # Create a backup file
    backup_dir = initialized_project / ".opencode" / "data"
    backup_file = backup_dir / "project.db.backup"
    backup_file.write_text("backup")

    result = runner.invoke(
        app,
        ["check"],
    )

    assert result.exit_code == 0, f"Command failed: {result.stdout}"
    assert "Found 1 backup file" in result.stdout


def test_check_detects_sqlite_temp_files(initialized_project: Path):
    """Test that check detects SQLite temporary files"""
    # Create a journal file (simulating active transaction)
    db_path = initialized_project / ".opencode" / "data" / "project.db"
    journal_file = db_path.parent / f"{db_path.name}-journal"
    journal_file.write_text("temp")

    # Verify file was created
    assert journal_file.exists(), f"Journal file not created at {journal_file}"

    result = runner.invoke(
        app,
        ["check"],
    )

    assert result.exit_code == 0, f"Command failed: {result.stdout}"
    # Check should detect the temp file
    assert "SQLite temporary files" in result.stdout or "project.db-journal" in result.stdout


def test_check_summary_shows_counts(initialized_project: Path):
    """Test that check shows summary with counts"""
    result = runner.invoke(
        app,
        ["check"],
    )

    assert result.exit_code == 0, f"Command failed: {result.stdout}"
    # Should show summary table
    assert "Passed" in result.stdout
    assert "Warnings" in result.stdout
    assert "Failed" in result.stdout


def test_check_handles_missing_sqlite3_gracefully(initialized_project: Path):
    """Test that check handles missing sqlite3 command gracefully"""
    with patch("subprocess.run", side_effect=FileNotFoundError("sqlite3 not found")):
        result = runner.invoke(
            app,
            ["check"],
        )

        # Should not fail, just warn
        assert result.exit_code == 0, f"Command failed: {result.stdout}"
        assert "sqlite3 command not found" in result.stdout.lower()


def test_check_handles_sqlite3_errors_gracefully(initialized_project: Path):
    """Test that check handles sqlite3 errors gracefully"""
    with patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "sqlite3", "error")):
        result = runner.invoke(
            app,
            ["check"],
        )

        # Should not crash, but might exit with error
        assert "Failed to run integrity check" in result.stdout or "integrity check" in result.stdout.lower()


def test_check_database_integrity_check_success(initialized_project: Path):
    """Test database integrity check when database is healthy"""
    result = runner.invoke(
        app,
        ["check"],
    )

    assert result.exit_code == 0, f"Command failed: {result.stdout}"
    assert "Database integrity check passed" in result.stdout


def test_check_warns_no_gitignore(in_temp_dir: Path):
    """Test check warns when no .gitignore exists"""
    # Initialize project
    runner.invoke(
        app,
        ["init"],
        input="\n" * 10,  # Accept all defaults
    )

    # Remove .gitignore if it exists
    gitignore = in_temp_dir / ".gitignore"
    if gitignore.exists():
        gitignore.unlink()

    result = runner.invoke(
        app,
        ["check"],
    )

    assert result.exit_code == 0, f"Command failed: {result.stdout}"
    assert "No .gitignore file found" in result.stdout
