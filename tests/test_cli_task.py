"""Integration tests for task CLI commands"""

from pathlib import Path

from site_nine.cli.main import app
from typer.testing import CliRunner

runner = CliRunner()


def test_task_commands_fail_without_init(in_temp_dir: Path):
    """Test that task commands fail if project not initialized"""
    result = runner.invoke(
        app,
        ["task", "list"],
    )

    assert result.exit_code != 0
    assert ".opencode" in result.stdout or "init" in result.stdout.lower()


def test_task_list_empty(initialized_project: Path):
    """Test listing when no tasks exist"""
    result = runner.invoke(
        app,
        ["task", "list"],
    )

    assert result.exit_code == 0, f"Command failed: {result.stdout}"
    # When empty, either shows "No tasks" message or produces no output
    # Just verify it doesn't crash


def test_task_show_invalid_id(initialized_project: Path):
    """Test showing a non-existent task"""
    result = runner.invoke(
        app,
        ["task", "show", "999999"],
    )

    assert result.exit_code != 0


def test_task_claim_invalid_id(initialized_project: Path):
    """Test claiming a non-existent task"""
    result = runner.invoke(
        app,
        ["task", "claim", "999999", "test-agent"],
    )

    assert result.exit_code != 0


def test_task_update_invalid_id(initialized_project: Path):
    """Test updating a non-existent task"""
    result = runner.invoke(
        app,
        ["task", "update", "999999", "done"],
    )

    assert result.exit_code != 0


def test_task_close_invalid_id(initialized_project: Path):
    """Test closing a non-existent task"""
    result = runner.invoke(
        app,
        ["task", "close", "999999"],
    )

    assert result.exit_code != 0
