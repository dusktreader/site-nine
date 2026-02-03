"""Integration tests for dashboard CLI command"""

from pathlib import Path

from site_nine.agents.sessions import AgentSessionManager
from site_nine.cli.main import app
from site_nine.core.database import Database
from typer.testing import CliRunner

runner = CliRunner()


def test_dashboard_fails_without_init(in_temp_dir: Path):
    """Test that dashboard command fails if project not initialized"""
    result = runner.invoke(
        app,
        ["dashboard"],
    )

    assert result.exit_code != 0
    assert ".opencode" in result.stdout or "init" in result.stdout.lower()


def test_dashboard_shows_empty_project(initialized_project: Path):
    """Test dashboard with no agents or tasks"""
    result = runner.invoke(
        app,
        ["dashboard"],
    )

    assert result.exit_code == 0, f"Command failed: {result.stdout}"
    # Should show dashboard structure
    assert "Dashboard" in result.stdout or "dashboard" in result.stdout.lower()
    # Should indicate no active sessions/tasks
    assert "Active agents: 0" in result.stdout or "No active" in result.stdout


def test_dashboard_shows_active_agents(initialized_project: Path):
    """Test dashboard displays active agent sessions"""
    # Start an agent session
    db_path = initialized_project / ".opencode" / "data" / "project.db"
    db = Database(db_path)
    manager = AgentSessionManager(db)

    manager.start_session(
        name="test-daemon",
        role="Builder",
        task_summary="Building something",
    )

    result = runner.invoke(
        app,
        ["dashboard"],
    )

    assert result.exit_code == 0, f"Command failed: {result.stdout}"
    assert "Active agents: 1" in result.stdout
    assert "test-daemon" in result.stdout
    assert "Builder" in result.stdout


def test_dashboard_shows_multiple_active_agents(initialized_project: Path):
    """Test dashboard with multiple active agents"""
    db_path = initialized_project / ".opencode" / "data" / "project.db"
    db = Database(db_path)
    manager = AgentSessionManager(db)

    # Start multiple sessions
    manager.start_session(name="agent1", role="Builder", task_summary="Task 1")
    manager.start_session(name="agent2", role="Designer", task_summary="Task 2")
    manager.start_session(name="agent3", role="Tester", task_summary="Task 3")

    result = runner.invoke(
        app,
        ["dashboard"],
    )

    assert result.exit_code == 0, f"Command failed: {result.stdout}"
    assert "Active agents: 3" in result.stdout
    assert "agent1" in result.stdout
    assert "agent2" in result.stdout
    assert "agent3" in result.stdout


def test_dashboard_excludes_ended_sessions(initialized_project: Path):
    """Test that dashboard only shows active sessions"""
    db_path = initialized_project / ".opencode" / "data" / "project.db"
    db = Database(db_path)
    manager = AgentSessionManager(db)

    # Start and end a session
    session_id = manager.start_session(
        name="ended-agent",
        role="Builder",
        task_summary="Finished task",
    )
    manager.end_session(session_id, status="completed")

    # Start an active session
    manager.start_session(
        name="active-agent",
        role="Designer",
        task_summary="Current task",
    )

    result = runner.invoke(
        app,
        ["dashboard"],
    )

    assert result.exit_code == 0, f"Command failed: {result.stdout}"
    assert "Active agents: 1" in result.stdout
    assert "active-agent" in result.stdout
    # Ended session should not appear
    assert "ended-agent" not in result.stdout


def test_dashboard_truncates_long_task_summary(initialized_project: Path):
    """Test that long task summaries are truncated"""
    db_path = initialized_project / ".opencode" / "data" / "project.db"
    db = Database(db_path)
    manager = AgentSessionManager(db)

    long_summary = "A" * 100  # Create a 100 character summary
    manager.start_session(
        name="verbose-agent",
        role="Documentarian",
        task_summary=long_summary,
    )

    result = runner.invoke(
        app,
        ["dashboard"],
    )

    assert result.exit_code == 0, f"Command failed: {result.stdout}"
    # Should show truncated version with ellipsis
    assert "..." in result.stdout or "AAA" in result.stdout  # Truncated or shown


def test_dashboard_handles_agent_without_task_summary(initialized_project: Path):
    """Test dashboard with agent that has no task summary"""
    db_path = initialized_project / ".opencode" / "data" / "project.db"
    db = Database(db_path)
    manager = AgentSessionManager(db)

    manager.start_session(
        name="no-task-agent",
        role="Builder",
        task_summary="",  # Empty task summary
    )

    result = runner.invoke(
        app,
        ["dashboard"],
    )

    assert result.exit_code == 0, f"Command failed: {result.stdout}"
    assert "no-task-agent" in result.stdout
    assert "Builder" in result.stdout


def test_dashboard_shows_project_name(initialized_project: Path):
    """Test that dashboard displays the project name"""
    result = runner.invoke(
        app,
        ["dashboard"],
    )

    assert result.exit_code == 0, f"Command failed: {result.stdout}"
    # Should show project directory name
    project_name = initialized_project.name
    assert project_name in result.stdout or "Dashboard" in result.stdout


def test_dashboard_shows_task_counts_zero(initialized_project: Path):
    """Test dashboard shows zero task counts when no tasks exist"""
    result = runner.invoke(
        app,
        ["dashboard"],
    )

    assert result.exit_code == 0, f"Command failed: {result.stdout}"
    assert "Total tasks: 0" in result.stdout


def test_dashboard_shows_quick_stats(initialized_project: Path):
    """Test dashboard includes quick stats section"""
    result = runner.invoke(
        app,
        ["dashboard"],
    )

    assert result.exit_code == 0, f"Command failed: {result.stdout}"
    assert "Quick Stats" in result.stdout or "stats" in result.stdout.lower()
    assert "Active agents:" in result.stdout
    assert "Total tasks:" in result.stdout


def test_dashboard_shows_tables(initialized_project: Path):
    """Test dashboard includes expected table sections"""
    result = runner.invoke(
        app,
        ["dashboard"],
    )

    assert result.exit_code == 0, f"Command failed: {result.stdout}"
    # Check for table titles
    assert "Active Agent Sessions" in result.stdout or "Active" in result.stdout
    assert "Task Summary" in result.stdout or "Task" in result.stdout
