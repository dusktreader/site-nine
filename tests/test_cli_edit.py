"""Integration tests for edit CLI command"""

from pathlib import Path
from unittest.mock import patch

from s9.cli.main import app
from typer.testing import CliRunner

runner = CliRunner()


def _get_called_file(mock_run):
    """Helper to get the file path that was passed to subprocess.run"""
    call_args = mock_run.call_args[0][0]
    # The call is [editor, filepath], so return the filepath
    return call_args[1] if len(call_args) > 1 else None


def test_edit_fails_without_init(in_temp_dir: Path):
    """Test that edit command fails if project not initialized"""
    result = runner.invoke(
        app,
        ["edit", "agents"],
    )

    assert result.exit_code != 0
    assert ".opencode" in result.stdout or "init" in result.stdout.lower()


def test_edit_agents_opens_file(initialized_project: Path):
    """Test editing AGENTS.md file"""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = None

        result = runner.invoke(
            app,
            ["edit", "agents"],
        )

        assert result.exit_code == 0, f"Command failed: {result.stdout}"
        assert "Opening AGENTS.md" in result.stdout
        assert "Done editing" in result.stdout

        # Verify the editor was called with AGENTS.md
        mock_run.assert_called_once()
        called_file = _get_called_file(mock_run)
        assert called_file and "AGENTS.md" in called_file


def test_edit_commits_opens_file(initialized_project: Path):
    """Test editing COMMIT_GUIDELINES.md file"""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = None

        result = runner.invoke(
            app,
            ["edit", "commits"],
        )

        assert result.exit_code == 0, f"Command failed: {result.stdout}"
        assert "Opening COMMIT_GUIDELINES.md" in result.stdout

        mock_run.assert_called_once()
        called_file = _get_called_file(mock_run)
        assert called_file and "COMMIT_GUIDELINES.md" in called_file


def test_edit_workflows_opens_file(initialized_project: Path):
    """Test editing WORKFLOWS.md file"""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = None

        result = runner.invoke(
            app,
            ["edit", "workflows"],
        )

        assert result.exit_code == 0, f"Command failed: {result.stdout}"
        assert "Opening WORKFLOWS.md" in result.stdout

        mock_run.assert_called_once()
        called_file = _get_called_file(mock_run)
        assert called_file and "WORKFLOWS.md" in called_file


def test_edit_troubleshooting_opens_file(initialized_project: Path):
    """Test editing TROUBLESHOOTING.md file"""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = None

        result = runner.invoke(
            app,
            ["edit", "troubleshooting"],
        )

        assert result.exit_code == 0, f"Command failed: {result.stdout}"
        assert "Opening TROUBLESHOOTING.md" in result.stdout

        mock_run.assert_called_once()
        called_file = _get_called_file(mock_run)
        assert called_file and "TROUBLESHOOTING.md" in called_file


def test_edit_task_workflow_opens_file(initialized_project: Path):
    """Test editing TASK_WORKFLOW.md file"""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = None

        result = runner.invoke(
            app,
            ["edit", "task-workflow"],
        )

        assert result.exit_code == 0, f"Command failed: {result.stdout}"
        assert "Opening TASK_WORKFLOW.md" in result.stdout

        mock_run.assert_called_once()
        called_file = _get_called_file(mock_run)
        assert called_file and "TASK_WORKFLOW.md" in called_file


def test_edit_project_status_opens_file(initialized_project: Path):
    """Test editing PROJECT_STATUS.md file"""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = None

        result = runner.invoke(
            app,
            ["edit", "project-status"],
        )

        assert result.exit_code == 0, f"Command failed: {result.stdout}"
        assert "Opening PROJECT_STATUS.md" in result.stdout

        mock_run.assert_called_once()
        called_file = _get_called_file(mock_run)
        assert called_file and "PROJECT_STATUS.md" in called_file


def test_edit_architecture_opens_file(initialized_project: Path):
    """Test editing architecture.md file"""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = None

        result = runner.invoke(
            app,
            ["edit", "architecture"],
        )

        assert result.exit_code == 0, f"Command failed: {result.stdout}"
        assert "Opening architecture.md" in result.stdout

        mock_run.assert_called_once()
        called_file = _get_called_file(mock_run)
        assert called_file and "architecture.md" in called_file


def test_edit_design_philosophy_opens_file(initialized_project: Path):
    """Test editing design-philosophy.md file"""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = None

        result = runner.invoke(
            app,
            ["edit", "design-philosophy"],
        )

        assert result.exit_code == 0, f"Command failed: {result.stdout}"
        assert "Opening design-philosophy.md" in result.stdout

        mock_run.assert_called_once()
        called_file = _get_called_file(mock_run)
        assert called_file and "design-philosophy.md" in called_file


def test_edit_opencode_config_opens_file(initialized_project: Path):
    """Test editing opencode.json file"""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = None

        result = runner.invoke(
            app,
            ["edit", "opencode-config"],
        )

        assert result.exit_code == 0, f"Command failed: {result.stdout}"
        assert "Opening opencode.json" in result.stdout

        mock_run.assert_called_once()
        called_file = _get_called_file(mock_run)
        assert called_file and "opencode.json" in called_file


def test_edit_uses_visual_env_var(initialized_project: Path):
    """Test that edit uses VISUAL environment variable if set"""
    with patch("subprocess.run") as mock_run, patch.dict("os.environ", {"VISUAL": "emacs"}):
        mock_run.return_value = None

        result = runner.invoke(
            app,
            ["edit", "agents"],
        )

        assert result.exit_code == 0
        call_args = mock_run.call_args[0][0]
        assert call_args[0] == "emacs"


def test_edit_uses_editor_env_var(initialized_project: Path):
    """Test that edit uses EDITOR environment variable if VISUAL not set"""
    with patch("subprocess.run") as mock_run, patch.dict("os.environ", {"EDITOR": "nano"}, clear=True):
        mock_run.return_value = None

        result = runner.invoke(
            app,
            ["edit", "agents"],
        )

        assert result.exit_code == 0
        call_args = mock_run.call_args[0][0]
        assert call_args[0] == "nano"


def test_edit_defaults_to_vim(initialized_project: Path):
    """Test that edit defaults to vim if no env vars set"""
    with patch("subprocess.run") as mock_run, patch.dict("os.environ", {}, clear=True):
        mock_run.return_value = None

        result = runner.invoke(
            app,
            ["edit", "agents"],
        )

        assert result.exit_code == 0
        call_args = mock_run.call_args[0][0]
        assert call_args[0] == "vim"


def test_edit_handles_editor_not_found(initialized_project: Path):
    """Test that edit handles missing editor gracefully"""
    with patch("subprocess.run", side_effect=FileNotFoundError("Editor not found")):
        result = runner.invoke(
            app,
            ["edit", "agents"],
        )

        assert result.exit_code != 0
        assert "not found" in result.stdout.lower()
        assert "EDITOR" in result.stdout or "VISUAL" in result.stdout


def test_edit_handles_editor_failure(initialized_project: Path):
    """Test that edit handles editor subprocess errors"""
    import subprocess

    with patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "vim", "error")):
        result = runner.invoke(
            app,
            ["edit", "agents"],
        )

        assert result.exit_code != 0
        assert "Failed to open editor" in result.stdout


def test_edit_fails_when_file_missing(initialized_project: Path):
    """Test that edit fails gracefully when file doesn't exist"""
    # Delete the AGENTS.md file
    agents_file = initialized_project / ".opencode" / "docs" / "guides" / "AGENTS.md"
    if agents_file.exists():
        agents_file.unlink()

    result = runner.invoke(
        app,
        ["edit", "agents"],
    )

    assert result.exit_code != 0
    assert "not found" in result.stdout


def test_edit_help_shows_all_subcommands(initialized_project: Path):
    """Test that edit --help shows all available subcommands"""
    result = runner.invoke(
        app,
        ["edit", "--help"],
    )

    assert result.exit_code == 0
    assert "agents" in result.stdout
    assert "commits" in result.stdout
    assert "workflows" in result.stdout
    assert "troubleshooting" in result.stdout
    assert "task-workflow" in result.stdout
    assert "project-status" in result.stdout
    assert "architecture" in result.stdout
    assert "design-philosophy" in result.stdout
    assert "opencode-config" in result.stdout
