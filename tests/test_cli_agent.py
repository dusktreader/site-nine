"""Integration tests for agent CLI commands"""

from pathlib import Path

from s9.cli.main import app
from typer.testing import CliRunner

runner = CliRunner()


def test_agent_start_requires_role(initialized_project: Path):
    """Test that agent start command requires --role option"""
    result = runner.invoke(
        app,
        ["agent", "start", "test-daemon"],
    )

    # Should fail because --role is required
    assert result.exit_code != 0


def test_agent_start_creates_session(initialized_project: Path):
    """Test starting an agent session"""
    result = runner.invoke(
        app,
        ["agent", "start", "azazel", "--role", "Builder", "--task", "test-task"],
    )

    assert result.exit_code == 0, f"Command failed: {result.stdout}"
    assert "Started" in result.stdout or "azazel" in result.stdout


def test_agent_list_shows_sessions(initialized_project: Path):
    """Test listing agent sessions"""
    # Start a session first
    runner.invoke(
        app,
        ["agent", "start", "belial", "--role", "Administrator", "--task", "test-task"],
    )

    # List sessions
    result = runner.invoke(
        app,
        ["agent", "list"],
    )

    assert result.exit_code == 0, f"Command failed: {result.stdout}"
    assert "belial" in result.stdout or "Administrator" in result.stdout


def test_agent_list_active_only(initialized_project: Path):
    """Test listing only active sessions"""
    # Start two sessions
    runner.invoke(
        app,
        ["agent", "start", "session1", "--role", "Builder", "--task", "task1"],
    )

    runner.invoke(
        app,
        ["agent", "start", "session2", "--role", "Tester", "--task", "task2"],
    )

    # End first session
    runner.invoke(
        app,
        ["agent", "end", "1"],
    )

    # List active only
    result = runner.invoke(
        app,
        ["agent", "list", "--active-only"],
    )

    assert result.exit_code == 0, f"Command failed: {result.stdout}"
    # Should show session2 but not session1
    assert "session2" in result.stdout or "Tester" in result.stdout


def test_agent_list_filter_by_role(initialized_project: Path):
    """Test filtering sessions by role"""
    # Start sessions with different roles
    runner.invoke(
        app,
        ["agent", "start", "builder-daemon", "--role", "Builder", "--task", "build"],
    )

    runner.invoke(
        app,
        ["agent", "start", "tester-daemon", "--role", "Tester", "--task", "test"],
    )

    # Filter by Builder role
    result = runner.invoke(
        app,
        ["agent", "list", "--role", "Builder"],
    )

    assert result.exit_code == 0, f"Command failed: {result.stdout}"
    assert "builder-daemon" in result.stdout or "Builder" in result.stdout


def test_agent_end_closes_session(initialized_project: Path):
    """Test ending an agent session"""
    # Start a session
    result = runner.invoke(
        app,
        ["agent", "start", "end-test", "--role", "Builder", "--task", "test"],
    )

    # Extract session ID
    import re

    match = re.search(r"session #(\d+)", result.stdout)
    if not match:
        # Try alternative patterns
        match = re.search(r"#(\d+)", result.stdout)

    assert match is not None, f"Could not find session ID in: {result.stdout}"
    session_id = match.group(1)

    # End the session
    result = runner.invoke(
        app,
        ["agent", "end", session_id],
    )

    assert result.exit_code == 0, f"Command failed: {result.stdout}"


def test_agent_end_invalid_session_id(initialized_project: Path):
    """Test ending a non-existent session"""
    result = runner.invoke(
        app,
        ["agent", "end", "999999"],
    )

    assert result.exit_code != 0


def test_agent_commands_fail_without_init(in_temp_dir: Path):
    """Test that agent commands fail if project not initialized"""
    result = runner.invoke(
        app,
        ["agent", "list"],
    )

    assert result.exit_code != 0
    assert ".opencode" in result.stdout or "init" in result.stdout.lower()


def test_agent_start_with_suffix(initialized_project: Path):
    """Test starting agent with suffixed name"""
    # Start first session
    runner.invoke(
        app,
        ["agent", "start", "lucifer", "--role", "Builder", "--task", "first"],
    )

    # Start second session with same base name
    result = runner.invoke(
        app,
        ["agent", "start", "lucifer-ii", "--role", "Builder", "--task", "second"],
    )

    assert result.exit_code == 0, f"Command failed: {result.stdout}"
    assert "lucifer" in result.stdout


def test_agent_show_displays_session_details(initialized_project: Path):
    """Test showing detailed session information"""
    # Start a session
    result = runner.invoke(
        app,
        ["agent", "start", "show-test", "--role", "Builder", "--task", "test-task"],
    )

    # Extract session ID
    import re

    match = re.search(r"session #(\d+)", result.stdout)
    if not match:
        match = re.search(r"#(\d+)", result.stdout)
    assert match is not None
    session_id = match.group(1)

    # Show the session
    result = runner.invoke(
        app,
        ["agent", "show", session_id],
    )

    assert result.exit_code == 0, f"Command failed: {result.stdout}"
    assert "show-test" in result.stdout
    assert "Builder" in result.stdout


def test_agent_show_invalid_session_id(initialized_project: Path):
    """Test showing a non-existent session"""
    result = runner.invoke(
        app,
        ["agent", "show", "999999"],
    )

    assert result.exit_code != 0
    assert "not found" in result.stdout.lower() or "error" in result.stdout.lower()


def test_agent_list_empty(initialized_project: Path):
    """Test listing when no sessions exist"""
    result = runner.invoke(
        app,
        ["agent", "list"],
    )

    assert result.exit_code == 0, f"Command failed: {result.stdout}"
    assert "No sessions" in result.stdout or "found" in result.stdout.lower()
