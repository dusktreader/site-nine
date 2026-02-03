"""Integration tests for reset CLI command"""

from pathlib import Path

from s9.agents.sessions import AgentSessionManager
from s9.cli.main import app
from s9.core.database import Database
from s9.tasks.manager import TaskManager
from typer.testing import CliRunner

runner = CliRunner()


def test_reset_fails_without_init(in_temp_dir: Path):
    """Test that reset command fails if project not initialized"""
    result = runner.invoke(
        app,
        ["reset"],
        input="y\nDELETE ALL DATA\n",
    )

    assert result.exit_code != 0
    assert ".opencode" in result.stdout or "init" in result.stdout.lower()


def test_reset_requires_confirmation(initialized_project: Path):
    """Test that reset requires confirmation"""
    # Create some data so reset doesn't exit early
    db_path = initialized_project / ".opencode" / "data" / "project.db"
    db = Database(db_path)
    agent_manager = AgentSessionManager(db)
    agent_manager.start_session(name="test", role="Builder", task_summary="test")

    result = runner.invoke(
        app,
        ["reset"],
        input="n\n",  # Say no to first confirmation
    )

    assert result.exit_code == 0
    assert "Cancelled" in result.stdout

    # Verify nothing was deleted
    assert db_path.exists()
    assert len(agent_manager.list_sessions()) == 1


def test_reset_requires_exact_text_confirmation(initialized_project: Path):
    """Test that reset requires exact confirmation text"""
    # Create some data so reset doesn't exit early
    db_path = initialized_project / ".opencode" / "data" / "project.db"
    db = Database(db_path)
    agent_manager = AgentSessionManager(db)
    agent_manager.start_session(name="test", role="Builder", task_summary="test")

    result = runner.invoke(
        app,
        ["reset"],
        input="y\ndelete all data\n",  # Wrong case
    )

    assert result.exit_code == 0
    assert "Cancelled" in result.stdout
    assert "Confirmation text did not match" in result.stdout

    # Verify nothing was deleted
    assert db_path.exists()
    assert len(agent_manager.list_sessions()) == 1


def test_reset_deletes_all_data(initialized_project: Path):
    """Test that reset deletes all agent and task data"""
    # Create some data
    db_path = initialized_project / ".opencode" / "data" / "project.db"
    db = Database(db_path)
    agent_manager = AgentSessionManager(db)
    task_manager = TaskManager(db)

    # Create agents
    session_id1 = agent_manager.start_session(
        name="agent1",
        role="Builder",
        task_summary="Task 1",
    )
    session_id2 = agent_manager.start_session(
        name="agent2",
        role="Designer",
        task_summary="Task 2",
    )

    # Create tasks
    task1_id = task_manager.generate_task_id(role="Builder", priority="HIGH")
    task_manager.create_task(
        task_id=task1_id,
        title="Test task 1",
        priority="HIGH",
        role="Builder",
    )
    task2_id = task_manager.generate_task_id(role="Designer", priority="MEDIUM")
    task_manager.create_task(
        task_id=task2_id,
        title="Test task 2",
        priority="MEDIUM",
        role="Designer",
    )

    # Verify data exists
    assert len(agent_manager.list_sessions()) == 2
    assert len(task_manager.list_tasks()) == 2

    # Run reset
    result = runner.invoke(
        app,
        ["reset"],
        input="y\nDELETE ALL DATA\n",
    )

    assert result.exit_code == 0, f"Command failed: {result.stdout}"
    assert "Reset complete" in result.stdout or "reset complete" in result.stdout.lower()

    # Verify all data deleted
    assert len(agent_manager.list_sessions()) == 0
    assert len(task_manager.list_tasks()) == 0

    # Verify database still exists
    assert db_path.exists()


def test_reset_deletes_session_files(initialized_project: Path):
    """Test that reset deletes session files"""
    # Create a session
    db_path = initialized_project / ".opencode" / "data" / "project.db"
    db = Database(db_path)
    manager = AgentSessionManager(db)

    session_id = manager.start_session(
        name="test-agent",
        role="Builder",
        task_summary="test-task",
    )

    # Create a session file
    sessions_dir = initialized_project / ".opencode" / "work" / "sessions"
    session_file = sessions_dir / "2026-02-02.12:00:00.builder.test-agent.test-task.md"
    session_file.write_text("# Test session")

    # Verify file exists
    assert session_file.exists()

    # Run reset
    result = runner.invoke(
        app,
        ["reset"],
        input="y\nDELETE ALL DATA\n",
    )

    assert result.exit_code == 0

    # Verify session file deleted
    assert not session_file.exists()

    # Verify README and TEMPLATE preserved
    assert (sessions_dir / "README.md").exists()
    assert (sessions_dir / "TEMPLATE.md").exists()


def test_reset_deletes_task_files(initialized_project: Path):
    """Test that reset deletes task files"""
    # Create a task
    db_path = initialized_project / ".opencode" / "data" / "project.db"
    db = Database(db_path)
    task_manager = TaskManager(db)

    task_id = task_manager.generate_task_id(role="Builder", priority="HIGH")
    task_manager.create_task(
        task_id=task_id,
        title="Test task",
        priority="HIGH",
        role="Builder",
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


def test_reset_resets_daemon_usage_counts(initialized_project: Path):
    """Test that reset resets daemon name usage counts"""
    # Create a session to increment usage count
    db_path = initialized_project / ".opencode" / "data" / "project.db"
    db = Database(db_path)
    manager = AgentSessionManager(db)

    session_id = manager.start_session(
        name="azazel",
        role="Builder",
        task_summary="test-task",
    )

    # Verify usage count incremented
    daemon_name = db.execute_query(
        "SELECT usage_count, last_used_at FROM daemon_names WHERE name = :name", {"name": "azazel"}
    )[0]
    assert daemon_name["usage_count"] > 0
    assert daemon_name["last_used_at"] is not None

    # Run reset
    result = runner.invoke(
        app,
        ["reset"],
        input="y\nDELETE ALL DATA\n",
    )

    assert result.exit_code == 0

    # Verify usage count reset
    daemon_name = db.execute_query(
        "SELECT usage_count, last_used_at FROM daemon_names WHERE name = :name", {"name": "azazel"}
    )[0]
    assert daemon_name["usage_count"] == 0
    assert daemon_name["last_used_at"] is None


def test_reset_preserves_daemon_names_list(initialized_project: Path):
    """Test that reset preserves the daemon names list"""
    db_path = initialized_project / ".opencode" / "data" / "project.db"
    db = Database(db_path)

    # Count daemon names before reset
    names_before = db.execute_query("SELECT COUNT(*) as count FROM daemon_names")[0]["count"]
    assert names_before > 0

    # Run reset
    result = runner.invoke(
        app,
        ["reset"],
        input="y\nDELETE ALL DATA\n",
    )

    assert result.exit_code == 0

    # Verify daemon names still exist
    names_after = db.execute_query("SELECT COUNT(*) as count FROM daemon_names")[0]["count"]
    assert names_after == names_before


def test_reset_preserves_config_files(initialized_project: Path):
    """Test that reset preserves configuration files"""
    config_file = initialized_project / ".opencode" / "opencode.json"
    readme_file = initialized_project / ".opencode" / "README.md"

    # Verify files exist before
    assert config_file.exists()
    assert readme_file.exists()

    # Run reset
    result = runner.invoke(
        app,
        ["reset"],
        input="y\nDELETE ALL DATA\n",
    )

    assert result.exit_code == 0

    # Verify files still exist
    assert config_file.exists()
    assert readme_file.exists()


def test_reset_shows_counts_before_deletion(initialized_project: Path):
    """Test that reset shows what will be deleted"""
    # Create some data
    db_path = initialized_project / ".opencode" / "data" / "project.db"
    db = Database(db_path)
    agent_manager = AgentSessionManager(db)
    task_manager = TaskManager(db)

    agent_manager.start_session(name="agent1", role="Builder", task_summary="Task 1")
    task_id = task_manager.generate_task_id(role="Builder", priority="HIGH")
    task_manager.create_task(task_id=task_id, title="Test task", priority="HIGH", role="Builder")

    result = runner.invoke(
        app,
        ["reset"],
        input="n\n",  # Cancel before deletion
    )

    assert result.exit_code == 0
    # Should show counts
    assert "1 agent" in result.stdout or "agent sessions" in result.stdout
    assert "1 task" in result.stdout or "tasks" in result.stdout


def test_reset_with_yes_flag_skips_first_confirmation(initialized_project: Path):
    """Test that --yes flag skips first confirmation"""
    # Create some data so reset doesn't exit early
    db_path = initialized_project / ".opencode" / "data" / "project.db"
    db = Database(db_path)
    agent_manager = AgentSessionManager(db)
    agent_manager.start_session(name="test", role="Builder", task_summary="test")

    result = runner.invoke(
        app,
        ["reset", "--yes"],
        input="WRONG TEXT\n",  # Still need second confirmation
    )

    assert result.exit_code == 0
    assert "Cancelled" in result.stdout
    # Should not ask for first confirmation
    assert "First confirmation" not in result.stdout


def test_reset_shows_summary_after_deletion(initialized_project: Path):
    """Test that reset shows summary of what was deleted"""
    # Create some data
    db_path = initialized_project / ".opencode" / "data" / "project.db"
    db = Database(db_path)
    agent_manager = AgentSessionManager(db)

    agent_manager.start_session(name="agent1", role="Builder", task_summary="Task 1")

    result = runner.invoke(
        app,
        ["reset"],
        input="y\nDELETE ALL DATA\n",
    )

    assert result.exit_code == 0
    assert "Reset complete" in result.stdout or "reset complete" in result.stdout.lower()
    # Should show summary
    assert "Deleted:" in result.stdout


def test_reset_on_empty_project_succeeds(initialized_project: Path):
    """Test that reset on empty project succeeds gracefully"""
    result = runner.invoke(
        app,
        ["reset"],
        input="y\nDELETE ALL DATA\n",
    )

    # Should exit early since there's nothing to delete
    assert "No data to delete" in result.stdout or result.exit_code == 0


def test_reset_deletes_handoff_files(initialized_project: Path):
    """Test that reset deletes handoff files"""
    # Create database data first so reset doesn't exit early
    db_path = initialized_project / ".opencode" / "data" / "project.db"
    db = Database(db_path)
    agent_manager = AgentSessionManager(db)
    agent_manager.start_session(name="test", role="Builder", task_summary="test")

    # Create handoff directory and file
    handoffs_dir = initialized_project / ".opencode" / "work" / "sessions" / "handoffs"
    handoffs_dir.mkdir(parents=True, exist_ok=True)

    handoff_file = handoffs_dir / "2026-02-02.12:00:00.builder.tester.pending.md"
    handoff_file.write_text("# Handoff")

    assert handoff_file.exists()

    result = runner.invoke(
        app,
        ["reset"],
        input="y\nDELETE ALL DATA\n",
    )

    assert result.exit_code == 0
    assert not handoff_file.exists()


def test_reset_deletes_task_dependencies(initialized_project: Path):
    """Test that reset deletes task dependencies"""
    db_path = initialized_project / ".opencode" / "data" / "project.db"
    db = Database(db_path)
    task_manager = TaskManager(db)

    # Create tasks with dependencies
    task1_id = task_manager.generate_task_id(role="Builder", priority="HIGH")
    task_manager.create_task(task_id=task1_id, title="Task 1", priority="HIGH", role="Builder")
    task2_id = task_manager.generate_task_id(role="Builder", priority="HIGH")
    task_manager.create_task(task_id=task2_id, title="Task 2", priority="HIGH", role="Builder")

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
    deps = db.execute_query("SELECT COUNT(*) as count FROM task_dependencies")[0]["count"]
    assert deps == 0
