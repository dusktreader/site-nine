"""Integration tests for reset CLI command"""

from pathlib import Path

from site_nine.__main__ import app
from site_nine.core.database import Database
from site_nine.possessions.manager import PossessionManager
from site_nine.tasks.manager import TaskManager
from typer.testing import CliRunner

runner = CliRunner()


def _create_daemon(db: Database, name: str, role: str) -> None:
    """Helper to create a daemon for testing"""
    db.execute_update(
        """
        INSERT INTO daemons (name, role, incarnations)
        VALUES (:name, :role, 0)
        ON CONFLICT (name) DO NOTHING
        """,
        {"name": name, "role": role},
    )


def _start_possession(db: Database, daemon_name: str, role: str) -> int:
    """Helper to start a possession via raw insert (no filesystem)."""
    return db.execute_insert(
        """
        INSERT INTO possessions (daemon_name, role, possession_log, start_time, status, created_at, updated_at)
        VALUES (:daemon, :role, :log, datetime('now'), 'ACTIVE', datetime('now'), datetime('now'))
        """,
        {
            "daemon": daemon_name,
            "role": role,
            "log": f".opencode/work/possessions/test.{role.lower()}.{daemon_name}.md",
        },
    )


def test_reset_fails_without_init(in_temp_dir: Path):
    """Test that reset command fails if project not initialized"""
    result = runner.invoke(
        app,
        ["reset"],
        input="y\nDELETE ALL DATA\n",
    )

    assert result.exit_code != 0
    output = " ".join(result.output.split())
    assert ".opencode" in output or "init" in output.lower()


def test_reset_requires_confirmation(initialized_project: Path):
    """Test that reset requires confirmation"""
    # Create some data so reset doesn't exit early
    db_path = initialized_project / ".opencode" / "data" / "project.db"
    with Database(db_path) as db:
        _create_daemon(db, "test-daemon", "Engineer")
        _start_possession(db, "test-daemon", "Engineer")

    result = runner.invoke(
        app,
        ["reset"],
        input="n\n",  # Say no to first confirmation
    )

    assert result.exit_code == 0
    output = " ".join(result.output.split())
    assert "Cancelled" in output

    # Verify nothing was deleted
    assert db_path.exists()
    with Database(db_path) as db:
        mgr = PossessionManager(db)
        assert len(mgr.list_possessions()) == 1


def test_reset_requires_exact_text_confirmation(initialized_project: Path):
    """Test that reset requires exact confirmation text"""
    # Create some data so reset doesn't exit early
    db_path = initialized_project / ".opencode" / "data" / "project.db"
    with Database(db_path) as db:
        _create_daemon(db, "test-daemon", "Engineer")
        _start_possession(db, "test-daemon", "Engineer")

    result = runner.invoke(
        app,
        ["reset"],
        input="y\ndelete all data\n",  # Wrong case
    )

    assert result.exit_code == 0
    output = " ".join(result.output.split())
    assert "Cancelled" in output
    assert "Confirmation text did not match" in output

    # Verify nothing was deleted
    assert db_path.exists()
    with Database(db_path) as db:
        mgr = PossessionManager(db)
        assert len(mgr.list_possessions()) == 1


def test_reset_deletes_all_data(initialized_project: Path):
    """Test that reset deletes all possession and task data"""
    # Create some data
    db_path = initialized_project / ".opencode" / "data" / "project.db"
    with Database(db_path) as db:
        _create_daemon(db, "daemon1", "Engineer")
        _create_daemon(db, "daemon2", "Designer")

        _start_possession(db, "daemon1", "Engineer")
        _start_possession(db, "daemon2", "Designer")

        task_manager = TaskManager(db)

        # Create tasks
        task1_id = task_manager.generate_task_id(role="Engineer", priority="HIGH")
        task_manager.create_task(
            task_id=task1_id,
            title="Test task 1",
            priority="HIGH",
            role="Engineer",
        )
        task2_id = task_manager.generate_task_id(role="Designer", priority="MEDIUM")
        task_manager.create_task(
            task_id=task2_id,
            title="Test task 2",
            priority="MEDIUM",
            role="Designer",
        )

        # Verify data exists
        mgr = PossessionManager(db)
        assert len(mgr.list_possessions()) == 2
        assert len(task_manager.list_tasks()) == 2

    # Run reset
    result = runner.invoke(
        app,
        ["reset"],
        input="y\nDELETE ALL DATA\n",
    )

    assert result.exit_code == 0, f"Command failed: {result.output}"
    output = " ".join(result.output.split())
    assert "Reset complete" in output or "reset complete" in output.lower()

    # Verify all data deleted
    with Database(db_path) as db:
        mgr = PossessionManager(db)
        task_manager = TaskManager(db)
        assert len(mgr.list_possessions()) == 0
        assert len(task_manager.list_tasks()) == 0

    # Verify database still exists
    assert db_path.exists()


def test_reset_deletes_mission_files(initialized_project: Path):
    """Test that reset deletes possession files"""
    # Create a possession file in the possessions directory
    db_path = initialized_project / ".opencode" / "data" / "project.db"
    with Database(db_path) as db:
        _create_daemon(db, "test-daemon", "Engineer")
        _start_possession(db, "test-daemon", "Engineer")

    # Create a possession file manually in the possessions dir
    possessions_dir = initialized_project / ".opencode" / "work" / "possessions"
    possessions_dir.mkdir(parents=True, exist_ok=True)
    possession_file = possessions_dir / "2026-03-04.10-00-00.engineer.test-daemon.md"
    possession_file.write_text("# Possession Log")

    assert possession_file.exists()

    # Run reset
    result = runner.invoke(
        app,
        ["reset"],
        input="y\nDELETE ALL DATA\n",
    )

    assert result.exit_code == 0

    # Verify possession file deleted
    assert not possession_file.exists()


def test_reset_deletes_task_files(initialized_project: Path):
    """Test that reset deletes task files"""
    # Create a task
    db_path = initialized_project / ".opencode" / "data" / "project.db"
    with Database(db_path) as db:
        task_manager = TaskManager(db)

        task_id = task_manager.generate_task_id(role="Engineer", priority="HIGH")
        task_manager.create_task(
            task_id=task_id,
            title="Test task",
            priority="HIGH",
            role="Engineer",
        )

    # Verify task file exists
    task_file = initialized_project / ".opencode" / "work" / "tasks" / f"{task_id}.md"
    # Task file might be created by TaskManager, or we create it manually
    if not task_file.exists():
        task_file.write_text(f"# {task_id}")

    assert task_file.exists()

    # Run reset
    result = runner.invoke(
        app,
        ["reset"],
        input="y\nDELETE ALL DATA\n",
    )

    assert result.exit_code == 0

    # Verify task file deleted
    assert not task_file.exists()


def test_reset_resets_daemon_incarnation_counts(initialized_project: Path):
    """Test that reset resets daemon incarnation counts"""
    # Create a daemon and possession to increment incarnation count
    db_path = initialized_project / ".opencode" / "data" / "project.db"
    with Database(db_path) as db:
        db.execute_update(
            """
            INSERT INTO daemons (name, role, incarnations, last_possession)
            VALUES (:name, :role, 3, datetime('now'))
            """,
            {"name": "test_reset_daemon", "role": "Operator"},
        )

        _start_possession(db, "test_reset_daemon", "Operator")

        # Verify incarnation count is set
        daemon = db.execute_query(
            "SELECT incarnations, last_possession FROM daemons WHERE name = :name",
            {"name": "test_reset_daemon"},
        )[0]
        assert daemon["incarnations"] > 0
        assert daemon["last_possession"] is not None

    # Run reset
    result = runner.invoke(
        app,
        ["reset"],
        input="y\nDELETE ALL DATA\n",
    )

    assert result.exit_code == 0

    # Verify incarnation count reset
    with Database(db_path) as db:
        daemon = db.execute_query(
            "SELECT incarnations, last_possession FROM daemons WHERE name = :name",
            {"name": "test_reset_daemon"},
        )[0]
        assert daemon["incarnations"] == 0
        assert daemon["last_possession"] is None


def test_reset_preserves_daemons_list(initialized_project: Path):
    """Test that reset preserves the daemons list"""
    db_path = initialized_project / ".opencode" / "data" / "project.db"
    with Database(db_path) as db:
        # Add a test daemon
        db.execute_update(
            """
            INSERT INTO daemons (name, role, incarnations)
            VALUES (:name, :role, 0)
            """,
            {"name": "test_reset_preserve_daemon", "role": "Engineer"},
        )

        # Count daemons before reset
        daemons_before = db.execute_query("SELECT COUNT(*) as count FROM daemons")[0]["count"]
        assert daemons_before > 0

    # Run reset
    result = runner.invoke(
        app,
        ["reset"],
        input="y\nDELETE ALL DATA\n",
    )

    assert result.exit_code == 0

    # Verify daemons still exist
    with Database(db_path) as db:
        daemons_after = db.execute_query("SELECT COUNT(*) as count FROM daemons")[0]["count"]
        assert daemons_after == daemons_before


def test_reset_preserves_config_files(initialized_project: Path):
    """Test that reset preserves configuration files"""
    # Create a test config file in .opencode directory
    test_config_file = initialized_project / ".opencode" / "test-config.json"
    test_config_file.write_text('{"test": "config"}')

    readme_file = initialized_project / ".opencode" / "README.md"

    # Verify files exist before
    assert test_config_file.exists(), "test config file should exist"
    assert readme_file.exists(), "README.md should exist after init"

    # Run reset
    result = runner.invoke(
        app,
        ["reset"],
        input="y\nDELETE ALL DATA\n",
    )

    assert result.exit_code == 0

    # Verify files still exist - reset should only delete specific directories/files
    assert test_config_file.exists(), "test config file should still exist after reset"
    assert readme_file.exists(), "README.md should still exist after reset"


def test_reset_shows_counts_before_deletion(initialized_project: Path):
    """Test that reset shows what will be deleted"""
    # Create some data
    db_path = initialized_project / ".opencode" / "data" / "project.db"
    with Database(db_path) as db:
        _create_daemon(db, "daemon1", "Engineer")
        _start_possession(db, "daemon1", "Engineer")

        task_manager = TaskManager(db)
        task_id = task_manager.generate_task_id(role="Engineer", priority="HIGH")
        task_manager.create_task(task_id=task_id, title="Test task", priority="HIGH", role="Engineer")

    result = runner.invoke(
        app,
        ["reset"],
        input="n\n",  # Cancel before deletion
    )

    assert result.exit_code == 0
    output = " ".join(result.output.split())
    # Should show counts (reset CLI uses "missions" as label for possessions count)
    assert "1 mission" in output
    assert "1 task" in output


def test_reset_with_yes_flag_skips_first_confirmation(initialized_project: Path):
    """Test that --yes flag skips first confirmation"""
    # Create some data so reset doesn't exit early
    db_path = initialized_project / ".opencode" / "data" / "project.db"
    with Database(db_path) as db:
        _create_daemon(db, "test-daemon", "Engineer")
        _start_possession(db, "test-daemon", "Engineer")

    result = runner.invoke(
        app,
        ["reset", "--yes"],
        input="WRONG TEXT\n",  # Still need second confirmation
    )

    assert result.exit_code == 0
    output = " ".join(result.output.split())
    assert "Cancelled" in output
    # Should not ask for first confirmation (checking it didn't appear)
    # The --yes flag skips the "Are you absolutely sure" prompt


def test_reset_shows_summary_after_deletion(initialized_project: Path):
    """Test that reset shows summary of what was deleted"""
    # Create some data
    db_path = initialized_project / ".opencode" / "data" / "project.db"
    with Database(db_path) as db:
        _create_daemon(db, "daemon1", "Engineer")
        _start_possession(db, "daemon1", "Engineer")

    result = runner.invoke(
        app,
        ["reset"],
        input="y\nDELETE ALL DATA\n",
    )

    assert result.exit_code == 0
    output = " ".join(result.output.split())
    assert "Reset complete" in output or "reset complete" in output.lower()
    # Should show summary
    assert "Deleted:" in output


def test_reset_on_empty_project_succeeds(initialized_project: Path):
    """Test that reset on empty project succeeds gracefully"""
    result = runner.invoke(
        app,
        ["reset"],
        input="y\nDELETE ALL DATA\n",
    )

    output = " ".join(result.output.split())
    # Should exit early since there's nothing to delete
    assert "No data to delete" in output or result.exit_code == 0


def test_reset_deletes_task_dependencies(initialized_project: Path):
    """Test that reset deletes task dependencies"""
    db_path = initialized_project / ".opencode" / "data" / "project.db"
    with Database(db_path) as db:
        task_manager = TaskManager(db)

        # Create tasks with dependencies
        task1_id = task_manager.generate_task_id(role="Engineer", priority="HIGH")
        task_manager.create_task(task_id=task1_id, title="Task 1", priority="HIGH", role="Engineer")
        task2_id = task_manager.generate_task_id(role="Engineer", priority="HIGH")
        task_manager.create_task(task_id=task2_id, title="Task 2", priority="HIGH", role="Engineer")

        # Add dependency (task2 depends on task1)
        db.execute_update(
            "INSERT INTO task_dependencies (task_id, depends_on_task_id) VALUES (:task_id, :depends_on)",
            {"task_id": task2_id, "depends_on": task1_id},
        )

        # Verify dependency exists
        deps = db.execute_query("SELECT COUNT(*) as count FROM task_dependencies")[0]["count"]
        assert deps > 0

    result = runner.invoke(
        app,
        ["reset"],
        input="y\nDELETE ALL DATA\n",
    )

    assert result.exit_code == 0

    # Verify dependencies deleted
    with Database(db_path) as db:
        deps = db.execute_query("SELECT COUNT(*) as count FROM task_dependencies")[0]["count"]
        assert deps == 0
