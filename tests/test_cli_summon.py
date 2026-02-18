"""Tests for summon CLI command"""

from pathlib import Path
from unittest.mock import patch

from site_nine.__main__ import app
from typer.testing import CliRunner

runner = CliRunner()


def test_summon_requires_role(initialized_project: Path):
    """Test that summon requires role argument"""
    result = runner.invoke(app, ["summon"])

    assert result.exit_code != 0


def test_summon_dry_run_basic(initialized_project: Path):
    """Test summon with dry-run flag"""
    result = runner.invoke(app, ["summon", "operator", "--dry-run"])

    assert result.exit_code == 0
    output = " ".join(result.output.split())
    assert "Launching OpenCode" in output
    assert "operator" in output
    assert "Dry run" in output
    assert "opencode" in output


def test_summon_dry_run_with_persona(initialized_project: Path):
    """Test summon with persona flag"""
    result = runner.invoke(app, ["summon", "operator", "--persona", "atlas", "--dry-run"])

    assert result.exit_code == 0
    output = " ".join(result.output.split())
    assert "operator" in output
    assert "atlas" in output


def test_summon_dry_run_with_auto_assign(initialized_project: Path):
    """Test summon with auto-assign flag"""
    result = runner.invoke(app, ["summon", "operator", "--auto-assign", "--dry-run"])

    assert result.exit_code == 0
    output = " ".join(result.output.split())
    assert "auto-assign" in output


def test_summon_dry_run_with_task(initialized_project: Path):
    """Test summon with specific task"""
    result = runner.invoke(app, ["summon", "operator", "--task", "OPR-H-0001", "--dry-run"])

    assert result.exit_code == 0
    output = " ".join(result.output.split())
    assert "OPR-H-0001" in output


def test_summon_dry_run_with_model(initialized_project: Path):
    """Test summon with custom model"""
    result = runner.invoke(app, ["summon", "operator", "--model", "github-copilot/gpt-4", "--dry-run"])

    assert result.exit_code == 0
    output = " ".join(result.output.split())
    assert "gpt-4" in output


def test_summon_conflict_auto_assign_and_task(initialized_project: Path):
    """Test that auto-assign and task flags conflict"""
    result = runner.invoke(app, ["summon", "operator", "--auto-assign", "--task", "OPR-H-0001", "--dry-run"])

    assert result.exit_code != 0
    output = " ".join(result.output.split())
    assert "Cannot use both" in output


@patch("site_nine.cli.summon.subprocess.run")
def test_summon_calls_opencode(mock_run, initialized_project: Path):
    """Test that summon actually calls opencode subprocess"""
    mock_run.return_value = None

    result = runner.invoke(app, ["summon", "operator"])

    # Should have called subprocess.run
    mock_run.assert_called_once()
    call_args = mock_run.call_args[0][0]
    assert "opencode" in call_args
    assert "/summon operator" in " ".join(call_args)


@patch("site_nine.cli.summon.subprocess.run")
def test_summon_handles_subprocess_error(mock_run, initialized_project: Path):
    """Test that summon handles subprocess errors gracefully"""
    import subprocess

    mock_run.side_effect = subprocess.CalledProcessError(1, "opencode")

    result = runner.invoke(app, ["summon", "operator"])

    assert result.exit_code != 0
    output = " ".join(result.output.split())
    assert "Error" in output


@patch("site_nine.cli.summon.subprocess.run")
def test_summon_handles_opencode_not_found(mock_run, initialized_project: Path):
    """Test that summon handles missing opencode command"""
    mock_run.side_effect = FileNotFoundError()

    result = runner.invoke(app, ["summon", "operator"])

    assert result.exit_code != 0
    output = " ".join(result.output.split())
    assert "not found" in output.lower()


def test_summon_dry_run_architect(initialized_project: Path):
    """Test summon architect role"""
    result = runner.invoke(app, ["summon", "architect", "--dry-run"])

    assert result.exit_code == 0
    output = " ".join(result.output.split())
    assert "architect" in output


def test_summon_dry_run_engineer(initialized_project: Path):
    """Test summon engineer role"""
    result = runner.invoke(app, ["summon", "engineer", "--dry-run"])

    assert result.exit_code == 0
    output = " ".join(result.output.split())
    assert "engineer" in output


def test_summon_dry_run_tester(initialized_project: Path):
    """Test summon tester role"""
    result = runner.invoke(app, ["summon", "tester", "--dry-run"])

    assert result.exit_code == 0
    output = " ".join(result.output.split())
    assert "tester" in output


def test_summon_dry_run_all_flags(initialized_project: Path):
    """Test summon with all compatible flags"""
    result = runner.invoke(app, ["summon", "operator", "--persona", "atlas", "--model", "gpt-4", "--dry-run"])

    assert result.exit_code == 0
    output = " ".join(result.output.split())
    assert "operator" in output
    assert "atlas" in output


def test_summon_short_flags(initialized_project: Path):
    """Test summon with short flags"""
    result = runner.invoke(app, ["summon", "operator", "-p", "atlas", "-m", "gpt-4", "-d"])

    assert result.exit_code == 0
    output = " ".join(result.output.split())
    assert "atlas" in output
