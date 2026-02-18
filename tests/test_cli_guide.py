"""Integration tests for guide CLI command"""

from pathlib import Path
from unittest.mock import patch

from site_nine.__main__ import app
from typer.testing import CliRunner

runner = CliRunner()


def _get_called_file(mock_run):
    """Helper to get the file path that was passed to subprocess.run"""
    call_args = mock_run.call_args[0][0]
    return call_args[1] if len(call_args) > 1 else None


# --- list command ---


def test_guide_list_shows_available(initialized_project: Path):
    """Test listing available guides"""
    result = runner.invoke(app, ["guide", "list"])

    assert result.exit_code == 0, f"Command failed: {result.output}"
    output = " ".join(result.output.split())
    assert "Available Guides" in output
    assert "testing" in output
    assert "commit-guidelines" in output


def test_guide_list_fails_without_init(in_temp_dir: Path):
    """Test that guide list fails if project not initialized"""
    result = runner.invoke(app, ["guide", "list"])

    assert result.exit_code != 0
    assert ".opencode" in result.output or "init" in result.output.lower()


def test_guide_list_fails_when_guides_dir_missing(initialized_project: Path):
    """Test that guide list fails when the guides directory is missing"""
    import shutil

    guides_dir = initialized_project / ".opencode" / "docs" / "guides"
    if guides_dir.exists():
        shutil.rmtree(guides_dir)

    result = runner.invoke(app, ["guide", "list"])

    assert result.exit_code != 0
    output = " ".join(result.output.split())
    assert "No guides found" in output


# --- edit command: happy path ---


def test_guide_edit_opens_file(initialized_project: Path):
    """Test editing a guide file by stem name"""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = None

        result = runner.invoke(app, ["guide", "edit", "testing"])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Opening testing.md" in result.output
        assert "Done editing" in result.output

        mock_run.assert_called_once()
        called_file = _get_called_file(mock_run)
        assert called_file and "testing.md" in called_file


def test_guide_edit_opens_hyphenated_name(initialized_project: Path):
    """Test editing a guide with a hyphenated name"""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = None

        result = runner.invoke(app, ["guide", "edit", "commit-guidelines"])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Opening commit-guidelines.md" in result.output

        mock_run.assert_called_once()
        called_file = _get_called_file(mock_run)
        assert called_file and "commit-guidelines.md" in called_file


def test_guide_edit_opens_code_review(initialized_project: Path):
    """Test editing code-review guide"""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = None

        result = runner.invoke(app, ["guide", "edit", "code-review"])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Opening code-review.md" in result.output

        mock_run.assert_called_once()
        called_file = _get_called_file(mock_run)
        assert called_file and "code-review.md" in called_file


def test_guide_edit_opens_dynamically_created(initialized_project: Path):
    """Test editing a dynamically-created guide"""
    guide_file = initialized_project / ".opencode" / "docs" / "guides" / "custom-guide.md"
    guide_file.write_text("# Custom Guide\n")

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = None

        result = runner.invoke(app, ["guide", "edit", "custom-guide"])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Opening custom-guide.md" in result.output


# --- edit command: error paths ---


def test_guide_edit_fails_without_init(in_temp_dir: Path):
    """Test that guide edit fails if project not initialized"""
    result = runner.invoke(app, ["guide", "edit", "testing"])

    assert result.exit_code != 0
    assert ".opencode" in result.output or "init" in result.output.lower()


def test_guide_edit_fails_when_not_found(initialized_project: Path):
    """Test that guide edit fails when guide doesn't exist"""
    result = runner.invoke(app, ["guide", "edit", "nonexistent"])

    assert result.exit_code != 0
    output = " ".join(result.output.split())
    assert "not found" in output.lower()
    assert "Available guides:" in output


def test_guide_edit_shows_available_on_not_found(initialized_project: Path):
    """Test that the error message includes available guide names"""
    result = runner.invoke(app, ["guide", "edit", "nonexistent"])

    assert result.exit_code != 0
    output = " ".join(result.output.split())
    assert "testing" in output
    assert "commit-guidelines" in output


def test_guide_edit_fails_when_file_deleted(initialized_project: Path):
    """Test that guide edit fails when the specific guide file has been deleted"""
    target = initialized_project / ".opencode" / "docs" / "guides" / "testing.md"
    if target.exists():
        target.unlink()

    result = runner.invoke(app, ["guide", "edit", "testing"])

    assert result.exit_code != 0
    output = " ".join(result.output.split())
    assert "not found" in output.lower()


def test_guide_edit_fails_when_guides_dir_missing(initialized_project: Path):
    """Test that guide edit fails when the entire guides directory is missing"""
    import shutil

    guides_dir = initialized_project / ".opencode" / "docs" / "guides"
    if guides_dir.exists():
        shutil.rmtree(guides_dir)

    result = runner.invoke(app, ["guide", "edit", "testing"])

    assert result.exit_code != 0
    output = " ".join(result.output.split())
    assert "not found" in output.lower()


# --- edit command: editor behavior ---


def test_guide_edit_uses_visual_env_var(initialized_project: Path):
    """Test that edit uses VISUAL environment variable if set"""
    with patch("subprocess.run") as mock_run, patch.dict("os.environ", {"VISUAL": "emacs"}):
        mock_run.return_value = None

        result = runner.invoke(app, ["guide", "edit", "testing"])

        assert result.exit_code == 0
        call_args = mock_run.call_args[0][0]
        assert call_args[0] == "emacs"


def test_guide_edit_uses_editor_env_var(initialized_project: Path):
    """Test that edit uses EDITOR environment variable if VISUAL not set"""
    with patch("subprocess.run") as mock_run, patch.dict("os.environ", {"EDITOR": "nano"}, clear=True):
        mock_run.return_value = None

        result = runner.invoke(app, ["guide", "edit", "testing"])

        assert result.exit_code == 0
        call_args = mock_run.call_args[0][0]
        assert call_args[0] == "nano"


def test_guide_edit_defaults_to_vim(initialized_project: Path):
    """Test that edit defaults to vim if no env vars set"""
    with patch("subprocess.run") as mock_run, patch.dict("os.environ", {}, clear=True):
        mock_run.return_value = None

        result = runner.invoke(app, ["guide", "edit", "testing"])

        assert result.exit_code == 0
        call_args = mock_run.call_args[0][0]
        assert call_args[0] == "vim"


def test_guide_edit_handles_editor_not_found(initialized_project: Path):
    """Test that edit handles missing editor gracefully"""
    with patch("subprocess.run", side_effect=FileNotFoundError("Editor not found")):
        result = runner.invoke(app, ["guide", "edit", "testing"])

        assert result.exit_code != 0
        output = " ".join(result.output.split())
        assert "not found" in output.lower()
        assert "EDITOR" in output or "VISUAL" in output


def test_guide_edit_handles_editor_failure(initialized_project: Path):
    """Test that edit handles editor subprocess errors"""
    import subprocess

    with patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "vim", "error")):
        result = runner.invoke(app, ["guide", "edit", "testing"])

        assert result.exit_code != 0
        output = " ".join(result.output.split())
        assert "Failed to open editor" in output


# --- help ---


def test_guide_help_shows_subcommands():
    """Test that guide --help shows available subcommands"""
    result = runner.invoke(app, ["guide", "--help"])

    assert result.exit_code == 0
    assert "list" in result.stdout
    assert "edit" in result.stdout
