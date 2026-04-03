"""Tests for summon CLI command"""

from pathlib import Path
from unittest.mock import MagicMock, patch

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


def test_summon_dry_run_with_daemon(initialized_project: Path):
    """Test summon with daemon flag"""
    result = runner.invoke(app, ["summon", "operator", "--daemon", "atlas", "--dry-run"])

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


@patch("site_nine.cli.summon.os.execvp")
def test_summon_calls_opencode(mock_execvp, initialized_project: Path):
    """Test that interactive summon uses os.execvp to replace the process"""
    mock_execvp.return_value = None

    result = runner.invoke(app, ["summon", "operator"])

    mock_execvp.assert_called_once()
    call_args = mock_execvp.call_args
    assert call_args[0][0] == "opencode"
    cmd_list = call_args[0][1]
    assert "opencode" in cmd_list
    assert "--prompt" in cmd_list


@patch("site_nine.cli.summon.os.execvp")
def test_summon_handles_opencode_not_found(mock_execvp, initialized_project: Path):
    """Test that summon handles missing opencode command"""
    mock_execvp.side_effect = FileNotFoundError()

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
    result = runner.invoke(app, ["summon", "operator", "--daemon", "atlas", "--model", "gpt-4", "--dry-run"])

    assert result.exit_code == 0
    output = " ".join(result.output.split())
    assert "operator" in output
    assert "atlas" in output


def test_summon_short_flags(initialized_project: Path):
    """Test summon with short flags"""
    result = runner.invoke(app, ["summon", "operator", "-d", "atlas", "-m", "gpt-4", "--dry-run"])

    assert result.exit_code == 0
    output = " ".join(result.output.split())
    assert "atlas" in output


# ---------------------------------------------------------------------------
# Desk mode tests
# ---------------------------------------------------------------------------


def test_summon_desk_dry_run_shows_desk_label(initialized_project: Path):
    """Test that --desk --dry-run shows desk-mode specific output"""
    result = runner.invoke(app, ["summon", "engineer", "--desk", "--dry-run"])

    assert result.exit_code == 0
    output = " ".join(result.output.split())
    assert "desk" in output.lower()
    assert "engineer" in output


def test_summon_desk_dry_run_uses_opencode_run(initialized_project: Path):
    """Test that --desk --dry-run shows the desk worker command"""
    result = runner.invoke(app, ["summon", "engineer", "--desk", "--dry-run"])

    assert result.exit_code == 0
    output = " ".join(result.output.split())
    # Desk mode uses desk_worker.py via uv run python
    assert "desk" in output.lower() or "worker" in output.lower() or "uv" in output


def test_summon_desk_instruction_message_contains_desk_mode(initialized_project: Path):
    """Test that --desk appends 'Mode: desk' to the instruction message"""
    result = runner.invoke(app, ["summon", "tester", "--desk", "--dry-run"])

    assert result.exit_code == 0
    output = " ".join(result.output.split())
    assert "desk" in output.lower()


def test_summon_desk_dry_run_with_daemon(initialized_project: Path):
    """Test that --desk --dry-run includes daemon in instruction"""
    result = runner.invoke(app, ["summon", "engineer", "--desk", "--daemon", "atlas", "--dry-run"])

    assert result.exit_code == 0
    output = " ".join(result.output.split())
    assert "atlas" in output
    assert "engineer" in output


def test_summon_desk_dry_run_with_task(initialized_project: Path):
    """Test that --desk --task is forbidden (conflicting flags)"""
    result = runner.invoke(app, ["summon", "engineer", "--desk", "--task", "ENG-H-0001", "--dry-run"])

    # --desk and --task are mutually exclusive
    assert result.exit_code != 0
    output = " ".join(result.output.split())
    assert "Cannot use" in output


def test_summon_desk_dry_run_with_auto_assign(initialized_project: Path):
    """Test that --desk --auto-assign is forbidden (conflicting flags)"""
    result = runner.invoke(app, ["summon", "engineer", "--desk", "--auto-assign", "--dry-run"])

    # --desk and --auto-assign are mutually exclusive
    assert result.exit_code != 0
    output = " ".join(result.output.split())
    assert "Cannot use" in output


@patch("site_nine.cli.summon.subprocess.Popen")
def test_summon_desk_spawns_popen(mock_popen, initialized_project: Path):
    """Test that --desk spawns subprocess.Popen (headless, non-blocking)"""
    mock_popen.return_value = MagicMock()

    result = runner.invoke(app, ["summon", "engineer", "--desk"])

    assert result.exit_code == 0
    mock_popen.assert_called_once()
    cmd_args = mock_popen.call_args[0][0]
    # Desk mode uses: uv run python desk_worker.py <role>
    assert cmd_args[0] == "uv"
    assert "python" in cmd_args


@patch("site_nine.cli.summon.subprocess.Popen")
def test_summon_desk_popen_includes_model(mock_popen, initialized_project: Path):
    """Test that --desk Popen call includes --model flag"""
    mock_popen.return_value = MagicMock()

    result = runner.invoke(app, ["summon", "engineer", "--desk", "--model", "github-copilot/gpt-4"])

    assert result.exit_code == 0
    mock_popen.assert_called_once()
    cmd_args = mock_popen.call_args[0][0]
    assert "--model" in cmd_args
    assert "gpt-4" in " ".join(cmd_args)


@patch("site_nine.cli.summon.subprocess.Popen")
def test_summon_desk_popen_includes_instruction(mock_popen, initialized_project: Path):
    """Test that --desk Popen call includes the role as a positional arg"""
    mock_popen.return_value = MagicMock()

    result = runner.invoke(app, ["summon", "tester", "--desk"])

    assert result.exit_code == 0
    cmd_args = mock_popen.call_args[0][0]
    # The desk worker command includes the role as an arg
    cmd_str = " ".join(str(a) for a in cmd_args)
    assert "tester" in cmd_str.lower() or "Tester" in cmd_str


@patch("site_nine.cli.summon.subprocess.Popen")
def test_summon_desk_popen_not_execvp(mock_popen, initialized_project: Path):
    """Test that --desk does NOT use os.execvp (stays non-blocking)"""
    mock_popen.return_value = MagicMock()

    with patch("site_nine.cli.summon.os.execvp") as mock_execvp:
        result = runner.invoke(app, ["summon", "engineer", "--desk"])

    assert result.exit_code == 0
    mock_popen.assert_called_once()
    mock_execvp.assert_not_called()


@patch("site_nine.cli.summon.subprocess.Popen")
def test_summon_interactive_not_popen(mock_popen, initialized_project: Path):
    """Test that interactive mode (no --desk) does NOT use subprocess.Popen"""
    with patch("site_nine.cli.summon.os.execvp") as mock_execvp:
        mock_execvp.return_value = None
        result = runner.invoke(app, ["summon", "engineer"])

    mock_popen.assert_not_called()
    mock_execvp.assert_called_once()


@patch("site_nine.cli.summon.subprocess.Popen")
def test_summon_desk_handles_file_not_found(mock_popen, initialized_project: Path):
    """Test that --desk raises CLIError when opencode is not found"""
    mock_popen.side_effect = FileNotFoundError()

    result = runner.invoke(app, ["summon", "engineer", "--desk"])

    assert result.exit_code != 0
    output = " ".join(result.output.split())
    assert "not found" in output.lower()


def test_summon_desk_conflict_auto_assign_and_task(initialized_project: Path):
    """Test that --desk still enforces --auto-assign / --task exclusion"""
    result = runner.invoke(app, ["summon", "engineer", "--desk", "--auto-assign", "--task", "ENG-H-0001"])

    assert result.exit_code != 0
    output = " ".join(result.output.split())
    assert "Cannot use both" in output
